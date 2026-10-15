"""
Módulo de Gestión de Base de Datos Local (SQLite)
Controla la base de datos local para configuraciones, historial de auditoría y programación.
"""
import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("BackupApp.Database")


def get_default_db_path() -> str:
    """
    Obtiene la ruta estándar para la base de datos local SQLite.
    Se ubica en %LOCALAPPDATA%/AplicativoBackupsBD o en el directorio del proyecto si falla.
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        app_dir = Path(local_app_data) / "AplicativoBackupsBD"
    else:
        app_dir = Path.home() / ".aplicativo_backups_bd"

    try:
        app_dir.mkdir(parents=True, exist_ok=True)
        return str(app_dir / "app_data.db")
    except Exception as e:
        logger.warning("No se pudo crear directorio en %s (%s). Usando directorio local.", app_dir, str(e))
        return "app_data.db"


class DatabaseManager:
    """
    Administrador de la base de datos SQLite embebida.
    Maneja la inicialización del esquema, migraciones y conexiones seguras con modo WAL.
    """
    _instance: Optional['DatabaseManager'] = None

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_default_db_path()
        self.init_database()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """
        Devuelve una conexión a la base de datos configurada para concurrencia y diccionarios de filas.
        """
        conn = sqlite3.connect(self.db_path, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")  # Permite lectura y escritura concurrente sin bloqueos
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_database(self) -> None:
        """
        Crea las tablas e índices si no existen.
        """
        logger.info("Inicializando esquema de base de datos en: %s", self.db_path)
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de Conexiones
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                engine TEXT NOT NULL DEFAULT 'sqlserver',
                host TEXT NOT NULL,
                port INTEGER DEFAULT 1433,
                instance TEXT DEFAULT '',
                database TEXT DEFAULT 'master',
                auth_type TEXT NOT NULL DEFAULT 'windows',
                username TEXT DEFAULT '',
                odbc_driver TEXT DEFAULT 'ODBC Driver 18 for SQL Server',
                trust_server_certificate INTEGER DEFAULT 1,
                encrypt INTEGER DEFAULT 0,
                timeout INTEGER DEFAULT 15,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            # Tabla de Tareas de Backup (Programadas o Perfiles)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL,
                connection_name TEXT NOT NULL,
                database_name TEXT NOT NULL,
                backup_type TEXT NOT NULL DEFAULT 'FULL',
                destination_folder TEXT NOT NULL,
                file_pattern TEXT NOT NULL,
                compression INTEGER DEFAULT 1,
                checksum INTEGER DEFAULT 1,
                verify_after INTEGER DEFAULT 1,
                retention_days INTEGER DEFAULT 15,
                retention_min_copies INTEGER DEFAULT 2,
                is_active INTEGER DEFAULT 1,
                schedule_frequency TEXT DEFAULT 'DAILY',
                schedule_time TEXT DEFAULT '02:00',
                schedule_days TEXT DEFAULT '',
                use_windows_scheduler INTEGER DEFAULT 1,
                last_run_at TEXT,
                next_run_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            );
            """)

            # Tabla de Historial y Auditoría de Operaciones
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_name TEXT NOT NULL,
                database_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration_seconds REAL DEFAULT 0,
                destination_path TEXT,
                file_size_bytes INTEGER DEFAULT 0,
                sha256_hash TEXT DEFAULT '',
                user_system TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                details_json TEXT DEFAULT '{}'
            );
            """)

            # Índices de alto rendimiento para el historial
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_started ON operations_history(started_at DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_conn_db ON operations_history(connection_name, database_name);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_status ON operations_history(status);")

            # Tabla de Configuración General de la Aplicación
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            conn.commit()
            logger.info("Esquema de base de datos verificado con éxito.")
