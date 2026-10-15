"""
Módulo de Auditoría y Logging Seguro
Configura el sistema de logging con rotación y filtros de sanitización
para evitar que contraseñas o datos sensibles aparezcan en los registros.
"""
import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Patrones para enmascarar contraseñas en logs
PASSWORD_PATTERNS = [
    (re.compile(r'(?i)(password|pwd|secret)\s*=\s*([^;,\s]+)'), r'\1=********'),
    (re.compile(r'(?i)(password|pwd|secret)\s*:\s*([^\s]+)'), r'\1: ********'),
]


class SensitiveDataFilter(logging.Filter):
    """Filtro de logging que anonimiza automáticamente secretos y contraseñas."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, repl in PASSWORD_PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
        return True


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Configura el logger principal con salida a consola y archivo rotativo.
    """
    logger = logging.getLogger("BackupApp")
    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    sensitive_filter = SensitiveDataFilter()

    # Consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    logger.addHandler(console_handler)

    # Archivo de log rotativo
    try:
        local_app_data = os.environ.get("LOCALAPPDATA")
        log_dir = Path(local_app_data) / "AplicativoBackupsBD" / "logs" if local_app_data else Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "audit.log"

        file_handler = RotatingFileHandler(
            str(log_file),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("No se pudo configurar archivo de log rotativo: %s", str(e))

    return logger
