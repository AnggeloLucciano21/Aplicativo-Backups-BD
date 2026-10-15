"""
Pruebas automatizadas para el conector MariaDB (bloque 5).
Se valida que la factoría registre y devuelva una instancia del nuevo conector.
"""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import ConnectionConfig
from connectors.factory import ConnectorFactory
from connectors.mariadb_connector import MariaDBConnector

class TestMariaDBConnector(unittest.TestCase):
    def test_factory_returns_mariadb_connector(self):
        cfg = ConnectionConfig(name="MariaDB_Test", engine="mariadb", host="localhost")
        conn = ConnectorFactory.create_connector(cfg)
        self.assertIsInstance(conn, MariaDBConnector)
        self.assertEqual(conn.engine_name, "mariadb")
        self.assertEqual(conn.default_port, 3306)
        self.assertEqual(conn.default_file_extension, ".sql")

if __name__ == "__main__":
    unittest.main()
