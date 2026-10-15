"""
Pruebas Automatizadas para el Bloque 2: Arquitectura Común Multi-Motor y Factory
Valida:
1. Instanciación y registro de conectores mediante ConnectorFactory.
2. Comportamiento seguro ante motores pendientes (stubs informativos).
3. Persistencia de campos de múltiples motores (service_name, sqlite_path) en SQLite.
4. Adaptación dinámica de campos en la interfaz de conexiones.
"""
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PySide6.QtWidgets import QApplication
from core.models import ConnectionConfig
from database.db_manager import DatabaseManager
from database.repositories import ConnectionRepository
from connectors.factory import ConnectorFactory, PendingEngineStubConnector
from connectors.sqlserver_connector import SQLServerConnector
from ui.views.connections_view import ConnectionsView


class TestBlock2Architecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)
        self.conn_repo = ConnectionRepository(self.db)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_factory_sqlserver_connector(self):
        """Verifica que la factoría devuelva una instancia real de SQLServerConnector."""
        cfg = ConnectionConfig(name="MSSQL_Test", engine="sqlserver", host="localhost")
        connector = ConnectorFactory.create_connector(cfg)
        self.assertIsInstance(connector, SQLServerConnector)
        self.assertEqual(connector.engine_name, "sqlserver")
        self.assertEqual(connector.default_port, 1433)

    def test_factory_pending_engines_safe_stub(self):
        """Verifica que los motores en desarrollo devuelvan un stub seguro con mensaje claro."""
        for eng in ["mysql", "postgresql", "oracle", "sqlite", "sybase"]:
            cfg = ConnectionConfig(name=f"{eng}_Test", engine=eng, host="localhost")
            connector = ConnectorFactory.create_connector(cfg)
            self.assertIsInstance(connector, PendingEngineStubConnector)
            ok, msg, _ = connector.test_connection()
            self.assertFalse(ok)
            self.assertIn("siguientes bloques", msg)

    def test_multi_engine_persistence_sqlite(self):
        """Verifica la persistencia de campos específicos (service_name y sqlite_path)."""
        # Conexión Oracle
        ora_cfg = ConnectionConfig(
            name="Oracle Prod",
            engine="oracle",
            host="192.168.1.50",
            port=1521,
            service_name="ORCL",
            username="SYSTEM"
        )
        ora_id = self.conn_repo.save(ora_cfg)
        retrieved_ora = self.conn_repo.get_by_id(ora_id)
        self.assertEqual(retrieved_ora.service_name, "ORCL")
        self.assertEqual(retrieved_ora.port, 1521)

        # Conexión SQLite
        sqlite_cfg = ConnectionConfig(
            name="SQLite Local App",
            engine="sqlite",
            sqlite_path="C:\\datos\\app.db"
        )
        sqlite_id = self.conn_repo.save(sqlite_cfg)
        retrieved_sqlite = self.conn_repo.get_by_id(sqlite_id)
        self.assertEqual(retrieved_sqlite.sqlite_path, "C:\\datos\\app.db")
        self.assertIsNone(retrieved_sqlite.port)

    def test_connections_view_dynamic_adaptation(self):
        """Verifica que el formulario de conexiones adapte sus campos al cambiar de motor."""
        view = ConnectionsView()
        view.show()

        # Probar cambio a SQLite: debe mostrar sqlite_container y ocultar network_container
        idx_sqlite = view.combo_engine.findData("sqlite")
        self.assertGreaterEqual(idx_sqlite, 0)
        view.combo_engine.setCurrentIndex(idx_sqlite)
        self.assertFalse(view.sqlite_container.isHidden())
        self.assertTrue(view.network_container.isHidden())

        # Probar cambio a Oracle: debe mostrar service_name y ocultar database
        idx_oracle = view.combo_engine.findData("oracle")
        self.assertGreaterEqual(idx_oracle, 0)
        view.combo_engine.setCurrentIndex(idx_oracle)
        self.assertTrue(view.sqlite_container.isHidden())
        self.assertFalse(view.network_container.isHidden())
        self.assertFalse(view.field_service_widget.isHidden())
        self.assertTrue(view.field_db_widget.isHidden())
        self.assertEqual(view.txt_port.value(), 1521)

        # Probar cambio a SQL Server: debe mostrar instance y driver
        idx_sql = view.combo_engine.findData("sqlserver")
        view.combo_engine.setCurrentIndex(idx_sql)
        self.assertFalse(view.field_instance_widget.isHidden())
        self.assertFalse(view.field_driver_widget.isHidden())
        self.assertEqual(view.txt_port.value(), 1433)


if __name__ == "__main__":
    unittest.main()
