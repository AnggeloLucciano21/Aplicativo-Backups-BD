"""
Vista de Historial y Auditoría de Operaciones
Permite consultar, filtrar y exportar a CSV todos los registros de copias de seguridad,
restauraciones y verificaciones realizadas, con visualización de firmas SHA-256 y detalles de error.
"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from database.repositories import HistoryRepository
from core.models import OperationRecord


class HistoryView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist_repo = HistoryRepository()
        self.current_records: List[OperationRecord] = []

        self.init_ui()
        self.apply_filters()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        # Encabezado
        header_layout = QHBoxLayout()
        h_box = QVBoxLayout()
        title = QLabel("Historial y Auditoría de Operaciones")
        title.setObjectName("viewTitle")
        desc = QLabel("Registro detallado e inmutable de respaldos, restauraciones y verificaciones de integridad.")
        desc.setObjectName("viewDescription")
        h_box.addWidget(title)
        h_box.addWidget(desc)
        header_layout.addLayout(h_box)

        header_layout.addStretch()

        self.btn_export = QPushButton("📥 Exportar a CSV (Excel)")
        self.btn_export.setProperty("class", "btn-secondary")
        self.btn_export.clicked.connect(self.export_csv)
        header_layout.addWidget(self.btn_export)

        main_layout.addLayout(header_layout)

        # Barra de Filtros
        filter_card = QFrame()
        filter_card.setProperty("class", "card")
        f_layout = QHBoxLayout(filter_card)
        f_layout.setSpacing(12)

        # Búsqueda por texto
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar por Servidor o Base de Datos...")
        self.txt_search.textChanged.connect(self.apply_filters)
        f_layout.addWidget(self.txt_search, 2)

        # Filtro de Estado
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Todos los Estados", "SUCCESS", "FAILED", "IN_PROGRESS"])
        self.combo_status.currentIndexChanged.connect(self.apply_filters)
        f_layout.addWidget(self.combo_status, 1)

        # Filtro de Fecha Desde
        lbl_from = QLabel("Desde:")
        lbl_from.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self.apply_filters)
        f_layout.addWidget(lbl_from)
        f_layout.addWidget(self.date_from)

        # Filtro de Fecha Hasta
        lbl_to = QLabel("Hasta:")
        lbl_to.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.apply_filters)
        f_layout.addWidget(lbl_to)
        f_layout.addWidget(self.date_to)

        self.btn_reset_filters = QPushButton("Limpiar")
        self.btn_reset_filters.setProperty("class", "btn-secondary")
        self.btn_reset_filters.clicked.connect(self.reset_filters)
        f_layout.addWidget(self.btn_reset_filters)

        main_layout.addWidget(filter_card)

        # Tabla de Historial
        self.table_hist = QTableWidget(0, 9)
        self.table_hist.setHorizontalHeaderLabels([
            "ID", "Servidor", "Base de Datos", "Operación", "Estado",
            "Fecha Inicio", "Duración", "Tamaño", "Firma SHA-256"
        ])
        self.table_hist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_hist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_hist.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_hist.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_hist.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_hist.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_hist.itemDoubleClicked.connect(self.show_record_details)
        main_layout.addWidget(self.table_hist)

        # Pie de tabla
        self.lbl_record_count = QLabel("Mostrando 0 registros")
        self.lbl_record_count.setStyleSheet("color: #64748B; font-size: 12px;")
        main_layout.addWidget(self.lbl_record_count)

    def apply_filters(self):
        search_txt = self.txt_search.text().strip()
        status_idx = self.combo_status.currentIndex()
        status_val = None
        if status_idx == 1:
            status_val = "SUCCESS"
        elif status_idx == 2:
            status_val = "FAILED"
        elif status_idx == 3:
            status_val = "IN_PROGRESS"

        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd")

        records = self.hist_repo.filter_records(
            server=search_txt,
            status=status_val,
            date_from=d_from,
            date_to=d_to,
            limit=300
        )
        self.current_records = records
        self.populate_table(records)

    def reset_filters(self):
        self.txt_search.clear()
        self.combo_status.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.apply_filters()

    def populate_table(self, records: List[OperationRecord]):
        self.table_hist.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            self.table_hist.setItem(row_idx, 0, QTableWidgetItem(str(r.id)))
            self.table_hist.setItem(row_idx, 1, QTableWidgetItem(r.connection_name))
            self.table_hist.setItem(row_idx, 2, QTableWidgetItem(r.database_name))
            self.table_hist.setItem(row_idx, 3, QTableWidgetItem(r.operation_type))

            # Estado
            status_item = QTableWidgetItem(r.status)
            if r.status == "SUCCESS":
                status_item.setForeground(QColor("#10B981"))
            elif r.status == "FAILED":
                status_item.setForeground(QColor("#EF4444"))
            else:
                status_item.setForeground(QColor("#F59E0B"))
            self.table_hist.setItem(row_idx, 4, status_item)

            start_str = str(r.started_at)[:19].replace("T", " ")
            self.table_hist.setItem(row_idx, 5, QTableWidgetItem(start_str))
            self.table_hist.setItem(row_idx, 6, QTableWidgetItem(r.duration_formatted))
            self.table_hist.setItem(row_idx, 7, QTableWidgetItem(r.file_size_formatted))

            # SHA-256 corto con tooltip completo
            sha_display = f"{r.sha256_hash[:12]}..." if r.sha256_hash else "--"
            sha_item = QTableWidgetItem(sha_display)
            sha_item.setToolTip(r.sha256_hash)
            self.table_hist.setItem(row_idx, 8, sha_item)

        self.lbl_record_count.setText(f"Mostrando {len(records)} operaciones auditadas (Doble clic para ver detalles técnicos completos).")

    def show_record_details(self, item):
        row = item.row()
        if row < 0 or row >= len(self.current_records):
            return

        r = self.current_records[row]
        details = (
            f"=== DETALLE DE OPERACIÓN ID #{r.id} ===\n\n"
            f"• Conexión: {r.connection_name}\n"
            f"• Base de Datos: {r.database_name}\n"
            f"• Operación: {r.operation_type}\n"
            f"• Estado: {r.status}\n"
            f"• Fecha Inicio: {r.started_at}\n"
            f"• Fecha Finalización: {r.finished_at or 'N/A'}\n"
            f"• Duración: {r.duration_seconds} segundos ({r.duration_formatted})\n"
            f"• Archivo: {r.destination_path}\n"
            f"• Tamaño: {r.file_size_formatted} ({r.file_size_bytes} bytes)\n"
            f"• Hash SHA-256: {r.sha256_hash or 'No calculado'}\n"
            f"• Usuario del Sistema: {r.user_system}\n"
            f"• Detalles JSON: {r.details_json}\n\n"
            f"• Error Técnico: {r.error_message or 'Ninguno (Operación Exitosa)'}"
        )
        QMessageBox.information(self, f"Auditoría de Operación #{r.id}", details)

    def export_csv(self):
        if not self.current_records:
            QMessageBox.warning(self, "Exportación", "No hay registros disponibles para exportar con los filtros actuales.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte de Auditoría", "Reporte_Backups_Auditoria.csv",
            "Archivos CSV (*.csv)"
        )
        if file_path:
            ok = self.hist_repo.export_to_csv_file(file_path, self.current_records)
            if ok:
                QMessageBox.information(self, "Exportación Exitosa", f"El reporte con {len(self.current_records)} registros fue guardado en:\n{file_path}")
            else:
                QMessageBox.critical(self, "Error de Exportación", "No se pudo escribir el archivo CSV.")
