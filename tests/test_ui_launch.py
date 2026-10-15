"""
Prueba de Validación de Inicialización de la Interfaz Gráfica PySide6
Comprueba que todos los componentes, vistas y ventanas se instancien sin errores de Qt.
"""
import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow


class TestUIAvailability(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Crear instancia de QApplication en modo offscreen si no existe
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_main_window_instantiation(self):
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.stack.count(), 7)

        # Probar cambio a cada vista
        for idx in range(7):
            window.on_nav_clicked(idx)
            self.assertEqual(window.stack.currentIndex(), idx)

        print("\n[UI TEST OK] Todas las 7 vistas de la aplicación se instanciaron y navegaron correctamente en modo offscreen.")


if __name__ == "__main__":
    unittest.main()
