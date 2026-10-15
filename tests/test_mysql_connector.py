"""
Pruebas Automatizadas para el Conector MySQL (Bloque 3)
Valida:
1. Detección de herramientas oficiales de MySQL (mysqldump.exe y mysql.exe).
2. Instanciación a través de ConnectorFactory.
3. Verificación de integridad de archivos de volcado (.sql y .sql.gz).
4. Extracción de metadatos de cabecera de mysqldump.
5. Detección de volcados truncados o incompletos.
6. Manejo controlado de fallos de conexión de red sin excepciones no capturadas.
"""
import os
import sys
import gzip
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.models import ConnectionConfig
from connectors.factory import ConnectorFactory
from connectors.mysql_connector import MySQLConnector


class TestMySQLConnector(unittest.TestCase):

    def setUp(self):
        self.config = ConnectionConfig(
            name="MySQL_Test_Conn",
            engine="mysql",
            host="127.0.0.1",
            port=3306,
            database="test_db",
            username="root"
        )
        self.connector = MySQLConnector(self.config, password="test_password")

    def test_prerequisites_detection(self):
        """Verifica que se detecten las herramientas oficiales de MySQL en el sistema."""
        ok, msg = MySQLConnector.check_prerequisites()
        print(f"\n[MYSQL PREREQUISITES] Detectado: {ok} | Detalle: {msg}")
        self.assertTrue(ok)
        dump_path = MySQLConnector.find_executable("mysqldump.exe")
        client_path = MySQLConnector.find_executable("mysql.exe")
        self.assertIsNotNone(dump_path)
        self.assertIsNotNone(client_path)
        self.assertTrue(os.path.isfile(dump_path))
        self.assertTrue(os.path.isfile(client_path))

    def test_factory_returns_mysql_connector(self):
        """Verifica que ConnectorFactory devuelva una instancia activa de MySQLConnector."""
        conn = ConnectorFactory.create_connector(self.config)
        self.assertIsInstance(conn, MySQLConnector)
        self.assertEqual(conn.engine_name, "mysql")
        self.assertEqual(conn.default_port, 3306)
        self.assertEqual(conn.default_file_extension, ".sql")

    def test_verify_and_headers_valid_dump(self):
        """Verifica un archivo de volcado MySQL íntegro con encabezado y marca final."""
        sample_dump = (
            "-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)\n"
            "-- Host: localhost    Database: clientes_db\n"
            "-- Server version	8.0.45\n\n"
            "DROP TABLE IF EXISTS `clientes`;\n"
            "CREATE TABLE `clientes` (`id` int, `nombre` varchar(50));\n"
            "INSERT INTO `clientes` VALUES (1, 'Acme Corp');\n\n"
            "-- Dump completed on 2026-10-15 10:15:00\n"
        )

        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(sample_dump)
            temp_path = temp_file.name

        try:
            # 1. Comprobar verificación
            ok, msg = self.connector.verify_backup(temp_path)
            self.assertTrue(ok)
            self.assertIn("Dump completed", msg)

            # 2. Comprobar extracción de metadatos
            headers = self.connector.get_backup_headers(temp_path)
            self.assertEqual(headers["database_name"], "clientes_db")
            self.assertIn("MySQL dump", headers["software_version"])
            self.assertEqual(headers["backup_start_date"], "2026-10-15 10:15:00")
            print(f"[MYSQL HEADERS OK] Base: {headers['database_name']} | Versión: {headers['software_version']}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_verify_truncated_dump_fails(self):
        """Verifica que un volcado truncado o cortado a mitad de camino sea detectado como inválido."""
        truncated_dump = (
            "-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)\n"
            "-- Host: localhost    Database: ventas_db\n"
            "CREATE TABLE `ventas` (`id` int);\n"
            # Falta la línea final '-- Dump completed'
        )

        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False, mode="w", encoding="utf-8") as temp_file:
            temp_file.write(truncated_dump)
            temp_path = temp_file.name

        try:
            ok, msg = self.connector.verify_backup(temp_path)
            self.assertFalse(ok)
            self.assertIn("incompleto o truncado", msg)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_verify_gzip_dump(self):
        """Verifica soporte nativo para archivos de volcado comprimidos con GZIP (.sql.gz)."""
        sample_dump = (
            "-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)\n"
            "-- Host: localhost    Database: contabilidad\n"
            "-- Dump completed on 2026-10-15 10:20:00\n"
        ).encode("utf-8")

        temp_gz = tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False)
        temp_gz.close()

        with gzip.open(temp_gz.name, "wb") as gz_file:
            gz_file.write(sample_dump)

        try:
            ok, msg = self.connector.verify_backup(temp_gz.name)
            self.assertTrue(ok)
            headers = self.connector.get_backup_headers(temp_gz.name)
            self.assertEqual(headers["database_name"], "contabilidad")
        finally:
            if os.path.exists(temp_gz.name):
                os.remove(temp_gz.name)

    def test_connection_failure_handling(self):
        """Verifica que un fallo de conexión a un puerto cerrado sea controlado y devuelva mensaje claro."""
        invalid_config = ConnectionConfig(
            name="MySQL_Invalid",
            engine="mysql",
            host="127.0.0.1",
            port=3307,  # Puerto cerrado
            timeout=2
        )
        invalid_conn = MySQLConnector(invalid_config)
        ok, msg, details = invalid_conn.test_connection()
        self.assertFalse(ok)
        self.assertIn("No se pudo conectar", msg)
        print(f"[MYSQL FAILURE HANDLING OK] Mensaje controlado: {msg}")


if __name__ == "__main__":
    unittest.main()
