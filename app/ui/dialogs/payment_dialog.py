from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QFrame,
    QGridLayout, QGroupBox, QCheckBox, QRadioButton, QButtonGroup,
    QWidget, QScrollArea, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from ...services.pos_service import PosService
from ...services.exchange_rate import ExchangeRateService
from ...utils.helpers import format_usd, format_bs
from ...utils.icon_helper import get_icon


class PaymentDialog(QDialog):
    sale_completed = Signal(dict)

    def __init__(self, items: List[Dict[str, Any]], total_usd: float, parent=None):
        super().__init__(parent)
        self.items = items
        self.total_usd = round(total_usd, 2)
        self.rate = ExchangeRateService.get_active_rate()
        self.total_bs = round(self.total_usd * self.rate, 2)

        self.setWindowTitle("Cobro y Facturación")
        self.total_change_usd = 0.0
        self.total_change_bs = 0.0
        self.current_over_usd = 0.0
        self.current_over_bs = 0.0

        # Altura fija a 540px según requerimiento del usuario
        self.setFixedSize(650, 540)

        self.setup_ui()
        self.calculate_balances()

    def showEvent(self, event):
        super().showEvent(event)
        # Centrar diálogo respecto a la ventana principal / pantalla asegurando margen inferior
        if self.parent():
            parent_win = self.parent().window()
            p_geom = parent_win.geometry()
            geo = self.geometry()
            geo.moveCenter(p_geom.center())
            screen = QApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                if geo.bottom() > avail.bottom() - 10:
                    geo.moveBottom(avail.bottom() - 15)
                if geo.top() < avail.top() + 10:
                    geo.moveTop(avail.top() + 15)
            self.setGeometry(geo)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(14, 12, 14, 12)

        # ==========================================
        # 1. Tarjeta de Totales a Pagar (Fija Superior)
        # ==========================================
        header_card = QFrame()
        header_card.setObjectName("cardHighlight")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 6, 14, 6)

        col1 = QVBoxLayout()
        lbl_t1 = QLabel("TOTAL A FACTURAR (USD)")
        lbl_t1.setStyleSheet("font-size: 10px; color: #222A2A; font-weight: 700; opacity: 0.8;")
        self.lbl_total_usd_disp = QLabel(format_usd(self.total_usd))
        self.lbl_total_usd_disp.setStyleSheet("font-size: 22px; font-weight: 900; color: #222A2A;")
        col1.addWidget(lbl_t1)
        col1.addWidget(self.lbl_total_usd_disp)

        col2 = QVBoxLayout()
        lbl_t2 = QLabel("TOTAL EN BOLIVARES")
        lbl_t2.setStyleSheet("font-size: 10px; color: #222A2A; font-weight: 700; opacity: 0.8;")
        self.lbl_total_bs_disp = QLabel(format_bs(self.total_bs))
        self.lbl_total_bs_disp.setStyleSheet("font-size: 22px; font-weight: 900; color: #4FBBBC;")
        col2.addWidget(lbl_t2)
        col2.addWidget(self.lbl_total_bs_disp)

        col3 = QVBoxLayout()
        lbl_rate_info = QLabel("TASA APLICADA:")
        lbl_rate_info.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_rate_val = QLabel(f"Bs. {self.rate:,.2f}")
        self.lbl_rate_val.setStyleSheet("font-size: 13px; font-weight: 700; color: #222A2A;")
        col3.addWidget(lbl_rate_info)
        col3.addWidget(self.lbl_rate_val)

        header_layout.addLayout(col1)
        header_layout.addLayout(col2)
        header_layout.addLayout(col3)
        main_layout.addWidget(header_card, 0)

        # ==========================================
        # 2. Área Desplazable con Slider / Scrollbar
        # ==========================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #EAE5D5;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4FBBBC;
                min-height: 28px;
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
        """)

        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(2, 2, 8, 2)
        scroll_layout.setSpacing(8)

        # Datos del Cliente
        client_box = QGroupBox("Datos del Cliente")
        client_box.setStyleSheet("font-weight: 600; color: #222A2A;")
        client_layout = QHBoxLayout(client_box)
        client_layout.setContentsMargins(10, 6, 10, 6)

        self.txt_client_name = QLineEdit("Consumidor Final")
        self.txt_client_name.setPlaceholderText("Nombre / Razón Social")

        self.txt_client_id = QLineEdit("V-00000000")
        self.txt_client_id.setPlaceholderText("Cédula / RIF")

        client_layout.addWidget(QLabel("Cliente:"))
        client_layout.addWidget(self.txt_client_name, 2)
        client_layout.addWidget(QLabel("C.I. / RIF:"))
        client_layout.addWidget(self.txt_client_id, 1)
        scroll_layout.addWidget(client_box)

        # Selección y Desglose de Métodos de Pago con Checkboxes
        pay_group = QGroupBox("Metodos de Pago")
        pay_group.setStyleSheet("font-weight: 700; color: #222A2A;")
        self.pay_layout = QVBoxLayout(pay_group)
        self.pay_layout.setContentsMargins(10, 10, 10, 10)
        self.pay_layout.setSpacing(8)

        inst_label = QLabel("Seleccione el o los metodos que utilizara el cliente:")
        inst_label.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal;")
        self.pay_layout.addWidget(inst_label)

        # Row 1: USD Efectivo
        self.row_usd = QWidget()
        l_usd = QHBoxLayout(self.row_usd)
        l_usd.setContentsMargins(0, 0, 0, 0)
        self.chk_usd = QCheckBox("USD Efectivo")
        self.chk_usd.setChecked(True)
        self.chk_usd.setStyleSheet("font-weight: 600;")
        self.chk_usd.toggled.connect(self.on_method_toggled)

        self.spn_usd_cash = QDoubleSpinBox()
        self.spn_usd_cash.setPrefix("$ ")
        self.spn_usd_cash.setRange(0.0, 999999.0)
        self.spn_usd_cash.setDecimals(2)
        self.spn_usd_cash.setValue(self.total_usd)
        self.spn_usd_cash.valueChanged.connect(self.calculate_balances)

        btn_auto_usd = QPushButton("Total")
        btn_auto_usd.setObjectName("btnSecondary")
        btn_auto_usd.setToolTip("Cubrir total en USD")
        btn_auto_usd.clicked.connect(self.fill_usd_remaining)

        l_usd.addWidget(self.chk_usd, 2)
        l_usd.addWidget(self.spn_usd_cash, 3)
        l_usd.addWidget(btn_auto_usd, 1)
        self.pay_layout.addWidget(self.row_usd)

        # Row 2: BS Efectivo
        self.row_bs_cash = QWidget()
        l_bs_cash = QHBoxLayout(self.row_bs_cash)
        l_bs_cash.setContentsMargins(0, 0, 0, 0)
        self.chk_bs_cash = QCheckBox("Bolivares Efectivo")
        self.chk_bs_cash.setStyleSheet("font-weight: 600;")
        self.chk_bs_cash.toggled.connect(self.on_method_toggled)

        self.spn_bs_cash = QDoubleSpinBox()
        self.spn_bs_cash.setPrefix("Bs. ")
        self.spn_bs_cash.setRange(0.0, 99999999.0)
        self.spn_bs_cash.setDecimals(2)
        self.spn_bs_cash.setValue(0.0)
        self.spn_bs_cash.setEnabled(False)
        self.spn_bs_cash.valueChanged.connect(self.calculate_balances)

        btn_auto_bs = QPushButton("Total")
        btn_auto_bs.setObjectName("btnSecondary")
        btn_auto_bs.setToolTip("Cubrir total en Bolívares")
        btn_auto_bs.clicked.connect(self.fill_bs_remaining)

        l_bs_cash.addWidget(self.chk_bs_cash, 2)
        l_bs_cash.addWidget(self.spn_bs_cash, 3)
        l_bs_cash.addWidget(btn_auto_bs, 1)
        self.pay_layout.addWidget(self.row_bs_cash)

        # Row 3: BS Tarjeta
        self.row_card = QWidget()
        l_card = QHBoxLayout(self.row_card)
        l_card.setContentsMargins(0, 0, 0, 0)
        self.chk_card = QCheckBox("Bolivares Tarjeta (P.O.S.)")
        self.chk_card.setStyleSheet("font-weight: 600;")
        self.chk_card.toggled.connect(self.on_method_toggled)

        self.spn_bs_card = QDoubleSpinBox()
        self.spn_bs_card.setPrefix("Bs. ")
        self.spn_bs_card.setRange(0.0, 99999999.0)
        self.spn_bs_card.setDecimals(2)
        self.spn_bs_card.setValue(0.0)
        self.spn_bs_card.setEnabled(False)
        self.spn_bs_card.valueChanged.connect(self.calculate_balances)

        self.txt_card_ref = QLineEdit()
        self.txt_card_ref.setPlaceholderText("Voucher / Lote (Opcional)")
        self.txt_card_ref.setEnabled(False)

        l_card.addWidget(self.chk_card, 2)
        l_card.addWidget(self.spn_bs_card, 2)
        l_card.addWidget(self.txt_card_ref, 2)
        self.pay_layout.addWidget(self.row_card)

        # Row 4: BS Pago Móvil
        self.row_pm = QWidget()
        l_pm = QHBoxLayout(self.row_pm)
        l_pm.setContentsMargins(0, 0, 0, 0)
        self.chk_pm = QCheckBox("Bolivares Pago Movil")
        self.chk_pm.setStyleSheet("font-weight: 600;")
        self.chk_pm.toggled.connect(self.on_method_toggled)

        self.spn_bs_pm = QDoubleSpinBox()
        self.spn_bs_pm.setPrefix("Bs. ")
        self.spn_bs_pm.setRange(0.0, 99999999.0)
        self.spn_bs_pm.setDecimals(2)
        self.spn_bs_pm.setValue(0.0)
        self.spn_bs_pm.setEnabled(False)
        self.spn_bs_pm.valueChanged.connect(self.calculate_balances)

        self.txt_pm_ref = QLineEdit()
        self.txt_pm_ref.setPlaceholderText("Referencia (Obligatorio) *")
        self.txt_pm_ref.setEnabled(False)

        l_pm.addWidget(self.chk_pm, 2)
        l_pm.addWidget(self.spn_bs_pm, 2)
        l_pm.addWidget(self.txt_pm_ref, 2)
        self.pay_layout.addWidget(self.row_pm)

        scroll_layout.addWidget(pay_group)

        # Resumen de Balances y Selector de Vuelto
        self.balance_card = QFrame()
        self.balance_card.setObjectName("card")
        bal_layout = QVBoxLayout(self.balance_card)
        bal_layout.setContentsMargins(12, 10, 12, 10)
        bal_layout.setSpacing(8)

        info_grid = QGridLayout()
        info_grid.addWidget(QLabel("Total Abonado:"), 0, 0)
        self.lbl_paid_disp = QLabel("$ 0.00 | Bs. 0,00")
        self.lbl_paid_disp.setStyleSheet("font-weight: 700; color: #222A2A;")
        info_grid.addWidget(self.lbl_paid_disp, 0, 1)

        info_grid.addWidget(QLabel("Resta por Pagar:"), 1, 0)
        self.lbl_remain_disp = QLabel()
        self.lbl_remain_disp.setStyleSheet("font-weight: 700; color: #EC4624;")
        info_grid.addWidget(self.lbl_remain_disp, 1, 1)

        bal_layout.addLayout(info_grid)

        # Panel de Vuelto / Sobrante (Soporta entrega combinada en USD y Bolívares)
        self.frame_change = QFrame()
        self.frame_change.setObjectName("cardHighlight")
        fc_layout = QVBoxLayout(self.frame_change)
        fc_layout.setContentsMargins(12, 8, 12, 8)
        fc_layout.setSpacing(6)

        # Encabezado con el Total General a Entregar de Vuelto
        h_vuelto_top = QHBoxLayout()
        lbl_change_title = QLabel("Vuelto / Cambio Total a Entregar:")
        lbl_change_title.setStyleSheet("font-weight: 700; color: #222A2A; font-size: 11px;")
        self.lbl_change_total_summary = QLabel("$ 0.00 | Bs. 0,00")
        self.lbl_change_total_summary.setStyleSheet("font-size: 13px; font-weight: 800; color: #EC4624;")
        h_vuelto_top.addWidget(lbl_change_title)
        h_vuelto_top.addStretch()
        h_vuelto_top.addWidget(self.lbl_change_total_summary)
        fc_layout.addLayout(h_vuelto_top)

        # Desglose Múltiple de Vuelto: USD y Bolívares combinables
        vuelto_grid = QGridLayout()
        vuelto_grid.setContentsMargins(0, 2, 0, 2)
        vuelto_grid.setSpacing(6)

        # Fila 1: Vuelto USD
        lbl_v_usd = QLabel("Vuelto en USD Efectivo:")
        lbl_v_usd.setStyleSheet("font-size: 11px; font-weight: 600; color: #222A2A;")
        self.spn_vuelto_usd = QDoubleSpinBox()
        self.spn_vuelto_usd.setPrefix("$ ")
        self.spn_vuelto_usd.setRange(0.0, 999999.0)
        self.spn_vuelto_usd.setDecimals(2)
        self.spn_vuelto_usd.valueChanged.connect(self.on_vuelto_usd_changed)

        btn_all_v_usd = QPushButton("Todo USD")
        btn_all_v_usd.setObjectName("btnSecondary")
        btn_all_v_usd.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_all_v_usd.clicked.connect(self.set_vuelto_all_usd)

        vuelto_grid.addWidget(lbl_v_usd, 0, 0)
        vuelto_grid.addWidget(self.spn_vuelto_usd, 0, 1)
        vuelto_grid.addWidget(btn_all_v_usd, 0, 2)

        # Fila 2: Vuelto Bs
        lbl_v_bs = QLabel("Vuelto en Bs. Efectivo:")
        lbl_v_bs.setStyleSheet("font-size: 11px; font-weight: 600; color: #222A2A;")
        self.spn_vuelto_bs = QDoubleSpinBox()
        self.spn_vuelto_bs.setPrefix("Bs. ")
        self.spn_vuelto_bs.setRange(0.0, 999999999.0)
        self.spn_vuelto_bs.setDecimals(2)
        self.spn_vuelto_bs.valueChanged.connect(self.on_vuelto_bs_changed)

        btn_all_v_bs = QPushButton("Todo Bs")
        btn_all_v_bs.setObjectName("btnSecondary")
        btn_all_v_bs.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_all_v_bs.clicked.connect(self.set_vuelto_all_bs)

        vuelto_grid.addWidget(lbl_v_bs, 1, 0)
        vuelto_grid.addWidget(self.spn_vuelto_bs, 1, 1)
        vuelto_grid.addWidget(btn_all_v_bs, 1, 2)

        fc_layout.addLayout(vuelto_grid)

        # Indicador de entrega detallada al cliente
        self.lbl_change_amount = QLabel("$ 0.00")
        self.lbl_change_amount.setStyleSheet("font-size: 14px; font-weight: 900; color: #222A2A;")
        fc_layout.addWidget(self.lbl_change_amount)

        bal_layout.addWidget(self.frame_change)
        self.frame_change.setVisible(False)

        scroll_layout.addWidget(self.balance_card)

        self.scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(self.scroll_area, 1)

        # ==========================================
        # 3. Botones de Acción (Fijos Inferiores)
        # ==========================================
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(0, 4, 0, 0)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("Facturar y Finalizar Venta")
        self.btn_confirm.setObjectName("btnSuccess")
        self.btn_confirm.setIcon(get_icon("check", "#222A2A"))
        self.btn_confirm.setStyleSheet("font-size: 14px; font-weight: 800; padding: 11px 24px;")
        self.btn_confirm.clicked.connect(self.process_checkout)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_confirm)
        main_layout.addLayout(btn_box, 0)

    def on_method_toggled(self):
        # USD
        self.spn_usd_cash.setEnabled(self.chk_usd.isChecked())
        if not self.chk_usd.isChecked():
            self.spn_usd_cash.setValue(0.0)

        # BS Efectivo
        self.spn_bs_cash.setEnabled(self.chk_bs_cash.isChecked())
        if not self.chk_bs_cash.isChecked():
            self.spn_bs_cash.setValue(0.0)

        # BS Tarjeta
        self.spn_bs_card.setEnabled(self.chk_card.isChecked())
        self.txt_card_ref.setEnabled(self.chk_card.isChecked())
        if not self.chk_card.isChecked():
            self.spn_bs_card.setValue(0.0)
            self.txt_card_ref.clear()

        # BS Pago Móvil
        self.spn_bs_pm.setEnabled(self.chk_pm.isChecked())
        self.txt_pm_ref.setEnabled(self.chk_pm.isChecked())
        if not self.chk_pm.isChecked():
            self.spn_bs_pm.setValue(0.0)
            self.txt_pm_ref.clear()

        self.calculate_balances()

    def fill_usd_remaining(self):
        if not self.chk_usd.isChecked():
            self.chk_usd.setChecked(True)
        bs_other = (self.spn_bs_cash.value() if self.chk_bs_cash.isChecked() else 0.0) + \
                   (self.spn_bs_card.value() if self.chk_card.isChecked() else 0.0) + \
                   (self.spn_bs_pm.value() if self.chk_pm.isChecked() else 0.0)
        usd_other = bs_other / self.rate
        rem = max(0.0, round(self.total_usd - usd_other, 2))
        self.spn_usd_cash.setValue(rem if rem > 0 else self.total_usd)

    def fill_bs_remaining(self):
        if not self.chk_bs_cash.isChecked():
            self.chk_bs_cash.setChecked(True)
        usd_cash = self.spn_usd_cash.value() if self.chk_usd.isChecked() else 0.0
        rem_usd = max(0.0, self.total_usd - usd_cash)
        rem_bs = round(rem_usd * self.rate, 2)
        self.spn_bs_cash.setValue(rem_bs if rem_bs > 0 else self.total_bs)

    def calculate_balances(self):
        usd_cash = self.spn_usd_cash.value() if self.chk_usd.isChecked() else 0.0
        bs_cash = self.spn_bs_cash.value() if self.chk_bs_cash.isChecked() else 0.0
        bs_card = self.spn_bs_card.value() if self.chk_card.isChecked() else 0.0
        bs_pm = self.spn_bs_pm.value() if self.chk_pm.isChecked() else 0.0

        paid_usd = usd_cash + ((bs_cash + bs_card + bs_pm) / self.rate)
        paid_bs = (usd_cash * self.rate) + (bs_cash + bs_card + bs_pm)

        self.lbl_paid_disp.setText(f"{format_usd(paid_usd)}  |  {format_bs(paid_bs)}")

        diff_usd = round(self.total_usd - paid_usd, 2)
        diff_bs = round(diff_usd * self.rate, 2)

        if diff_usd > 0.01:
            self.lbl_remain_disp.setText(f"{format_usd(diff_usd)}  |  {format_bs(diff_bs)}")
            self.lbl_remain_disp.setStyleSheet("font-size: 15px; font-weight: 700; color: #EC4624;")
            self.frame_change.setVisible(False)
            self.current_over_usd = 0.0
            self.current_over_bs = 0.0
            self.spn_vuelto_usd.setValue(0.0)
            self.spn_vuelto_bs.setValue(0.0)
            self.btn_confirm.setEnabled(False)
        else:
            self.lbl_remain_disp.setText("PAGADO COMPLETAMENTE")
            self.lbl_remain_disp.setStyleSheet("font-size: 14px; font-weight: 700; color: #4FBBBC;")
            self.btn_confirm.setEnabled(True)

            over_usd = round(abs(diff_usd), 2) if diff_usd < -0.01 else 0.0
            if over_usd > 0.01:
                prev_over = self.current_over_usd
                self.current_over_usd = over_usd
                self.current_over_bs = round(over_usd * self.rate, 2)
                self.frame_change.setVisible(True)
                self.lbl_change_total_summary.setText(f"{format_usd(self.current_over_usd)}  |  {format_bs(self.current_over_bs)}")

                # Configurar rangos máximos de los spinboxes
                self.spn_vuelto_usd.setMaximum(self.current_over_usd)
                self.spn_vuelto_bs.setMaximum(self.current_over_bs)

                # Si cambió el monto total de vuelto o estaba en cero, inicializar desglose
                if abs(prev_over - over_usd) > 0.01 or (self.spn_vuelto_usd.value() == 0 and self.spn_vuelto_bs.value() == 0):
                    if self.chk_usd.isChecked() and self.spn_usd_cash.value() > 0:
                        self.set_vuelto_all_usd()
                    else:
                        self.set_vuelto_all_bs()
                else:
                    self.update_vuelto_summary_text()
            else:
                self.current_over_usd = 0.0
                self.current_over_bs = 0.0
                self.frame_change.setVisible(False)
                self.spn_vuelto_usd.setValue(0.0)
                self.spn_vuelto_bs.setValue(0.0)

    def on_vuelto_usd_changed(self, val: float):
        if not self.frame_change.isVisible() or self.current_over_usd <= 0:
            return
        v_usd = min(val, self.current_over_usd)
        rem_usd = max(0.0, round(self.current_over_usd - v_usd, 2))
        rem_bs = round(rem_usd * self.rate, 2)
        self.spn_vuelto_bs.blockSignals(True)
        self.spn_vuelto_bs.setValue(rem_bs)
        self.spn_vuelto_bs.blockSignals(False)
        self.update_vuelto_summary_text()

    def on_vuelto_bs_changed(self, val: float):
        if not self.frame_change.isVisible() or self.current_over_bs <= 0:
            return
        v_bs = min(val, self.current_over_bs)
        rem_bs = max(0.0, round(self.current_over_bs - v_bs, 2))
        rem_usd = round(rem_bs / self.rate, 2)
        self.spn_vuelto_usd.blockSignals(True)
        self.spn_vuelto_usd.setValue(rem_usd)
        self.spn_vuelto_usd.blockSignals(False)
        self.update_vuelto_summary_text()

    def set_vuelto_all_usd(self):
        self.spn_vuelto_usd.setValue(self.current_over_usd)

    def set_vuelto_all_bs(self):
        self.spn_vuelto_bs.setValue(self.current_over_bs)

    def update_vuelto_summary_text(self):
        v_usd = round(self.spn_vuelto_usd.value(), 2)
        v_bs = round(self.spn_vuelto_bs.value(), 2)
        if v_usd > 0 and v_bs > 0:
            self.lbl_change_amount.setText(f"Entregar: {format_usd(v_usd)} (USD)  +  {format_bs(v_bs)} (Bolívares)")
            self.lbl_change_amount.setStyleSheet("font-size: 13px; font-weight: 800; color: #222A2A;")
        elif v_usd > 0:
            self.lbl_change_amount.setText(f"Entregar: {format_usd(v_usd)} en efectivo (USD)")
            self.lbl_change_amount.setStyleSheet("font-size: 13px; font-weight: 800; color: #222A2A;")
        elif v_bs > 0:
            self.lbl_change_amount.setText(f"Entregar: {format_bs(v_bs)} en efectivo (Bolívares)")
            self.lbl_change_amount.setStyleSheet("font-size: 13px; font-weight: 800; color: #F39120;")
        else:
            self.lbl_change_amount.setText("$ 0.00 | Bs. 0,00")

    def process_checkout(self):
        payments = []

        if self.chk_usd.isChecked() and self.spn_usd_cash.value() > 0:
            payments.append({
                "method": "USD_EFECTIVO",
                "amount": self.spn_usd_cash.value(),
                "currency": "USD",
                "reference": ""
            })

        if self.chk_bs_cash.isChecked() and self.spn_bs_cash.value() > 0:
            payments.append({
                "method": "BS_EFECTIVO",
                "amount": self.spn_bs_cash.value(),
                "currency": "BS",
                "reference": ""
            })

        if self.chk_card.isChecked() and self.spn_bs_card.value() > 0:
            payments.append({
                "method": "BS_TARJETA",
                "amount": self.spn_bs_card.value(),
                "currency": "BS",
                "reference": self.txt_card_ref.text().strip()
            })

        if self.chk_pm.isChecked() and self.spn_bs_pm.value() > 0:
            pm_ref = self.txt_pm_ref.text().strip()
            if not pm_ref:
                QMessageBox.warning(self, "Referencia Requerida",
                                    "El metodo Pago Movil requiere obligatoriamente el numero de referencia bancaria.")
                self.txt_pm_ref.setFocus()
                return

            payments.append({
                "method": "BS_PAGO_MOVIL",
                "amount": self.spn_bs_pm.value(),
                "currency": "BS",
                "reference": pm_ref
            })

        if not payments:
            QMessageBox.warning(self, "Sin Pagos", "Debe marcar y especificar al menos un metodo de pago.")
            return

        client_name = self.txt_client_name.text().strip() or "Consumidor Final"
        client_id = self.txt_client_id.text().strip() or "V-00000000"

        change_usd = round(self.spn_vuelto_usd.value(), 2) if self.frame_change.isVisible() else 0.0
        change_bs = round(self.spn_vuelto_bs.value(), 2) if self.frame_change.isVisible() else 0.0

        ok, msg, sale_data = PosService.process_sale(
            items=self.items,
            payments=payments,
            client_name=client_name,
            client_id_doc=client_id,
            change_usd=change_usd,
            change_bs=change_bs
        )

        if ok:
            vuelto_msg = ""
            if self.frame_change.isVisible() and (change_usd > 0 or change_bs > 0):
                vuelto_msg = f"\n\nRECORDATORIO DE VUELTO ENTREGADO:\n{self.lbl_change_amount.text()}"

            QMessageBox.information(
                self,
                "Venta Procesada",
                f"Factura {sale_data['invoice_number']} registrada exitosamente.\n\n"
                f"Cliente: {client_name}\n"
                f"Total: {format_usd(sale_data['total_usd'])} ({format_bs(sale_data['total_bs'])})"
                f"{vuelto_msg}"
            )
            self.sale_completed.emit(sale_data or {})
            self.accept()
        else:
            QMessageBox.critical(self, "Error al Facturar", msg)
