"""
Módulo de Gestión de Almacenamiento y Políticas de Retención
Supervisa el espacio disponible en disco y aplica políticas de rotación de copias
protegiendo estrictamente la última copia de seguridad válida para evitar pérdida de datos.
"""
import os
import time
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("BackupApp.Retention")


class StorageManager:
    """
    Controlador de espacio en disco y retención segura de copias de seguridad.
    """

    @staticmethod
    def get_disk_space_info(target_folder: str) -> Dict[str, Any]:
        """
        Obtiene el espacio total, usado y libre del disco donde reside la carpeta de destino.
        """
        try:
            folder_path = os.path.abspath(target_folder)
            os.makedirs(folder_path, exist_ok=True)
            total, used, free = shutil.disk_usage(folder_path)

            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            percent_free = (free / total) * 100 if total > 0 else 0

            return {
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_gb": round(total_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_free": round(percent_free, 1),
                "is_low_space": free_gb < 5.0 or percent_free < 10.0  # Alerta si hay menos de 5 GB o menos del 10%
            }
        except Exception as e:
            logger.error("Error al consultar espacio en disco para %s: %s", target_folder, str(e))
            return {
                "total_bytes": 0, "used_bytes": 0, "free_bytes": 0,
                "total_gb": 0.0, "free_gb": 0.0, "percent_free": 0.0,
                "is_low_space": False, "error": str(e)
            }

    @staticmethod
    def apply_retention_policy(target_folder: str,
                               database_name: str,
                               retention_days: int = 15,
                               min_copies_to_keep: int = 2) -> List[Dict[str, Any]]:
        """
        Aplica la política de retención:
        1. Identifica únicamente archivos de backup de la base de datos especificada (.bak, .trn, .diff).
        2. Ordena los archivos del más reciente al más antiguo.
        3. NUNCA elimina las últimas `min_copies_to_keep` copias, sin importar su antigüedad.
        4. Solo elimina archivos que superen los `retention_days` y no violen la regla de copias mínimas.
        """
        if not os.path.exists(target_folder):
            logger.warning("La carpeta de destino no existe para retención: %s", target_folder)
            return []

        if retention_days <= 0:
            logger.info("Retención deshabilitada (retention_days <= 0)")
            return []

        now = time.time()
        max_age_seconds = retention_days * 86400  # 24 * 3600

        # Encontrar archivos asociados a la base de datos
        db_lower = database_name.lower()
        backup_files: List[Tuple[str, float, int]] = []  # (filepath, mtime, size)

        folder = Path(target_folder)
        for entry in folder.iterdir():
            if entry.is_file() and entry.suffix.lower() in [".bak", ".trn", ".diff"]:
                # Comprobar si el nombre del archivo contiene el nombre de la BD para no tocar otros backups
                if db_lower in entry.name.lower():
                    try:
                        stat = entry.stat()
                        backup_files.append((str(entry.resolve()), stat.st_mtime, stat.st_size))
                    except Exception as e:
                        logger.warning("No se pudo leer metadatos de %s: %s", entry.name, str(e))

        # Ordenar por fecha de modificación descendente (más nuevos primero)
        backup_files.sort(key=lambda x: x[1], reverse=True)

        total_found = len(backup_files)
        logger.info("Encontrados %d archivos de backup para '%s' en %s", total_found, database_name, target_folder)

        deleted_records = []

        # Proteger siempre al menos `min_copies_to_keep` copias
        # Por seguridad nacional y empresarial, al menos 1 copia jamás se borra
        safe_copies_count = max(1, min_copies_to_keep)

        # Candidatos para evaluación de borrado: los que queden después de proteger las N copias más recientes
        candidates = backup_files[safe_copies_count:]

        for filepath, mtime, size in candidates:
            age_seconds = now - mtime
            if age_seconds > max_age_seconds:
                try:
                    os.remove(filepath)
                    age_days = round(age_seconds / 86400, 1)
                    logger.info("Copia de seguridad antigua eliminada por retención (>%d días): %s (Antigüedad: %s días)",
                                retention_days, filepath, age_days)
                    deleted_records.append({
                        "file": filepath,
                        "age_days": age_days,
                        "size_bytes": size,
                        "status": "DELETED"
                    })
                except Exception as ex:
                    logger.error("No se pudo eliminar el archivo de retención %s: %s", filepath, str(ex))

        return deleted_records
