"""
Módulo de Gestión Segura de Credenciales
Utiliza el Administrador de Credenciales de Windows (Windows Credential Manager / DPAPI)
a través de keyring para evitar almacenar contraseñas en texto plano.
"""
import logging
from typing import Optional

logger = logging.getLogger("BackupApp.Security")
SERVICE_NAME = "AplicativoBackupsBD"


class CredentialsManager:
    """
    Gestor seguro de credenciales integrado con Windows Credential Manager.
    Garantiza que ninguna contraseña viaje en texto plano en la base de datos local ni en logs.
    """

    @staticmethod
    def _make_key(connection_name: str, username: str) -> str:
        """Genera una clave única por conexión y usuario."""
        sanitized_conn = connection_name.strip()
        sanitized_user = username.strip()
        return f"{sanitized_conn}::{sanitized_user}"

    @classmethod
    def save_password(cls, connection_name: str, username: str, password: str) -> bool:
        """
        Almacena la contraseña de forma segura en Windows Credential Manager.
        """
        if not password:
            return True
        try:
            import keyring
            key = cls._make_key(connection_name, username)
            keyring.set_password(SERVICE_NAME, key, password)
            logger.info("Credencial guardada de forma segura para la conexión: %s", connection_name)
            return True
        except Exception as e:
            logger.error("Error al almacenar credencial en Windows Credential Manager: %s", str(e))
            return False

    @classmethod
    def get_password(cls, connection_name: str, username: str) -> Optional[str]:
        """
        Recupera la contraseña desde Windows Credential Manager.
        """
        try:
            import keyring
            key = cls._make_key(connection_name, username)
            return keyring.get_password(SERVICE_NAME, key)
        except Exception as e:
            logger.error("Error al obtener credencial de Windows Credential Manager: %s", str(e))
            return None

    @classmethod
    def delete_password(cls, connection_name: str, username: str) -> bool:
        """
        Elimina la credencial del almacén seguro al borrar o modificar una conexión.
        """
        try:
            import keyring
            key = cls._make_key(connection_name, username)
            try:
                keyring.delete_password(SERVICE_NAME, key)
                logger.info("Credencial eliminada para la conexión: %s", connection_name)
            except keyring.errors.PasswordDeleteError:
                # La credencial no existía previamente
                pass
            return True
        except Exception as e:
            logger.error("Error al eliminar credencial segura: %s", str(e))
            return False
