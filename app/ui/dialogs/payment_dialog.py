from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from ...services.pos_service import PosService
from ...services.exchange_rate import ExchangeRateService
from ...utils.helpers import format_usd, format_bs, parse_float


class PaymentDialog(QDialog):
    sale_completed = Signal(dict)

    def __init__(self, items: List[Dict[str, Any]], total_usd: float, parent=None):
        super().__init__(parent)
        self.items = items
        self.total_usd = round(total_usd, 2)
        self.rate = ExchangeRateService.get_active_rate()
        self.total_bs = round(self.total_usd * self.rate, 2)

        self.setWindowTitle("Cobro y Facturación - Múltiples Métodos de Pago")
        self.setMinimumWidth(560)
        self.setup_ui()
        self.calculate_balances()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Tarjeta de Totales a Pagar
        header_card = QFrame()
        header_card.setObjectName("cardHighlight")
        header_layout = QHBoxLayout(header_card)

        col1 = QVBoxLayout()
        lbl_t1 = QLabel("TOTAL A FACTURAR (USD)")
        lbl_t1.setStyleSheet("font-size: 11px; color: #166534; font-weight: 600;")
        self.lbl_total_usd_disp = QLabel(format_usd(self.total_usd))
        self.lbl_total_usd_disp.setStyleSheet("font-size: 24px; font-weight: 800; color: #15803D;")
        col1.addWidget(lbl_t1)
        col1.addWidget(self.lbl_total_usd_disp)

        col2 = QVBoxLayout()
        lbl_t2 = QLabel("TOTAL A FACTURAR (BOLÍVARES)")
        lbl_t2.setStyleSheet("font-size: 11px; color: #1E40AF; font-weight: 600;")
        self.lbl_total_bs_disp = QLabel(format_bs(self.total_bs))
        self.lbl_total_bs_disp.setStyleSheet("font-size: 24px; font-weight: 800; color: #2563EB;")
        col2.addWidget(lbl_t2)
        col2.addWidget(self.lbl_total_bs_disp)

        col3 = QVBoxLayout()
        lbl_rate_info = QLabel("TASA APLICADA:")
        lbl_rate_info.setStyleSheet("font-size: 11px; color: #64748B;")
        self.lbl_rate_val = QLabel(f"Bs. {self.rate:,.2f}")
        self.lbl_rate_val.setStyleSheet("font-size: 14px; font-weight: 700; color: #334155;")
        col3.addWidget(lbl_rate_info)
        col3.addWidget(self.lbl_rate_val)

        header_layout.addLayout(col1)
        header_layout.addLayout(col2)
        header_layout.addLayout(col3)
        layout.addWidget(header_card)

        # Datos del Cliente
        client_box = QGroupBox("Datos del Cliente")
        client_box.setStyleSheet("font-weight: 600; color: #334155;")
        client_layout = QHBoxLayout(client_box)

        self.txt_client_name = QLineEdit("Consumidor Final")
        self.txt_client_name.setPlaceholderText("Nombre / Razón Social")

        self.txt_client_id = QLineEdit("V-00000000")
        self.txt_client_id.setPlaceholderText("Cédula / RIF")

        client_layout.addWidget(QLabel("Cliente:"))
        client_layout.addWidget(self.txt_client_name, 2)
        client_layout.addWidget(QLabel("C.I. / RIF:"))
        client_layout.addWidget(self.txt_client_id, 1)
        layout.addWidget(client_box)

        # Desglose de Métodos de Pago
        pay_group = QGroupBox("Ingreso de Métodos de Pago (Combinables)")
        pay_group.setStyleSheet("font-weight: 600; color: #334155;")
        pay_layout = QGridLayout(pay_group)
        pay_layout.setSpacing(10)

        # 1. USD Efectivo
        lbl_usd_cash = QLabel("💵 USD Efectivo:")
        self.spn_usd_cash = QDoubleSpinBox()
        self.spn_usd_cash.setPrefix("$ ")
        self.spn_usd_cash.setRange(0.0, 999999.0)
        self.spn_usd_cash.setDecimals(2)
        self.spn_usd_cash.setValue(0.0)
        self.spn_usd_cash.valueChanged.connect(self.calculate_balances)

        btn_fill_usd = QPushButton("Llenar Todo")
        btn_fill_usd.setObjectName("btnSecondary")
        btn_fill_usd.clicked.connect(self.fill_all_usd)

        pay_layout.addWidget(lbl_usd_cash, 0, 0)
        pay_layout.addWidget(self.spn_usd_cash, 0, 1)
        pay_layout.addWidget(btn_fill_usd, 0, 2)

        # 2. BS Efectivo
        lbl_bs_cash = QLabel("💴 BS Efectivo:")
        self.spn_bs_cash = QDoubleSpinBox()
        self.spn_bs_cash.setPrefix("Bs. ")
        self.spn_bs_cash.setRange(0.0, 99999999.0)
        self.spn_bs_cash.setDecimals(2)
        self.spn_bs_cash.setValue(0.0)
        self.spn_bs_cash.valueChanged.connect(self.calculate_balances)

        btn_fill_bs = QPushButton("Llenar Todo")
        btn_fill_bs.setObjectName("btnSecondary")
        btn_fill_bs.clicked.connect(self.fill_all_bs)

        pay_layout.addWidget(lbl_bs_cash, 1, 0)
        pay_layout.addWidget(self.spn_bs_cash, 1, 1)
        pay_layout.addWidget(btn_fill_bs, 1, 2)

        # 3. BS Tarjeta (P.O.S.)
        lbl_bs_card = QLabel("💳 BS Tarjeta (Punto):")
        self.spn_bs_card = QDoubleSpinBox()
        self.spn_bs_card.setPrefix("Bs. ")
        self.spn_bs_card.setRange(0.0, 99999999.0)
        self.spn_bs_card.setDecimals(2)
        self.spn_bs_card.setValue(0.0)
        self.spn_bs_card.valueChanged.connect(self.calculate_balances)

        self.txt_card_ref = QLineEdit()
        self.txt_card_ref.setPlaceholderText("Ref / Voucher (Opcional)")

        pay_layout.addWidget(lbl_bs_card, 2, 0)
        pay_layout.addWidget(self.spn_bs_card, 2, 1)
        pay_layout.addWidget(self.txt_card_ref, 2, 2)

        # 4. BS Pago Móvil
        lbl_bs_pm = QLabel("📱 BS Pago Móvil *:")
        self.spn_bs_pm = QDoubleSpinBox()
        self.spn_bs_pm.setPrefix("Bs. ")
        self.spn_bs_pm.setRange(0.0, 99999999.0)
        self.spn_bs_pm.setDecimals(2)
        self.spn_bs_pm.setValue(0.0)
        self.spn_bs_pm.valueChanged.connect(self.calculate_balances)

        self.txt_pm_ref = QLineEdit()
        self.txt_pm_ref.setPlaceholderText("Nro de Referencia (Obligatorio) *")
        self.txt_pm_ref.setStyleSheet("border-color: #2563EB;")

        pay_layout.addWidget(lbl_bs_pm, 3, 0)
        pay_layout.addWidget(self.spn_bs_pm, 3, 1)
        pay_layout.addWidget(self.txt_pm_ref, 3, 2)

        layout.addWidget(pay_group)

        # Resumen de Balances y Cambio
        balance_card = QFrame()
        balance_card.setObjectName("card")
        bal_layout = QGridLayout(balance_card)

        bal_layout.addWidget(QLabel("Total Abonado:"), 0, 0)
        self.lbl_paid_disp = QLabel("$ 0.00 / Bs. 0,00")
        self.lbl_paid_disp.setStyleSheet("font-weight: 700; color: #1E293B;")
        bal_layout.addWidget(self.lbl_paid_disp, 0, 1)

        bal_layout.addWidget(QLabel("Resta por Pagar:"), 1, 0)
        self.lbl_remain_disp = QLabel()
        self.lbl_remain_disp.setStyleSheet("font-weight: 700; color: #E11D48;")
        bal_layout.addWidget(self.lbl_remain_disp, 1, 1)

        bal_layout.addWidget(QLabel("Vuelto / Cambio:"), 2, 0)
        self.lbl_change_disp = QLabel("$ 0.00 / Bs. 0,00")
        self.lbl_change_disp.setStyleSheet("font-weight: 700; color: #059669;")
        bal_layout.addWidget(self.lbl_change_disp, 2, 1)

        layout.addWidget(balance_card)

        # Botones de Acción
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("✅ Facturar y Finalizar Venta")
        self.btn_confirm.setObjectName("btnSuccess")
        self.btn_confirm.setStyleSheet("font-size: 14px; padding: 10px 24px;")
        self.btn_confirm.clicked.connect(self.process_checkout)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_confirm)
        layout.addLayout(btn_box)

    def fill_all_usd(self):
        self.reset_payments()
        self.spn_usd_cash.setValue(self.total_usd)

    def fill_all_bs(self):
        self.reset_payments()
        self.spn_bs_cash.setValue(self.total_bs)

    def reset_payments(self):
        self.spn_usd_cash.setValue(0.0)
        self.spn_bs_cash.setValue(0.0)
        self.spn_bs_card.setValue(0.0)
        self.spn_bs_pm.setValue(0.0)

    def calculate_balances(self):
        usd_cash = self.spn_usd_cash.value()
        bs_cash = self.spn_bs_cash.value()
        bs_card = self.spn_bs_card.value()
        bs_pm = self.spn_bs_pm.value()

        # Convertir todo a USD equivalente
        paid_usd = usd_cash + ((bs_cash + bs_card + bs_pm) / self.rate)
        paid_bs = (usd_cash * self.rate) + (bs_cash + bs_card + bs_pm)

        self.lbl_paid_disp.setText(f"{format_usd(paid_usd)}  |  {format_bs(paid_bs)}")

        diff_usd = round(self.total_usd - paid_usd, 2)
        diff_bs = round(diff_usd * self.rate, 2)

        if diff_usd > 0.01:
            self.lbl_remain_disp.setText(f"{format_usd(diff_usd)}  |  {format_bs(diff_bs)}")
            self.lbl_remain_disp.setStyleSheet("font-size: 15px; font-weight: 700; color: #E11D48;")
            self.lbl_change_disp.setText("$ 0.00  |  Bs. 0,00")
            self.btn_confirm.setEnabled(False)
        else:
            self.lbl_remain_disp.setText("PAGADO COMPLETAMENTE")
            self.lbl_remain_disp.setStyleSheet("font-size: 14px; font-weight: 700; color: #166534;")
            over_usd = round(abs(diff_usd), 2) if diff_usd < -0.01 else 0.0
            over_bs = round(over_usd * self.rate, 2)
            self.lbl_change_disp.setText(f"{format_usd(over_usd)}  |  {format_bs(over_bs)}")
            self.btn_confirm.setEnabled(True)

    def process_checkout(self):
        payments = []

        if self.spn_usd_cash.value() > 0:
            payments.append({
                "method": "USD_EFECTIVO",
                "amount": self.spn_usd_cash.value(),
                "currency": "USD",
                "reference": ""
            })

        if self.spn_bs_cash.value() > 0:
            payments.append({
                "method": "BS_EFECTIVO",
                "amount": self.spn_bs_cash.value(),
                "currency": "BS",
                "reference": ""
            })

        if self.spn_bs_card.value() > 0:
            payments.append({
                "method": "BS_TARJETA",
                "amount": self.spn_bs_card.value(),
                "currency": "BS",
                "reference": self.txt_card_ref.text().strip()
            })

        if self.spn_bs_pm.value() > 0:
            pm_ref = self.txt_pm_ref.text().strip()
            if not pm_ref:
                QMessageBox.warning(self, "Referencia Requerida",
                                    "El pago mediante Pago Móvil requiere obligatoriamente el número de referencia bancaria.")
                self.txt_pm_ref.setFocus()
                return

            payments.append({
                "method": "BS_PAGO_MOVIL",
                "amount": self.spn_bs_pm.value(),
                "currency": "BS",
                "reference": pm_ref
            })

        if not payments:
            QMessageBox.warning(self, "Sin Pagos", "Debe ingresar al menos un método de pago.")
            return

        client_name = self.txt_client_name.text().strip() or "Consumidor Final"
        client_id = self.txt_client_id.text().strip() or "V-00000000"

        ok, msg, sale_data = PosService.process_sale(
            items=self.items,
            payments=payments,
            client_name=client_name,
            client_id_doc=client_id
        )

        if ok:
            QMessageBox.information(
                self,
                "Venta Exitosa",
                f"✅ Factura {sale_data['invoice_number']} registrada exitosamente.\n\n"
                f"Cliente: {client_name}\n"
                f"Total USD: {format_usd(sale_data['total_usd'])}\n"
                f"Total BS: {format_bs(sale_data['total_bs'])}\n\n"
                f"Inventario descontado y registrado en arqueo de turno."
            )
            self.sale_completed.emit(sale_data or {})
            self.accept()
        else:
            QMessageBox.critical(self, "Error de Facturación", msg)
