"""
Módulo Conector para MariaDB (compatible con MySQL).
Reutiliza la lógica de MySQLConnector ya que MariaDB comparte el mismo protocolo y cliente pymysql.
"""

from connectors.mysql_connector import MySQLConnector

class MariaDBConnector(MySQLConnector):
    """Connector for MariaDB servers.
    Inherits all behavior from MySQLConnector because the client library and CLI tools are compatible.
    """
    engine_name = "mariadb"
    default_port = 3306
    # No additional changes needed; backup/restore use the same mysqldump/mysql tools.
