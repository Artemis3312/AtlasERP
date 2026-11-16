from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from ...services.shift_service import ShiftService
from ...utils.icon_helper import get_icon


class ShiftOpenDialog(QDialog):
    shift_opened = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apertura de Turno de Caja")
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("cardHighlight")
        form_layout = QFormLayout(card)
        form_layout.setSpacing(10)

        self.txt_cashier = QLineEdit("Cajero Principal")
        self.txt_cashier.setPlaceholderText("Nombre del cajero responsable")

        self.spn_initial_usd = QDoubleSpinBox()
        self.spn_initial_usd.setPrefix("$ ")
        self.spn_initial_usd.setRange(0.0, 999999.0)
        self.spn_initial_usd.setDecimals(2)
        self.spn_initial_usd.setValue(0.0)

        self.spn_initial_bs = QDoubleSpinBox()
        self.spn_initial_bs.setPrefix("Bs. ")
        self.spn_initial_bs.setRange(0.0, 99999999.0)
        self.spn_initial_bs.setDecimals(2)
        self.spn_initial_bs.setValue(0.0)

        form_layout.addRow("Cajero Responsable:", self.txt_cashier)
        form_layout.addRow("Base Inicial Efectivo USD:", self.spn_initial_usd)
        form_layout.addRow("Base Inicial Efectivo BS:", self.spn_initial_bs)

        layout.addWidget(card)

        # Botones
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)

        btn_open = QPushButton("Abrir Turno")
        btn_open.setObjectName("btnSuccess")
        btn_open.setIcon(get_icon("unlock", "#222A2A", size=16))
        btn_open.clicked.connect(self.process_open)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_open)
        layout.addLayout(btn_box)

    def process_open(self):
        cashier = self.txt_cashier.text().strip() or "Cajero Principal"
        usd = self.spn_initial_usd.value()
        bs = self.spn_initial_bs.value()

        ok, msg, shift_id = ShiftService.open_shift(usd, bs, cashier)
        if ok:
            QMessageBox.information(self, "Turno Abierto", msg)
            self.shift_opened.emit(shift_id)
            self.accept()
        else:
            QMessageBox.warning(self, "Atencion", msg)
