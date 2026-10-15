"""
Vista de Ejecución de Copias de Seguridad Manuales
Permite seleccionar servidor, base de datos, tipo de copia (FULL, DIFF, LOG),
carpeta de destino y opciones de verificación con barra de progreso y bitácora en vivo.
"""
import os
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QLineEdit, QCheckBox, QSpinBox, QPushButton,
    QProgressBar, QPlainTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from database.repositories import ConnectionRepository
from core.models import ConnectionConfig, OperationRecord
from ui.workers.connection_worker import LoadDatabasesWorker
from ui.workers.backup_worker import BackupWorker


class ManualBackupView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn_repo = ConnectionRepository()
        self.active_db_worker: Optional[LoadDatabasesWorker] = None
        self.active_backup_worker: Optional[BackupWorker] = None

        self.init_ui()
        self.reload_connections()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_box = QVBoxLayout()
        title = QLabel("Copias de Seguridad Manuales")
        title.setObjectName("viewTitle")
        desc = QLabel("Genere respaldos bajo demanda con verificación de integridad y firma digital SHA-256.")
        desc.setObjectName("viewDescription")
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        # Tarjeta de Configuración de la Operación
        config_card = QFrame()
        config_card.setProperty("class", "card")
        card_layout = QVBoxLayout(config_card)
        card_layout.setSpacing(12)

        # Fila 1: Servidor y Base de Datos
        row1 = QHBoxLayout()
        self.combo_conn = QComboBox()
        self.combo_conn.currentIndexChanged.connect(self.on_connection_changed)
        row1.addWidget(self._create_field("Servidor / Conexión:", self.combo_conn), 1)

        self.combo_db = QComboBox()
        row1.addWidget(self._create_field("Base de Datos:", self.combo_db), 1)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["FULL (Copia Completa)", "DIFFERENTIAL (Diferencial)", "LOG (Registro de Transacciones)"])
        row1.addWidget(self._create_field("Tipo de Respaldo:", self.combo_type), 1)
        card_layout.addLayout(row1)

        # Fila 2: Carpeta de Destino y Nombre de Archivo
        row2 = QHBoxLayout()
        dest_box = QHBoxLayout()
        self.txt_dest = QLineEdit()
        self.txt_dest.setText("C:\\SQL_Backups")
        dest_box.addWidget(self.txt_dest)

        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setProperty("class", "btn-secondary")
        self.btn_browse.clicked.connect(self.browse_destination)
        dest_box.addWidget(self.btn_browse)

        row2.addWidget(self._create_field_layout("Carpeta de Destino:", dest_box), 2)

        self.txt_pattern = QLineEdit()
        self.txt_pattern.setText("{db}_{type}_{date}_{time}.bak")
        row2.addWidget(self._create_field("Patrón de Archivo:", self.txt_pattern), 1)
        card_layout.addLayout(row2)

        # Fila 3: Opciones Avanzadas
        row3 = QHBoxLayout()
        self.chk_compression = QCheckBox("Compresión Nativa (COMPRESSION)")
        self.chk_compression.setChecked(True)
        row3.addWidget(self.chk_compression)

        self.chk_checksum = QCheckBox("Suma de Comprobación (CHECKSUM)")
        self.chk_checksum.setChecked(True)
        row3.addWidget(self.chk_checksum)

        self.chk_verify = QCheckBox("Verificar con Motor (RESTORE VERIFYONLY)")
        self.chk_verify.setChecked(True)
        row3.addWidget(self.chk_verify)

        # Retención
        ret_box = QHBoxLayout()
        ret_lbl = QLabel("Días Retención:")
        ret_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.spin_retention = QSpinBox()
        self.spin_retention.setRange(0, 365)
        self.spin_retention.setValue(15)
        ret_box.addWidget(ret_lbl)
        ret_box.addWidget(self.spin_retention)
        row3.addLayout(ret_box)

        card_layout.addLayout(row3)

        # Botón de Inicio
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_start = QPushButton("▶ Iniciar Copia de Seguridad")
        self.btn_start.setProperty("class", "btn-success")
        self.btn_start.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.btn_start.clicked.connect(self.start_backup)
        btn_layout.addWidget(self.btn_start)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(config_card)

        # Área de Progreso y Bitácora en Vivo
        monitor_title = QLabel("Supervisión en Tiempo Real")
        monitor_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #E2E8F0; margin-top: 4px;")
        main_layout.addWidget(monitor_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setPlaceholderText("La bitácora de eventos y salida técnica aparecerá aquí durante la ejecución...")
        main_layout.addWidget(self.txt_logs)

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

    def reload_connections(self):
        self.combo_conn.clear()
        conns = self.conn_repo.get_all()
        for c in conns:
            self.combo_conn.addItem(c.name, c.id)

    def on_connection_changed(self, index: int):
        conn_id = self.combo_conn.currentData()
        if not conn_id:
            return

        config = self.conn_repo.get_by_id(conn_id)
        if not config:
            return

        # Adaptar patrón de archivo según extensión recomendada del motor
        from connectors.factory import ConnectorFactory
        meta = ConnectorFactory.get_engine_metadata(config.engine)
        ext = meta.get("default_extension", ".bak")
        self.txt_pattern.setText(f"{{db}}_{{type}}_{{date}}_{{time}}{ext}")

        self.combo_db.clear()
        self.combo_db.addItem("Cargando bases de datos...", None)
        self.combo_db.setEnabled(False)

        self.active_db_worker = LoadDatabasesWorker(config)
        self.active_db_worker.databases_loaded.connect(self.on_databases_loaded)
        self.active_db_worker.start()

    def on_databases_loaded(self, success: bool, dbs: list, err: str):
        self.combo_db.clear()
        self.combo_db.setEnabled(True)
        if success and dbs:
            self.combo_db.addItems(dbs)
        else:
            conn_id = self.combo_conn.currentData()
            config = self.conn_repo.get_by_id(conn_id) if conn_id else None
            fallback_db = config.database if config and config.database else ("master" if config and config.engine == "sqlserver" else "")
            if fallback_db:
                self.combo_db.addItem(fallback_db)
            if err:
                self.log_message(f"Aviso al listar bases de datos: {err}")

    def browse_destination(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Destino de Respaldos", self.txt_dest.text())
        if folder:
            self.txt_dest.setText(folder)

    def log_message(self, msg: str):
        self.txt_logs.appendPlainText(msg)

    def start_backup(self):
        conn_id = self.combo_conn.currentData()
        if not conn_id:
            QMessageBox.warning(self, "Validación", "Debe seleccionar un servidor de base de datos.")
            return

        db_name = self.combo_db.currentText()
        if not db_name or "Cargando" in db_name:
            QMessageBox.warning(self, "Validación", "Debe seleccionar una base de datos válida.")
            return

        destination = self.txt_dest.text().strip()
        if not destination:
            QMessageBox.warning(self, "Validación", "Debe indicar una carpeta de destino.")
            return

        conn_config = self.conn_repo.get_by_id(conn_id)
        if not conn_config:
            return

        # Interpretar tipo
        type_idx = self.combo_type.currentIndex()
        backup_type = "FULL" if type_idx == 0 else ("DIFFERENTIAL" if type_idx == 1 else "LOG")

        # Bloquear controles
        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self.txt_logs.clear()
        self.log_message(f"=== INICIANDO OPERACIÓN DE RESPALDO: [{db_name}] ({backup_type}) ===")
        self.log_message(f"Servidor: {conn_config.name} ({conn_config.host})")
        self.log_message(f"Destino: {destination}")

        self.active_backup_worker = BackupWorker(
            conn_config=conn_config,
            database_name=db_name,
            backup_type=backup_type,
            destination_folder=destination,
            file_pattern=self.txt_pattern.text().strip(),
            compression=self.chk_compression.isChecked(),
            checksum=self.chk_checksum.isChecked(),
            verify_after=self.chk_verify.isChecked(),
            retention_days=self.spin_retention.value(),
            min_copies_to_keep=2
        )
        self.active_backup_worker.progress_updated.connect(self.on_backup_progress)
        self.active_backup_worker.backup_finished.connect(self.on_backup_finished)
        self.active_backup_worker.start()

    def on_backup_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.log_message(f"[{percent}%] {msg}")

    def on_backup_finished(self, success: bool, message: str, record: Optional[OperationRecord]):
        self.btn_start.setEnabled(True)
        if success and record:
            self.progress_bar.setValue(100)
            self.log_message("✓ OPERACIÓN COMPLETADA CON ÉXITO")
            self.log_message(f"Ruta del archivo generado: {record.destination_path}")
            self.log_message(f"Tamaño: {record.file_size_formatted} ({record.file_size_bytes} bytes)")
            self.log_message(f"Duración: {record.duration_formatted}")
            self.log_message(f"Firma digital SHA-256: {record.sha256_hash}")
            QMessageBox.information(self, "Backup Exitoso", f"La copia de seguridad de '{record.database_name}' finalizó con éxito.\nTamaño: {record.file_size_formatted}\nSHA-256: {record.sha256_hash[:16]}...")
        else:
            self.log_message(f"✗ ERROR EN LA OPERACIÓN: {message}")
            QMessageBox.critical(self, "Fallo de Backup", f"No se pudo completar la copia de seguridad:\n{message}")
