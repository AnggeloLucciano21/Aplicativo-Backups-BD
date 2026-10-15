"""
Vista de Administración del Almacenamiento y Retención
Supervisa unidades de disco del sistema, evalúa espacio libre y
permite auditar carpetas de copias de seguridad para aplicar políticas de retención.
"""
import os
import psutil
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QProgressBar, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QFileDialog, QMessageBox, QSpinBox
)
from PySide6.QtCore import Qt

from backup.retention import StorageManager


class StorageView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_disk_info()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_box = QVBoxLayout()
        title = QLabel("Administración de Almacenamiento y Discos")
        title.setObjectName("viewTitle")
        desc = QLabel("Supervise el espacio físico en disco y examine los archivos de copias de seguridad.")
        desc.setObjectName("viewDescription")
        header_box.addWidget(title)
        header_box.addWidget(desc)
        main_layout.addLayout(header_box)

        # Sección: Unidades de Disco Físicas
        lbl_disks = QLabel("Unidades de Disco del Sistema")
        lbl_disks.setStyleSheet("font-size: 14px; font-weight: 700; color: #E2E8F0;")
        main_layout.addWidget(lbl_disks)

        self.disks_container = QVBoxLayout()
        main_layout.addLayout(self.disks_container)

        # Sección: Auditoría de Carpeta de Respaldos
        folder_card = QFrame()
        folder_card.setProperty("class", "card")
        f_layout = QVBoxLayout(folder_card)
        f_layout.setSpacing(12)

        lbl_folder_title = QLabel("Explorador y Auditoría de Carpeta de Respaldos")
        lbl_folder_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #38BDF8;")
        f_layout.addWidget(lbl_folder_title)

        row_pick = QHBoxLayout()
        self.txt_folder = QLineEdit()
        self.txt_folder.setText("C:\\SQL_Backups")
        row_pick.addWidget(self.txt_folder, 2)

        self.btn_browse = QPushButton("Examinar...")
        self.btn_browse.setProperty("class", "btn-secondary")
        self.btn_browse.clicked.connect(self.browse_folder)
        row_pick.addWidget(self.btn_browse)

        self.btn_scan = QPushButton("Escanear Archivos")
        self.btn_scan.setProperty("class", "btn-primary")
        self.btn_scan.clicked.connect(self.scan_folder)
        row_pick.addWidget(self.btn_scan)
        f_layout.addLayout(row_pick)

        self.table_files = QTableWidget(0, 4)
        self.table_files.setHorizontalHeaderLabels(["Nombre de Archivo", "Tamaño (MB)", "Fecha Modificación", "Extensión"])
        self.table_files.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_files.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        f_layout.addWidget(self.table_files)

        self.lbl_folder_summary = QLabel("Archivos encontrados: 0")
        self.lbl_folder_summary.setStyleSheet("color: #94A3B8; font-size: 12px;")
        f_layout.addWidget(self.lbl_folder_summary)

        main_layout.addWidget(folder_card)

    def refresh_disk_info(self):
        # Limpiar contenedor de discos
        while self.disks_container.count():
            item = self.disks_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Obtener particiones reales con psutil
        try:
            partitions = psutil.disk_partitions()
            for p in partitions:
                if 'cdrom' in p.opts or p.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    card = self._create_disk_card(p.mountpoint, usage.total, usage.used, usage.free, usage.percent)
                    self.disks_container.addWidget(card)
                except Exception:
                    pass
        except Exception as e:
            err_lbl = QLabel(f"Error al leer discos: {str(e)}")
            self.disks_container.addWidget(err_lbl)

    def _create_disk_card(self, mountpoint: str, total: int, used: int, free: int, percent: float) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        lbl_drive = QLabel(f"Unidad: {mountpoint}")
        lbl_drive.setStyleSheet("font-weight: 700; font-size: 13px; color: #F8FAFC;")
        header.addWidget(lbl_drive)

        total_gb = total / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        used_gb = used / (1024 ** 3)

        lbl_stats = QLabel(f"{free_gb:.1f} GB Libres de {total_gb:.1f} GB ({100 - percent:.1f}% disponible)")
        lbl_stats.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        header.addStretch()
        header.addWidget(lbl_stats)
        layout.addLayout(header)

        pbar = QProgressBar()
        pbar.setValue(int(percent))
        pbar.setFormat(f"Uso: {percent:.1f}%")
        if percent > 85.0:
            pbar.setStyleSheet("QProgressBar::chunk { background-color: #EF4444; }")
        layout.addWidget(pbar)

        return card

    def browse_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta", self.txt_folder.text())
        if f:
            self.txt_folder.setText(f)
            self.scan_folder()

    def scan_folder(self):
        folder = self.txt_folder.text().strip()
        if not os.path.exists(folder):
            QMessageBox.warning(self, "Aviso", f"La carpeta no existe: {folder}")
            return

        p = Path(folder)
        files = []
        try:
            for item in p.iterdir():
                if item.is_file() and item.suffix.lower() in [".bak", ".trn", ".diff", ".csv", ".log"]:
                    stat = item.stat()
                    files.append((item.name, stat.st_size, stat.st_mtime, item.suffix))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo escanear la carpeta: {str(e)}")
            return

        from datetime import datetime
        self.table_files.setRowCount(len(files))
        total_size = 0
        for r_idx, (name, size, mtime, ext) in enumerate(files):
            total_size += size
            self.table_files.setItem(r_idx, 0, QTableWidgetItem(name))
            self.table_files.setItem(r_idx, 1, QTableWidgetItem(f"{size / (1024 * 1024):.2f} MB"))
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            self.table_files.setItem(r_idx, 2, QTableWidgetItem(mtime_str))
            self.table_files.setItem(r_idx, 3, QTableWidgetItem(ext.upper()))

        total_mb = total_size / (1024 * 1024)
        self.lbl_folder_summary.setText(f"Encontrados {len(files)} archivos de respaldo. Tamaño total acumulado: {total_mb:.2f} MB.")
