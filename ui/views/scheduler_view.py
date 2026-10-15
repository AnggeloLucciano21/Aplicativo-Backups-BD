"""
Vista del Programador de Tareas Automáticas (Scheduler)
Permite calendarizar backups periódicos (diarios, semanales, mensuales)
con integración opcional al Programador de Tareas de Windows (schtasks)
para su ejecución autónoma con la app cerrada.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QLineEdit, QTimeEdit, QSpinBox, QCheckBox,
    QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTime

from core.models import BackupTaskConfig
from database.repositories import BackupTaskRepository, ConnectionRepository
from scheduler.windows_task_scheduler import WindowsTaskScheduler
from ui.workers.connection_worker import LoadDatabasesWorker


class SchedulerView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_repo = BackupTaskRepository()
        self.conn_repo = ConnectionRepository()
        self.selected_task_id: Optional[int] = None
        self.active_db_worker: Optional[LoadDatabasesWorker] = None

        self.init_ui()
        self.reload_connections()
        self.load_tasks_table()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_box = QVBoxLayout()
        title = QLabel("Programación de Copias de Seguridad Automáticas")
        title.setObjectName("viewTitle")
        desc = QLabel("Configure respaldos desatendidos con rotación de retención e integración con el Programador de Windows.")
        desc.setObjectName("viewDescription")
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        splitter = QSplitter(Qt.Horizontal)

        # PANEL IZQUIERDO: Tabla de Tareas Programadas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        t_header = QHBoxLayout()
        t_label = QLabel("Tareas Programadas")
        t_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #E2E8F0;")
        t_header.addWidget(t_label)
        t_header.addStretch()

        self.btn_new = QPushButton("+ Nueva Tarea")
        self.btn_new.setProperty("class", "btn-secondary")
        self.btn_new.clicked.connect(self.clear_form)
        t_header.addWidget(self.btn_new)
        left_layout.addLayout(t_header)

        self.table_tasks = QTableWidget(0, 6)
        self.table_tasks.setHorizontalHeaderLabels([
            "ID", "Servidor", "Base de Datos", "Frecuencia", "Hora", "Estado"
        ])
        self.table_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_tasks.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_tasks.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_tasks.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tasks.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_tasks.itemSelectionChanged.connect(self.on_table_selection_changed)
        left_layout.addWidget(self.table_tasks)

        # Botonera de control de tarea seleccionada
        ctrl_bar = QHBoxLayout()
        self.btn_toggle_active = QPushButton("Activar / Desactivar")
        self.btn_toggle_active.setProperty("class", "btn-secondary")
        self.btn_toggle_active.setEnabled(False)
        self.btn_toggle_active.clicked.connect(self.toggle_task_active)
        ctrl_bar.addWidget(self.btn_toggle_active)

        self.btn_run_now = QPushButton("Ejecutar Ahora")
        self.btn_run_now.setProperty("class", "btn-secondary")
        self.btn_run_now.setEnabled(False)
        self.btn_run_now.clicked.connect(self.run_task_now)
        ctrl_bar.addWidget(self.btn_run_now)
        left_layout.addLayout(ctrl_bar)

        splitter.addWidget(left_widget)

        # PANEL DERECHO: Formulario de Configuración de la Tarea
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        card = QFrame()
        card.setProperty("class", "card")
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(12)

        form_title = QLabel("Configuración de la Tarea")
        form_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8;")
        form_layout.addWidget(form_title)

        # Conexión y Base de Datos
        row1 = QHBoxLayout()
        self.combo_conn = QComboBox()
        self.combo_conn.currentIndexChanged.connect(self.on_connection_changed)
        row1.addWidget(self._create_field("Servidor:", self.combo_conn), 1)

        self.combo_db = QComboBox()
        row1.addWidget(self._create_field("Base de Datos:", self.combo_db), 1)
        form_layout.addLayout(row1)

        # Frecuencia y Hora
        row2 = QHBoxLayout()
        self.combo_freq = QComboBox()
        self.combo_freq.addItems(["DAILY (Diario)", "WEEKLY (Semanal)", "MONTHLY (Mensual)"])
        row2.addWidget(self._create_field("Frecuencia:", self.combo_freq), 1)

        self.time_picker = QTimeEdit()
        self.time_picker.setTime(QTime(2, 0))  # 02:00 AM por defecto
        self.time_picker.setDisplayFormat("HH:mm")
        row2.addWidget(self._create_field("Hora de Ejecución:", self.time_picker), 1)
        form_layout.addLayout(row2)

        # Carpeta y Retención
        row3 = QHBoxLayout()
        self.txt_dest = QLineEdit()
        self.txt_dest.setText("C:\\SQL_Backups")
        row3.addWidget(self._create_field("Carpeta Destino:", self.txt_dest), 2)

        self.spin_retention = QSpinBox()
        self.spin_retention.setRange(1, 365)
        self.spin_retention.setValue(15)
        row3.addWidget(self._create_field("Días Retención:", self.spin_retention), 1)
        form_layout.addLayout(row3)

        # Opciones de Ejecución y Windows Task Scheduler
        row4 = QVBoxLayout()
        self.chk_windows_sch = QCheckBox("Registrar en el Programador de Tareas de Windows (schtasks)")
        self.chk_windows_sch.setChecked(True)
        self.chk_windows_sch.setStyleSheet("color: #38BDF8; font-weight: 600;")
        row4.addWidget(self.chk_windows_sch)

        sch_note = QLabel("✓ Permite que los backups se ejecuten puntualmente incluso con la interfaz cerrada.")
        sch_note.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")
        row4.addWidget(sch_note)
        form_layout.addLayout(row4)

        # Botonera
        row_btn = QHBoxLayout()
        self.btn_delete = QPushButton("Eliminar Tarea")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_task)
        row_btn.addWidget(self.btn_delete)

        row_btn.addStretch()

        self.btn_save = QPushButton("Guardar Tarea")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self.save_task)
        row_btn.addWidget(self.btn_save)
        form_layout.addLayout(row_btn)

        right_layout.addWidget(card)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        main_layout.addWidget(splitter)

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

        self.combo_db.clear()
        self.combo_db.addItem("Cargando bases...", None)
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
            self.combo_db.addItem("master")

    def load_tasks_table(self):
        tasks = self.task_repo.get_all()
        self.table_tasks.setRowCount(len(tasks))
        for r_idx, t in enumerate(tasks):
            self.table_tasks.setItem(r_idx, 0, QTableWidgetItem(str(t.id)))
            self.table_tasks.setItem(r_idx, 1, QTableWidgetItem(t.connection_name))
            self.table_tasks.setItem(r_idx, 2, QTableWidgetItem(t.database_name))
            self.table_tasks.setItem(r_idx, 3, QTableWidgetItem(t.schedule_frequency))
            self.table_tasks.setItem(r_idx, 4, QTableWidgetItem(t.schedule_time))

            status_str = "Activa" if t.is_active else "Pausada"
            item_status = QTableWidgetItem(status_str)
            item_status.setForeground(Qt.green if t.is_active else Qt.gray)
            self.table_tasks.setItem(r_idx, 5, item_status)

    def on_table_selection_changed(self):
        row = self.table_tasks.currentRow()
        if row < 0:
            return
        id_item = self.table_tasks.item(row, 0)
        if not id_item:
            return

        task_id = int(id_item.text())
        task = self.task_repo.get_by_id(task_id)
        if not task:
            return

        self.selected_task_id = task.id
        self.btn_delete.setEnabled(True)
        self.btn_toggle_active.setEnabled(True)
        self.btn_run_now.setEnabled(True)

        # Cargar valores en formulario
        idx_conn = self.combo_conn.findData(task.connection_id)
        if idx_conn >= 0:
            self.combo_conn.setCurrentIndex(idx_conn)

        time_obj = QTime.fromString(task.schedule_time, "HH:mm")
        if time_obj.isValid():
            self.time_picker.setTime(time_obj)

        self.txt_dest.setText(task.destination_folder)
        self.spin_retention.setValue(task.retention_days)
        self.chk_windows_sch.setChecked(task.use_windows_scheduler)

    def clear_form(self):
        self.selected_task_id = None
        self.table_tasks.clearSelection()
        self.btn_delete.setEnabled(False)
        self.btn_toggle_active.setEnabled(False)
        self.btn_run_now.setEnabled(False)
        self.txt_dest.setText("C:\\SQL_Backups")
        self.time_picker.setTime(QTime(2, 0))

    def save_task(self):
        conn_id = self.combo_conn.currentData()
        db_name = self.combo_db.currentText()
        if not conn_id or not db_name or "Cargando" in db_name:
            QMessageBox.warning(self, "Validación", "Seleccione un servidor y base de datos válidos.")
            return

        conn = self.conn_repo.get_by_id(conn_id)
        if not conn:
            return

        freq_str = "DAILY"
        if self.combo_freq.currentIndex() == 1:
            freq_str = "WEEKLY"
        elif self.combo_freq.currentIndex() == 2:
            freq_str = "MONTHLY"

        time_str = self.time_picker.time().toString("HH:mm")

        task = BackupTaskConfig(
            id=self.selected_task_id,
            connection_id=conn.id,
            connection_name=conn.name,
            database_name=db_name,
            backup_type="FULL",
            destination_folder=self.txt_dest.text().strip(),
            retention_days=self.spin_retention.value(),
            retention_min_copies=2,
            is_active=True,
            schedule_frequency=freq_str,
            schedule_time=time_str,
            use_windows_scheduler=self.chk_windows_sch.isChecked()
        )

        saved_id = self.task_repo.save(task)
        task.id = saved_id

        # Registrar en Windows Task Scheduler si fue marcado
        if task.use_windows_scheduler:
            reg_ok, reg_msg = WindowsTaskScheduler.register_task(
                task_id=saved_id,
                frequency=freq_str,
                time_hhmm=time_str
            )
            if not reg_ok:
                QMessageBox.warning(self, "Aviso de Windows Scheduler", f"La tarea se guardó localmente, pero Windows Task Scheduler reportó:\n{reg_msg}")

        QMessageBox.information(self, "Tarea Guardada", f"La tarea programada para [{db_name}] se guardó correctamente.")
        self.load_tasks_table()
        self.clear_form()

    def toggle_task_active(self):
        if not self.selected_task_id:
            return
        task = self.task_repo.get_by_id(self.selected_task_id)
        if not task:
            return

        new_status = not task.is_active
        self.task_repo.toggle_active(task.id, new_status)

        # Si se desactiva, borrar de Windows Task Scheduler
        if not new_status and task.use_windows_scheduler:
            WindowsTaskScheduler.delete_task(task.id)
        elif new_status and task.use_windows_scheduler:
            WindowsTaskScheduler.register_task(task.id, task.schedule_frequency, task.schedule_time)

        self.load_tasks_table()

    def run_task_now(self):
        if not self.selected_task_id:
            return

        res, msg = WindowsTaskScheduler.run_task_now(self.selected_task_id)
        if res:
            QMessageBox.information(self, "Ejecución Disparada", f"Se inició la ejecución en segundo plano:\n{msg}")
        else:
            # Fallback a ejecución local CLI si no está en Windows Task Scheduler
            import subprocess, sys
            cli_path = WindowsTaskScheduler._get_cli_path()
            subprocess.Popen([sys.executable, cli_path, "--task-id", str(self.selected_task_id)])
            QMessageBox.information(self, "Ejecución Disparada", "La tarea de respaldo fue lanzada en segundo plano de manera autónoma.")

    def delete_task(self):
        if not self.selected_task_id:
            return

        res = QMessageBox.question(
            self, "Confirmar Eliminación",
            "¿Desea eliminar esta tarea programada?\nSe removerá también del Programador de Tareas de Windows.",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            WindowsTaskScheduler.delete_task(self.selected_task_id)
            self.task_repo.delete(self.selected_task_id)
            self.load_tasks_table()
            self.clear_form()
