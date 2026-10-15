# DataShield Enterprise — Sistema de Gestión y Respaldo de Bases de Datos

Aplicativo de escritorio empresarial desarrollado en **Python** y **PySide6 (Qt6)** para la administración, ejecución manual, programación automática, verificación criptográfica e inspección y restauración asistida de copias de seguridad de bases de datos relacionales, con soporte nativo de alto rendimiento para **Microsoft SQL Server**.

---

## Características Principales

### 📊 Módulo A. Gestión de Conexiones
- Registro de múltiples servidores SQL Server (locales o remotos).
- Soporte para **Autenticación Integrada de Windows (SSPI)** y **Autenticación SQL Server** (usuario y contraseña).
- Detección automática de los controladores ODBC instalados (`ODBC Driver 18 for SQL Server`, `ODBC Driver 17`, etc.).
- **Seguridad nativa**: Las contraseñas se almacenan cifradas en el **Administrador de Credenciales de Windows (Windows Credential Manager / DPAPI)** a través de `keyring`. **Cero contraseñas en texto plano**.
- Comprobación asíncrona de conectividad en segundo plano con obtención de la versión exacta y edición del motor.

### 💾 Módulo B. Copias de Seguridad Manuales
- Selección de servidor y carga dinámica asíncrona de bases de datos.
- Tipos de backup disponibles:
  - **FULL** (Completo).
  - **DIFFERENTIAL** (Diferencial).
  - **LOG** (Registro de transacciones).
- Opciones nativas avanzadas: **COMPRESSION** (compresión en tiempo real), **CHECKSUM** (verificación de páginas de disco) y **INIT** (reemplazo seguro de conjunto de medios).
- **Supervisión real en vivo**: Barra de progreso interactiva (0 a 100%) y bitácora técnica de eventos en tiempo real sin bloquear la interfaz (`QThread`).

### ⏱ Módulo C. Backups Automáticos y Programación
- Calendarización periódica: **Diaria, Semanal o Mensual** a horas específicas.
- Políticas de retención configurables por tarea.
- **Doble motor de ejecución**:
  1. *Programador en tiempo de ejecución*: Cuando la aplicación gráfica está abierta.
  2. *Integración con el Programador de Tareas de Windows (`schtasks`)*: Crea tareas programadas en el sistema operativo que ejecutan el motor CLI autónomo (`app/cli.py`) **incluso con la aplicación gráfica cerrada**.

### 📜 Módulo D. Historial y Auditoría
- Registro de trazabilidad inmutable en base de datos local SQLite: servidor, base de datos, tipo de operación, estado (`SUCCESS`, `FAILED`, `IN_PROGRESS`), fecha y hora, duración, tamaño del archivo y usuario del sistema.
- Búsqueda por texto, filtro por servidor, por estado y por rango de fechas.
- **Exportación a CSV**: Formato compatible con Microsoft Excel (codificación UTF-8 con BOM).
- Visualización de detalles técnicos y excepciones del motor para diagnóstico forense.

### 🔄 Módulo E. Restauración y Recuperación
- Selección de archivo `.bak` con explorador de archivos.
- **Inspección previa de metadatos**: Ejecuta `RESTORE HEADERONLY` y `RESTORE FILELISTONLY` para mostrar base de datos de origen, fecha de backup, versión del servidor y nombres lógicos.
- **Protección contra sobrescrituras**: Requiere confirmación explícita mediante diálogo modal con advertencias visuales antes de aplicar `WITH REPLACE`.
- Soporte automático de cláusulas `WITH MOVE` para restaurar copias con nombres alternativos o en bases de prueba aisladas.

### 🛡 Módulo F. Verificación e Integridad Criptográfica
- Verificación estructural con el motor mediante `RESTORE VERIFYONLY WITH CHECKSUM`.
- Comprobación de existencia y tamaño mínimo en el sistema de archivos.
- **Cálculo de firma digital SHA-256** por bloques de memoria para auditar la inmutabilidad de los archivos de backup generados.

### 💽 Módulo G. Administración del Almacenamiento y Retención
- Supervisión en tiempo real del espacio total, usado y libre en las unidades de disco con alertas de espacio bajo (< 5 GB o < 10%).
- **Regla inquebrantable de retención**: La política de retención elimina backups caducados pero **NUNCA elimina la última copia válida disponible**, asegurando que siempre exista un punto de recuperación.
- Explorador de carpetas de backup con cálculo de espacio acumulado.

### 📈 Módulo H. Panel Principal (Dashboard)
- Indicadores KPI en tiempo real: Servidores activos, Total de backups realizados, Tasa global de éxito, Tareas automáticas activas y Espacio libre en disco.
- Banner de estado con el último respaldo exitoso registrado.
- Tabla resumida con las últimas operaciones y códigos de estado por color.

---

## Arquitectura del Proyecto

```
Aplicativo-Backups-BD/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Punto de entrada de la GUI (PySide6)
│   └── cli.py                      # Ejecutor CLI autónomo para el Programador de Windows
├── core/
│   ├── __init__.py
│   └── models.py                   # Entidades de dominio (ConnectionConfig, BackupTask, etc.)
├── database/
│   ├── __init__.py
│   ├── db_manager.py               # Gestor SQLite local con modo WAL
│   └── repositories.py             # Repositorios CRUD e índices de auditoría
├── security/
│   ├── __init__.py
│   └── credentials_manager.py      # Integración con Windows Credential Manager (keyring)
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py           # Interfaz abstracta multi-motor
│   └── sqlserver_connector.py      # Conector nativo SQL Server (pyodbc, T-SQL nativo)
├── backup/
│   ├── __init__.py
│   ├── backup_engine.py            # Orquestador del ciclo de vida de copias
│   ├── integrity.py                # Verificación física y cálculo SHA-256 en bloques
│   └── retention.py                # Políticas de rotación y preservación de última copia
├── restore/
│   ├── __init__.py
│   └── restore_engine.py           # Inspección de cabeceras y restauración asistida
├── scheduler/
│   ├── __init__.py
│   └── windows_task_scheduler.py   # Integrador seguro con schtasks.exe
├── logging_system/
│   ├── __init__.py
│   └── audit_logger.py             # Logger rotativo con sanitización de contraseñas
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # Ventana principal y barra de navegación lateral
│   ├── styles.py                   # Tema Modern Corporate Slate Dark (QSS)
│   ├── workers/                    # Hilos en segundo plano (QThread)
│   │   ├── connection_worker.py
│   │   ├── backup_worker.py
│   │   └── restore_worker.py
│   └── views/                      # Vistas independientes por módulo
│       ├── dashboard_view.py
│       ├── connections_view.py
│       ├── manual_backup_view.py
│       ├── restore_view.py
│       ├── scheduler_view.py
│       ├── history_view.py
│       └── storage_view.py
├── tests/
│   ├── __init__.py
│   ├── test_core_and_sql.py        # Pruebas de SQLite, Keyring y conectividad
│   ├── test_backup_restore_cycle.py # Ciclo completo real (Backup, SHA256, Verify, Restore)
│   └── test_ui_launch.py           # Verificación de inicialización de la interfaz
├── requirements.txt
├── run_app.bat                     # Lanzador directo de la aplicación en Windows
├── build_executable.bat            # Compilador a binario .exe con PyInstaller
└── README.md
```

---

## Requisitos Previos

1. **Sistema Operativo:** Windows 10, Windows 11 o Windows Server 2016+.
2. **Python:** 3.10 o superior (verificado con Python 3.12.6 x64).
3. **Controlador ODBC de SQL Server:**
   - Se recomienda `ODBC Driver 18 for SQL Server` o `ODBC Driver 17 for SQL Server` ([Descarga oficial de Microsoft](https://learn.microsoft.com/es-es/sql/connect/odbc/download-odbc-driver-for-sql-server)).
4. **Permisos de carpeta:**
   - La carpeta de destino de respaldos (por ejemplo `C:\SQL_Backups`) debe tener permisos concedidos al servicio de SQL Server (`NT Service\MSSQLSERVER` o grupo `Users`) para permitir la escritura del archivo `.bak`.

---

## Instalación y Puesta en Marcha

### Opción 1. Ejecución Rápida
Simplemente haga doble clic en el archivo:
```bat
run_app.bat
```

### Opción 2. Instalación Manual con Entorno Virtual
Abra una consola de PowerShell o CMD en la carpeta del proyecto:

1. **Crear y activar el entorno virtual:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Instalar dependencias requeridas:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Ejecutar la suite de pruebas automatizadas:**
   ```powershell
   python -m unittest discover -s tests -p "test_*.py"
   ```

4. **Iniciar la aplicación gráfica:**
   ```powershell
   python app\main.py
   ```

---

## Compilación a Ejecutable Windows (.exe)

Para generar un ejecutable independiente que pueda distribuirse a otros equipos sin necesidad de tener Python instalado:

Ejecute el script:
```bat
build_executable.bat
```
El archivo ejecutable se compilará en:
`.\dist\DataShieldBackup\DataShieldBackup.exe`

---

## Medidas de Seguridad Implementadas

1. **Almacenamiento de Credenciales:** Las contraseñas de las conexiones SQL nunca se guardan en SQLite, ni en archivos de configuración, ni en texto plano; se delegan a las APIs nativas de **Windows Credential Manager / DPAPI**.
2. **Sanitización de Logs:** El subsistema de auditoría incluye filtros mediante expresiones regulares que anonimizan automáticamente cualquier parámetro `Password=********` o `PWD=********` antes de escribir en disco.
3. **Invocación Segura de Procesos:** La integración con `schtasks.exe` se realiza mediante listas de argumentos estrictas en `subprocess.run`, evitando vulnerabilidades de inyección de comandos en el shell.
4. **Protección Anti-Sobrescritura:** La restauración de bases de datos exige confirmación interactiva explícita cuando se especifica la cláusula `WITH REPLACE`.
5. **No Bloqueo de Interfaz:** Todas las operaciones de I/O pesadas corren en subprocesos `QThread` dedicados, garantizando fluidez constante y control en la ventana principal.
