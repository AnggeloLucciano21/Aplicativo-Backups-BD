"""
Módulo Conector Nativo para PostgreSQL
Utiliza psycopg2 para la conexión directa y los clientes oficiales pg_dump, pg_restore y psql
para operaciones de backup, verificación y restauración.
"""

import os
import shutil
import logging
import subprocess
import gzip
from typing import List, Tuple, Dict, Any, Optional, Callable

import psycopg2
from psycopg2 import sql

from core.models import ConnectionConfig
from connectors.base_connector import BaseDatabaseConnector

logger = logging.getLogger("BackupApp.PostgreSQLConnector")

# Rutas típicas de instalación de PostgreSQL en Windows
KNOWN_PG_PATHS = [
    r"C:\Program Files\PostgreSQL",
    r"C:\Program Files (x86)\PostgreSQL",
    r"C:\Program Files\PostgreSQL\bin",
    r"C:\Program Files (x86)\PostgreSQL\bin",
]

class PostgreSQLConnector(BaseDatabaseConnector):
    """Conector PostgreSQL que implementa la interfaz abstracta.

    - Herramientas externas: pg_dump.exe, pg_restore.exe, psql.exe
    - Credenciales: se pasan mediante la variable de entorno PGPASSWORD
    - Compatibilidad Windows: búsqueda de binarios en PATH y en rutas conocidas.
    """

    engine_name: str = "postgresql"
    default_port: Optional[int] = 5432
    default_file_extension: str = ".sql"
    supported_backup_types: List[str] = ["FULL"]

    # ---------------------------------------------------------------------
    # Utilidades comunes
    # ---------------------------------------------------------------------
    @classmethod
    def find_executable(cls, exe_name: str) -> Optional[str]:
        """Busca el ejecutable especificado en PATH o en ubicaciones típicas.
        Retorna la ruta absoluta o None si no se encuentra.
        """
        # 1. PATH del sistema
        found = shutil.which(exe_name)
        if found:
            return found
        # 2. Búsqueda en carpetas conocidas de PostgreSQL
        for base in KNOWN_PG_PATHS:
            for root, dirs, files in os.walk(base):
                candidate = os.path.join(root, exe_name)
                if os.path.isfile(candidate):
                    return candidate
        return None

    @classmethod
    def check_prerequisites(cls) -> Tuple[bool, str]:
        """Verifica que pg_dump, pg_restore y psql estén disponibles.
        """
        missing = []
        dump = cls.find_executable("pg_dump.exe")
        restore = cls.find_executable("pg_restore.exe")
        client = cls.find_executable("psql.exe")
        if not dump:
            missing.append("pg_dump.exe")
        if not restore:
            missing.append("pg_restore.exe")
        if not client:
            missing.append("psql.exe")
        if missing:
            return False, f"Faltan herramientas PostgreSQL: {', '.join(missing)}"
        return True, f"Herramientas PostgreSQL encontradas: pg_dump={dump}, pg_restore={restore}, psql={client}"

    # ---------------------------------------------------------------------
    # Conexión directa
    # ---------------------------------------------------------------------
    def _get_connection(self, database: Optional[str] = None) -> psycopg2.extensions.connection:
        """Crea una conexión psycopg2 usando la configuración del objeto.
        Si ``database`` es None, usa la base configurada en ``self.config``.
        """
        dbname = database or self.config.database
        conn = psycopg2.connect(
            host=self.config.host or "localhost",
            port=self.config.port or 5432,
            user=self.config.username,
            password=self.password,
            dbname=dbname,
            connect_timeout=self.config.timeout or 10,
        )
        return conn

    # ---------------------------------------------------------------------
    # Implementación de la interfaz abstracta
    # ---------------------------------------------------------------------
    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Prueba la conectividad y devuelve información de versión.
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()
            msg = f"Conexión exitosa a PostgreSQL {version}"
            details = {"version": version, "server": self.config.host or "localhost"}
            return True, msg, details
        except Exception as e:
            logger.error("Error en test_connection PostgreSQL: %s", str(e))
            return False, f"Error de conexión: {str(e)}", {}

    def list_databases(self) -> List[str]:
        """Lista bases de datos excluyendo plantillas y sistemas.
        """
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT datname FROM pg_database
                WHERE datistemplate = FALSE AND datallowconn = TRUE;
                """
            )
            databases = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            return databases
        except Exception as e:
            logger.error("Error list_databases PostgreSQL: %s", str(e))
            return []

    def execute_backup(
        self,
        database_name: str,
        backup_type: str,
        destination_path: str,
        compression: bool = True,
        checksum: bool = True,  # PostgreSQL no tiene checksum directo
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Realiza backup usando pg_dump.
        - ``backup_type`` se ignora (solo FULL soportado).
        - ``compression`` habilita gzip del archivo resultante.
        """
        dump_exe = self.find_executable("pg_dump.exe")
        if not dump_exe:
            return False, "pg_dump.exe no encontrado en el sistema."

        if progress_callback:
            progress_callback(10, f"Iniciando backup de {database_name} con pg_dump…")

        # Construir argumentos seguros
        host = self.config.host or "localhost"
        port = str(self.config.port or 5432)
        user = self.config.username or "postgres"

        args = [
            dump_exe,
            f"--host={host}",
            f"--port={port}",
            f"--username={user}",
            "--format=plain",  # texto SQL que puede comprimir después
            "--no-owner",
            "--no-privileges",
            database_name,
        ]

        env = os.environ.copy()
        if self.password:
            env["PGPASSWORD"] = self.password

        # Preparar ruta destino (crea carpeta si es necesario)
        dest_dir = os.path.dirname(destination_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        try:
            if compression and destination_path.lower().endswith('.gz'):
                # escribe directamente en gzip
                with gzip.open(destination_path, 'wb') as f_out:
                    proc = subprocess.Popen(args, stdout=f_out, stderr=subprocess.PIPE, env=env)
                    _, stderr_bytes = proc.communicate()
            else:
                with open(destination_path, 'wb') as f_out:
                    proc = subprocess.Popen(args, stdout=f_out, stderr=subprocess.PIPE, env=env)
                    _, stderr_bytes = proc.communicate()

            if proc.returncode != 0:
                err = stderr_bytes.decode('utf-8', errors='replace').strip()
                logger.error("pg_dump falló (rc=%d): %s", proc.returncode, err)
                return False, f"pg_dump error: {err}"

            if progress_callback:
                progress_callback(100, f"Backup de {database_name} completado en {destination_path}")
            return True, f"Backup PostgreSQL guardado en {destination_path}"
        except Exception as e:
            logger.error("Excepción en execute_backup PostgreSQL: %s", str(e))
            return False, f"Error durante backup: {str(e)}"

    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Verifica que el dump sea legible usando pg_restore --list.
        Funciona tanto con archivos .sql como .sql.gz.
        """
        # Descomprimir si es gzip
        is_gzip = backup_path.lower().endswith('.gz')
        opener = gzip.open if is_gzip else open
        try:
            # pg_restore solo entiende formatos custom; para plain usamos pg_restore --list
            restore_exe = self.find_executable("pg_restore.exe")
            if not restore_exe:
                return False, "pg_restore.exe no encontrado para verificación."
            args = [restore_exe, "--list", backup_path]
            env = os.environ.copy()
            if self.password:
                env["PGPASSWORD"] = self.password
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            out, err = proc.communicate()
            if proc.returncode != 0:
                return False, f"Verificación falló: {err.decode('utf-8', errors='replace').strip()}"
            return True, "Backup verificado correctamente (pg_restore --list)."
        except Exception as e:
            logger.error("Error en verify_backup PostgreSQL: %s", str(e))
            return False, f"Error de verificación: {str(e)}"

    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        """Extrae metadatos básicos del dump usando pg_restore --list.
        Sólo disponible para dumps en formato *plain* o *custom*.
        """
        restore_exe = self.find_executable("pg_restore.exe")
        if not restore_exe:
            return {"error": "pg_restore.exe no disponible para extraer encabezado."}
        args = [restore_exe, "--list", backup_path]
        env = os.environ.copy()
        if self.password:
            env["PGPASSWORD"] = self.password
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            out, err = proc.communicate()
            if proc.returncode != 0:
                return {"error": err.decode('utf-8', errors='replace').strip()}
            # Analizamos la salida mínima: primera línea contiene la versión del dump
            lines = out.decode('utf-8', errors='ignore').splitlines()
            header = {
                "software_version": "PostgreSQL",
                "backup_type": "FULL",
                "database_name": self.config.database or "",
                "has_checksum": False,
                "backup_start_date": "",
                "error": None,
            }
            # Intentamos extraer una fecha si el dump contiene comment '-- Dumped ...'
            for line in lines:
                if "Dumped" in line and "on" in line:
                    header["backup_start_date"] = line.strip()
                    break
            return header
        except Exception as e:
            logger.error("Error al obtener encabezado PostgreSQL: %s", str(e))
            return {"error": str(e)}

    def execute_restore(
        self,
        backup_path: str,
        target_database: str,
        replace_existing: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[bool, str]:
        """Restaurar un dump usando psql (para formato plain) o pg_restore (custom).
        Si ``replace_existing`` es True, se ejecuta ``DROP DATABASE`` antes de crear.
        """
        # Descomprimir temporalmente si es gzip
        is_gzip = backup_path.lower().endswith('.gz')
        if is_gzip:
            temp_path = backup_path.rstrip('.gz')
            try:
                with gzip.open(backup_path, 'rb') as f_in, open(temp_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                dump_file = temp_path
            except Exception as e:
                return False, f"Error al descomprimir gzip: {str(e)}"
        else:
            dump_file = backup_path

        # Crear o reemplazar la base de datos sin usar context managers
        admin_conn = self._get_connection(database='postgres')
        admin_conn.autocommit = True
        cur = admin_conn.cursor()
        if replace_existing:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {db}").format(db=sql.Identifier(target_database)))
        cur.execute(sql.SQL("CREATE DATABASE {db}").format(db=sql.Identifier(target_database)))
        cur.close()
        admin_conn.close()

        # Restaurar usando psql (plain) o pg_restore (custom)
        if dump_file.lower().endswith('.sql'):
            psql_exe = self.find_executable('psql.exe')
            if not psql_exe:
                return False, 'psql.exe no encontrado para restaurar dump SQL.'
            args = [psql_exe, f"--host={self.config.host or 'localhost'}", f"--port={self.config.port or 5432}", f"--username={self.config.username or 'postgres'}", '-d', target_database, '-f', dump_file]
        else:
            restore_exe = self.find_executable('pg_restore.exe')
            if not restore_exe:
                return False, 'pg_restore.exe no encontrado para restaurar dump.'
            args = [restore_exe, f"--host={self.config.host or 'localhost'}", f"--port={self.config.port or 5432}", f"--username={self.config.username or 'postgres'}", '--no-owner', '--no-privileges', '-d', target_database, dump_file]

        env = os.environ.copy()
        if self.password:
            env['PGPASSWORD'] = self.password

        if progress_callback:
            progress_callback(10, f"Restaurando {dump_file} en {target_database} …")

        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        out, err = proc.communicate()
        if proc.returncode != 0:
            return False, f"Error restaurando: {err.decode('utf-8', errors='replace').strip()}"

        if progress_callback:
            progress_callback(100, f"Restauración de {target_database} completada.")
        # Cleanup temporary gzip file
        if is_gzip and os.path.exists(temp_path):
            os.remove(temp_path)
        return True, f"Base de datos '{target_database}' restaurada exitosamente."

    def close(self) -> None:
        """Cierra recursos si los hubiera (no necesario en psycopg2)."""
        pass
