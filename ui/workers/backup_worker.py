"""
Worker Asíncrono para Operaciones de Copias de Seguridad (Backup)
Emite actualizaciones de progreso y mensajes en tiempo real hacia la UI sin bloquear el bucle de eventos.
"""
from typing import Optional
from PySide6.QtCore import QThread, Signal

from core.models import ConnectionConfig, OperationRecord
from backup.backup_engine import BackupEngine


class BackupWorker(QThread):
    # Señal de progreso: porcentaje (int: 0-100), mensaje descriptivo (str)
    progress_updated = Signal(int, str)
    # Señal de finalización: éxito (bool), mensaje (str), registro (OperationRecord)
    backup_finished = Signal(bool, str, object)

    def __init__(self,
                 conn_config: ConnectionConfig,
                 database_name: str,
                 backup_type: str,
                 destination_folder: str,
                 file_pattern: str = "{db}_{type}_{date}_{time}.bak",
                 compression: bool = True,
                 checksum: bool = True,
                 verify_after: bool = True,
                 retention_days: int = 15,
                 min_copies_to_keep: int = 2):
        super().__init__()
        self.conn_config = conn_config
        self.database_name = database_name
        self.backup_type = backup_type
        self.destination_folder = destination_folder
        self.file_pattern = file_pattern
        self.compression = compression
        self.checksum = checksum
        self.verify_after = verify_after
        self.retention_days = retention_days
        self.min_copies_to_keep = min_copies_to_keep

    def run(self):
        engine = BackupEngine()

        def on_progress(percent: int, message: str):
            self.progress_updated.emit(percent, message)

        try:
            success, message, record = engine.run_backup(
                conn_config=self.conn_config,
                database_name=self.database_name,
                backup_type=self.backup_type,
                destination_folder=self.destination_folder,
                file_pattern=self.file_pattern,
                compression=self.compression,
                checksum=self.checksum,
                verify_after=self.verify_after,
                retention_days=self.retention_days,
                min_copies_to_keep=self.min_copies_to_keep,
                progress_callback=on_progress
            )
            self.backup_finished.emit(success, message, record)
        except Exception as e:
            self.backup_finished.emit(False, f"Error no controlado en el worker: {str(e)}", None)
