"""
Módulo de Verificación de Integridad y Hash Criptográfico
Calcula hashes SHA-256 por bloques para no saturar memoria RAM con backups grandes,
y valida la coherencia física de los archivos.
"""
import os
import hashlib
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger("BackupApp.Integrity")


class IntegrityVerifier:
    """
    Verificador de integridad de archivos de respaldo.
    """

    @staticmethod
    def calculate_sha256(filepath: str, chunk_size: int = 1024 * 1024) -> str:
        """
        Calcula el hash SHA-256 de un archivo en bloques de 1MB para eficiencia y bajo consumo de memoria.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def check_file_health(filepath: str, min_expected_bytes: int = 1024) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verifica que el archivo exista en disco, no esté vacío y no tenga bloqueos exclusivos de escritura.
        """
        if not os.path.exists(filepath):
            return False, f"El archivo no existe: {filepath}", {}

        try:
            stat_info = os.stat(filepath)
            size_bytes = stat_info.st_size

            if size_bytes < min_expected_bytes:
                return False, f"El archivo tiene un tamaño anómalo ({size_bytes} bytes). Podría estar incompleto o corrupto.", {
                    "size_bytes": size_bytes
                }

            # Probar apertura de lectura
            with open(filepath, "rb") as f:
                f.read(512)

            return True, "Archivo verificado correctamente en el sistema de archivos.", {
                "size_bytes": size_bytes,
                "created_time": stat_info.st_ctime,
                "modified_time": stat_info.st_mtime
            }
        except PermissionError:
            return False, f"Permiso denegado al acceder al archivo: {filepath}", {}
        except Exception as e:
            return False, f"Error al verificar estado del archivo: {str(e)}", {}
