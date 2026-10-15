"""
Vista del Panel Principal (Dashboard)
Despliega indicadores clave de rendimiento (KPIs), estado de los servidores,
espacio en almacenamiento y resumen de operaciones recientes con datos en tiempo real.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from database.repositories import HistoryRepository, ConnectionRepository, BackupTaskRepository
from backup.retention import StorageManager


class DashboardView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist_repo = HistoryRepository()
        self.conn_repo = ConnectionRepository()
        self.task_repo = BackupTaskRepository()

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(20)

        # Encabezado
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Panel Principal de Control")
        title.setObjectName("viewTitle")
        subtitle = QLabel("Monitoreo en tiempo real del estado de respaldos, almacenamiento y tareas.")
        subtitle.setObjectName("viewDescription")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.btn_refresh = QPushButton("Actualizar Métricas")
        self.btn_refresh.setProperty("class", "btn-secondary")
        self.btn_refresh.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.btn_refresh)

        main_layout.addLayout(header_layout)

        # Fila de Tarjetas KPI
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)

        self.card_conns = self._create_kpi_card("SERVIDORES ACTIVOS", "0", "Instancias registradas")
        self.card_backups = self._create_kpi_card("TOTAL RESPALDOS", "0", "Operaciones en historial")
        self.card_success_rate = self._create_kpi_card("TASA DE ÉXITO", "100%", "Confiabilidad global")
        self.card_tasks = self._create_kpi_card("TAREAS AUTOMÁTICAS", "0", "Programadas activas")
        self.card_space = self._create_kpi_card("ESPACIO DISPONIBLE (C:)", "-- GB", "Unidad predeterminada")

        kpi_layout.addWidget(self.card_conns)
        kpi_layout.addWidget(self.card_backups)
        kpi_layout.addWidget(self.card_success_rate)
        kpi_layout.addWidget(self.card_tasks)
        kpi_layout.addWidget(self.card_space)

        main_layout.addLayout(kpi_layout)

        # Sección: Último Respaldo Exitoso Banner
        self.last_backup_card = QFrame()
        self.last_backup_card.setProperty("class", "card")
        last_bk_layout = QHBoxLayout(self.last_backup_card)
        last_bk_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_last_backup = QLabel("Último respaldo exitoso: Ninguno registrado aún.")
        self.lbl_last_backup.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 13px;")
        last_bk_layout.addWidget(self.lbl_last_backup)

        main_layout.addWidget(self.last_backup_card)

        # Tabla de Operaciones Recientes
        table_title = QLabel("Actividad Reciente del Sistema")
        table_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #E2E8F0; margin-top: 10px;")
        main_layout.addWidget(table_title)

        self.table_recent = QTableWidget(0, 7)
        self.table_recent.setHorizontalHeaderLabels([
            "ID", "Servidor", "Base de Datos", "Operación", "Estado", "Fecha / Hora", "Tamaño"
        ])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_recent.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_recent.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_recent.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_recent.setEditTriggers(QTableWidget.NoEditTriggers)

        main_layout.addWidget(self.table_recent)

    def _create_kpi_card(self, title: str, value: str, desc: str) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-kpi")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "kpi-title")

        lbl_value = QLabel(value)
        lbl_value.setProperty("class", "kpi-value")

        lbl_desc = QLabel(desc)
        lbl_desc.setProperty("class", "kpi-desc")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        layout.addWidget(lbl_desc)

        card.lbl_val = lbl_value
        card.lbl_desc = lbl_desc
        return card

    def refresh_data(self):
        """Carga datos reales desde SQLite y el sistema de almacenamiento."""
        metrics = self.hist_repo.get_dashboard_metrics()

        # Actualizar KPIs
        self.card_conns.lbl_val.setText(str(metrics["total_connections"]))
        self.card_backups.lbl_val.setText(str(metrics["total_backups"]))
        self.card_tasks.lbl_val.setText(str(metrics["active_tasks"]))

        total = metrics["total_backups"]
        success = metrics["success_backups"]
        rate = (success / total * 100) if total > 0 else 100.0
        self.card_success_rate.lbl_val.setText(f"{rate:.1f}%")
        if rate < 90.0:
            self.card_success_rate.lbl_val.setStyleSheet("color: #EF4444;")
        else:
            self.card_success_rate.lbl_val.setStyleSheet("color: #10B981;")

        # Espacio en disco
        space = StorageManager.get_disk_space_info("C:\\")
        free_gb = space.get("free_gb", 0)
        self.card_space.lbl_val.setText(f"{free_gb} GB")
        if space.get("is_low_space"):
            self.card_space.lbl_val.setStyleSheet("color: #F59E0B;")
            self.card_space.lbl_desc.setText("ALERTA: Espacio bajo")
        else:
            self.card_space.lbl_val.setStyleSheet("color: #38BDF8;")
            self.card_space.lbl_desc.setText(f"{space.get('percent_free', 0)}% disponible")

        # Último backup exitoso
        last_b = metrics.get("last_success")
        if last_b:
            db_name = last_b.get("database_name")
            fin_at = str(last_b.get("finished_at", ""))[:19].replace("T", " ")
            size_mb = (last_b.get("file_size_bytes", 0) or 0) / (1024 * 1024)
            self.lbl_last_backup.setText(
                f"✓ Último respaldo exitoso: Base de datos [{db_name}] el {fin_at} ({size_mb:.2f} MB)"
            )
        else:
            self.lbl_last_backup.setText("ℹ Aún no se han ejecutado copias de seguridad exitosas.")

        # Recientes
        recent = self.hist_repo.get_recent(15)
        self.table_recent.setRowCount(len(recent))
        for row_idx, r in enumerate(recent):
            self.table_recent.setItem(row_idx, 0, QTableWidgetItem(str(r.id)))
            self.table_recent.setItem(row_idx, 1, QTableWidgetItem(r.connection_name))
            self.table_recent.setItem(row_idx, 2, QTableWidgetItem(r.database_name))
            self.table_recent.setItem(row_idx, 3, QTableWidgetItem(r.operation_type))

            # Status con color
            status_item = QTableWidgetItem(r.status)
            if r.status == "SUCCESS":
                status_item.setForeground(QColor("#10B981"))
            elif r.status == "FAILED":
                status_item.setForeground(QColor("#EF4444"))
            else:
                status_item.setForeground(QColor("#F59E0B"))
            self.table_recent.setItem(row_idx, 4, status_item)

            date_str = str(r.started_at)[:19].replace("T", " ")
            self.table_recent.setItem(row_idx, 5, QTableWidgetItem(date_str))
            self.table_recent.setItem(row_idx, 6, QTableWidgetItem(r.file_size_formatted))
