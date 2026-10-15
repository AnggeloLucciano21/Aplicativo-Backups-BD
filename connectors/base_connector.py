"""
Módulo de Conector Base de Datos Abstracto
Define el contrato para cualquier motor de base de datos (SQL Server, SQLite, PostgreSQL, etc.)
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Callable, Optional
from core.models import ConnectionConfig


class BaseDatabaseConnector(ABC):
    """
    Clase base abstracta para conectores de bases de datos.
    Permite desacoplar el motor subyacente de la interfaz y la lógica de negocio.
    """

    engine_name: str = "base"
    default_port: Optional[int] = 1433
    default_file_extension: str = ".bak"
    supported_backup_types: List[str] = ["FULL"]

    def __init__(self, config: ConnectionConfig, password: Optional[str] = None):
        self.config = config
        self.password = password

    @classmethod
    def check_prerequisites(cls) -> Tuple[bool, str]:
        """
        Comprueba si las herramientas o controladores externos necesarios
        para este motor están instalados en el sistema operativo.
        """
        return True, "Prerrequisitos disponibles."

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Prueba la conectividad con el servidor.
        Retorna: (éxito, mensaje, detalles_servidor).
        """
        pass

    @abstractmethod
    def list_databases(self) -> List[str]:
        """
        Obtiene la lista de bases de datos disponibles en el servidor.
        """
        pass

    @abstractmethod
    def execute_backup(self,
                       database_name: str,
                       backup_type: str,
                       destination_path: str,
                       compression: bool = True,
                       checksum: bool = True,
                       progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Ejecuta el backup de la base de datos seleccionada.
        """
        pass

    @abstractmethod
    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Verifica la validez y cabeceras del archivo de copia de seguridad.
        """
        pass

    @abstractmethod
    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        """
        Extrae los metadatos almacenados en la cabecera del archivo de backup.
        """
        pass

    @abstractmethod
    def execute_restore(self,
                        backup_path: str,
                        target_database: str,
                        replace_existing: bool = False,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Restaura la base de datos a partir del archivo de backup.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Cierra conexiones abiertas."""
        pass
