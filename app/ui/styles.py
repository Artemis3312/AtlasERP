"""
Estilos QSS modernos para AtlasERP.
Diseño profesional, limpio y de alto contraste optimizado para entornos de punto de venta.
"""

MODERN_STYLE = """
/* Global */
QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #1E293B;
    background-color: #F8FAFC;
}

/* Sidebar & Header */
#sidebar {
    background-color: #0F172A;
    border-right: 1px solid #1E293B;
}

#sidebarHeader {
    background-color: #0F172A;
    border-bottom: 1px solid #1E293B;
    padding: 15px 10px;
}

#sidebarTitle {
    color: #FFFFFF;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

#sidebarSubtitle {
    color: #94A3B8;
    font-size: 11px;
}

#navButton {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    text-align: left;
    padding: 12px 18px;
    font-size: 13px;
    font-weight: 500;
    border-radius: 8px;
    margin: 2px 8px;
}

#navButton:hover {
    background-color: #1E293B;
    color: #F8FAFC;
}

#navButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

/* Header bar */
#topHeader {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 8px 16px;
}

/* Cards & Containers */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px;
}

QFrame#cardHighlight {
    background-color: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 10px;
    padding: 14px;
}

QFrame#cardWarning {
    background-color: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 14px;
}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    color: #0F172A;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus {
    border: 1.5px solid #2563EB;
    background-color: #FFFFFF;
}

/* Buttons */
QPushButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1D4ED8;
}

QPushButton:pressed {
    background-color: #1E40AF;
}

QPushButton:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}

/* Button Variants */
QPushButton#btnSuccess {
    background-color: #059669;
}
QPushButton#btnSuccess:hover {
    background-color: #047857;
}

QPushButton#btnWarning {
    background-color: #D97706;
}
QPushButton#btnWarning:hover {
    background-color: #B45309;
}

QPushButton#btnDanger {
    background-color: #E11D48;
}
QPushButton#btnDanger:hover {
    background-color: #BE123C;
}

QPushButton#btnSecondary {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#btnSecondary:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QPushButton#btnPurple {
    background-color: #7C3AED;
}
QPushButton#btnPurple:hover {
    background-color: #6D28D9;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #1E3A8A;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:selected {
    background-color: #DBEAFE;
    color: #1E40AF;
    font-weight: 600;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 8px;
    font-weight: 600;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid #CBD5E1;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

/* Modals & Dialogs */
QDialog {
    background-color: #F8FAFC;
}

/* Badges / Labels */
QLabel#badgeSuccess {
    background-color: #DCFCE7;
    color: #166534;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeWarning {
    background-color: #FEF3C7;
    color: #92400E;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeDanger {
    background-color: #FEE2E2;
    color: #991B1B;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeInfo {
    background-color: #E0E7FF;
    color: #3730A3;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}
"""
