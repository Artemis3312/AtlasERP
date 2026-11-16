from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from ...services.shift_service import ShiftService
from ...utils.helpers import format_usd, format_bs, parse_float


class ShiftCloseDialog(QDialog):
    shift_closed = Signal(dict)

    def __init__(self, shift_id: int, parent=None):
        super().__init__(parent)
        self.shift_id = shift_id
        self.metrics = ShiftService.get_shift_metrics(shift_id)

        self.setWindowTitle(f"Arqueo de Caja y Cierre de Turno #{shift_id}")
        self.setMinimumWidth(640)
        self.setup_ui()
        self.calculate_differences()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # Encabezado
        lbl_title = QLabel(f"Arqueo y Cierre de Turno #{self.shift_id}")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        layout.addWidget(lbl_title)

        # Cuadrícula comparativa
        grid = QGridLayout()
        grid.setSpacing(12)

        # Columna Izquierda: Esperado según Sistema
        grp_expected = QGroupBox("1. Saldo Esperado en Sistema")
        grp_expected.setStyleSheet("font-weight: 600; color: #334155;")
        exp_layout = QVBoxLayout(grp_expected)

        self.lbl_exp_usd = QLabel(format_usd(self.metrics.get("expected_cash_usd", 0.0)))
        self.lbl_exp_usd.setStyleSheet("font-size: 18px; font-weight: 800; color: #166534;")

        self.lbl_exp_bs = QLabel(format_bs(self.metrics.get("expected_cash_bs", 0.0)))
        self.lbl_exp_bs.setStyleSheet("font-size: 18px; font-weight: 800; color: #2563EB;")

        exp_layout.addWidget(QLabel("Efectivo USD Esperado en Gaveta:"))
        exp_layout.addWidget(self.lbl_exp_usd)
        exp_layout.addSpacing(6)
        exp_layout.addWidget(QLabel("Efectivo Bolívares Esperado en Gaveta:"))
        exp_layout.addWidget(self.lbl_exp_bs)
        exp_layout.addSpacing(8)

        detalles_txt = (
            f"• Base Inicial: {format_usd(self.metrics.get('initial_cash_usd', 0))} | {format_bs(self.metrics.get('initial_cash_bs', 0))}\n"
            f"• Ventas Efec. USD: +{format_usd(self.metrics.get('sales_usd_cash', 0))}\n"
            f"• Ventas Efec. BS: +{format_bs(self.metrics.get('sales_bs_cash', 0))}\n"
            f"• Avances BS Entregados: -{format_bs(self.metrics.get('advances_dispensed_bs', 0))}"
        )
        lbl_details = QLabel(detalles_txt)
        lbl_details.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal;")
        exp_layout.addWidget(lbl_details)

        grid.addWidget(grp_expected, 0, 0)

        # Columna Derecha: Conteo Físico Real del Cajero
        grp_real = QGroupBox("2. Conteo Físico en Caja (Real)")
        grp_real.setStyleSheet("font-weight: 600; color: #334155;")
        real_layout = QVBoxLayout(grp_real)

        real_layout.addWidget(QLabel("💵 Efectivo Físico USD Contado:"))
        self.spn_real_usd = QDoubleSpinBox()
        self.spn_real_usd.setPrefix("$ ")
        self.spn_real_usd.setRange(0.0, 9999999.0)
        self.spn_real_usd.setDecimals(2)
        self.spn_real_usd.setValue(float(self.metrics.get("expected_cash_usd", 0.0)))
        self.spn_real_usd.setStyleSheet("font-size: 16px; font-weight: 700; color: #166534;")
        self.spn_real_usd.valueChanged.connect(self.calculate_differences)
        real_layout.addWidget(self.spn_real_usd)

        real_layout.addSpacing(6)
        real_layout.addWidget(QLabel("💴 Efectivo Físico Bolívares Contado:"))
        self.spn_real_bs = QDoubleSpinBox()
        self.spn_real_bs.setPrefix("Bs. ")
        self.spn_real_bs.setRange(0.0, 999999999.0)
        self.spn_real_bs.setDecimals(2)
        self.spn_real_bs.setValue(float(self.metrics.get("expected_cash_bs", 0.0)))
        self.spn_real_bs.setStyleSheet("font-size: 16px; font-weight: 700; color: #2563EB;")
        self.spn_real_bs.valueChanged.connect(self.calculate_differences)
        real_layout.addWidget(self.spn_real_bs)

        grid.addWidget(grp_real, 0, 1)

        layout.addLayout(grid)

        # Sección 3: Contabilización de Pagos Electrónicos (Tarjeta y Pago Móvil)
        grp_electronic = QGroupBox("3. Contabilización de Medios Electrónicos (A conciliar con Bancos)")
        grp_electronic.setStyleSheet("font-weight: 600; color: #334155;")
        elec_layout = QHBoxLayout(grp_electronic)

        card_card = QFrame()
        card_card.setObjectName("card")
        cc_l = QVBoxLayout(card_card)
        cc_l.addWidget(QLabel("💳 TOTAL TARJETA (P.O.S. / Débito):"))
        self.lbl_total_card = QLabel(format_bs(self.metrics.get("total_card_bs", 0.0)))
        self.lbl_total_card.setStyleSheet("font-size: 18px; font-weight: 800; color: #7C3AED;")
        cc_l.addWidget(self.lbl_total_card)
        cc_sub = QLabel("Verificar con Cierre de Lote del Terminal")
        cc_sub.setStyleSheet("font-size: 10px; color: #64748B; font-weight: normal;")
        cc_l.addWidget(cc_sub)
        elec_layout.addWidget(card_card)

        pm_card = QFrame()
        pm_card.setObjectName("card")
        pm_l = QVBoxLayout(pm_card)
        pm_l.addWidget(QLabel("📱 TOTAL PAGO MÓVIL:"))
        self.lbl_total_pm = QLabel(format_bs(self.metrics.get("total_pago_movil_bs", 0.0)))
        self.lbl_total_pm.setStyleSheet("font-size: 18px; font-weight: 800; color: #0284C7;")
        pm_l.addWidget(self.lbl_total_pm)
        pm_sub = QLabel("Verificar con Estado de Cuenta / App Bancaria")
        pm_sub.setStyleSheet("font-size: 10px; color: #64748B; font-weight: normal;")
        pm_l.addWidget(pm_sub)
        elec_layout.addWidget(pm_card)

        layout.addWidget(grp_electronic)

        # Sección 4: Comparación y Verificación de Faltantes/Sobrantes
        diff_card = QFrame()
        diff_card.setObjectName("card")
        diff_layout = QHBoxLayout(diff_card)

        diff_box_usd = QVBoxLayout()
        diff_box_usd.addWidget(QLabel("Diferencia Efectivo USD:"))
        self.lbl_diff_usd = QLabel()
        self.lbl_diff_usd.setStyleSheet("font-size: 16px; font-weight: 800;")
        diff_box_usd.addWidget(self.lbl_diff_usd)
        diff_layout.addLayout(diff_box_usd)

        diff_box_bs = QVBoxLayout()
        diff_box_bs.addWidget(QLabel("Diferencia Efectivo Bolívares:"))
        self.lbl_diff_bs = QLabel()
        self.lbl_diff_bs.setStyleSheet("font-size: 16px; font-weight: 800;")
        diff_box_bs.addWidget(self.lbl_diff_bs)
        diff_layout.addLayout(diff_box_bs)

        layout.addWidget(diff_card)

        # Observaciones
        layout.addWidget(QLabel("Notas u Observaciones del Cierre:"))
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Ej: Caja cuadrada sin novedades / Faltante justificado por redondeo")
        layout.addWidget(self.txt_notes)

        # Botones
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm_close = QPushButton("🔒 Confirmar y Cerrar Turno")
        self.btn_confirm_close.setObjectName("btnDanger")
        self.btn_confirm_close.setStyleSheet("font-size: 13px; font-weight: 700; padding: 10px 20px;")
        self.btn_confirm_close.clicked.connect(self.process_close)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_confirm_close)
        layout.addLayout(btn_box)

    def calculate_differences(self):
        exp_usd = float(self.metrics.get("expected_cash_usd", 0.0))
        exp_bs = float(self.metrics.get("expected_cash_bs", 0.0))

        real_usd = self.spn_real_usd.value()
        real_bs = self.spn_real_bs.value()

        diff_usd = round(real_usd - exp_usd, 2)
        diff_bs = round(real_bs - exp_bs, 2)

        # Etiqueta USD
        if abs(diff_usd) < 0.01:
            self.lbl_diff_usd.setText("✅ CUADRADO ($ 0.00)")
            self.lbl_diff_usd.setStyleSheet("font-size: 16px; font-weight: 800; color: #166534;")
        elif diff_usd > 0:
            self.lbl_diff_usd.setText(f"⚠️ SOBRANTE: +{format_usd(diff_usd)}")
            self.lbl_diff_usd.setStyleSheet("font-size: 16px; font-weight: 800; color: #D97706;")
        else:
            self.lbl_diff_usd.setText(f"❌ FALTANTE: {format_usd(diff_usd)}")
            self.lbl_diff_usd.setStyleSheet("font-size: 16px; font-weight: 800; color: #E11D48;")

        # Etiqueta BS
        if abs(diff_bs) < 0.01:
            self.lbl_diff_bs.setText("✅ CUADRADO (Bs. 0,00)")
            self.lbl_diff_bs.setStyleSheet("font-size: 16px; font-weight: 800; color: #166534;")
        elif diff_bs > 0:
            self.lbl_diff_bs.setText(f"⚠️ SOBRANTE: +{format_bs(diff_bs)}")
            self.lbl_diff_bs.setStyleSheet("font-size: 16px; font-weight: 800; color: #D97706;")
        else:
            self.lbl_diff_bs.setText(f"❌ FALTANTE: {format_bs(diff_bs)}")
            self.lbl_diff_bs.setStyleSheet("font-size: 16px; font-weight: 800; color: #E11D48;")

    def process_close(self):
        real_usd = self.spn_real_usd.value()
        real_bs = self.spn_real_bs.value()
        notes = self.txt_notes.text().strip()

        reply = QMessageBox.question(
            self,
            "Confirmar Cierre de Turno",
            f"¿Está seguro de cerrar el Turno #{self.shift_id}?\n\n"
            f"Efectivo Real USD: {format_usd(real_usd)}\n"
            f"Efectivo Real BS: {format_bs(real_bs)}\n\n"
            f"Esta acción finalizará el turno actual y registrará el arqueo.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        ok, msg, result = ShiftService.close_shift(self.shift_id, real_usd, real_bs, notes)
        if ok:
            QMessageBox.information(
                self,
                "Turno Cerrado",
                f"✅ Turno #{self.shift_id} cerrado exitosamente.\n\n"
                f"• Saldo USD: {format_usd(result['real_usd'])} (Dif: {format_usd(result['diff_usd'])})\n"
                f"• Saldo BS: {format_bs(result['real_bs'])} (Dif: {format_bs(result['diff_bs'])})\n"
                f"• Total Tarjeta: {format_bs(result['total_card_bs'])}\n"
                f"• Total Pago Móvil: {format_bs(result['total_pago_movil_bs'])}"
            )
            self.shift_closed.emit(result or {})
            self.accept()
        else:
            QMessageBox.critical(self, "Error al Cerrar", msg)
