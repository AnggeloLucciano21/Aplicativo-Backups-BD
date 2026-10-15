"""
Pruebas automatizadas para el conector PostgreSQL (Bloque 4)
Cubre:
1. Detección de herramientas externas (pg_dump, pg_restore, psql).
2. Creación vía ConnectorFactory.
3. test_connection (mock psycopg2).
4. execute_backup (mock subprocess).
5. verify_backup (mock subprocess).
6. get_backup_headers (mock subprocess).
7. execute_restore (mock subprocess y creación de DB).
"""

import unittest
from unittest import mock
import os
import sys
import pathlib

# Añadir el raíz del proyecto al sys.path (en caso de que pytest lo haya hecho ya)
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.models import ConnectionConfig
from connectors.factory import ConnectorFactory
from connectors.postgresql_connector import PostgreSQLConnector

class TestPostgreSQLConnector(unittest.TestCase):
    def setUp(self):
        self.config = ConnectionConfig(
            name="Postgres_Test_Conn",
            engine="postgresql",
            host="127.0.0.1",
            port=5432,
            database="testdb",
            username="postgres",
        )
        self.password = "test_password"
        self.connector = PostgreSQLConnector(self.config, password=self.password)

    @mock.patch.object(PostgreSQLConnector, 'find_executable')
    def test_prerequisites_detection(self, mock_find):
        # Simular que todas las herramientas están presentes
        mock_find.side_effect = lambda exe: f"C:/fake/path/{exe}"
        ok, msg = PostgreSQLConnector.check_prerequisites()
        self.assertTrue(ok)
        self.assertIn('pg_dump.exe', msg)
        self.assertIn('pg_restore.exe', msg)
        self.assertIn('psql.exe', msg)
        # Verificar que se llamaron 3 veces
        self.assertEqual(mock_find.call_count, 3)

    def test_factory_returns_postgresql_connector(self):
        conn = ConnectorFactory.create_connector(self.config)
        self.assertIsInstance(conn, PostgreSQLConnector)
        self.assertEqual(conn.engine_name, "postgresql")
        self.assertEqual(conn.default_port, 5432)
        self.assertEqual(conn.default_file_extension, ".sql")

    @mock.patch('psycopg2.connect')
    def test_test_connection_success(self, mock_connect):
        mock_conn = mock.Mock()
        mock_cursor = mock.Mock()
        mock_cursor.fetchone.return_value = ["PostgreSQL 15.3 on x86_64-pc-windows-msvc"]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        ok, msg, details = self.connector.test_connection()
        self.assertTrue(ok)
        self.assertIn('Conexión exitosa', msg)
        self.assertIn('PostgreSQL', details['version'])

    @mock.patch('subprocess.Popen')
    @mock.patch.object(PostgreSQLConnector, 'find_executable')
    def test_execute_backup_success(self, mock_find, mock_popen):
        # Simular que pg_dump está disponible
        mock_find.return_value = r"C:\\Program Files\\PostgreSQL\\bin\\pg_dump.exe"
        # Simular proceso exitoso
        mock_proc = mock.Mock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b'', b'')
        mock_popen.return_value = mock_proc
        ok, msg = self.connector.execute_backup(
            database_name="testdb",
            backup_type="FULL",
            destination_path="tmp/test_dump.sql",
            compression=False,
            progress_callback=lambda p, s: None,
        )
        self.assertTrue(ok)
        self.assertIn('Backup PostgreSQL guardado', msg)
        # Verificar que se llamó a pg_dump con los argumentos esperados
        args_passed = mock_popen.call_args[0][0]
        self.assertIn('pg_dump.exe', args_passed[0])
        self.assertIn('testdb', args_passed)

    @mock.patch('subprocess.Popen')
    @mock.patch.object(PostgreSQLConnector, 'find_executable')
    def test_verify_backup_success(self, mock_find, mock_popen):
        mock_find.return_value = r"C:\\Program Files\\PostgreSQL\\bin\\pg_restore.exe"
        mock_proc = mock.Mock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b'list output', b'')
        mock_popen.return_value = mock_proc
        ok, msg = self.connector.verify_backup('tmp/dump.sql')
        self.assertTrue(ok)
        self.assertIn('verificado', msg.lower())

    @mock.patch('subprocess.Popen')
    @mock.patch.object(PostgreSQLConnector, 'find_executable')
    def test_get_backup_headers(self, mock_find, mock_popen):
        mock_find.return_value = r"C:\\Program Files\\PostgreSQL\\bin\\pg_restore.exe"
        mock_proc = mock.Mock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"; 3300 0 0 DATABASE public\n-- Dumped by pg_dump version 15.3 on 2026-10-15 12:00:00", b'')
        mock_popen.return_value = mock_proc
        headers = self.connector.get_backup_headers('tmp/dump.sql')
        self.assertEqual(headers['software_version'], 'PostgreSQL')
        self.assertIn('backup_start_date', headers)

    @mock.patch('subprocess.Popen')
    @mock.patch.object(PostgreSQLConnector, 'find_executable')
    @mock.patch('psycopg2.connect')
    def test_execute_restore_success(self, mock_connect, mock_find, mock_popen):
        # Simular que psql y pg_restore están disponibles
        def find_side(exe):
            return f"C:/fake/{exe}" if exe in ('psql.exe', 'pg_restore.exe') else None
        mock_find.side_effect = find_side
        # Mock para crear y drop DB
        mock_admin_conn = mock.Mock()
        mock_admin_conn.cursor.return_value = mock.Mock()
        mock_connect.return_value = mock_admin_conn
        # Mock proceso de restauración exitoso
        mock_proc = mock.Mock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b'', b'')
        mock_popen.return_value = mock_proc
        ok, msg = self.connector.execute_restore(
            backup_path='tmp/dump.sql',
            target_database='restored_db',
            replace_existing=True,
            progress_callback=lambda p, s: None,
        )
        self.assertTrue(ok)
        self.assertIn('restaurada exitosamente', msg.lower())

if __name__ == '__main__':
    unittest.main()

