"""
Ventana Principal de la Aplicación (Main Window)
Orquesta el menú lateral de navegación, la pila de vistas (QStackedWidget)
y el ciclo de actualización entre módulos.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.styles import THEME_QSS
from ui.views.dashboard_view import DashboardView
from ui.views.connections_view import ConnectionsView
from ui.views.manual_backup_view import ManualBackupView
from ui.views.restore_view import RestoreView
from ui.views.scheduler_view import SchedulerView
from ui.views.history_view import HistoryView
from ui.views.storage_view import StorageView


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataShield Enterprise - Gestión de Respaldos de Bases de Datos")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 700)

        self.init_ui()
        self.setStyleSheet(THEME_QSS)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # BARRA LATERAL (SIDEBAR)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(6)

        # Logo / Marca
        logo_title = QLabel("DATASHIELD")
        logo_title.setObjectName("appLogoTitle")
        logo_sub = QLabel("DATABASE BACKUP & RECOVERY")
        logo_sub.setObjectName("appLogoSubtitle")
        side_layout.addWidget(logo_title)
        side_layout.addWidget(logo_sub)

        side_layout.addSpacing(10)

        # Botones de navegación
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_dashboard = self._create_nav_button("📊  Panel Principal", 0)
        self.btn_nav_conns = self._create_nav_button("🔗  Conexiones", 1)
        self.btn_nav_backup = self._create_nav_button("💾  Copia Manual", 2)
        self.btn_nav_restore = self._create_nav_button("🔄  Restauración", 3)
        self.btn_nav_scheduler = self._create_nav_button("⏱  Programación", 4)
        self.btn_nav_history = self._create_nav_button("📜  Historial y Auditoría", 5)
        self.btn_nav_storage = self._create_nav_button("💽  Almacenamiento", 6)

        side_layout.addWidget(self.btn_nav_dashboard)
        side_layout.addWidget(self.btn_nav_conns)
        side_layout.addWidget(self.btn_nav_backup)
        side_layout.addWidget(self.btn_nav_restore)
        side_layout.addWidget(self.btn_nav_scheduler)
        side_layout.addWidget(self.btn_nav_history)
        side_layout.addWidget(self.btn_nav_storage)

        side_layout.addStretch()

        # Versión / Pie de barra lateral
        lbl_version = QLabel("v1.0.0 Enterprise • SQL Server")
        lbl_version.setStyleSheet("color: #475569; font-size: 11px; padding: 8px 12px;")
        side_layout.addWidget(lbl_version)

        root_layout.addWidget(sidebar)

        # ÁREA DE CONTENIDO (QStackedWidget)
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainContent")

        self.view_dashboard = DashboardView()
        self.view_conns = ConnectionsView()
        self.view_backup = ManualBackupView()
        self.view_restore = RestoreView()
        self.view_scheduler = SchedulerView()
        self.view_history = HistoryView()
        self.view_storage = StorageView()

        self.stack.addWidget(self.view_dashboard)  # 0
        self.stack.addWidget(self.view_conns)      # 1
        self.stack.addWidget(self.view_backup)     # 2
        self.stack.addWidget(self.view_restore)    # 3
        self.stack.addWidget(self.view_scheduler)  # 4
        self.stack.addWidget(self.view_history)    # 5
        self.stack.addWidget(self.view_storage)    # 6

        root_layout.addWidget(self.stack)

        # Activar primera vista
        self.btn_nav_dashboard.setChecked(True)
        self.on_nav_clicked(0)

    def _create_nav_button(self, label: str, view_index: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("class", "nav-btn")
        btn.setCheckable(True)
        self.nav_group.addButton(btn, view_index)
        btn.clicked.connect(lambda: self.on_nav_clicked(view_index))
        return btn

    def on_nav_clicked(self, index: int):
        self.stack.setCurrentIndex(index)

        # Actualizar datos de la vista que entra en foco
        if index == 0:
            self.view_dashboard.refresh_data()
        elif index == 1:
            self.view_conns.load_connections_table()
        elif index == 2:
            self.view_backup.reload_connections()
        elif index == 3:
            self.view_restore.reload_connections()
        elif index == 4:
            self.view_scheduler.reload_connections()
            self.view_scheduler.load_tasks_table()
        elif index == 5:
            self.view_history.apply_filters()
        elif index == 6:
            self.view_storage.refresh_disk_info()
