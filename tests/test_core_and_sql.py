"""
Pruebas Automatizadas de Componentes Críticos y Conexión SQL Server
Valida el funcionamiento de:
1. Almacenamiento seguro de credenciales (keyring / Windows Credential Manager).
2. Base de datos SQLite local (conexiones, tareas, historial).
3. Conector SQL Server con autenticación de Windows contra la instancia local MSSQLSERVER.
4. Integridad de archivos y hash SHA-256.
"""
import os
import sys
import tempfile
import unittest

# Asegurar path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import ConnectionConfig, BackupTaskConfig, OperationRecord
from database.db_manager import DatabaseManager
from database.repositories import ConnectionRepository, BackupTaskRepository, HistoryRepository
from security.credentials_manager import CredentialsManager
from connectors.sqlserver_connector import SQLServerConnector
from backup.integrity import IntegrityVerifier
from backup.retention import StorageManager


class TestCoreModules(unittest.TestCase):

    def setUp(self):
        # Crear base de datos SQLite temporal en memoria / archivo temporal
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
        self.conn_repo = ConnectionRepository(self.db_manager)
        self.task_repo = BackupTaskRepository(self.db_manager)
        self.hist_repo = HistoryRepository(self.db_manager)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_database_crud(self):
        """Prueba inserción, consulta y borrado en SQLite."""
        conn = ConnectionConfig(
            name="Servidor Local Test",
            host="localhost",
            database="master",
            auth_type="windows"
        )
        conn_id = self.conn_repo.save(conn)
        self.assertIsNotNone(conn_id)

        retrieved = self.conn_repo.get_by_id(conn_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Servidor Local Test")

        # Historial
        rec = OperationRecord(
            connection_name="Servidor Local Test",
            database_name="master",
            operation_type="BACKUP_FULL",
            status="SUCCESS",
            destination_path="C:\\backups\\master.bak",
            file_size_bytes=1048576,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        rec_id = self.hist_repo.add_record(rec)
        self.assertIsNotNone(rec_id)

        stats = self.hist_repo.get_dashboard_metrics()
        self.assertEqual(stats["total_connections"], 1)
        self.assertEqual(stats["total_backups"], 1)
        self.assertEqual(stats["success_backups"], 1)

    def test_credentials_manager(self):
        """Prueba de almacenamiento y recuperación segura con Windows Credential Manager."""
        test_conn = "UnitTestConn_SecTest"
        test_user = "sa_test"
        test_pass = "ComplexP@ssw0rd!2026"

        saved = CredentialsManager.save_password(test_conn, test_user, test_pass)
        self.assertTrue(saved)

        retrieved = CredentialsManager.get_password(test_conn, test_user)
        self.assertEqual(retrieved, test_pass)

        deleted = CredentialsManager.delete_password(test_conn, test_user)
        self.assertTrue(deleted)

    def test_integrity_verifier(self):
        """Prueba cálculo de SHA-256 e integridad física."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        temp_file.write(b"Backup content test string for SHA256")
        temp_file.close()

        sha = IntegrityVerifier.calculate_sha256(temp_file.name)
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 64)

        is_healthy, msg, _ = IntegrityVerifier.check_file_health(temp_file.name, min_expected_bytes=10)
        self.assertTrue(is_healthy)

        os.remove(temp_file.name)

    def test_sqlserver_connection_local(self):
        """Prueba conexión real a la instancia local de SQL Server si el servicio está activo."""
        config = ConnectionConfig(
            name="Instancia Local",
            host="localhost",
            database="master",
            auth_type="windows"
        )
        connector = SQLServerConnector(config)
        ok, msg, details = connector.test_connection()
        print(f"\n[TEST SQL SERVER LOCAL] Resultado: {ok} | Mensaje: {msg}")
        if ok:
            dbs = connector.list_databases()
            print(f"[TEST SQL SERVER LOCAL] Bases de datos detectadas ({len(dbs)}): {dbs[:5]}")
            self.assertIn("master", dbs)


if __name__ == "__main__":
    unittest.main()
