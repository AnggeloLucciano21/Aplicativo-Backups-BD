"""
Módulo del Motor de Copias de Seguridad (Backup Engine)
Coordina la ejecución de respaldos de extremo a extremo:
validación de espacio, ejecución nativa en SQL Server, verificación,
cálculo criptográfico SHA-256, rotación por retención y registro en auditoría.
"""
import os
import time
import getpass
import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Any, Callable, Optional

from core.models import ConnectionConfig, BackupTaskConfig, OperationRecord
from database.repositories import HistoryRepository
from connectors.factory import ConnectorFactory
from security.credentials_manager import CredentialsManager
from backup.integrity import IntegrityVerifier
from backup.retention import StorageManager

logger = logging.getLogger("BackupApp.BackupEngine")


class BackupEngine:
    """
    Orquestador integral de copias de seguridad.
    """

    def __init__(self, history_repo: Optional[HistoryRepository] = None):
        self.history_repo = history_repo or HistoryRepository()

    @staticmethod
    def generate_filename(pattern: str, database_name: str, backup_type: str) -> str:
        """
        Genera el nombre del archivo de backup sustituyendo variables de plantilla:
        {db}, {type}, {date}, {time}.
        """
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")

        filename = pattern.replace("{db}", database_name)
        filename = filename.replace("{type}", backup_type.lower())
        filename = filename.replace("{date}", date_str)
        filename = filename.replace("{time}", time_str)

        if not filename.endswith(".bak") and backup_type.upper() == "FULL":
            filename += ".bak"

        return filename

    def run_backup(self,
                   conn_config: ConnectionConfig,
                   database_name: str,
                   backup_type: str,
                   destination_folder: str,
                   file_pattern: str = "{db}_{type}_{date}_{time}.bak",
                   compression: bool = True,
                   checksum: bool = True,
                   verify_after: bool = True,
                   retention_days: int = 15,
                   min_copies_to_keep: int = 2,
                   progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str, OperationRecord]:
        """
        Ejecuta el ciclo de vida completo de un respaldo con trazabilidad estricta.
        """
        start_time = time.time()
        start_iso = datetime.now().isoformat()
        current_user = getpass.getuser()

        record = OperationRecord(
            connection_name=conn_config.name,
            database_name=database_name,
            operation_type=f"BACKUP_{backup_type.upper()}",
            status="IN_PROGRESS",
            started_at=start_iso,
            user_system=current_user
        )
        record_id = self.history_repo.add_record(record)
        record.id = record_id

        # 1. Validar directorio y espacio en disco
        try:
            os.makedirs(destination_folder, exist_ok=True)
            space_info = StorageManager.get_disk_space_info(destination_folder)
            if space_info.get("is_low_space"):
                logger.warning("Espacio en disco bajo en %s: %.2f GB libres", destination_folder, space_info.get("free_gb", 0))
                if progress_callback:
                    progress_callback(5, f"Advertencia: Espacio en disco bajo ({space_info.get('free_gb', 0)} GB libres)")
        except Exception as e:
            err_msg = f"No se pudo acceder o crear la carpeta de destino: {str(e)}"
            return self._finalize_failure(record, err_msg, start_time)

        filename = self.generate_filename(file_pattern, database_name, backup_type)
        destination_path = os.path.join(destination_folder, filename)
        record.destination_path = destination_path

        # 2. Conectar al motor de base de datos
        password = None
        if conn_config.auth_type.lower() != "windows" or conn_config.engine.lower() != "sqlserver":
            password = CredentialsManager.get_password(conn_config.name, conn_config.username)

        connector = ConnectorFactory.create_connector(conn_config, password=password)

        if progress_callback:
            progress_callback(10, f"Iniciando copia de seguridad {backup_type} en '{database_name}'...")

        # 3. Ejecutar backup nativo
        success, message = connector.execute_backup(
            database_name=database_name,
            backup_type=backup_type,
            destination_path=destination_path,
            compression=compression,
            checksum=checksum,
            progress_callback=progress_callback
        )

        if not success:
            return self._finalize_failure(record, f"Error del motor: {message}", start_time)

        # 4. Validar integridad física del archivo
        if progress_callback:
            progress_callback(75, "Validando integridad física del archivo...")

        is_healthy, health_msg, health_data = IntegrityVerifier.check_file_health(destination_path)
        if not is_healthy:
            return self._finalize_failure(record, f"Fallo de salud del archivo: {health_msg}", start_time)

        file_size = health_data.get("size_bytes", 0)
        record.file_size_bytes = file_size

        # 5. Verificación opcional con RESTORE VERIFYONLY
        verification_passed = False
        if verify_after:
            if progress_callback:
                progress_callback(85, "Ejecutando verificación con el motor (RESTORE VERIFYONLY)...")
            v_ok, v_msg = connector.verify_backup(destination_path)
            if not v_ok:
                return self._finalize_failure(record, f"El backup falló la verificación RESTORE VERIFYONLY: {v_msg}", start_time)
            verification_passed = True

        # 6. Cálculo de hash criptográfico SHA-256
        if progress_callback:
            progress_callback(92, "Calculando firma digital SHA-256...")
        try:
            sha256 = IntegrityVerifier.calculate_sha256(destination_path)
            record.sha256_hash = sha256
        except Exception as e:
            logger.warning("No se pudo calcular SHA-256: %s", str(e))
            record.sha256_hash = "ERROR_CALCULATING"

        # 7. Aplicar política de retención
        if progress_callback:
            progress_callback(97, "Aplicando políticas de retención...")
        try:
            deleted = StorageManager.apply_retention_policy(
                target_folder=destination_folder,
                database_name=database_name,
                retention_days=retention_days,
                min_copies_to_keep=min_copies_to_keep
            )
            details = {
                "verified": verification_passed,
                "retention_deleted_count": len(deleted),
                "sha256": record.sha256_hash
            }
            record.details_json = json.dumps(details)
        except Exception as ex_ret:
            logger.error("Error aplicando retención: %s", str(ex_ret))

        # 8. Finalizar con éxito
        end_time = time.time()
        record.finished_at = datetime.now().isoformat()
        record.duration_seconds = round(end_time - start_time, 2)
        record.status = "SUCCESS"
        self.history_repo.update_record(record)

        if progress_callback:
            progress_callback(100, f"Backup completado con éxito en {record.duration_formatted} ({record.file_size_formatted})")

        return True, "Backup completado y verificado exitosamente.", record

    def _finalize_failure(self, record: OperationRecord, error_msg: str, start_time: float) -> Tuple[bool, str, OperationRecord]:
        """Registra el fallo de la operación en el historial y devuelve el estado."""
        end_time = time.time()
        record.status = "FAILED"
        record.finished_at = datetime.now().isoformat()
        record.duration_seconds = round(end_time - start_time, 2)
        record.error_message = error_msg
        self.history_repo.update_record(record)
        logger.error("Operación de backup fallida: %s", error_msg)
        return False, error_msg, record
