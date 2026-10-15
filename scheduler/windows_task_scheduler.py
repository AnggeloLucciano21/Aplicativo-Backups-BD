"""
Módulo de Integración con el Programador de Tareas de Windows (schtasks)
Permite programar la ejecución autónoma de backups en Windows Task Scheduler
para que los respaldos se efectúen puntualmente sin importar si la aplicación GUI está abierta.
"""
import os
import sys
import subprocess
import logging
from typing import Tuple

logger = logging.getLogger("BackupApp.WindowsScheduler")
TASK_PREFIX = "AplicativoBackupsBD_Task_"


class WindowsTaskScheduler:
    """
    Administrador de tareas programadas nativas en Windows mediante schtasks.exe.
    """

    @staticmethod
    def _get_python_path() -> str:
        """Obtiene la ruta absoluta al ejecutable de Python o venv."""
        return sys.executable

    @staticmethod
    def _get_cli_path() -> str:
        """Obtiene la ruta al script CLI."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "app", "cli.py")

    @classmethod
    def get_task_name(cls, task_id: int) -> str:
        return f"{TASK_PREFIX}{task_id}"

    @classmethod
    def register_task(cls,
                      task_id: int,
                      frequency: str,
                      time_hhmm: str,
                      days: str = "") -> Tuple[bool, str]:
        """
        Crea o actualiza una tarea programada en el Programador de Tareas de Windows.
        frequency: 'DAILY', 'WEEKLY', 'MONTHLY'
        time_hhmm: '02:00' (formato 24h)
        days: 'MON,WED,FRI' (para semanal)
        """
        task_name = cls.get_task_name(task_id)
        python_exe = cls._get_python_path()
        cli_script = cls._get_cli_path()

        # Construir comando exacto: "python.exe" "C:\...\app\cli.py" --task-id <id>
        command_to_run = f'"{python_exe}" "{cli_script}" --task-id {task_id}'

        # Mapear frecuencia a schtasks /SC
        sc_map = {
            "DAILY": "DAILY",
            "WEEKLY": "WEEKLY",
            "MONTHLY": "MONTHLY"
        }
        sc = sc_map.get(frequency.upper(), "DAILY")

        args = [
            "schtasks", "/Create",
            "/TN", task_name,
            "/TR", command_to_run,
            "/SC", sc,
            "/ST", time_hhmm,
            "/F"  # Forzar sobrescritura si ya existe
        ]

        if sc == "WEEKLY" and days:
            args.extend(["/D", days.upper()])

        try:
            logger.info("Registrando tarea en Windows Scheduler: %s a las %s", task_name, time_hhmm)
            res = subprocess.run(args, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return True, f"Tarea registrada exitosamente en Windows Task Scheduler ({task_name})."
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                logger.error("Error al registrar tarea en schtasks: %s", err_msg)
                return False, f"Fallo al registrar en Windows: {err_msg}"
        except Exception as e:
            logger.error("Excepción al invocar schtasks: %s", str(e))
            return False, f"Error al ejecutar schtasks: {str(e)}"

    @classmethod
    def delete_task(cls, task_id: int) -> Tuple[bool, str]:
        """Elimina la tarea programada de Windows."""
        task_name = cls.get_task_name(task_id)
        args = ["schtasks", "/Delete", "/TN", task_name, "/F"]

        try:
            res = subprocess.run(args, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                logger.info("Tarea eliminada de Windows Scheduler: %s", task_name)
                return True, "Tarea eliminada exitosamente del Programador de Windows."
            else:
                return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    @classmethod
    def run_task_now(cls, task_id: int) -> Tuple[bool, str]:
        """Dispara inmediatamente la ejecución de la tarea en Windows."""
        task_name = cls.get_task_name(task_id)
        args = ["schtasks", "/Run", "/TN", task_name]

        try:
            res = subprocess.run(args, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return True, f"Ejecución de '{task_name}' disparada con éxito."
            else:
                return False, res.stderr.strip() or res.stdout.strip()
        except Exception as e:
            return False, str(e)

    @classmethod
    def exists(cls, task_id: int) -> bool:
        """Comprueba si la tarea existe en Windows Scheduler."""
        task_name = cls.get_task_name(task_id)
        args = ["schtasks", "/Query", "/TN", task_name]
        try:
            res = subprocess.run(args, capture_output=True, text=True, check=False)
            return res.returncode == 0
        except Exception:
            return False
