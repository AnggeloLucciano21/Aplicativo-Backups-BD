"""
Prueba de Ciclo Completo de Backup y Verificación Real en SQL Server
1. Crea una base de datos temporal de prueba en SQL Server: _Test_Backup_App_DB.
2. Ejecuta un backup FULL nativo a una carpeta temporal.
3. Verifica el archivo mediante RESTORE VERIFYONLY.
4. Calcula hash SHA-256.
5. Inspecciona metadatos con RESTORE HEADERONLY.
6. Restaura la copia en una base de datos alternativa: _Test_Backup_App_DB_Restored.
7. Comprueba existencia y limpia las bases de prueba temporales.
"""
import os
import sys
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import ConnectionConfig
from connectors.sqlserver_connector import SQLServerConnector
from backup.backup_engine import BackupEngine
from restore.restore_engine import RestoreEngine
from database.repositories import HistoryRepository


class TestBackupRestoreLiveCycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = ConnectionConfig(
            name="TestLocalMSSQL",
            host="localhost",
            database="master",
            auth_type="windows"
        )
        cls.connector = SQLServerConnector(cls.config)
        cls.test_db = "_Test_Backup_App_DB"
        cls.restored_db = "_Test_Backup_App_DB_Restored"

        # Crear base de datos de prueba
        with cls.connector.get_connection(autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                IF EXISTS (SELECT name FROM sys.databases WHERE name = '{cls.test_db}')
                    DROP DATABASE [{cls.test_db}];
                IF EXISTS (SELECT name FROM sys.databases WHERE name = '{cls.restored_db}')
                    DROP DATABASE [{cls.restored_db}];
                CREATE DATABASE [{cls.test_db}];
            """)

        # Crear tabla y datos en la base de prueba
        with cls.connector.get_connection(autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"USE [{cls.test_db}]; CREATE TABLE Clientes (Id INT PRIMARY KEY, Nombre NVARCHAR(100));")
            cursor.execute(f"INSERT INTO [{cls.test_db}].dbo.Clientes VALUES (1, 'Empresa Ejemplo S.A.');")

        cls.backup_dir = "C:\\SQL_Backups"

    @classmethod
    def tearDownClass(cls):
        # Limpiar bases de prueba
        try:
            with cls.connector.get_connection(autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    IF EXISTS (SELECT name FROM sys.databases WHERE name = '{cls.test_db}')
                    BEGIN
                        ALTER DATABASE [{cls.test_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                        DROP DATABASE [{cls.test_db}];
                    END
                    IF EXISTS (SELECT name FROM sys.databases WHERE name = '{cls.restored_db}')
                    BEGIN
                        ALTER DATABASE [{cls.restored_db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                        DROP DATABASE [{cls.restored_db}];
                    END
                """)
        except Exception as e:
            print("Error en tearDownClass:", e)

    def test_live_backup_verify_and_restore(self):
        engine = BackupEngine()
        restore_engine = RestoreEngine()

        # 1. Ejecutar Backup
        success, msg, record = engine.run_backup(
            conn_config=self.config,
            database_name=self.test_db,
            backup_type="FULL",
            destination_folder=self.backup_dir,
            compression=True,
            checksum=True,
            verify_after=True
        )
        self.assertTrue(success, f"Fallo al ejecutar backup: {msg}")
        self.assertTrue(os.path.exists(record.destination_path))
        self.assertGreater(record.file_size_bytes, 0)
        self.assertEqual(len(record.sha256_hash), 64)
        print(f"\n[BACKUP LIVE OK] Archivo: {record.destination_path} ({record.file_size_formatted}) SHA256: {record.sha256_hash[:16]}...")

        # 2. Inspeccionar cabeceras
        inspection = restore_engine.inspect_backup(self.config, record.destination_path)
        self.assertTrue(inspection["success"])
        self.assertTrue(inspection["verify_only_passed"])
        self.assertEqual(inspection["headers"]["database_name"], self.test_db)
        print(f"[INSPECT HEADERS OK] BD Origen: {inspection['headers']['database_name']} | Versión Servidor: {inspection['headers']['software_version']}")

        # 3. Restaurar en base de datos secundaria aislada
        r_success, r_msg, r_rec = restore_engine.run_restore(
            conn_config=self.config,
            backup_path=record.destination_path,
            target_database=self.restored_db,
            replace_existing=True
        )
        self.assertTrue(r_success, f"Fallo al restaurar: {r_msg}")
        print(f"[RESTORE LIVE OK] {r_msg}")

        # 4. Validar datos dentro de la base de datos restaurada
        with self.connector.get_connection(autocommit=True) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT Nombre FROM [{self.restored_db}].dbo.Clientes WHERE Id = 1;")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], 'Empresa Ejemplo S.A.')
            print(f"[DATA INTEGRITY VERIFIED] Registro recuperado intacto: {row[0]}")


if __name__ == "__main__":
    unittest.main()
