"""
Conector para SAP Sybase ASE.
Utiliza pyodbc como driver ODBC para conectar al motor.
"""
import logging
from typing import Tuple, Dict, Any, Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None  # Will be handled in check_prerequisites

from core.models import ConnectionConfig
from connectors.base_connector import BaseDatabaseConnector

logger = logging.getLogger("BackupApp.SybaseConnector")


class SybaseConnector(BaseDatabaseConnector):
    """Conector nativo para SAP Sybase ASE usando ODBC (pyodbc)."""

    engine_name: str = "sybase"
    default_port: Optional[int] = 5000
    default_file_extension: str = ".bak"
    supported_backup_types: list = []  # No implementado aún

    @classmethod
    def check_prerequisites(cls) -> Tuple[bool, str]:
        """Verifica que el driver pyodbc esté disponible."""
        if pyodbc is None:
            return (
                False,
                "pyodbc no está instalado. Instale el paquete 'pyodbc' y el driver ODBC de Sybase."
            )
        return True, "pyodbc está disponible."

    def _get_connection(self) -> Any:
        """Crea y devuelve una conexión pyodbc al motor Sybase.
        Usa DSN o parámetros de conexión directa.
        """
        if pyodbc is None:
            raise RuntimeError("pyodbc no está disponible.")

        driver = self.config.driver or "Adaptive Server Enterprise"
        server = self.config.host or "localhost"
        port = self.config.port or self.default_port
        uid = self.config.username or ""
        pwd = self.password or ""
        database = self.config.database or "master"
        conn_str = (
            f"DRIVER={{ {driver} }};SERVER={server},{port};UID={uid};PWD={pwd};DATABASE={database};"
        )
        return pyodbc.connect(conn_str, timeout=self.config.timeout or 10)

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Intenta conectar y ejecuta una consulta ligera para validar la conexión."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            row = cursor.fetchone()
            version = row[0] if row else "Desconocida"
            conn.close()
            msg = f"Conexión exitosa a Sybase ASE (versión: {version}) en {self.config.host}:{self.config.port or self.default_port}"
            return True, msg, {"version": version}
        except Exception as e:
            return False, f"Error de conexión a Sybase ASE: {str(e)}", {}

    # Métodos placeholder – aún no implementados
    def list_databases(self) -> list:
        return []

    def execute_backup(self, database_name: str, backup_type: str, destination_path: str,
                        compression: bool = True, checksum: bool = True,
                        progress_callback: Optional[Any] = None) -> Tuple[bool, str]:
        return False, "Backup no implementado para Sybase ASE"

    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        return False, "Verificación no implementada para Sybase ASE"

    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        return {"error": "Extracción de metadatos no disponible para Sybase ASE"}

    def execute_restore(self, backup_path: str, target_database: str, replace_existing: bool = False,
                        progress_callback: Optional[Any] = None) -> Tuple[bool, str]:
        return False, "Restauración no implementada para Sybase ASE"

    def close(self) -> None:
        pass
