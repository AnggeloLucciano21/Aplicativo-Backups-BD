"""
Punto de Entrada CLI Autónomo para Tareas Programadas de Windows
Permite ejecutar copias de seguridad automáticas en segundo plano
incluso cuando la interfaz gráfica del usuario está completamente cerrada.
"""
import sys
import os
import argparse
import logging

# Asegurar que el directorio raíz del proyecto esté en sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from logging_system.audit_logger import setup_logging
from database.repositories import ConnectionRepository, BackupTaskRepository, HistoryRepository
from backup.backup_engine import BackupEngine

logger = setup_logging()


def run_task(task_id: int) -> int:
    """Ejecuta una tarea programada por su ID."""
    logger.info("Iniciando ejecución programada de la tarea ID: %d", task_id)

    task_repo = BackupTaskRepository()
    conn_repo = ConnectionRepository()
    engine = BackupEngine()

    task = task_repo.get_by_id(task_id)
    if not task:
        logger.error("No se encontró la tarea ID %d en la base de datos.", task_id)
        return 1

    if not task.is_active:
        logger.warning("La tarea ID %d está desactivada. Omitiendo ejecución.", task_id)
        return 0

    conn_config = conn_repo.get_by_id(task.connection_id)
    if not conn_config:
        logger.error("No se encontró la conexión asociada ID %d para la tarea.", task.connection_id)
        return 1

    success, msg, record = engine.run_backup(
        conn_config=conn_config,
        database_name=task.database_name,
        backup_type=task.backup_type,
        destination_folder=task.destination_folder,
        file_pattern=task.file_pattern,
        compression=task.compression,
        checksum=task.checksum,
        verify_after=task.verify_after,
        retention_days=task.retention_days,
        min_copies_to_keep=task.retention_min_copies,
        progress_callback=lambda p, m: logger.info("[%d%%] %s", p, m)
    )

    from datetime import datetime
    task_repo.update_run_times(task.id, datetime.now().isoformat(), None)

    if success:
        logger.info("Tarea ID %d completada exitosamente. Archivo: %s", task_id, record.destination_path)
        return 0
    else:
        logger.error("Fallo al ejecutar tarea ID %d: %s", task_id, msg)
        return 2


def main():
    parser = argparse.ArgumentParser(description="Ejecutor CLI de Backups para Tareas Programadas")
    parser.add_argument("--task-id", type=int, required=True, help="ID de la tarea de backup a ejecutar")
    args = parser.parse_args()

    exit_code = run_task(args.task_id)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
