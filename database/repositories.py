"""
Módulo de Repositorios de Acceso a Datos
Proporciona operaciones CRUD desacopladas para conexiones, tareas e historial de operaciones.
"""
import csv
import io
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from core.models import ConnectionConfig, BackupTaskConfig, OperationRecord
from database.db_manager import DatabaseManager

logger = logging.getLogger("BackupApp.Repositories")


class ConnectionRepository:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def get_all(self) -> List[ConnectionConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM connections ORDER BY name ASC;")
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]

    def get_by_id(self, conn_id: int) -> Optional[ConnectionConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM connections WHERE id = ?;", (conn_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def get_by_name(self, name: str) -> Optional[ConnectionConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM connections WHERE name = ?;", (name,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def save(self, config: ConnectionConfig) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if config.id is None:
                cursor.execute("""
                    INSERT INTO connections (
                        name, engine, host, port, instance, database, auth_type,
                        username, odbc_driver, trust_server_certificate, encrypt, timeout,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    config.name, config.engine, config.host, config.port, config.instance,
                    config.database, config.auth_type, config.username, config.odbc_driver,
                    1 if config.trust_server_certificate else 0,
                    1 if config.encrypt else 0,
                    config.timeout, config.created_at, config.updated_at
                ))
                config.id = cursor.lastrowid
            else:
                cursor.execute("""
                    UPDATE connections SET
                        name = ?, engine = ?, host = ?, port = ?, instance = ?,
                        database = ?, auth_type = ?, username = ?, odbc_driver = ?,
                        trust_server_certificate = ?, encrypt = ?, timeout = ?,
                        updated_at = ?
                    WHERE id = ?;
                """, (
                    config.name, config.engine, config.host, config.port, config.instance,
                    config.database, config.auth_type, config.username, config.odbc_driver,
                    1 if config.trust_server_certificate else 0,
                    1 if config.encrypt else 0,
                    config.timeout, config.updated_at, config.id
                ))
            conn.commit()
            return config.id

    def delete(self, conn_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM connections WHERE id = ?;", (conn_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row) -> ConnectionConfig:
        return ConnectionConfig(
            id=row["id"],
            name=row["name"],
            engine=row["engine"],
            host=row["host"],
            port=row["port"],
            instance=row["instance"] or "",
            database=row["database"] or "master",
            auth_type=row["auth_type"],
            username=row["username"] or "",
            odbc_driver=row["odbc_driver"] or "ODBC Driver 18 for SQL Server",
            trust_server_certificate=bool(row["trust_server_certificate"]),
            encrypt=bool(row["encrypt"]),
            timeout=row["timeout"] or 15,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


class BackupTaskRepository:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def get_all(self) -> List[BackupTaskConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backup_tasks ORDER BY id DESC;")
            return [self._row_to_model(r) for r in cursor.fetchall()]

    def get_active(self) -> List[BackupTaskConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backup_tasks WHERE is_active = 1 ORDER BY schedule_time ASC;")
            return [self._row_to_model(r) for r in cursor.fetchall()]

    def get_by_id(self, task_id: int) -> Optional[BackupTaskConfig]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM backup_tasks WHERE id = ?;", (task_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None

    def save(self, task: BackupTaskConfig) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            if task.id is None:
                cursor.execute("""
                    INSERT INTO backup_tasks (
                        connection_id, connection_name, database_name, backup_type,
                        destination_folder, file_pattern, compression, checksum,
                        verify_after, retention_days, retention_min_copies, is_active,
                        schedule_frequency, schedule_time, schedule_days,
                        use_windows_scheduler, last_run_at, next_run_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    task.connection_id, task.connection_name, task.database_name, task.backup_type,
                    task.destination_folder, task.file_pattern,
                    1 if task.compression else 0,
                    1 if task.checksum else 0,
                    1 if task.verify_after else 0,
                    task.retention_days, task.retention_min_copies,
                    1 if task.is_active else 0,
                    task.schedule_frequency, task.schedule_time, task.schedule_days,
                    1 if task.use_windows_scheduler else 0,
                    task.last_run_at, task.next_run_at, task.created_at
                ))
                task.id = cursor.lastrowid
            else:
                cursor.execute("""
                    UPDATE backup_tasks SET
                        connection_id = ?, connection_name = ?, database_name = ?, backup_type = ?,
                        destination_folder = ?, file_pattern = ?, compression = ?, checksum = ?,
                        verify_after = ?, retention_days = ?, retention_min_copies = ?, is_active = ?,
                        schedule_frequency = ?, schedule_time = ?, schedule_days = ?,
                        use_windows_scheduler = ?, last_run_at = ?, next_run_at = ?
                    WHERE id = ?;
                """, (
                    task.connection_id, task.connection_name, task.database_name, task.backup_type,
                    task.destination_folder, task.file_pattern,
                    1 if task.compression else 0,
                    1 if task.checksum else 0,
                    1 if task.verify_after else 0,
                    task.retention_days, task.retention_min_copies,
                    1 if task.is_active else 0,
                    task.schedule_frequency, task.schedule_time, task.schedule_days,
                    1 if task.use_windows_scheduler else 0,
                    task.last_run_at, task.next_run_at, task.id
                ))
            conn.commit()
            return task.id

    def update_run_times(self, task_id: int, last_run: str, next_run: Optional[str]) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE backup_tasks SET last_run_at = ?, next_run_at = ? WHERE id = ?;", (last_run, next_run, task_id))
            conn.commit()

    def toggle_active(self, task_id: int, is_active: bool) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE backup_tasks SET is_active = ? WHERE id = ?;", (1 if is_active else 0, task_id))
            conn.commit()

    def delete(self, task_id: int) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM backup_tasks WHERE id = ?;", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row) -> BackupTaskConfig:
        return BackupTaskConfig(
            id=row["id"],
            connection_id=row["connection_id"],
            connection_name=row["connection_name"],
            database_name=row["database_name"],
            backup_type=row["backup_type"],
            destination_folder=row["destination_folder"],
            file_pattern=row["file_pattern"],
            compression=bool(row["compression"]),
            checksum=bool(row["checksum"]),
            verify_after=bool(row["verify_after"]),
            retention_days=row["retention_days"],
            retention_min_copies=row["retention_min_copies"],
            is_active=bool(row["is_active"]),
            schedule_frequency=row["schedule_frequency"],
            schedule_time=row["schedule_time"],
            schedule_days=row["schedule_days"] or "",
            use_windows_scheduler=bool(row["use_windows_scheduler"]),
            last_run_at=row["last_run_at"],
            next_run_at=row["next_run_at"],
            created_at=row["created_at"]
        )


class HistoryRepository:
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    def add_record(self, record: OperationRecord) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO operations_history (
                    connection_name, database_name, operation_type, status,
                    started_at, finished_at, duration_seconds, destination_path,
                    file_size_bytes, sha256_hash, user_system, error_message, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                record.connection_name, record.database_name, record.operation_type, record.status,
                record.started_at, record.finished_at, record.duration_seconds, record.destination_path,
                record.file_size_bytes, record.sha256_hash, record.user_system, record.error_message,
                record.details_json
            ))
            conn.commit()
            record.id = cursor.lastrowid
            return record.id

    def update_record(self, record: OperationRecord) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE operations_history SET
                    status = ?, finished_at = ?, duration_seconds = ?,
                    destination_path = ?, file_size_bytes = ?, sha256_hash = ?,
                    error_message = ?, details_json = ?
                WHERE id = ?;
            """, (
                record.status, record.finished_at, record.duration_seconds,
                record.destination_path, record.file_size_bytes, record.sha256_hash,
                record.error_message, record.details_json, record.id
            ))
            conn.commit()

    def get_recent(self, limit: int = 50) -> List[OperationRecord]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM operations_history ORDER BY id DESC LIMIT ?;", (limit,))
            return [self._row_to_model(r) for r in cursor.fetchall()]

    def filter_records(self,
                       server: Optional[str] = None,
                       database: Optional[str] = None,
                       status: Optional[str] = None,
                       date_from: Optional[str] = None,
                       date_to: Optional[str] = None,
                       limit: int = 200) -> List[OperationRecord]:
        query = "SELECT * FROM operations_history WHERE 1=1"
        params: List[Any] = []

        if server:
            query += " AND connection_name LIKE ?"
            params.append(f"%{server}%")
        if database:
            query += " AND database_name LIKE ?"
            params.append(f"%{database}%")
        if status and status != "ALL":
            query += " AND status = ?"
            params.append(status)
        if date_from:
            query += " AND started_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND started_at <= ?"
            params.append(date_to + " 23:59:59")

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [self._row_to_model(r) for r in cursor.fetchall()]

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calcula las métricas reales para el panel principal."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Conexiones totales
            cursor.execute("SELECT COUNT(*) FROM connections;")
            total_connections = cursor.fetchone()[0]

            # Operaciones de backup totales
            cursor.execute("SELECT COUNT(*) FROM operations_history WHERE operation_type LIKE 'BACKUP%';")
            total_backups = cursor.fetchone()[0]

            # Backups exitosos vs fallidos
            cursor.execute("SELECT COUNT(*) FROM operations_history WHERE operation_type LIKE 'BACKUP%' AND status = 'SUCCESS';")
            success_backups = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM operations_history WHERE status = 'FAILED';")
            failed_operations = cursor.fetchone()[0]

            # Último backup exitoso
            cursor.execute("""
                SELECT database_name, finished_at, destination_path, file_size_bytes
                FROM operations_history
                WHERE operation_type LIKE 'BACKUP%' AND status = 'SUCCESS'
                ORDER BY id DESC LIMIT 1;
            """)
            last_success_row = cursor.fetchone()
            last_success = dict(last_success_row) if last_success_row else None

            # Tareas programadas activas
            cursor.execute("SELECT COUNT(*) FROM backup_tasks WHERE is_active = 1;")
            active_tasks = cursor.fetchone()[0]

            return {
                "total_connections": total_connections,
                "total_backups": total_backups,
                "success_backups": success_backups,
                "failed_operations": failed_operations,
                "last_success": last_success,
                "active_tasks": active_tasks
            }

    def export_to_csv_file(self, filepath: str, records: List[OperationRecord]) -> bool:
        """Exporta los registros dados a un archivo CSV con codificación UTF-8 con BOM para Excel."""
        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "Servidor/Conexión", "Base de Datos", "Operación",
                    "Estado", "Inicio", "Fin", "Duración (s)", "Ruta Archivo",
                    "Tamaño (Bytes)", "Tamaño Formato", "SHA-256", "Usuario Sistema", "Error"
                ])
                for r in records:
                    writer.writerow([
                        r.id, r.connection_name, r.database_name, r.operation_type,
                        r.status, r.started_at, r.finished_at or "", f"{r.duration_seconds:.2f}",
                        r.destination_path, r.file_size_bytes, r.file_size_formatted,
                        r.sha256_hash, r.user_system, r.error_message
                    ])
            return True
        except Exception as e:
            logger.error("Error al exportar a CSV: %s", str(e))
            return False

    @staticmethod
    def _row_to_model(row) -> OperationRecord:
        return OperationRecord(
            id=row["id"],
            connection_name=row["connection_name"],
            database_name=row["database_name"],
            operation_type=row["operation_type"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            duration_seconds=row["duration_seconds"] or 0.0,
            destination_path=row["destination_path"] or "",
            file_size_bytes=row["file_size_bytes"] or 0,
            sha256_hash=row["sha256_hash"] or "",
            user_system=row["user_system"] or "",
            error_message=row["error_message"] or "",
            details_json=row["details_json"] or "{}"
        )
