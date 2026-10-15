"""
Módulo Conector Nativo para MySQL y MariaDB
Utiliza pymysql para operaciones directas de catálogo y conectividad,
y las utilidades oficiales mysqldump.exe y mysql.exe para respaldos y restauraciones
con paso seguro de credenciales sin exposición en procesos del sistema.
"""
import os
import sys
import gzip
import shutil
import subprocess
import logging
from typing import List, Tuple, Dict, Any, Callable, Optional

import pymysql

from core.models import ConnectionConfig
from connectors.base_connector import BaseDatabaseConnector

logger = logging.getLogger("BackupApp.MySQLConnector")

# Rutas estándar de búsqueda de ejecutables MySQL en Windows
KNOWN_MYSQL_PATHS = [
    r"C:\Program Files\MySQL\MySQL Workbench 8.0 CE",
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin",
    r"C:\Program Files\MySQL\MySQL Server 8.4\bin",
    r"C:\Program Files\MySQL\MySQL Server 5.7\bin",
    r"C:\Program Files (x86)\MySQL\MySQL Server 8.0\bin",
    r"C:\xampp\mysql\bin",
    r"C:\laragon\bin\mysql\mysql-8.0.30-winx64\bin",
]


class MySQLConnector(BaseDatabaseConnector):
    """
    Conector nativo para servidores MySQL con soporte de transacciones consistentes,
    volcados con mysqldump y restauración validada.
    """
    engine_name: str = "mysql"
    default_port: Optional[int] = 3306
    default_file_extension: str = ".sql"
    supported_backup_types: List[str] = ["FULL"]

    @classmethod
    def find_executable(cls, exe_name: str) -> Optional[str]:
        """Localiza la herramienta oficial (mysqldump.exe o mysql.exe)."""
        # 1. Comprobar en el PATH del sistema
        found = shutil.which(exe_name)
        if found:
            return found

        # 2. Comprobar en ubicaciones conocidas de Windows
        for directory in KNOWN_MYSQL_PATHS:
            candidate = os.path.join(directory, exe_name)
            if os.path.isfile(candidate):
                return candidate

        return None

    @classmethod
    def check_prerequisites(cls) -> Tuple[bool, str]:
        """Comprueba si las herramientas oficiales mysqldump y mysql están disponibles."""
        dump_exe = cls.find_executable("mysqldump.exe")
        client_exe = cls.find_executable("mysql.exe")

        missing = []
        if not dump_exe:
            missing.append("mysqldump.exe")
        if not client_exe:
            missing.append("mysql.exe")

        if missing:
            return False, f"Faltan herramientas oficiales de MySQL: {', '.join(missing)}. Instale MySQL Server o MySQL Workbench."

        return True, f"Herramientas detectadas: {dump_exe}"

    def _get_connection(self, database: Optional[str] = None) -> pymysql.Connection:
        """Abre una conexión directa con el servidor MySQL."""
        port = self.config.port or 3306
        db = database or (self.config.database if self.config.database != "master" else None)

        return pymysql.connect(
            host=self.config.host or "localhost",
            port=int(port),
            user=self.config.username or "root",
            password=self.password or "",
            database=db,
            connect_timeout=self.config.timeout or 10,
            charset="utf8mb4",
            autocommit=True
        )

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Prueba la conectividad y devuelve la versión y comentarios del motor MySQL.
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        VERSION() AS Version,
                        @@hostname AS Hostname,
                        @@version_comment AS Comment;
                """)
                row = cursor.fetchone()
                version = row[0] if row else "Desconocida"
                hostname = row[1] if row and len(row) > 1 else ""
                comment = row[2] if row and len(row) > 2 else ""

            conn.close()
            details = {
                "version": version,
                "hostname": hostname,
                "edition": comment,
                "full_version": f"MySQL {version} ({comment})"
            }
            msg = f"Conexión exitosa a MySQL {version} en {self.config.host}:{self.config.port or 3306}"
            return True, msg, details

        except pymysql.err.OperationalError as ex:
            code, text = ex.args[0], ex.args[1] if len(ex.args) > 1 else str(ex)
            if code == 2003:
                return False, f"No se pudo conectar al servidor MySQL en {self.config.host}:{self.config.port or 3306}. Verifique que el servicio esté activo y el puerto abierto.", {}
            elif code == 1045:
                return False, f"Acceso denegado para el usuario '{self.config.username}'. Verifique la contraseña.", {}
            elif code == 1049:
                return False, f"La base de datos especificada '{self.config.database}' no existe en el servidor.", {}
            return False, f"Error operativo MySQL [{code}]: {text}", {}
        except Exception as e:
            return False, f"Error general de conexión a MySQL: {str(e)}", {}

    def list_databases(self) -> List[str]:
        """Obtiene la lista de bases de datos del servidor excluyendo esquemas del sistema."""
        system_dbs = {"information_schema", "performance_schema", "sys"}
        try:
            conn = self._get_connection()
            dbs = []
            with conn.cursor() as cursor:
                cursor.execute("SHOW DATABASES;")
                for row in cursor.fetchall():
                    db_name = row[0]
                    if db_name.lower() not in system_dbs:
                        dbs.append(db_name)
            conn.close()
            return sorted(dbs)
        except Exception as e:
            logger.error("Error al listar bases de datos MySQL: %s", str(e))
            return []

    def execute_backup(self,
                       database_name: str,
                       backup_type: str,
                       destination_path: str,
                       compression: bool = True,
                       checksum: bool = True,
                       progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Ejecuta el backup de la base de datos MySQL mediante mysqldump oficial.
        Aplica --single-transaction para consistencia sin bloqueos y pasa credenciales de forma segura.
        """
        dump_exe = self.find_executable("mysqldump.exe")
        if not dump_exe:
            return False, "No se encontró la utilidad oficial 'mysqldump.exe' en el sistema."

        if progress_callback:
            progress_callback(10, f"Iniciando respaldo de MySQL para [{database_name}] con mysqldump...")

        # Construir argumentos de mysqldump de forma segura
        host = self.config.host or "localhost"
        port = str(self.config.port or 3306)
        user = self.config.username or "root"

        args = [
            dump_exe,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            "--add-drop-table",
            "--hex-blob",
            "--max_allowed_packet=512M",
            "--default-character-set=utf8mb4",
            database_name
        ]

        # Pasar contraseña mediante variable de entorno del proceso para NO exponerla en argumentos de línea de comandos
        env = os.environ.copy()
        if self.password:
            env["MYSQL_PWD"] = self.password

        # Asegurar directorio de destino
        dest_dir = os.path.dirname(destination_path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)

        if progress_callback:
            progress_callback(30, "Extrayendo esquemas, tablas y datos con mysqldump...")

        try:
            # Ejecutar mysqldump y redirigir salida directamente al archivo de destino
            is_gzip = destination_path.endswith(".gz")

            if is_gzip:
                # Comprimir al vuelo con gzip
                with gzip.open(destination_path, "wb", compresslevel=6) as f_out:
                    proc = subprocess.Popen(args, stdout=f_out, stderr=subprocess.PIPE, env=env)
                    _, stderr_bytes = proc.communicate()
            else:
                with open(destination_path, "wb") as f_out:
                    proc = subprocess.Popen(args, stdout=f_out, stderr=subprocess.PIPE, env=env)
                    _, stderr_bytes = proc.communicate()

            if proc.returncode != 0:
                err_msg = stderr_bytes.decode("utf-8", errors="replace").strip()
                logger.error("mysqldump falló con código %d: %s", proc.returncode, err_msg)
                return False, f"Fallo al ejecutar mysqldump: {err_msg}"

            if progress_callback:
                progress_callback(90, "Verificando consistencia del archivo generado...")

            # Validar que el archivo se haya generado y no esté vacío
            if not os.path.exists(destination_path) or os.path.getsize(destination_path) == 0:
                return False, "El archivo de copia de seguridad no se generó o tiene tamaño 0 bytes."

            if progress_callback:
                progress_callback(100, f"Respaldo de [{database_name}] completado con éxito.")

            return True, f"Copia de seguridad de MySQL completada exitosamente en {destination_path}."

        except Exception as e:
            logger.error("Excepción durante mysqldump: %s", str(e))
            return False, f"Error durante la ejecución del respaldo MySQL: {str(e)}"

    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Verifica que el archivo de volcado SQL no esté truncado y contenga las marcas de éxito.
        """
        if not os.path.exists(backup_path):
            return False, f"El archivo de backup no existe: {backup_path}"

        try:
            is_gzip = backup_path.endswith(".gz")
            opener = gzip.open if is_gzip else open

            with opener(backup_path, "rt", encoding="utf-8", errors="ignore") as f:
                first_lines = [f.readline() for _ in range(15)]
                header_text = "".join(first_lines)

                # Validar cabecera de mysqldump
                if "MySQL dump" not in header_text and "MariaDB dump" not in header_text:
                    return False, "El archivo no contiene un encabezado válido de volcado MySQL/MariaDB."

                # Validar cola del archivo (Dump completed on ...)
                f.seek(0, os.SEEK_END)
                size = f.tell()
                # Leer los últimos 2048 bytes
                read_size = min(size, 2048)
                f.seek(size - read_size)
                tail_text = f.read()

                if "Dump completed" in tail_text:
                    return True, "Volcado MySQL íntegro y verificado (marca 'Dump completed' confirmada)."
                else:
                    return False, "El volcado parece estar incompleto o truncado (no se halló la marca 'Dump completed')."

        except Exception as e:
            return False, f"Error al verificar archivo de volcado MySQL: {str(e)}"

    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        """
        Extrae metadatos del encabezado del volcado de MySQL.
        """
        if not os.path.exists(backup_path):
            return {"error": f"Archivo no encontrado: {backup_path}"}

        try:
            is_gzip = backup_path.endswith(".gz")
            opener = gzip.open if is_gzip else open

            metadata = {
                "server_name": self.config.host,
                "software_version": "MySQL",
                "database_name": "Detectada en volcado",
                "backup_type": "FULL (Volcado SQL)",
                "backup_start_date": "",
                "has_checksums": True
            }

            with opener(backup_path, "rt", encoding="utf-8", errors="ignore") as f:
                for _ in range(40):
                    line = f.readline()
                    if not line:
                        break
                    if "MySQL dump" in line or "MariaDB dump" in line:
                        metadata["software_version"] = line.strip().replace("--", "").strip()
                    elif "Host:" in line and "Database:" in line:
                        # Ejemplo: -- Host: localhost    Database: mi_base
                        parts = line.split("Database:")
                        if len(parts) > 1:
                            metadata["database_name"] = parts[1].strip()
                    elif "Dump completed on" in line:
                        metadata["backup_start_date"] = line.replace("-- Dump completed on", "").strip()

            return metadata
        except Exception as e:
            return {"error": f"Error al leer cabecera MySQL: {str(e)}"}

    def execute_restore(self,
                        backup_path: str,
                        target_database: str,
                        replace_existing: bool = False,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Restaura el archivo de volcado SQL hacia la base de datos destino utilizando mysql.exe.
        """
        client_exe = self.find_executable("mysql.exe")
        if not client_exe:
            return False, "No se encontró la utilidad oficial 'mysql.exe' en el sistema."

        if not os.path.exists(backup_path):
            return False, f"El archivo de backup no existe: {backup_path}"

        if progress_callback:
            progress_callback(10, f"Validando base de datos destino [{target_database}]...")

        # 1. Asegurar que la base de datos destino exista en el servidor
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                if replace_existing:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{target_database}` DEFAULT CHARACTER SET utf8mb4;")
                else:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{target_database}` DEFAULT CHARACTER SET utf8mb4;")
            conn.close()
        except Exception as ex_db:
            return False, f"No se pudo asegurar la creación de la base de datos destino: {str(ex_db)}"

        if progress_callback:
            progress_callback(30, f"Importando datos con cliente oficial mysql.exe hacia [{target_database}]...")

        host = self.config.host or "localhost"
        port = str(self.config.port or 3306)
        user = self.config.username or "root"

        args = [
            client_exe,
            f"--host={host}",
            f"--port={port}",
            f"--user={user}",
            "--default-character-set=utf8mb4",
            target_database
        ]

        env = os.environ.copy()
        if self.password:
            env["MYSQL_PWD"] = self.password

        try:
            is_gzip = backup_path.endswith(".gz")
            opener = gzip.open if is_gzip else open

            with opener(backup_path, "rb") as f_in:
                proc = subprocess.Popen(args, stdin=f_in, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                _, stderr_bytes = proc.communicate()

            if proc.returncode != 0:
                err_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                logger.error("Error al restaurar MySQL con código %d: %s", proc.returncode, err_text)
                return False, f"Fallo al restaurar: {err_text}"

            if progress_callback:
                progress_callback(100, f"Restauración de [{target_database}] completada exitosamente.")

            return True, f"Base de datos MySQL '{target_database}' restaurada exitosamente."

        except Exception as e:
            return False, f"Error durante la restauración MySQL: {str(e)}"

    def close(self) -> None:
        pass
