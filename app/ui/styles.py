"""
Estilos QSS modernos para AtlasERP con la paleta de marca:
  #222A2A (Pizarra oscura / Gris carbón)
  #4FBBBC (Turquesa / Teal)
  #EC4624 (Rojo anaranjado / Coral)
  #F39120 (Ámbar cálido / Naranja)
  #E2DAC2 (Crema suave / Arena)
"""

MODERN_STYLE = """
/* Global Window & Typography */
QMainWindow, QDialog {
    background-color: #F5F2EB;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #222A2A;
}

QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    color: #222A2A;
}

/* Sidebar Navigation */
#sidebar {
    background-color: #222A2A;
    border-right: 1px solid #1C2323;
}

#sidebarHeader {
    background-color: transparent;
    border-bottom: 1px solid rgba(226, 218, 194, 0.15);
    padding: 18px 16px;
}

#sidebarTitle {
    color: #FFFFFF;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 1px;
    background: transparent;
}

#sidebarSubtitle {
    color: #4FBBBC;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 2px;
    background: transparent;
}

#sidebarFooter {
    color: #E2DAC2;
    font-size: 10px;
    background: transparent;
    padding: 0 16px;
    line-height: 14px;
}

#navButton {
    background-color: transparent;
    color: #E2DAC2;
    border: none;
    text-align: left;
    padding: 12px 18px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    margin: 3px 10px;
}

#navButton:hover {
    background-color: #2E3838;
    color: #FFFFFF;
}

#navButton:checked {
    background-color: #4FBBBC;
    color: #222A2A;
    font-weight: 800;
}

/* Top Header Bar */
#topHeader {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2DAC2;
    padding: 8px 16px;
}

/* Cards & Containers */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E2DAC2;
    border-radius: 10px;
    padding: 12px;
}

QFrame#cardHighlight {
    background-color: #F2FAFA;
    border: 1px solid #4FBBBC;
    border-radius: 10px;
    padding: 12px;
}

QFrame#cardWarning {
    background-color: #FEF8F0;
    border: 1px solid #F39120;
    border-radius: 10px;
    padding: 12px;
}

QGroupBox {
    border: 1px solid #E2DAC2;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 14px;
    font-weight: 700;
    color: #222A2A;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #222A2A;
}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #D5CEB9;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    color: #222A2A;
    selection-background-color: #4FBBBC;
    selection-color: #222A2A;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
    border: 1.5px solid #4FBBBC;
    background-color: #FFFFFF;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Buttons */
QPushButton {
    background-color: #4FBBBC;
    color: #222A2A;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 700;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #43A5A6;
}

QPushButton:pressed {
    background-color: #388C8D;
}

QPushButton:disabled {
    background-color: #E2DAC2;
    color: #8C8673;
}

/* Button Variants */
QPushButton#btnSuccess {
    background-color: #4FBBBC;
    color: #222A2A;
}
QPushButton#btnSuccess:hover {
    background-color: #43A5A6;
}

QPushButton#btnWarning {
    background-color: #F39120;
    color: #FFFFFF;
}
QPushButton#btnWarning:hover {
    background-color: #DD8015;
}

QPushButton#btnDanger {
    background-color: #EC4624;
    color: #FFFFFF;
}
QPushButton#btnDanger:hover {
    background-color: #D33918;
}

QPushButton#btnSecondary {
    background-color: #FFFFFF;
    color: #222A2A;
    border: 1px solid #D5CEB9;
}
QPushButton#btnSecondary:hover {
    background-color: #F5F0E4;
    border-color: #B5AD96;
}

QPushButton#btnPurple {
    background-color: #F39120;
    color: #FFFFFF;
}
QPushButton#btnPurple:hover {
    background-color: #DD8015;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2DAC2;
    border-radius: 8px;
    gridline-color: #F0ECE1;
    selection-background-color: #E0F4F4;
    selection-color: #222A2A;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #F5F1E6;
}

QTableWidget::item:selected {
    background-color: #D3EFEF;
    color: #222A2A;
    font-weight: 700;
}

QHeaderView::section {
    background-color: #EAE5D5;
    color: #222A2A;
    padding: 8px;
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1.5px solid #D5CEB9;
}

/* CheckBox & RadioButton */
QCheckBox, QRadioButton {
    spacing: 8px;
    font-size: 13px;
    color: #222A2A;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #D5CEB9;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #4FBBBC;
    border-color: #4FBBBC;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1.5px solid #D5CEB9;
    border-radius: 8px;
    background-color: #FFFFFF;
}

QRadioButton::indicator:checked {
    background-color: #4FBBBC;
    border-color: #4FBBBC;
}

/* ScrollBars / Sliders */
QScrollBar:vertical {
    border: none;
    background: #EAE5D5;
    width: 10px;
    border-radius: 5px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #4FBBBC;
    min-height: 30px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #368A8B;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #EAE5D5;
    height: 10px;
    border-radius: 5px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #4FBBBC;
    min-width: 30px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #368A8B;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
"""
