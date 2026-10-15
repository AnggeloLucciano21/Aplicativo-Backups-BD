"""
Worker Asíncrono para Operaciones de Restauración e Inspección
Permite examinar archivos .bak y ejecutar restauraciones complejas sin congelar la ventana.
"""
from typing import Optional, Dict, Any
from PySide6.QtCore import QThread, Signal

from core.models import ConnectionConfig, OperationRecord
from restore.restore_engine import RestoreEngine


class InspectBackupWorker(QThread):
    # Señal: éxito (bool), datos_inspeccion (dict)
    inspection_finished = Signal(bool, dict)

    def __init__(self, conn_config: ConnectionConfig, backup_path: str):
        super().__init__()
        self.conn_config = conn_config
        self.backup_path = backup_path

    def run(self):
        engine = RestoreEngine()
        res = engine.inspect_backup(self.conn_config, self.backup_path)
        self.inspection_finished.emit(res.get("success", False), res)


class RestoreWorker(QThread):
    progress_updated = Signal(int, str)
    restore_finished = Signal(bool, str, object)

    def __init__(self,
                 conn_config: ConnectionConfig,
                 backup_path: str,
                 target_database: str,
                 replace_existing: bool = False):
        super().__init__()
        self.conn_config = conn_config
        self.backup_path = backup_path
        self.target_database = target_database
        self.replace_existing = replace_existing

    def run(self):
        engine = RestoreEngine()

        def on_progress(p: int, msg: str):
            self.progress_updated.emit(p, msg)

        try:
            success, msg, record = engine.run_restore(
                conn_config=self.conn_config,
                backup_path=self.backup_path,
                target_database=self.target_database,
                replace_existing=self.replace_existing,
                progress_callback=on_progress
            )
            self.restore_finished.emit(success, msg, record)
        except Exception as e:
            self.restore_finished.emit(False, f"Error durante la restauración: {str(e)}", None)
