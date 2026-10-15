"""
Vista de Gestión de Conexiones a Servidores de Bases de Datos
Formulario adaptativo multi-motor (SQL Server, MySQL, PostgreSQL, MariaDB,
Oracle, SQLite, Sybase) con almacenamiento seguro en Windows Credential Manager.
"""
from typing import Optional, Dict, Any, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSplitter,
    QFileDialog
)
from PySide6.QtCore import Qt

from core.models import ConnectionConfig
from database.repositories import ConnectionRepository
from connectors.sqlserver_connector import SQLServerConnector
from connectors.factory import ConnectorFactory
from security.credentials_manager import CredentialsManager
from ui.workers.connection_worker import ConnectionTestWorker


class ConnectionsView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn_repo = ConnectionRepository()
        self.active_test_worker: Optional[ConnectionTestWorker] = None
        self.selected_connection_id: Optional[int] = None

        self.init_ui()
        self.load_connections_table()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_box = QVBoxLayout()
        title = QLabel("Gestión de Conexiones de Servidores")
        title.setObjectName("viewTitle")
        desc = QLabel("Configure y administre servidores de bases de datos multi-motor con credenciales protegidas por DPAPI.")
        desc.setObjectName("viewDescription")
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        # Splitter horizontal: Tabla a la izquierda y Formulario a la derecha
        splitter = QSplitter(Qt.Horizontal)

        # PANEL IZQUIERDO: Lista de Conexiones
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        list_header = QHBoxLayout()
        lbl_list = QLabel("Conexiones Registradas")
        lbl_list.setStyleSheet("font-size: 14px; font-weight: 700; color: #E2E8F0;")
        list_header.addWidget(lbl_list)
        list_header.addStretch()

        self.btn_new = QPushButton("+ Nueva")
        self.btn_new.setProperty("class", "btn-secondary")
        self.btn_new.clicked.connect(self.clear_form)
        list_header.addWidget(self.btn_new)
        left_layout.addLayout(list_header)

        self.table_conns = QTableWidget(0, 5)
        self.table_conns.setHorizontalHeaderLabels(["ID", "Nombre", "Motor", "Host / Destino", "Autenticación"])
        self.table_conns.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_conns.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_conns.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_conns.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_conns.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_conns.itemSelectionChanged.connect(self.on_table_selection_changed)
        left_layout.addWidget(self.table_conns)

        splitter.addWidget(left_widget)

        # PANEL DERECHO: Formulario Adaptativo
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(12)

        form_card = QFrame()
        form_card.setProperty("class", "card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(12)

        form_title = QLabel("Detalles de Conexión")
        form_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8; margin-bottom: 4px;")
        form_layout.addWidget(form_title)

        # Fila 1: Nombre y Motor
        row1 = QHBoxLayout()
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ej. Producción Principal")
        row1.addWidget(self._create_field("Nombre Conexión:", self.txt_name), 2)

        self.combo_engine = QComboBox()
        engines = ConnectorFactory.get_supported_engines()
        for eng in engines:
            label = eng["name"]
            if not eng["is_active"]:
                label += " (Próx. Bloque)"
            self.combo_engine.addItem(label, eng["id"])

        self.combo_engine.currentIndexChanged.connect(self.on_engine_changed)
        row1.addWidget(self._create_field("Motor de Base de Datos:", self.combo_engine), 2)
        form_layout.addLayout(row1)

        # WIDGET ESPECÍFICO SQLITE: Selector de archivo local
        self.sqlite_container = QWidget()
        sqlite_layout = QVBoxLayout(self.sqlite_container)
        sqlite_layout.setContentsMargins(0, 0, 0, 0)

        sqlite_pick_layout = QHBoxLayout()
        self.txt_sqlite_path = QLineEdit()
        self.txt_sqlite_path.setPlaceholderText("Ruta al archivo SQLite (ej. C:\\datos\\app.db)")
        sqlite_pick_layout.addWidget(self.txt_sqlite_path)

        self.btn_browse_sqlite = QPushButton("Examinar...")
        self.btn_browse_sqlite.setProperty("class", "btn-secondary")
        self.btn_browse_sqlite.clicked.connect(self.browse_sqlite_file)
        sqlite_pick_layout.addWidget(self.btn_browse_sqlite)

        sqlite_layout.addWidget(self._create_field_layout("Archivo de Base de Datos SQLite:", sqlite_pick_layout))
        form_layout.addWidget(self.sqlite_container)
        self.sqlite_container.setVisible(False)

        # WIDGET DE RED: Host, Puerto, Instancia (Para motores cliente-servidor)
        self.network_container = QWidget()
        net_layout = QVBoxLayout(self.network_container)
        net_layout.setContentsMargins(0, 0, 0, 0)
        net_layout.setSpacing(10)

        # Host, Puerto, Instancia
        row_host = QHBoxLayout()
        self.txt_host = QLineEdit()
        self.txt_host.setText("localhost")
        row_host.addWidget(self._create_field("Host / IP:", self.txt_host), 2)

        self.txt_port = QSpinBox()
        self.txt_port.setRange(1, 65535)
        self.txt_port.setValue(1433)
        self.field_port_widget = self._create_field("Puerto:", self.txt_port)
        row_host.addWidget(self.field_port_widget, 1)

        self.txt_instance = QLineEdit()
        self.txt_instance.setPlaceholderText("Opcional")
        self.field_instance_widget = self._create_field("Instancia:", self.txt_instance)
        row_host.addWidget(self.field_instance_widget, 1)
        net_layout.addLayout(row_host)

        # Base de datos o Servicio (Oracle)
        row_db = QHBoxLayout()
        self.txt_database = QLineEdit()
        self.txt_database.setText("master")
        self.field_db_widget = self._create_field("Base de Datos Inicial:", self.txt_database)
        row_db.addWidget(self.field_db_widget, 1)

        self.txt_service_name = QLineEdit()
        self.txt_service_name.setPlaceholderText("Ej. ORCL o XEPDB1")
        self.field_service_widget = self._create_field("Service Name / SID (Oracle):", self.txt_service_name)
        row_db.addWidget(self.field_service_widget, 1)

        self.combo_driver = QComboBox()
        available_drivers = SQLServerConnector.get_available_drivers()
        if available_drivers:
            self.combo_driver.addItems(available_drivers)
        else:
            self.combo_driver.addItem("ODBC Driver 18 for SQL Server")
        self.field_driver_widget = self._create_field("Controlador ODBC:", self.combo_driver)
        row_db.addWidget(self.field_driver_widget, 1)
        net_layout.addLayout(row_db)

        # Autenticación (Solo aplicable cuando el motor lo soporte)
        self.auth_type_container = QWidget()
        row_auth = QHBoxLayout(self.auth_type_container)
        row_auth.setContentsMargins(0, 0, 0, 0)
        self.combo_auth = QComboBox()
        self.combo_auth.addItems(["Autenticación de Windows (SSPI)", "Autenticación con Usuario / Password"])
        self.combo_auth.currentIndexChanged.connect(self.on_auth_type_changed)
        row_auth.addWidget(self._create_field("Método de Autenticación:", self.combo_auth))
        net_layout.addWidget(self.auth_type_container)

        # Usuario y Contraseña
        self.auth_credentials_widget = QWidget()
        auth_cred_layout = QHBoxLayout(self.auth_credentials_widget)
        auth_cred_layout.setContentsMargins(0, 0, 0, 0)

        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("Usuario")
        auth_cred_layout.addWidget(self._create_field("Usuario:", self.txt_username))

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText("Contraseña (protegida por Windows Credential Manager)")
        auth_cred_layout.addWidget(self._create_field("Contraseña:", self.txt_password))
        net_layout.addWidget(self.auth_credentials_widget)

        # Opciones avanzadas de seguridad
        self.adv_opts_container = QWidget()
        row_opts = QHBoxLayout(self.adv_opts_container)
        row_opts.setContentsMargins(0, 0, 0, 0)
        self.chk_trust_cert = QCheckBox("Confiar en Certificado de Servidor (TrustServerCertificate)")
        self.chk_trust_cert.setChecked(True)
        self.chk_encrypt = QCheckBox("Cifrar Conexión (Encrypt / SSL)")
        self.chk_encrypt.setChecked(False)
        row_opts.addWidget(self.chk_trust_cert)
        row_opts.addWidget(self.chk_encrypt)
        net_layout.addWidget(self.adv_opts_container)

        form_layout.addWidget(self.network_container)

        # Banner de Estado del Test
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setWordWrap(True)
        self.lbl_test_result.setStyleSheet("padding: 8px; border-radius: 6px; font-size: 12px;")
        self.lbl_test_result.setVisible(False)
        form_layout.addWidget(self.lbl_test_result)

        # Botonera de Acciones
        btn_bar = QHBoxLayout()
        self.btn_test = QPushButton("Probar Conexión")
        self.btn_test.setProperty("class", "btn-secondary")
        self.btn_test.clicked.connect(self.test_connection)
        btn_bar.addWidget(self.btn_test)

        btn_bar.addStretch()

        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_connection)
        btn_bar.addWidget(self.btn_delete)

        self.btn_save = QPushButton("Guardar Conexión")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self.save_connection)
        btn_bar.addWidget(self.btn_save)

        form_layout.addLayout(btn_bar)

        right_layout.addWidget(form_card)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([380, 520])

        main_layout.addWidget(splitter)

        # Adaptar vista inicial
        self.on_engine_changed(0)

    def _create_field(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        v.addWidget(lbl)
        v.addWidget(widget)
        return container

    def _create_field_layout(self, label_text: str, layout: QHBoxLayout) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        v.addWidget(lbl)
        v.addLayout(layout)
        return container

    def on_engine_changed(self, index: int):
        engine_id = self.combo_engine.currentData()
        if not engine_id:
            return

        meta = ConnectorFactory.get_engine_metadata(engine_id)

        # Visibilidad según tipo de motor
        if engine_id == "sqlite":
            self.sqlite_container.setVisible(True)
            self.network_container.setVisible(False)
        else:
            self.sqlite_container.setVisible(False)
            self.network_container.setVisible(True)

            # Ajuste de puerto predeterminado si el usuario no ha especificado uno
            default_port = meta.get("default_port", 1433)
            if default_port:
                self.txt_port.setValue(default_port)

            # Campos específicos
            is_sqlserver = (engine_id == "sqlserver")
            is_oracle = (engine_id == "oracle")

            self.field_instance_widget.setVisible(is_sqlserver)
            self.field_driver_widget.setVisible(is_sqlserver or engine_id == "sybase")
            self.auth_type_container.setVisible(is_sqlserver)
            self.field_service_widget.setVisible(is_oracle)
            self.field_db_widget.setVisible(not is_oracle)

            # Para motores que no admiten Windows Auth, forzar credenciales visibles
            if not is_sqlserver:
                self.auth_credentials_widget.setVisible(True)
                if engine_id == "postgresql":
                    self.txt_database.setText("postgres")
                    self.txt_username.setPlaceholderText("postgres")
                elif engine_id in ["mysql", "mariadb"]:
                    self.txt_username.setPlaceholderText("root")
                elif engine_id == "oracle":
                    self.txt_username.setPlaceholderText("SYSTEM o usuario de base de datos")
            else:
                self.auth_credentials_widget.setVisible(self.combo_auth.currentIndex() == 1)

    def on_auth_type_changed(self, index: int):
        engine_id = self.combo_engine.currentData()
        if engine_id == "sqlserver":
            self.auth_credentials_widget.setVisible(index == 1)
        else:
            self.auth_credentials_widget.setVisible(True)

    def browse_sqlite_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Base de Datos SQLite", "",
            "Bases de Datos SQLite (*.db *.sqlite *.sqlite3);;Todos los archivos (*.*)"
        )
        if file:
            self.txt_sqlite_path.setText(file)

    def load_connections_table(self):
        conns = self.conn_repo.get_all()
        self.table_conns.setRowCount(len(conns))
        for row_idx, c in enumerate(conns):
            self.table_conns.setItem(row_idx, 0, QTableWidgetItem(str(c.id)))
            self.table_conns.setItem(row_idx, 1, QTableWidgetItem(c.name))
            self.table_conns.setItem(row_idx, 2, QTableWidgetItem(c.engine.upper()))

            host_display = c.sqlite_path if c.engine == "sqlite" else f"{c.host}:{c.port}"
            self.table_conns.setItem(row_idx, 3, QTableWidgetItem(host_display))

            auth_desc = "Windows (SSPI)" if c.auth_type.lower() == "windows" else f"Usuario: {c.username}"
            if c.engine == "sqlite":
                auth_desc = "Archivo Local"
            self.table_conns.setItem(row_idx, 4, QTableWidgetItem(auth_desc))

    def on_table_selection_changed(self):
        selected_rows = self.table_conns.selectedItems()
        if not selected_rows:
            return
        row = self.table_conns.currentRow()
        conn_id_item = self.table_conns.item(row, 0)
        if not conn_id_item:
            return

        conn_id = int(conn_id_item.text())
        self.load_connection_into_form(conn_id)

    def load_connection_into_form(self, conn_id: int):
        conn = self.conn_repo.get_by_id(conn_id)
        if not conn:
            return

        self.selected_connection_id = conn.id
        self.txt_name.setText(conn.name)

        idx_eng = self.combo_engine.findData(conn.engine)
        if idx_eng >= 0:
            self.combo_engine.setCurrentIndex(idx_eng)

        self.txt_host.setText(conn.host)
        self.txt_port.setValue(conn.port or 1433)
        self.txt_instance.setText(conn.instance or "")
        self.txt_database.setText(conn.database or "master")
        self.txt_service_name.setText(conn.service_name or "")
        self.txt_sqlite_path.setText(conn.sqlite_path or "")

        idx_driver = self.combo_driver.findText(conn.odbc_driver)
        if idx_driver >= 0:
            self.combo_driver.setCurrentIndex(idx_driver)

        if conn.auth_type.lower() == "windows":
            self.combo_auth.setCurrentIndex(0)
            self.txt_username.clear()
            self.txt_password.clear()
        else:
            self.combo_auth.setCurrentIndex(1)
            self.txt_username.setText(conn.username or "")
            saved_pwd = CredentialsManager.get_password(conn.name, conn.username)
            self.txt_password.setText(saved_pwd or "")

        self.chk_trust_cert.setChecked(conn.trust_server_certificate)
        self.chk_encrypt.setChecked(conn.encrypt)

        self.btn_delete.setEnabled(True)
        self.lbl_test_result.setVisible(False)

    def clear_form(self):
        self.selected_connection_id = None
        self.table_conns.clearSelection()
        self.txt_name.clear()
        self.combo_engine.setCurrentIndex(0)
        self.txt_host.setText("localhost")
        self.txt_port.setValue(1433)
        self.txt_instance.clear()
        self.txt_database.setText("master")
        self.txt_service_name.clear()
        self.txt_sqlite_path.clear()
        self.combo_auth.setCurrentIndex(0)
        self.txt_username.clear()
        self.txt_password.clear()
        self.chk_trust_cert.setChecked(True)
        self.chk_encrypt.setChecked(False)
        self.btn_delete.setEnabled(False)
        self.lbl_test_result.setVisible(False)

    def _get_form_config(self) -> ConnectionConfig:
        engine_id = self.combo_engine.currentData() or "sqlserver"
        auth_type = "windows" if (engine_id == "sqlserver" and self.combo_auth.currentIndex() == 0) else "sql"

        return ConnectionConfig(
            id=self.selected_connection_id,
            name=self.txt_name.text().strip(),
            engine=engine_id,
            host=self.txt_host.text().strip() or "localhost",
            port=self.txt_port.value() if engine_id != "sqlite" else None,
            instance=self.txt_instance.text().strip(),
            database=self.txt_database.text().strip() or "master",
            service_name=self.txt_service_name.text().strip(),
            sqlite_path=self.txt_sqlite_path.text().strip(),
            auth_type=auth_type,
            username=self.txt_username.text().strip() if auth_type != "windows" else "",
            odbc_driver=self.combo_driver.currentText(),
            trust_server_certificate=self.chk_trust_cert.isChecked(),
            encrypt=self.chk_encrypt.isChecked(),
            timeout=15
        )

    def test_connection(self):
        config = self._get_form_config()
        if not config.name:
            config.name = "Prueba Temporal"

        password = self.txt_password.text() if config.auth_type != "windows" else None

        self.btn_test.setEnabled(False)
        self.btn_test.setText("Probando conexión...")
        self.lbl_test_result.setVisible(True)
        self.lbl_test_result.setStyleSheet("background-color: #1E293B; color: #38BDF8; padding: 10px; border-radius: 6px;")
        self.lbl_test_result.setText("⏳ Conectando al servidor...")

        self.active_test_worker = ConnectionTestWorker(config, password=password)
        self.active_test_worker.result_ready.connect(self.on_test_finished)
        self.active_test_worker.start()

    def on_test_finished(self, success: bool, msg: str, details: dict):
        self.btn_test.setEnabled(True)
        self.btn_test.setText("Probar Conexión")
        self.lbl_test_result.setVisible(True)

        if success:
            self.lbl_test_result.setStyleSheet("background-color: #064E3B; color: #34D399; padding: 10px; border-radius: 6px; border: 1px solid #059669;")
            self.lbl_test_result.setText(f"✓ {msg}")
        else:
            self.lbl_test_result.setStyleSheet("background-color: #450A0A; color: #F87171; padding: 10px; border-radius: 6px; border: 1px solid #DC2626;")
            self.lbl_test_result.setText(f"✗ Fallo de Conexión: {msg}")

    def save_connection(self):
        config = self._get_form_config()
        if not config.name:
            QMessageBox.warning(self, "Validación Requerida", "Debe ingresar un nombre para la conexión.")
            return

        if config.engine == "sqlite" and not config.sqlite_path:
            QMessageBox.warning(self, "Validación Requerida", "Debe especificar la ruta del archivo SQLite.")
            return

        # Guardar credencial en Windows Credential Manager
        if config.auth_type != "windows" and config.username:
            pwd = self.txt_password.text()
            CredentialsManager.save_password(config.name, config.username, pwd)

        # Guardar en SQLite
        saved_id = self.conn_repo.save(config)
        self.selected_connection_id = saved_id

        QMessageBox.information(self, "Conexión Guardada", f"La conexión '{config.name}' ({config.engine.upper()}) fue guardada exitosamente.")
        self.load_connections_table()
        self.clear_form()

    def delete_connection(self):
        if not self.selected_connection_id:
            return

        res = QMessageBox.question(
            self, "Confirmar Eliminación",
            "¿Está seguro de eliminar esta conexión?\nLas tareas asociadas y credenciales seguras serán removidas.",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            conn = self.conn_repo.get_by_id(self.selected_connection_id)
            if conn and conn.username:
                CredentialsManager.delete_password(conn.name, conn.username)

            self.conn_repo.delete(self.selected_connection_id)
            self.load_connections_table()
            self.clear_form()
