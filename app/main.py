"""
Punto de Entrada Principal de la Aplicación de Escritorio
Inicializa el entorno gráfico, el subsistema de logging seguro y la ventana principal.
"""
import sys
import os
import logging
import traceback

# Asegurar que el directorio raíz del proyecto esté en el PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from logging_system.audit_logger import setup_logging
from ui.main_window import MainWindow

logger = setup_logging()


def exception_hook(exctype, value, tb):
    """Manejador global de excepciones no capturadas para auditoría técnica."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical("Excepción no capturada en la aplicación:\n%s", err_msg)
    # Si la aplicación ya está corriendo, mostrar diálogo informativo
    if QApplication.instance():
        try:
            QMessageBox.critical(
                None,
                "Error Inesperado del Sistema",
                f"Se produjo un error no controlado:\n{str(value)}\n\nConsulte el archivo de log para más detalles."
            )
        except Exception:
            pass
    sys.__excepthook__(exctype, value, tb)


def main():
    sys.excepthook = exception_hook

    logger.info("Iniciando DataShield Enterprise Backup & Recovery...")

    app = QApplication(sys.argv)
    app.setApplicationName("DataShield Enterprise")
    app.setOrganizationName("Enterprise Security")

    window = MainWindow()
    window.show()

    logger.info("Ventana principal desplegada correctamente.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
