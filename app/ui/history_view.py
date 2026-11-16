from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QAbstractItemView, QDateEdit, QGridLayout
)
from PySide6.QtCore import Qt, QDate, Signal
from ..services.movement_service import MovementService
from ..services.shift_service import ShiftService
from ..utils.helpers import format_usd, format_bs, format_dt_display
from ..utils.icon_helper import get_icon
from .dialogs.shift_close_dialog import ShiftCloseDialog
from .dialogs.shift_open_dialog import ShiftOpenDialog
from .dialogs.manual_movement_dialog import ManualMovementDialog


class HistoryView(QWidget):
    shift_state_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_movements()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Panel de Control de Turno y Arqueo
        self.shift_card = QFrame()
        self.shift_card.setObjectName("card")
        sc_layout = QGridLayout(self.shift_card)
        sc_layout.setSpacing(12)

        # Estado del turno
        self.lbl_shift_title = QLabel("ESTADO DEL TURNO:")
        self.lbl_shift_title.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 700;")
        self.lbl_shift_desc = QLabel("Cargando...")
        self.lbl_shift_desc.setStyleSheet("font-size: 16px; font-weight: 900; color: #222A2A;")

        sc_layout.addWidget(self.lbl_shift_title, 0, 0)
        sc_layout.addWidget(self.lbl_shift_desc, 1, 0)

        # Resumen de Gaveta
        self.lbl_drawer_summary = QLabel()
        self.lbl_drawer_summary.setStyleSheet("font-size: 12px; color: #222A2A; font-weight: 500;")
        sc_layout.addWidget(self.lbl_drawer_summary, 0, 1, 2, 1)

        # Botones de Operación de Turno
        btn_box = QHBoxLayout()
        self.btn_open_shift = QPushButton("Abrir Turno")
        self.btn_open_shift.setObjectName("btnSuccess")
        self.btn_open_shift.setIcon(get_icon("unlock", "#222A2A", size=16))
        self.btn_open_shift.clicked.connect(self.open_shift_modal)

        self.btn_manual_move = QPushButton("Movimiento Manual (+ / -)")
        self.btn_manual_move.setObjectName("btnSecondary")
        self.btn_manual_move.setIcon(get_icon("cash", "#222A2A", size=16))
        self.btn_manual_move.clicked.connect(self.open_manual_movement_modal)

        self.btn_close_shift = QPushButton("Cerrar Turno y Arquear")
        self.btn_close_shift.setObjectName("btnDanger")
        self.btn_close_shift.setIcon(get_icon("lock", "#FFFFFF", size=16))
        self.btn_close_shift.setStyleSheet("font-weight: 700; padding: 10px 16px;")
        self.btn_close_shift.clicked.connect(self.open_close_shift_modal)

        btn_box.addWidget(self.btn_open_shift)
        btn_box.addWidget(self.btn_manual_move)
        btn_box.addWidget(self.btn_close_shift)
        sc_layout.addLayout(btn_box, 0, 2, 2, 1)

        layout.addWidget(self.shift_card)

        # Barra de Filtros
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        filter_bar.addWidget(QLabel("Filtrar por:"))

        self.cmb_shift_filter = QComboBox()
        self.cmb_shift_filter.addItem("Turno Actual", "CURRENT")
        self.cmb_shift_filter.addItem("Todos los Movimientos", "ALL")
        self.cmb_shift_filter.currentIndexChanged.connect(self.load_movements)
        filter_bar.addWidget(self.cmb_shift_filter)

        self.cmb_type_filter = QComboBox()
        self.cmb_type_filter.addItems([
            "TODOS", "VENTA", "AVANCE_EFECTIVO", "INGRESO_MANUAL", "EGRESO_MANUAL", "APERTURA", "CIERRE"
        ])
        self.cmb_type_filter.currentIndexChanged.connect(self.load_movements)
        filter_bar.addWidget(self.cmb_type_filter)

        filter_bar.addWidget(QLabel("Desde:"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(-7))
        self.date_start.dateChanged.connect(self.load_movements)
        filter_bar.addWidget(self.date_start)

        filter_bar.addWidget(QLabel("Hasta:"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self.load_movements)
        filter_bar.addWidget(self.date_end)

        btn_refresh = QPushButton("Actualizar")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.setIcon(get_icon("refresh", "#222A2A", size=15))
        btn_refresh.clicked.connect(self.load_movements)
        filter_bar.addWidget(btn_refresh)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # Tabla de Movimientos
        self.tbl_movements = QTableWidget()
        self.tbl_movements.setColumnCount(8)
        self.tbl_movements.setHorizontalHeaderLabels([
            "ID", "Fecha y Hora", "Turno", "Tipo de Movimiento",
            "Descripción", "Método", "Monto USD", "Monto Bolívares"
        ])
        self.tbl_movements.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_movements.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_movements.setColumnWidth(0, 50)
        self.tbl_movements.setColumnWidth(1, 140)
        self.tbl_movements.setColumnWidth(2, 70)
        self.tbl_movements.setColumnWidth(3, 130)
        self.tbl_movements.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tbl_movements.setColumnWidth(5, 100)
        self.tbl_movements.setColumnWidth(6, 95)
        self.tbl_movements.setColumnWidth(7, 125)
        layout.addWidget(self.tbl_movements)

    def refresh_active_shift(self):
        shift = ShiftService.get_active_shift()
        if shift:
            s_id = shift["id"]
            self.lbl_shift_desc.setText(f"Turno #{s_id} ABIERTO")
            self.lbl_shift_desc.setStyleSheet("font-size: 16px; font-weight: 900; color: #4FBBBC;")

            metrics = ShiftService.get_shift_metrics(s_id)
            exp_usd = metrics.get("expected_cash_usd", 0.0)
            exp_bs = metrics.get("expected_cash_bs", 0.0)
            card = metrics.get("total_card_bs", 0.0)
            pm = metrics.get("total_pago_movil_bs", 0.0)

            self.lbl_drawer_summary.setText(
                f"Efectivo en Gaveta: {format_usd(exp_usd)}  |  {format_bs(exp_bs)}\n"
                f"Tarjeta POS: {format_bs(card)}  |  Pago Móvil: {format_bs(pm)}"
            )

            self.btn_open_shift.setEnabled(False)
            self.btn_close_shift.setEnabled(True)
            self.btn_manual_move.setEnabled(True)
        else:
            self.lbl_shift_desc.setText("Turno CERRADO")
            self.lbl_shift_desc.setStyleSheet("font-size: 16px; font-weight: 900; color: #EC4624;")
            self.lbl_drawer_summary.setText("No hay turno abierto. Abra un turno para registrar ventas y movimientos.")
            self.btn_open_shift.setEnabled(True)
            self.btn_close_shift.setEnabled(False)
            self.btn_manual_move.setEnabled(False)

    def load_movements(self):
        self.refresh_active_shift()

        shift_mode = self.cmb_shift_filter.currentData()
        active_shift = ShiftService.get_active_shift()

        shift_id = None
        if shift_mode == "CURRENT":
            shift_id = active_shift["id"] if active_shift else -1

        m_type = self.cmb_type_filter.currentText()
        d_start = self.date_start.date().toString("yyyy-MM-dd")
        d_end = self.date_end.date().toString("yyyy-MM-dd")

        movements = MovementService.list_movements(
            shift_id=shift_id,
            start_date=d_start if shift_mode == "ALL" else None,
            end_date=d_end if shift_mode == "ALL" else None,
            movement_type=m_type,
            limit=300
        )

        self.tbl_movements.setRowCount(len(movements))

        for row, m in enumerate(movements):
            it_id = QTableWidgetItem(str(m["id"]))
            it_date = QTableWidgetItem(format_dt_display(m["created_at"]))
            it_shift = QTableWidgetItem(f"#{m['shift_id']}" if m["shift_id"] else "N/A")
            it_type = QTableWidgetItem(str(m["type"]))
            it_desc = QTableWidgetItem(str(m["description"]))
            it_method = QTableWidgetItem(str(m.get("payment_method") or "").replace("BS_", "").replace("USD_", ""))
            it_usd = QTableWidgetItem(format_usd(m["amount_usd"]))
            it_bs = QTableWidgetItem(format_bs(m["amount_bs"]))

            it_id.setTextAlignment(Qt.AlignCenter)
            it_date.setTextAlignment(Qt.AlignCenter)
            it_shift.setTextAlignment(Qt.AlignCenter)
            it_type.setTextAlignment(Qt.AlignCenter)
            it_method.setTextAlignment(Qt.AlignCenter)
            it_usd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_bs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if m["type"] == "VENTA":
                it_type.setForeground(Qt.darkGreen)
            elif m["type"] == "AVANCE_EFECTIVO":
                it_type.setForeground(Qt.darkYellow)
            elif m["type"] == "EGRESO_MANUAL":
                it_type.setForeground(Qt.red)
            elif m["type"] == "CIERRE":
                it_type.setForeground(Qt.darkRed)

            self.tbl_movements.setItem(row, 0, it_id)
            self.tbl_movements.setItem(row, 1, it_date)
            self.tbl_movements.setItem(row, 2, it_shift)
            self.tbl_movements.setItem(row, 3, it_type)
            self.tbl_movements.setItem(row, 4, it_desc)
            self.tbl_movements.setItem(row, 5, it_method)
            self.tbl_movements.setItem(row, 6, it_usd)
            self.tbl_movements.setItem(row, 7, it_bs)

    def open_shift_modal(self):
        dlg = ShiftOpenDialog(parent=self)
        dlg.shift_opened.connect(lambda s_id: self.on_shift_changed())
        dlg.exec()

    def open_close_shift_modal(self):
        shift = ShiftService.get_active_shift()
        if not shift:
            QMessageBox.information(self, "Aviso", "No hay ningun turno abierto actualmente.")
            return

        dlg = ShiftCloseDialog(shift_id=shift["id"], parent=self)
        dlg.shift_closed.connect(lambda r: self.on_shift_changed())
        dlg.exec()

    def open_manual_movement_modal(self):
        dlg = ManualMovementDialog(parent=self)
        dlg.movement_added.connect(self.load_movements)
        dlg.exec()

    def on_shift_changed(self):
        self.load_movements()
        self.shift_state_changed.emit()
