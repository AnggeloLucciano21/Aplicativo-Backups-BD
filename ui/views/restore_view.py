"""
Vista de Restauración y Recuperación de Bases de Datos
Permite inspeccionar metadatos de archivos .bak, verificar integridad con el motor
y ejecutar procesos de restauración asistidos con confirmación explícita anti-sobrescritura.
"""
import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QLineEdit, QCheckBox, QPushButton,
    QProgressBar, QPlainTextEdit, QFileDialog, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt

from database.repositories import ConnectionRepository
from core.models import ConnectionConfig, OperationRecord
from ui.workers.restore_worker import InspectBackupWorker, RestoreWorker


class RestoreView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn_repo = ConnectionRepository()
        self.active_inspect_worker: Optional[InspectBackupWorker] = None
        self.active_restore_worker: Optional[RestoreWorker] = None

        self.init_ui()
        self.reload_connections()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_box = QVBoxLayout()
        title = QLabel("Restauración y Recuperación de Bases de Datos")
        title.setObjectName("viewTitle")
        desc = QLabel("Recupere bases de datos a partir de respaldos con validación de cabeceras y control anti-sobrescritura.")
        desc.setObjectName("viewDescription")
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        # Tarjeta 1: Selección del Archivo e Inspección
        file_card = QFrame()
        file_card.setProperty("class", "card")
        file_layout = QVBoxLayout(file_card)
        file_layout.setSpacing(10)

        f_title = QLabel("1. Selección e Inspección del Archivo de Respaldo (.bak)")
        f_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38BDF8;")
        file_layout.addWidget(f_title)

        row_file = QHBoxLayout()
        self.combo_conn = QComboBox()
        row_file.addWidget(self._create_field("Servidor Destino:", self.combo_conn), 1)

        file_pick_layout = QHBoxLayout()
        self.txt_file = QLineEdit()
        self.txt_file.setPlaceholderText("Seleccione un archivo de respaldo (.bak)...")
        file_pick_layout.addWidget(self.txt_file)

        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setProperty("class", "btn-secondary")
        self.btn_browse.clicked.connect(self.browse_backup_file)
        file_pick_layout.addWidget(self.btn_browse)

        self.btn_inspect = QPushButton("Inspeccionar Metadatos")
        self.btn_inspect.setProperty("class", "btn-primary")
        self.btn_inspect.clicked.connect(self.inspect_backup)
        file_pick_layout.addWidget(self.btn_inspect)

        row_file.addWidget(self._create_field_layout("Archivo .BAK:", file_pick_layout), 2)
        file_layout.addLayout(row_file)

        # Panel de Metadatos Inspeccionados
        self.metadata_frame = QFrame()
        self.metadata_frame.setStyleSheet("background-color: #090D16; border: 1px solid #1E293B; border-radius: 8px; padding: 10px;")
        grid_meta = QGridLayout(self.metadata_frame)
        grid_meta.setContentsMargins(12, 10, 12, 10)
        grid_meta.setSpacing(8)

        self.lbl_orig_db = QLabel("--")
        self.lbl_orig_type = QLabel("--")
        self.lbl_orig_date = QLabel("--")
        self.lbl_orig_ver = QLabel("--")
        self.lbl_verify_status = QLabel("--")

        grid_meta.addWidget(self._meta_label("BD Origen:"), 0, 0)
        grid_meta.addWidget(self.lbl_orig_db, 0, 1)

        grid_meta.addWidget(self._meta_label("Tipo de Respaldo:"), 0, 2)
        grid_meta.addWidget(self.lbl_orig_type, 0, 3)

        grid_meta.addWidget(self._meta_label("Fecha Creación:"), 1, 0)
        grid_meta.addWidget(self.lbl_orig_date, 1, 1)

        grid_meta.addWidget(self._meta_label("Versión SQL Server:"), 1, 2)
        grid_meta.addWidget(self.lbl_orig_ver, 1, 3)

        grid_meta.addWidget(self._meta_label("Integridad (VERIFYONLY):"), 2, 0)
        grid_meta.addWidget(self.lbl_verify_status, 2, 1, 1, 3)

        file_layout.addWidget(self.metadata_frame)
        main_layout.addWidget(file_card)

        # Tarjeta 2: Parámetros de Restauración
        restore_card = QFrame()
        restore_card.setProperty("class", "card")
        r_layout = QVBoxLayout(restore_card)
        r_layout.setSpacing(12)

        r_title = QLabel("2. Destino y Medidas de Seguridad")
        r_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38BDF8;")
        r_layout.addWidget(r_title)

        row_dest = QHBoxLayout()
        self.txt_target_db = QLineEdit()
        self.txt_target_db.setPlaceholderText("Nombre de la base de datos destino")
        row_dest.addWidget(self._create_field("Nombre de Base de Datos a Restaurar:", self.txt_target_db), 2)

        self.chk_replace = QCheckBox("Sobrescribir base de datos existente si ya existe (WITH REPLACE)")
        self.chk_replace.setStyleSheet("color: #F87171; font-weight: 600;")
        row_dest.addWidget(self._create_field("Control de Sobrescritura:", self.chk_replace), 2)
        r_layout.addLayout(row_dest)

        # Botón de Restauración
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        self.btn_restore = QPushButton("⚠ Ejecutar Restauración")
        self.btn_restore.setProperty("class", "btn-danger")
        self.btn_restore.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.btn_restore.clicked.connect(self.confirm_and_restore)
        row_btn.addWidget(self.btn_restore)
        r_layout.addLayout(row_btn)

        main_layout.addWidget(restore_card)

        # Supervisión en Vivo
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.txt_logs = QPlainTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setPlaceholderText("Eventos y registros de la restauración aparecerán aquí...")
        main_layout.addWidget(self.txt_logs)

    def _meta_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 12px;")
        return lbl

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

    def browse_backup_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Archivo de Respaldo", "C:\\SQL_Backups",
            "Todos los Respaldos (*.bak *.sql *.sql.gz *.dmp *.db *.trn *.diff);;Volcados MySQL/PostgreSQL (*.sql *.sql.gz);;Respaldos SQL Server (*.bak *.trn *.diff);;Data Pump Oracle (*.dmp);;Bases SQLite (*.db *.sqlite);;Todos los archivos (*.*)"
        )
        if file:
            self.txt_file.setText(file)
            self.inspect_backup()

    def inspect_backup(self):
        conn_id = self.combo_conn.currentData()
        file_path = self.txt_file.text().strip()

        if not conn_id:
            QMessageBox.warning(self, "Validación", "Seleccione un servidor de destino.")
            return

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Validación", "Seleccione un archivo de copia de seguridad existente.")
            return

        conn = self.conn_repo.get_by_id(conn_id)
        if not conn:
            return

        self.btn_inspect.setEnabled(False)
        self.btn_inspect.setText("Inspeccionando...")

        self.active_inspect_worker = InspectBackupWorker(conn, file_path)
        self.active_inspect_worker.inspection_finished.connect(self.on_inspection_finished)
        self.active_inspect_worker.start()

    def on_inspection_finished(self, success: bool, data: dict):
        self.btn_inspect.setEnabled(True)
        self.btn_inspect.setText("Inspeccionar Metadatos")

        if success:
            headers = data.get("headers", {})
            orig_db = headers.get("database_name", "Desconocida")
            self.lbl_orig_db.setText(orig_db)
            self.lbl_orig_type.setText(headers.get("backup_type", "--"))
            self.lbl_orig_date.setText(headers.get("backup_start_date", "--"))
            self.lbl_orig_ver.setText(f"SQL Server {headers.get('software_version', '--')}")

            v_ok = data.get("verify_only_passed", False)
            if v_ok:
                self.lbl_verify_status.setText("✓ Verificación del conjunto de copias superada exitosamente.")
                self.lbl_verify_status.setStyleSheet("color: #10B981; font-weight: 600;")
            else:
                self.lbl_verify_status.setText(f"✗ Fallo en comprobación: {data.get('verify_only_message')}")
                self.lbl_verify_status.setStyleSheet("color: #EF4444; font-weight: 600;")

            # Sugerir nombre de base de datos
            if not self.txt_target_db.text().strip():
                self.txt_target_db.setText(orig_db)
        else:
            QMessageBox.critical(self, "Error de Inspección", f"No se pudieron leer los metadatos del backup:\n{data.get('error', 'Error desconocido')}")

    def confirm_and_restore(self):
        conn_id = self.combo_conn.currentData()
        backup_file = self.txt_file.text().strip()
        target_db = self.txt_target_db.text().strip()
        replace = self.chk_replace.isChecked()

        if not conn_id or not backup_file or not target_db:
            QMessageBox.warning(self, "Validación", "Complete todos los campos requeridos antes de restaurar.")
            return

        # Advertencia de seguridad explícita (Módulo E y Reglas de Seguridad)
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("¡ADVERTENCIA DE SEGURIDAD CRÍTICA!")

        warning_text = (
            f"Está a punto de ejecutar una operación de RESTAURACIÓN en el servidor.\n\n"
            f"• Base de datos destino: [{target_db}]\n"
            f"• Archivo origen: {backup_file}\n"
            f"• Modo de reemplazo: {'SOBRESCRITURA FORZADA (WITH REPLACE)' if replace else 'Normal'}\n\n"
            "Si la base de datos ya existe, cualquier dato no respaldado podría perderse permanentemente.\n"
            "¿Desea continuar de manera consciente y autorizada?"
        )
        msg_box.setText(warning_text)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        if msg_box.exec() != QMessageBox.Yes:
            return

        conn = self.conn_repo.get_by_id(conn_id)
        if not conn:
            return

        self.btn_restore.setEnabled(False)
        self.progress_bar.setValue(0)
        self.txt_logs.clear()
        self.txt_logs.appendPlainText(f"=== INICIANDO RESTAURACIÓN DE [{target_db}] ===")

        self.active_restore_worker = RestoreWorker(
            conn_config=conn,
            backup_path=backup_file,
            target_database=target_db,
            replace_existing=replace
        )
        self.active_restore_worker.progress_updated.connect(self.on_restore_progress)
        self.active_restore_worker.restore_finished.connect(self.on_restore_finished)
        self.active_restore_worker.start()

    def on_restore_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.txt_logs.appendPlainText(f"[{percent}%] {msg}")

    def on_restore_finished(self, success: bool, msg: str, record: Optional[OperationRecord]):
        self.btn_restore.setEnabled(True)
        if success and record:
            self.progress_bar.setValue(100)
            self.txt_logs.appendPlainText("✓ RESTAURACIÓN COMPLETADA EXITOSAMENTE")
            self.txt_logs.appendPlainText(f"Duración: {record.duration_formatted}")
            QMessageBox.information(self, "Restauración Exitosa", f"La base de datos '{record.database_name}' fue restaurada con éxito.")
        else:
            self.txt_logs.appendPlainText(f"✗ ERROR EN RESTAURACIÓN: {msg}")
            QMessageBox.critical(self, "Fallo de Restauración", f"No se pudo completar la restauración:\n{msg}")
