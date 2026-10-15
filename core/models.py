"""
Módulo de Modelos de Datos del Dominio
Define las estructuras y entidades de la aplicación.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class ConnectionConfig:
    id: Optional[int] = None
    name: str = ""
    engine: str = "sqlserver"  # 'sqlserver', 'sqlite', 'postgresql', etc.
    host: str = "localhost"
    port: Optional[int] = 1433
    instance: str = ""
    database: str = "master"
    auth_type: str = "windows"  # 'windows' (SSPI) o 'sql' (SQL Server Authentication)
    username: str = ""
    odbc_driver: str = "ODBC Driver 18 for SQL Server"
    service_name: str = ""   # Para Oracle (ej. ORCL, XEPDB1)
    sqlite_path: str = ""    # Para SQLite (ej. C:\data\db.sqlite)
    trust_server_certificate: bool = True
    encrypt: bool = False
    timeout: int = 15
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @staticmethod
    def get_default_port_for_engine(engine: str) -> Optional[int]:
        eng = engine.lower()
        if eng in ["sqlserver", "mssql"]:
            return 1433
        elif eng in ["mysql", "mariadb"]:
            return 3306
        elif eng in ["postgresql", "postgres"]:
            return 5432
        elif eng == "oracle":
            return 1521
        elif eng in ["sybase", "ase"]:
            return 5000
        elif eng == "sqlite":
            return None
        return 1433

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "engine": self.engine,
            "host": self.host,
            "port": self.port,
            "instance": self.instance,
            "database": self.database,
            "auth_type": self.auth_type,
            "username": self.username,
            "odbc_driver": self.odbc_driver,
            "service_name": self.service_name,
            "sqlite_path": self.sqlite_path,
            "trust_server_certificate": self.trust_server_certificate,
            "encrypt": self.encrypt,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class BackupTaskConfig:
    id: Optional[int] = None
    connection_id: int = 0
    connection_name: str = ""
    database_name: str = ""
    backup_type: str = "FULL"  # 'FULL', 'DIFFERENTIAL', 'LOG'
    destination_folder: str = ""
    file_pattern: str = "{db}_{type}_{date}_{time}.bak"
    compression: bool = True
    checksum: bool = True
    verify_after: bool = True
    retention_days: int = 15
    retention_min_copies: int = 2  # Asegura nunca borrar las últimas N copias válidas
    is_active: bool = True
    schedule_frequency: str = "DAILY"  # 'DAILY', 'WEEKLY', 'MONTHLY', 'MANUAL'
    schedule_time: str = "02:00"       # Formato HH:MM (24h)
    schedule_days: str = ""           # Para semanal: "MON,WED,FRI"
    use_windows_scheduler: bool = True
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OperationRecord:
    id: Optional[int] = None
    connection_name: str = ""
    database_name: str = ""
    operation_type: str = "BACKUP_FULL"  # 'BACKUP_FULL', 'BACKUP_DIFF', 'BACKUP_LOG', 'RESTORE', 'VERIFY'
    status: str = "IN_PROGRESS"          # 'SUCCESS', 'FAILED', 'CANCELLED', 'IN_PROGRESS'
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    duration_seconds: float = 0.0
    destination_path: str = ""
    file_size_bytes: int = 0
    sha256_hash: str = ""
    user_system: str = ""
    error_message: str = ""
    details_json: str = "{}"

    @property
    def file_size_formatted(self) -> str:
        """Devuelve el tamaño en formato legible para humanos."""
        size = float(self.file_size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @property
    def duration_formatted(self) -> str:
        """Devuelve la duración formateada en mm:ss o hh:mm:ss."""
        total_seconds = int(self.duration_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
