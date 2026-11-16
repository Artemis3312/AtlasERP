from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QComboBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from ...services.pos_service import PosService
from ...services.shift_service import ShiftService
from ...utils.helpers import format_bs, parse_float


class CashAdvanceDialog(QDialog):
    advance_completed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Realizar Avance de Efectivo en Bolívares")
        self.setMinimumWidth(480)
        self.setup_ui()
        self.check_cash_drawer()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Tarjeta de aviso de efectivo disponible
        self.drawer_info_card = QFrame()
        self.drawer_info_card.setObjectName("cardHighlight")
        card_layout = QVBoxLayout(self.drawer_info_card)

        self.lbl_drawer_cash = QLabel()
        self.lbl_drawer_cash.setStyleSheet("font-size: 14px; font-weight: 700; color: #166534;")
        card_layout.addWidget(self.lbl_drawer_cash)

        desc = QLabel("El negocio entrega bolívares en efectivo y recibe el cobro electrónico equivalente vía Tarjeta o Pago Móvil.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #4B5563;")
        card_layout.addWidget(desc)

        layout.addWidget(self.drawer_info_card)

        # Formulario
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)

        self.spn_dispense_bs = QDoubleSpinBox()
        self.spn_dispense_bs.setPrefix("Bs. ")
        self.spn_dispense_bs.setRange(0.01, 99999999.0)
        self.spn_dispense_bs.setDecimals(2)
        self.spn_dispense_bs.setValue(100.0)
        self.spn_dispense_bs.valueChanged.connect(self.calculate_totals)

        self.spn_commission_pct = QDoubleSpinBox()
        self.spn_commission_pct.setSuffix(" %")
        self.spn_commission_pct.setRange(0.0, 100.0)
        self.spn_commission_pct.setDecimals(1)
        self.spn_commission_pct.setValue(0.0)
        self.spn_commission_pct.valueChanged.connect(self.calculate_totals)

        self.lbl_total_charge = QLabel()
        self.lbl_total_charge.setStyleSheet("font-size: 16px; font-weight: 700; color: #2563EB;")

        self.cmb_method = QComboBox()
        self.cmb_method.addItems([
            "Bolívares Tarjeta (P.O.S. / Débito)",
            "Bolívares Pago Móvil"
        ])
        self.cmb_method.currentIndexChanged.connect(self.on_method_changed)

        self.txt_reference = QLineEdit()
        self.txt_reference.setPlaceholderText("Ej: 489201 (Obligatorio para Pago Móvil)")

        self.txt_client = QLineEdit()
        self.txt_client.setPlaceholderText("Nombre del cliente o solicitante (Opcional)")

        form_layout.addRow("Efectivo a Entregar (BS) *:", self.spn_dispense_bs)
        form_layout.addRow("Comisión de Avance (%):", self.spn_commission_pct)
        form_layout.addRow("Total a Cobrar al Cliente:", self.lbl_total_charge)
        form_layout.addRow("Método de Cobro *:", self.cmb_method)
        form_layout.addRow("Referencia Bancaria *:", self.txt_reference)
        form_layout.addRow("Cliente:", self.txt_client)

        layout.addWidget(form_card)

        self.calculate_totals()

        # Botones
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_process = QPushButton("💸 Procesar Avance de Efectivo")
        self.btn_process.setObjectName("btnWarning")
        self.btn_process.clicked.connect(self.process_advance)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_process)
        layout.addLayout(btn_box)

    def check_cash_drawer(self):
        shift = ShiftService.get_active_shift()
        if not shift:
            self.lbl_drawer_cash.setText("⚠️ No hay turno de caja abierto.")
            self.drawer_info_card.setObjectName("cardWarning")
            self.drawer_info_card.setStyleSheet("")
            return

        metrics = ShiftService.get_shift_metrics(shift["id"])
        avail = metrics.get("expected_cash_bs", 0.0)
        self.lbl_drawer_cash.setText(f"💵 Efectivo disponible en gaveta: {format_bs(avail)}")

    def calculate_totals(self):
        dispense = self.spn_dispense_bs.value()
        pct = self.spn_commission_pct.value()
        total_charge = round(dispense * (1.0 + pct / 100.0), 2)
        comm_bs = round(total_charge - dispense, 2)

        if comm_bs > 0:
            self.lbl_total_charge.setText(f"{format_bs(total_charge)} (incluye {format_bs(comm_bs)} comisión)")
        else:
            self.lbl_total_charge.setText(format_bs(total_charge))

    def on_method_changed(self, idx):
        if idx == 1:  # Pago Móvil
            self.txt_reference.setPlaceholderText("Número de referencia de Pago Móvil (Obligatorio)")
        else:
            self.txt_reference.setPlaceholderText("Número de voucher / aprobación (Opcional)")

    def process_advance(self):
        dispense = self.spn_dispense_bs.value()
        pct = self.spn_commission_pct.value()
        method_key = "BS_TARJETA" if self.cmb_method.currentIndex() == 0 else "BS_PAGO_MOVIL"
        ref = self.txt_reference.text().strip()
        client = self.txt_client.text().strip() or "Cliente Avance"

        if method_key == "BS_PAGO_MOVIL" and not ref:
            QMessageBox.warning(self, "Referencia Requerida", "Debe ingresar el número de referencia bancaria del Pago Móvil.")
            self.txt_reference.setFocus()
            return

        ok, msg, data = PosService.process_cash_advance(
            amount_cash_dispensed_bs=dispense,
            payment_method=method_key,
            reference=ref,
            commission_pct=pct,
            client_name=client
        )

        if ok:
            QMessageBox.information(self, "Avance Realizado", msg)
            self.advance_completed.emit(data or {})
            self.accept()
        else:
            QMessageBox.warning(self, "Error al Procesar", msg)
