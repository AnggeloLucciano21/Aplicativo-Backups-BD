"""
Estilos y Tema Visual para la Aplicación (Modern Corporate Slate Dark)
Proporciona una interfaz visual refinada, sobria y de nivel corporativo
optimizada para monitores de alta resolución y uso prolongado.
"""

THEME_QSS = """
/* Reset y Estilos Globales */
QWidget {
    background-color: #0F172A; /* Slate 900 */
    color: #F8FAFC;            /* Slate 50 */
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

/* Barra Lateral (Sidebar) */
#sidebar {
    background-color: #090D16; /* Ultra dark navy */
    border-right: 1px solid #1E293B;
    min-width: 230px;
    max-width: 230px;
}

#appLogoTitle {
    font-size: 16px;
    font-weight: 700;
    color: #38BDF8; /* Sky 400 */
    padding: 16px 12px 6px 12px;
}

#appLogoSubtitle {
    font-size: 11px;
    color: #64748B; /* Slate 500 */
    padding: 0px 12px 18px 12px;
    border-bottom: 1px solid #1E293B;
}

/* Botones de Navegación del Sidebar */
QPushButton.nav-btn {
    background-color: transparent;
    color: #94A3B8; /* Slate 400 */
    text-align: left;
    padding: 11px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 10px;
    border: none;
}

QPushButton.nav-btn:hover {
    background-color: #1E293B;
    color: #F1F5F9;
}

QPushButton.nav-btn:checked {
    background-color: #1D4ED8; /* Blue 700 */
    color: #FFFFFF;
    font-weight: 600;
}

/* Área de Contenido Principal */
#mainContent {
    background-color: #0F172A;
}

#viewHeader {
    background-color: #0B1120;
    border-bottom: 1px solid #1E293B;
    padding: 14px 24px;
}

#viewTitle {
    font-size: 20px;
    font-weight: 700;
    color: #F8FAFC;
}

#viewDescription {
    font-size: 12px;
    color: #94A3B8;
    margin-top: 2px;
}

/* Tarjetas y Contenedores */
QFrame.card {
    background-color: #1E293B; /* Slate 800 */
    border: 1px solid #334155; /* Slate 700 */
    border-radius: 10px;
    padding: 16px;
}

QFrame.card-kpi {
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #172033);
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
}

QLabel.kpi-title {
    color: #94A3B8;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}

QLabel.kpi-value {
    color: #F8FAFC;
    font-size: 26px;
    font-weight: 700;
    margin: 4px 0px;
}

QLabel.kpi-desc {
    color: #64748B;
    font-size: 11px;
}

/* Botones de Acción Estándar */
QPushButton.btn-primary {
    background-color: #2563EB; /* Blue 600 */
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.btn-primary:hover {
    background-color: #1D4ED8;
}

QPushButton.btn-primary:pressed {
    background-color: #1E40AF;
}

QPushButton.btn-primary:disabled {
    background-color: #334155;
    color: #64748B;
}

QPushButton.btn-success {
    background-color: #059669; /* Emerald 600 */
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.btn-success:hover {
    background-color: #047857;
}

QPushButton.btn-danger {
    background-color: #DC2626; /* Red 600 */
    color: #FFFFFF;
    font-weight: 600;
    padding: 8px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.btn-danger:hover {
    background-color: #B91C1C;
}

QPushButton.btn-secondary {
    background-color: #334155; /* Slate 700 */
    color: #E2E8F0;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #475569;
}

QPushButton.btn-secondary:hover {
    background-color: #475569;
}

/* Campos de Formulario */
QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {
    background-color: #0B1120;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 7px 10px;
    font-size: 13px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38BDF8;
    background-color: #0F172A;
}

QLineEdit:disabled, QComboBox:disabled {
    background-color: #1E293B;
    color: #64748B;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    border: 1px solid #475569;
    color: #F8FAFC;
    selection-background-color: #2563EB;
}

/* Tablas */
QTableWidget, QTableView {
    background-color: #0F172A;
    border: 1px solid #1E293B;
    border-radius: 8px;
    gridline-color: #1E293B;
    color: #E2E8F0;
}

QHeaderView::section {
    background-color: #1E293B;
    color: #94A3B8;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #334155;
    font-weight: 600;
    font-size: 12px;
}

QTableWidget::item {
    padding: 6px 12px;
    border-bottom: 1px solid #1E293B;
}

QTableWidget::item:selected {
    background-color: #1E3A8A; /* Blue 900 */
    color: #FFFFFF;
}

/* Barra de Progreso */
QProgressBar {
    background-color: #0B1120;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 600;
    height: 22px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #38BDF8);
    border-radius: 5px;
}

/* Área de Texto y Logs */
QPlainTextEdit, QTextEdit {
    background-color: #090D16;
    border: 1px solid #1E293B;
    border-radius: 6px;
    color: #38BDF8; /* Cyan terminal style */
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}

/* Barras de Desplazamiento */
QScrollBar:vertical {
    background-color: #0B1120;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Checkbox */
QCheckBox {
    spacing: 8px;
    color: #E2E8F0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0B1120;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #38BDF8;
}
"""
