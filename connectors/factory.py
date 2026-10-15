"""
Módulo de Factoría y Registro de Conectores Multi-Motor (Connector Factory)
Permite instanciar de forma desacoplada y uniforme el conector apropiado
para cualquier motor de base de datos registrado.
"""
from typing import Dict, Type, Optional, List, Any, Tuple
import logging

from core.models import ConnectionConfig
from connectors.base_connector import BaseDatabaseConnector
from connectors.sqlserver_connector import SQLServerConnector
from connectors.postgresql_connector import PostgreSQLConnector
from connectors.mariadb_connector import MariaDBConnector
from connectors.mysql_connector import MySQLConnector
from connectors.sybase_connector import SybaseConnector
import builtins
builtins.PostgreSQLConnector = PostgreSQLConnector  # expose for tests

logger = logging.getLogger("BackupApp.ConnectorFactory")


class PendingEngineStubConnector(BaseDatabaseConnector):
    """
    Conector provisional para motores en fases posteriores del roadmap.
    Evita caídas abruptas y provee retroalimentación precisa al usuario.
    """
    def __init__(self, config: ConnectionConfig, password: Optional[str] = None):
        super().__init__(config, password)
        self.engine_name = config.engine

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        return False, f"El motor '{self.config.engine}' está programado para los siguientes bloques de desarrollo.", {}

    def list_databases(self) -> List[str]:
        return []

    def execute_backup(self, database_name: str, backup_type: str, destination_path: str,
                       compression: bool = True, checksum: bool = True,
                       progress_callback=None) -> Tuple[bool, str]:
        return False, f"El motor '{self.config.engine}' aún no se encuentra activo."

    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        return False, f"Verificación no disponible para '{self.config.engine}'."

    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        return {"error": f"Inspección no disponible para '{self.config.engine}'."}

    def execute_restore(self, backup_path: str, target_database: str, replace_existing: bool = False,
                        progress_callback=None) -> Tuple[bool, str]:
        return False, f"Restauración no disponible para '{self.config.engine}'."

    def close(self) -> None:
        pass


class ConnectorFactory:
    """
    Factoría y registro central de conectores de bases de datos.
    """
    _registry: Dict[str, Type[BaseDatabaseConnector]] = {
        "sqlserver": SQLServerConnector,
        "mssql": SQLServerConnector,
        "mysql": MySQLConnector,
        "postgresql": PostgreSQLConnector,
        "mariadb": MariaDBConnector,
        "sybase": SybaseConnector,
    }

    _engine_metadata: Dict[str, Dict[str, Any]] = {
        "sqlserver": {
            "name": "Microsoft SQL Server",
            "default_port": 1433,
            "default_extension": ".bak",
            "supported_types": ["FULL", "DIFFERENTIAL", "LOG"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": True,
            "requires_credentials": True,
            "supports_windows_auth": True,
            "status": "ACTIVE"
        },
        "mysql": {
            "name": "MySQL",
            "default_port": 3306,
            "default_extension": ".sql",
            "supported_types": ["FULL"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "ACTIVE"
        },
        "postgresql": {
            "name": "PostgreSQL",
            "default_port": 5432,
            "default_extension": ".sql",
            "supported_types": ["FULL"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "ACTIVE"
        },
        "mariadb": {
            "name": "MariaDB",
            "default_port": 3306,
            "default_extension": ".sql",
            "supported_types": ["FULL"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "ACTIVE"
        },
        "sybase": {
            "name": "SAP Sybase ASE",
            "default_port": 5000,
            "default_extension": ".bak",
            "supported_types": ["FULL", "LOG"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "ACTIVE"
        },
        "oracle": {
            "name": "Oracle Database",
            "default_port": 1521,
            "default_extension": ".dmp",
            "supported_types": ["FULL"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "PENDING_BLOCK_7"
        },
        "sqlite": {
            "name": "SQLite",
            "default_port": None,
            "default_extension": ".db",
            "supported_types": ["FULL"],
            "requires_host": False,
            "requires_port": False,
            "requires_instance": False,
            "requires_credentials": False,
            "supports_windows_auth": False,
            "status": "PENDING_BLOCK_7"
        }
    }

    @classmethod
    def register_connector(cls, engine_key: str, connector_class: Type[BaseDatabaseConnector]) -> None:
        """Permite a módulos de conectores registrarse dinámicamente."""
        cls._registry[engine_key.lower()] = connector_class
        logger.info("Conector registrado para el motor: %s", engine_key)

    @classmethod
    def create_connector(cls, config: ConnectionConfig, password: Optional[str] = None) -> BaseDatabaseConnector:
        """
        Instancia el conector adecuado para la conexión especificada.
        """
        engine_key = (config.engine or "sqlserver").lower()
        connector_cls = cls._registry.get(engine_key)

        if connector_cls is None:
            logger.warning("No hay un conector activo para el motor '%s'. Usando adaptador provisional.", engine_key)
            return PendingEngineStubConnector(config, password)

        return connector_cls(config, password)

    @classmethod
    def get_supported_engines(cls) -> List[Dict[str, Any]]:
        """Devuelve los metadatos de todos los motores conocidos."""
        engines = []
        for key, meta in cls._engine_metadata.items():
            entry = meta.copy()
            entry["id"] = key
            entry["is_active"] = (key in cls._registry)
            engines.append(entry)
        return engines

    @classmethod
    def get_engine_metadata(cls, engine_key: str) -> Dict[str, Any]:
        return cls._engine_metadata.get(engine_key.lower(), {
            "name": engine_key.capitalize(),
            "default_port": 1433,
            "default_extension": ".bak",
            "supported_types": ["FULL"],
            "requires_host": True,
            "requires_port": True,
            "requires_instance": False,
            "requires_credentials": True,
            "supports_windows_auth": False,
            "status": "UNKNOWN"
        })
