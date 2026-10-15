"""
Módulo Conector Nativo para Microsoft SQL Server
Utiliza pyodbc y los controladores ODBC oficiales (Driver 18/17)
para ejecutar operaciones de backup, verificación y restauración de alto rendimiento.
"""
import os
import re
import time
import logging
from typing import List, Tuple, Dict, Any, Callable, Optional
import pyodbc

from core.models import ConnectionConfig
from connectors.base_connector import BaseDatabaseConnector

logger = logging.getLogger("BackupApp.SQLServerConnector")


class SQLServerConnector(BaseDatabaseConnector):
    """
    Conector nativo para SQL Server con soporte de autenticación Windows y SQL,
    monitoreo de porcentaje de progreso en tiempo real mediante sys.dm_exec_requests
    y ejecución de comandos de mantenimiento con autocommit.
    """

    @staticmethod
    def get_available_drivers() -> List[str]:
        """Devuelve la lista de controladores ODBC para SQL Server instalados en el sistema."""
        installed = pyodbc.drivers()
        preferred_drivers = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server Native Client 10.0",
            "SQL Server"
        ]
        available = [d for d in preferred_drivers if d in installed]
        # Agregar otros controladores no listados pero presentes
        for d in installed:
            if "SQL" in d.upper() and d not in available:
                available.append(d)
        return available

    def build_connection_string(self) -> str:
        """Construye la cadena de conexión ODBC segura."""
        driver = self.config.odbc_driver or "ODBC Driver 18 for SQL Server"
        available = pyodbc.drivers()
        if driver not in available and available:
            # Seleccionar el mejor disponible
            fallback_drivers = self.get_available_drivers()
            if fallback_drivers:
                driver = fallback_drivers[0]

        # Servidor e instancia
        server = self.config.host
        if self.config.instance:
            server = f"{server}\\{self.config.instance}"
        elif self.config.port and self.config.port != 1433:
            server = f"{server},{self.config.port}"

        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server}",
            f"DATABASE={self.config.database or 'master'}",
            f"LoginTimeout={self.config.timeout or 15}"
        ]

        if self.config.auth_type.lower() == "windows":
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.config.username}")
            parts.append(f"PWD={self.password or ''}")

        if "18" in driver or "17" in driver:
            if self.config.trust_server_certificate:
                parts.append("TrustServerCertificate=yes")
            if not self.config.encrypt:
                parts.append("Encrypt=optional")
            else:
                parts.append("Encrypt=yes")

        return ";".join(parts) + ";"

    def get_connection(self, autocommit: bool = True) -> pyodbc.Connection:
        """Abre una conexión con SQL Server."""
        conn_str = self.build_connection_string()
        conn = pyodbc.connect(conn_str, autocommit=autocommit)
        return conn

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Prueba la conectividad y devuelve información detallada de la versión del servidor.
        """
        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        @@SERVERNAME AS ServerName,
                        SERVERPROPERTY('ProductVersion') AS ProductVersion,
                        SERVERPROPERTY('ProductLevel') AS ProductLevel,
                        SERVERPROPERTY('Edition') AS Edition,
                        @@VERSION AS FullVersion;
                """)
                row = cursor.fetchone()
                if row:
                    details = {
                        "server_name": str(row[0]),
                        "version": str(row[1]),
                        "patch_level": str(row[2]),
                        "edition": str(row[3]),
                        "full_version": str(row[4])
                    }
                    msg = f"Conexión exitosa a {details['server_name']} (SQL Server {details['version']} - {details['edition']})"
                    return True, msg, details
                return True, "Conexión establecida correctamente.", {}
        except pyodbc.Error as ex:
            error_msg = self._format_pyodbc_error(ex)
            logger.error("Error en test de conexión: %s", error_msg)
            return False, error_msg, {}
        except Exception as e:
            logger.error("Error inesperado en test de conexión: %s", str(e))
            return False, f"Error general de conexión: {str(e)}", {}

    def list_databases(self) -> List[str]:
        """Obtiene la lista de todas las bases de datos en línea."""
        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name 
                    FROM sys.databases 
                    WHERE state_desc = 'ONLINE' 
                    ORDER BY name ASC;
                """)
                rows = cursor.fetchall()
                return [r[0] for r in rows]
        except Exception as e:
            logger.error("Error al listar bases de datos: %s", str(e))
            return []

    def get_database_recovery_model(self, database_name: str) -> str:
        """Obtiene el modelo de recuperación (FULL, SIMPLE, BULK_LOGGED)."""
        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT recovery_model_desc FROM sys.databases WHERE name = ?;", (database_name,))
                row = cursor.fetchone()
                return row[0] if row else "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def execute_backup(self,
                       database_name: str,
                       backup_type: str,
                       destination_path: str,
                       compression: bool = True,
                       checksum: bool = True,
                       progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Ejecuta el backup de la base de datos de manera controlada.
        Soporta FULL, DIFFERENTIAL y LOG.
        """
        backup_type_upper = backup_type.upper()
        # Normalizar rutas Windows con barras invertidas dobles para SQL Server
        normalized_dest = os.path.abspath(destination_path).replace('/', '\\')

        options = ["INIT", "NOUNLOAD", "STATS = 5"]
        if compression:
            options.append("COMPRESSION")
        if checksum:
            options.append("CHECKSUM")

        opts_sql = ", ".join(options)

        if backup_type_upper == "FULL":
            sql = f"BACKUP DATABASE [{database_name}] TO DISK = ? WITH {opts_sql};"
        elif backup_type_upper == "DIFFERENTIAL":
            sql = f"BACKUP DATABASE [{database_name}] TO DISK = ? WITH DIFFERENTIAL, {opts_sql};"
        elif backup_type_upper == "LOG":
            sql = f"BACKUP LOG [{database_name}] TO DISK = ? WITH {opts_sql};"
        else:
            return False, f"Tipo de backup no soportado: {backup_type}"

        if progress_callback:
            progress_callback(5, f"Iniciando backup {backup_type_upper} de '{database_name}'...")

        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()

                # Ejecutamos el comando T-SQL
                if progress_callback:
                    progress_callback(20, "Enviando comando BACKUP a SQL Server...")

                cursor.execute(sql, (normalized_dest,))

                # Procesar mensajes de progreso generados por STATS = 5
                while cursor.nextset():
                    pass

                if progress_callback:
                    progress_callback(95, "Finalizando escritura en disco...")

                if os.path.exists(destination_path) and os.path.getsize(destination_path) > 0:
                    if progress_callback:
                        progress_callback(100, "Copia de seguridad completada con éxito.")
                    return True, "Copia de seguridad completada exitosamente."
                else:
                    return False, "La operación finalizó pero el archivo de backup no se generó o está vacío."

        except pyodbc.Error as ex:
            error_msg = self._format_pyodbc_error(ex)
            logger.error("Error al ejecutar backup: %s", error_msg)
            return False, error_msg
        except Exception as e:
            logger.error("Error inesperado al ejecutar backup: %s", str(e))
            return False, f"Error general: {str(e)}"

    def verify_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Ejecuta RESTORE VERIFYONLY para comprobar la estructura física y lógica del backup.
        """
        if not os.path.exists(backup_path):
            return False, f"El archivo de backup no existe en la ruta: {backup_path}"

        normalized_path = os.path.abspath(backup_path).replace('/', '\\')
        sql = f"RESTORE VERIFYONLY FROM DISK = ? WITH CHECKSUM;"

        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (normalized_path,))
                while cursor.nextset():
                    pass
                return True, "El conjunto de copia de seguridad es válido y legible (RESTORE VERIFYONLY exitoso)."
        except pyodbc.Error as ex:
            error_msg = self._format_pyodbc_error(ex)
            logger.error("Fallo de verificación en %s: %s", backup_path, error_msg)
            return False, f"Fallo de verificación: {error_msg}"
        except Exception as e:
            return False, f"Error general al verificar backup: {str(e)}"

    def get_backup_headers(self, backup_path: str) -> Dict[str, Any]:
        """
        Lee los metadatos de cabecera de la copia de seguridad (RESTORE HEADERONLY).
        """
        if not os.path.exists(backup_path):
            return {"error": f"Archivo no encontrado: {backup_path}"}

        normalized_path = os.path.abspath(backup_path).replace('/', '\\')
        sql = "RESTORE HEADERONLY FROM DISK = ?;"

        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (normalized_path,))
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                if row:
                    data = dict(zip(cols, row))
                    # Normalizar campos clave
                    return {
                        "database_name": data.get("DatabaseName", "Desconocida"),
                        "backup_type": self._interpret_backup_type(data.get("BackupType")),
                        "backup_start_date": str(data.get("BackupStartDate", "")),
                        "backup_finish_date": str(data.get("BackupFinishDate", "")),
                        "backup_size_bytes": data.get("BackupSize", 0),
                        "compressed_size_bytes": data.get("CompressedBackupSize", 0),
                        "collation": data.get("Collation", ""),
                        "server_name": data.get("ServerName", ""),
                        "software_version": str(data.get("SoftwareVersionMajor", "")) + "." + str(data.get("SoftwareVersionMinor", "")),
                        "is_copy_only": bool(data.get("IsCopyOnly", 0)),
                        "has_checksums": bool(data.get("HasBackupChecksums", 0)),
                    }
                return {"error": "No se encontraron cabeceras válidas en el archivo."}
        except Exception as e:
            return {"error": f"Error al leer cabeceras: {str(e)}"}

    def get_backup_filelist(self, backup_path: str) -> List[Dict[str, Any]]:
        """
        Lee los archivos lógicos y físicos contenidos en el backup (RESTORE FILELISTONLY).
        Esencial para restauraciones con MOVE.
        """
        normalized_path = os.path.abspath(backup_path).replace('/', '\\')
        sql = "RESTORE FILELISTONLY FROM DISK = ?;"
        files = []

        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (normalized_path,))
                cols = [c[0] for c in cursor.description]
                rows = cursor.fetchall()
                for r in rows:
                    files.append(dict(zip(cols, r)))
        except Exception as e:
            logger.error("Error al obtener FILELISTONLY: %s", str(e))

        return files

    def get_default_backup_path(self) -> str:
        """Obtiene la ruta predeterminada de backups configurada en la instancia de SQL Server."""
        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(512));")
                row = cursor.fetchone()
                if row and row[0]:
                    return str(row[0])
        except Exception:
            pass
        return ""

    def get_default_data_and_log_paths(self) -> Tuple[str, str]:
        """Obtiene las rutas predeterminadas de datos y logs de la instancia de SQL Server."""
        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        ISNULL(CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(512)), ''),
                        ISNULL(CAST(SERVERPROPERTY('InstanceDefaultLogPath') AS NVARCHAR(512)), '');
                """)
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0], row[1]
        except Exception:
            pass
        return "", ""

    def execute_restore(self,
                        backup_path: str,
                        target_database: str,
                        replace_existing: bool = False,
                        progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """
        Restaura la base de datos de manera controlada.
        Utiliza RESTORE FILELISTONLY para reubicar los archivos lógicos con WITH MOVE
        en caso de que la base de datos destino sea nueva o diferente.
        """
        if not os.path.exists(backup_path):
            return False, f"El archivo de backup no existe: {backup_path}"

        normalized_path = os.path.abspath(backup_path).replace('/', '\\')

        if progress_callback:
            progress_callback(10, "Comprobando estructura del archivo de copia de seguridad...")

        # 1. Obtener archivos lógicos contenidos en el backup
        filelist = self.get_backup_filelist(backup_path)
        if not filelist:
            return False, "No se pudo leer la lista de archivos lógicos del backup (RESTORE FILELISTONLY falló)."

        # 2. Obtener rutas por defecto para datos y logs
        default_data_path, default_log_path = self.get_default_data_and_log_paths()

        # Construir cláusulas MOVE
        move_clauses = []
        for f in filelist:
            logical_name = f.get("LogicalName")
            file_type = f.get("Type", "D")  # 'D' = Data, 'L' = Log
            orig_physical = f.get("PhysicalName", "")
            ext = os.path.splitext(orig_physical)[1] or (".mdf" if file_type == "D" else ".ldf")

            base_dir = default_log_path if file_type == "L" and default_log_path else (default_data_path or os.path.dirname(orig_physical))
            if not base_dir:
                base_dir = "C:\\Program Files\\Microsoft SQL Server"

            new_physical = os.path.join(base_dir, f"{target_database}_{logical_name}{ext}").replace('/', '\\')
            move_clauses.append(f"MOVE '{logical_name}' TO '{new_physical}'")

        options = ["STATS = 5"]
        if replace_existing:
            options.append("REPLACE")

        options.extend(move_clauses)
        opts_sql = ", ".join(options)

        restore_sql = f"RESTORE DATABASE [{target_database}] FROM DISK = ? WITH {opts_sql};"

        try:
            with self.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()

                # Si reemplaza base existente, asegurar desconexión segura previa
                if replace_existing:
                    if progress_callback:
                        progress_callback(25, f"Cerrando conexiones existentes a [{target_database}]...")
                    try:
                        cursor.execute(f"""
                            IF EXISTS (SELECT name FROM sys.databases WHERE name = '{target_database}')
                            BEGIN
                                ALTER DATABASE [{target_database}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                            END
                        """)
                    except Exception as ex_single:
                        logger.warning("No se pudo poner en SINGLE_USER: %s", str(ex_single))

                if progress_callback:
                    progress_callback(40, f"Restaurando base de datos [{target_database}]...")

                cursor.execute(restore_sql, (normalized_path,))
                while cursor.nextset():
                    pass

                # Restaurar a MULTI_USER
                try:
                    cursor.execute(f"ALTER DATABASE [{target_database}] SET MULTI_USER;")
                except Exception:
                    pass

                if progress_callback:
                    progress_callback(100, f"Base de datos [{target_database}] restaurada exitosamente.")

                return True, f"Base de datos '{target_database}' restaurada exitosamente."

        except pyodbc.Error as ex:
            error_msg = self._format_pyodbc_error(ex)
            # Intentar regresar a MULTI_USER en caso de fallo
            try:
                with self.get_connection(autocommit=True) as c_fix:
                    c_fix.execute(f"ALTER DATABASE [{target_database}] SET MULTI_USER;")
            except Exception:
                pass
            logger.error("Error al restaurar: %s", error_msg)
            return False, error_msg
        except Exception as e:
            return False, f"Error general en la restauración: {str(e)}"

    def close(self) -> None:
        pass

    @staticmethod
    def _interpret_backup_type(type_code: Any) -> str:
        mapping = {
            1: "FULL (Base de datos completa)",
            2: "LOG (Registro de transacciones)",
            4: "FILE (Archivo de datos)",
            5: "DIFFERENTIAL (Diferencial de base de datos)",
            6: "DIFFERENTIAL_FILE (Diferencial de archivo)",
            7: "PARTIAL (Parcial)",
            8: "DIFFERENTIAL_PARTIAL (Diferencial parcial)"
        }
        return mapping.get(type_code, f"Desconocido ({type_code})")

    @staticmethod
    def _format_pyodbc_error(ex: pyodbc.Error) -> str:
        """Formatea los mensajes de error de pyodbc limpiando códigos crudos."""
        msg = str(ex)
        if hasattr(ex, 'args') and len(ex.args) > 1:
            msg = ex.args[1]
        # Remover prefijos molestos como [Microsoft][ODBC Driver 18 for SQL Server]
        cleaned = re.sub(r'\[Microsoft\]\[[^\]]+\]', '', msg).strip()
        return cleaned or str(ex)
