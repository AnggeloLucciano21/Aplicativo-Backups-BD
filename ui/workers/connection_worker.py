"""
Worker Asíncrono para Comprobación de Conexiones
Ejecuta la prueba de conexión y la consulta de bases de datos en un hilo separado
para no bloquear la interfaz gráfica del usuario.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QThread, Signal

from core.models import ConnectionConfig
from connectors.factory import ConnectorFactory
from security.credentials_manager import CredentialsManager


class ConnectionTestWorker(QThread):
    # Señales: success (bool), message (str), details (dict)
    result_ready = Signal(bool, str, dict)

    def __init__(self, config: ConnectionConfig, password: Optional[str] = None):
        super().__init__()
        self.config = config
        self.password = password

    def run(self):
        pwd = self.password
        if pwd is None and (self.config.auth_type.lower() != "windows" or self.config.engine.lower() != "sqlserver"):
            pwd = CredentialsManager.get_password(self.config.name, self.config.username)

        connector = ConnectorFactory.create_connector(self.config, password=pwd)
        success, msg, details = connector.test_connection()
        self.result_ready.emit(success, msg, details)


class LoadDatabasesWorker(QThread):
    # Señales: success (bool), databases (list), error_msg (str)
    databases_loaded = Signal(bool, list, str)

    def __init__(self, config: ConnectionConfig):
        super().__init__()
        self.config = config

    def run(self):
        pwd = None
        if self.config.auth_type.lower() != "windows" or self.config.engine.lower() != "sqlserver":
            pwd = CredentialsManager.get_password(self.config.name, self.config.username)

        connector = ConnectorFactory.create_connector(self.config, password=pwd)
        try:
            dbs = connector.list_databases()
            if dbs:
                self.databases_loaded.emit(True, dbs, "")
            else:
                self.databases_loaded.emit(False, [], "No se pudieron listar las bases de datos o la lista está vacía.")
        except Exception as e:
            self.databases_loaded.emit(False, [], str(e))
