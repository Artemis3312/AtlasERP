from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QComboBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from ...services.movement_service import MovementService
from ...utils.icon_helper import get_icon


class ManualMovementDialog(QDialog):
    movement_added = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Movimiento Manual de Caja")
        self.setMinimumWidth(440)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("card")
        form_layout = QFormLayout(card)
        form_layout.setSpacing(10)

        self.cmb_type = QComboBox()
        self.cmb_type.addItem("Ingreso Manual a Caja (Entrada)", "INGRESO_MANUAL")
        self.cmb_type.addItem("Egreso Manual de Caja (Salida / Gasto)", "EGRESO_MANUAL")

        self.spn_usd = QDoubleSpinBox()
        self.spn_usd.setPrefix("$ ")
        self.spn_usd.setRange(0.0, 999999.0)
        self.spn_usd.setDecimals(2)
        self.spn_usd.setValue(0.0)

        self.spn_bs = QDoubleSpinBox()
        self.spn_bs.setPrefix("Bs. ")
        self.spn_bs.setRange(0.0, 99999999.0)
        self.spn_bs.setDecimals(2)
        self.spn_bs.setValue(0.0)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Ej: Pago de proveedor / Inyeccion de sencillo")

        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("Numero de recibo o comprobante (Opcional)")

        form_layout.addRow("Tipo de Movimiento:", self.cmb_type)
        form_layout.addRow("Monto en USD:", self.spn_usd)
        form_layout.addRow("Monto en Bolivares:", self.spn_bs)
        form_layout.addRow("Descripcion / Motivo *:", self.txt_desc)
        form_layout.addRow("Referencia / Recibo:", self.txt_ref)

        layout.addWidget(card)

        # Botones
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Registrar Movimiento")
        btn_save.setObjectName("btnSuccess")
        btn_save.setIcon(get_icon("check", "#222A2A", size=16))
        btn_save.clicked.connect(self.save)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def save(self):
        m_type = self.cmb_type.currentData()
        usd = self.spn_usd.value()
        bs = self.spn_bs.value()
        desc = self.txt_desc.text().strip()
        ref = self.txt_ref.text().strip()

        if usd <= 0 and bs <= 0:
            QMessageBox.warning(self, "Monto Invalido", "Debe indicar un monto mayor a 0 en USD o en Bolivares.")
            return

        if not desc:
            QMessageBox.warning(self, "Descripcion Requerida", "Debe ingresar el motivo del movimiento.")
            self.txt_desc.setFocus()
            return

        ok, msg = MovementService.add_manual_movement(m_type, usd, bs, desc, ref)
        if ok:
            QMessageBox.information(self, "Registrado", msg)
            self.movement_added.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)
