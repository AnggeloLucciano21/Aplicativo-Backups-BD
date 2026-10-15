# ROADMAP: Ampliación Multi-Motor de DataShield Enterprise

Este documento establece el plan de trabajo modular, el estado de avance por bloques y el registro de cambios para la incorporación progresiva de múltiples gestores de bases de datos relacionales en la plataforma.

---

## 1. Estado de los Bloques de Trabajo

| Bloque | Descripción | Estado | Fecha de Finalización | Notas / Verificación |
| :---: | :--- | :---: | :---: | :--- |
| **Bloque 1** | Análisis del proyecto actual, arquitectura y plan de cambios | **COMPLETADO** | 2026-10-15 | Inspección del entorno, detección de herramientas y definición del plan maestro. |
| **Bloque 2** | Arquitectura común (Factoría de Conectores) y adaptación dinámica de la UI de conexiones | **COMPLETADO** | 2026-10-15 | Implementación de `ConnectorFactory`, desacoplamiento de motores y formulario adaptativo. 10/10 pruebas OK. |
| **Bloque 3** | Implementación del motor **MySQL** y validación | **COMPLETADO** | 2026-10-15 | Conector `MySQLConnector`, detección de `mysqldump.exe` y `mysql.exe`, verificación y restauración. 16/16 pruebas OK. |
| **Bloque 4** | Implementación del motor **PostgreSQL** y validación | *PENDIENTE* | — | Integración de `pg_dump` y conector `psycopg2` / CLI. |
| **Bloque 5** | Implementación del motor **MariaDB** y validación | *PENDIENTE* | — | Compatibilidad con protocolo MySQL / MariaDB dump y binarios dedicados. |
| **Bloque 6** | Implementación del motor **SAP Sybase ASE** y requisitos | *PENDIENTE* | — | Evaluación de driver ODBC ASE, T-SQL de Sybase (`DUMP DATABASE`) o CLI `isql`. |
| **Bloque 7** | Implementación de **Oracle Database** y **SQLite** | *PENDIENTE* | — | Oracle (`expdp`/`impdp`/`oracledb` sobre servicio ORCL local activo) y SQLite (API nativa `sqlite3.backup`). |
| **Bloque 8** | Integración total con Historial, Scheduler, Verificación y Dashboard | *PENDIENTE* | — | Homogeneización de reportes, SHA-256 e integración con Windows Task Scheduler. |
| **Bloque 9** | Pruebas integradas, control de calidad, empaquetado y documentación | *PENDIENTE* | — | Suite de pruebas automatizadas y actualización de manuales. |

---

## 2. Análisis del Sistema Actual y Reutilización de Componentes

### Componentes Actuales y su Nivel de Reutilización
1. **Modelos de Dominio (`core/models.py`):**
   - **Alta reutilización.** `OperationRecord` y `BackupTaskConfig` son universales para cualquier motor.
   - **Ajuste requerido en `ConnectionConfig`:** Agregar campos opcionales específicos: `service_name` (Oracle), `sqlite_path` (SQLite) y valores de puerto predeterminados por motor.

2. **Gestor de Credenciales (`security/credentials_manager.py`):**
   - **100% Reutilizable.** Almacena cualquier credencial en **Windows Credential Manager / DPAPI** de manera totalmente segura, sin depender del motor.

3. **Cálculo de Integridad y Almacenamiento (`backup/integrity.py` y `backup/retention.py`):**
   - **100% Reutilizable.** El cálculo del hash SHA-256 en bloques de memoria y la regla de no eliminar nunca el último backup válido operan a nivel de sistema de archivos sin acoplamiento al motor de base de datos.

4. **Base de Datos Local y Auditoría (`database/`):**
   - **100% Reutilizable.** La base SQLite local ya posee el campo `engine` en la tabla `connections`, lista para persistir conexiones de cualquier gestor.

5. **Conector Base Abstracto (`connectors/base_connector.py`):**
   - **Reutilizable y extensible.** Define el contrato estándar (`test_connection`, `list_databases`, `execute_backup`, `verify_backup`, `get_backup_headers`, `execute_restore`).
   - Se adicionarán métodos auxiliares de metadatos propios de cada motor (ej. extensiones de archivo recomendadas: `.bak` para SQL Server, `.sql`/`.sql.gz` para MySQL/PostgreSQL, `.dmp` para Oracle, `.db` para SQLite).

6. **Motores de Operación (`backup/backup_engine.py` y `restore/restore_engine.py`):**
   - Actualmente instancian directamente `SQLServerConnector`.
   - Se desacoplarán mediante el patrón **Factory / Adapter**:
     ```python
     connector = ConnectorFactory.create_connector(conn_config, password)
     ```

7. **Interfaz Gráfica (`ui/`):**
   - La estructura de navegación en barra lateral y vistas (`QStackedWidget`) se mantiene intacta.
   - En `ui/views/connections_view.py`, los campos del formulario se adaptarán dinámicamente según el motor seleccionado en el combo (ocultando opciones no aplicables y mostrando las requeridas).

---

## 3. Diagnóstico de Herramientas Disponibles en el Entorno

- **Microsoft SQL Server:** Servicio `MSSQLSERVER` en ejecución, ODBC Driver 18/17 disponible.
- **Oracle Database:** Servicio `OracleServiceORCL` y Listener `OracleOraDB19Home1TNSListener` en ejecución en `C:\ORACLE\`. Herramientas `expdp.exe`, `impdp.exe`, `sqlplus.exe` y `rman.exe` disponibles en `C:\ORACLE\bin`.
- **MySQL:** Herramientas cliente instaladas en `C:\Program Files\MySQL\MySQL Workbench 8.0 CE\` (`mysql.exe`, `mysqldump.exe`, `mysqlsh.exe`).
- **SQLite:** Soporte nativo incorporado en la librería estándar de Python (`sqlite3`) con API nativa `connection.backup()`.
- **PostgreSQL y MariaDB:** Compatibles mediante clientes estándar, CLI (`mysqldump`/`pg_dump`) o conectores Python dedicados.
- **SAP Sybase ASE:** Compatible mediante `pyodbc` con controlador ODBC de Sybase o clientes T-SQL.

---

## 4. Próximo Paso (Bloque 2)
Implementar la arquitectura común de adaptadores ([connectors/factory.py](file:///c:/Users/user/Desktop/Aplicativo%20BACKUPS%20BD/Aplicativo-Backups-BD/connectors/factory.py)) y adaptar el formulario de conexiones en [ui/views/connections_view.py](file:///c:/Users/user/Desktop/Aplicativo%20BACKUPS%20BD/Aplicativo-Backups-BD/ui/views/connections_view.py) para alternar dinámicamente según el motor seleccionado.
