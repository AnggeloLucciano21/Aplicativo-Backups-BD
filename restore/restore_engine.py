"""
Módulo del Motor de Restauración (Restore Engine)
Controla la inspección previa de metadatos, verificación y restauración asistida
con protecciones estrictas contra la sobrescritura no autorizada de bases de datos.
"""
import os
import time
import getpass
import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Any, Callable, Optional, List

from core.models import ConnectionConfig, OperationRecord
from database.repositories import HistoryRepository
from connectors.sqlserver_connector import SQLServerConnector
from security.credentials_manager import CredentialsManager

logger = logging.getLogger("BackupApp.RestoreEngine")


class RestoreEngine:
    """
    Orquestador de procesos de restauración de bases de datos.
    """

    def __init__(self, history_repo: Optional[HistoryRepository] = None):
        self.history_repo = history_repo or HistoryRepository()

    def inspect_backup(self, conn_config: ConnectionConfig, backup_path: str) -> Dict[str, Any]:
        """
        Inspecciona el archivo de backup sin alterarlo, extrayendo cabeceras y archivos lógicos.
        """
        password = None
        if conn_config.auth_type.lower() == "sql":
            password = CredentialsManager.get_password(conn_config.name, conn_config.username)

        connector = SQLServerConnector(conn_config, password=password)

        headers = connector.get_backup_headers(backup_path)
        if "error" in headers:
            return {"success": False, "error": headers["error"]}

        filelist = connector.get_backup_filelist(backup_path)
        v_ok, v_msg = connector.verify_backup(backup_path)

        return {
            "success": True,
            "headers": headers,
            "filelist": filelist,
            "verify_only_passed": v_ok,
            "verify_only_message": v_msg
        }

    def run_restore(self,
                    conn_config: ConnectionConfig,
                    backup_path: str,
                    target_database: str,
                    replace_existing: bool = False,
                    progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str, OperationRecord]:
        """
        Ejecuta la restauración de la base de datos de manera segura y controlada.
        """
        start_time = time.time()
        start_iso = datetime.now().isoformat()
        current_user = getpass.getuser()

        record = OperationRecord(
            connection_name=conn_config.name,
            database_name=target_database,
            operation_type="RESTORE",
            status="IN_PROGRESS",
            started_at=start_iso,
            destination_path=backup_path,
            user_system=current_user
        )
        record.id = self.history_repo.add_record(record)

        if not os.path.exists(backup_path):
            err_msg = f"El archivo de backup no existe: {backup_path}"
            return self._finalize_failure(record, err_msg, start_time)

        try:
            record.file_size_bytes = os.path.getsize(backup_path)
        except Exception:
            pass

        password = None
        if conn_config.auth_type.lower() == "sql":
            password = CredentialsManager.get_password(conn_config.name, conn_config.username)

        connector = SQLServerConnector(conn_config, password=password)

        if progress_callback:
            progress_callback(15, f"Iniciando proceso de restauración hacia [{target_database}]...")

        success, message = connector.execute_restore(
            backup_path=backup_path,
            target_database=target_database,
            replace_existing=replace_existing,
            progress_callback=progress_callback
        )

        if not success:
            return self._finalize_failure(record, message, start_time)

        end_time = time.time()
        record.status = "SUCCESS"
        record.finished_at = datetime.now().isoformat()
        record.duration_seconds = round(end_time - start_time, 2)
        record.details_json = json.dumps({
            "target_database": target_database,
            "replaced_existing": replace_existing,
            "source_file": backup_path
        })
        self.history_repo.update_record(record)

        if progress_callback:
            progress_callback(100, f"Restauración de [{target_database}] completada exitosamente en {record.duration_formatted}")

        return True, f"Base de datos '{target_database}' restaurada exitosamente.", record

    def _finalize_failure(self, record: OperationRecord, error_msg: str, start_time: float) -> Tuple[bool, str, OperationRecord]:
        end_time = time.time()
        record.status = "FAILED"
        record.finished_at = datetime.now().isoformat()
        record.duration_seconds = round(end_time - start_time, 2)
        record.error_message = error_msg
        self.history_repo.update_record(record)
        logger.error("Operación de restauración fallida: %s", error_msg)
        return False, error_msg, record
