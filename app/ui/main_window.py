import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QButtonGroup,
    QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from .styles import MODERN_STYLE
from .home_view import HomeView
from .pos_view import PosView
from .inventory_view import InventoryView
from .history_view import HistoryView
from .reports_view import ReportsView
from .dialogs.rate_dialog import RateDialog
from .dialogs.shift_open_dialog import ShiftOpenDialog
from .dialogs.shift_close_dialog import ShiftCloseDialog
from ..services.exchange_rate import ExchangeRateService
from ..services.shift_service import ShiftService
from ..utils.helpers import format_bs
from ..utils.icon_helper import get_icon, get_stateful_icon


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AtlasERP - Sistema de Gestion y Punto de Venta Offline")
        self.resize(1240, 780)
        self.setMinimumSize(1020, 660)
        self.setStyleSheet(MODERN_STYLE)

        # Cargar icono de aplicación si existe
        app_icon_path = Path("img/atlaserp.ico")
        if app_icon_path.exists():
            self.setWindowIcon(QIcon(str(app_icon_path)))

        self.setup_ui()
        self.setup_timers()
        self.refresh_global_header()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ==========================================
        # 1. Barra Lateral de Navegación (Sidebar)
        # ==========================================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 16)
        sidebar_layout.setSpacing(6)

        # Header de la Barra Lateral con Logo
        sb_header = QFrame()
        sb_header.setObjectName("sidebarHeader")
        sb_h_layout = QVBoxLayout(sb_header)
        sb_h_layout.setContentsMargins(18, 16, 18, 16)
        sb_h_layout.setSpacing(6)

        # Logo SVG de AtlasERP si está disponible
        logo_svg = Path("img/atlaserp-icon-sin-fondo.svg")
        if logo_svg.exists():
            lbl_logo_svg = QLabel()
            lbl_logo_svg.setStyleSheet("background: transparent;")
            lbl_logo_svg.setPixmap(get_icon("inventory", "#4FBBBC", size=36).pixmap(36, 36))
            sb_h_layout.addWidget(lbl_logo_svg)

        lbl_logo = QLabel("AtlasERP")
        lbl_logo.setObjectName("sidebarTitle")

        lbl_sub = QLabel("PUNTO DE VENTA OFFLINE")
        lbl_sub.setObjectName("sidebarSubtitle")

        sb_h_layout.addWidget(lbl_logo)
        sb_h_layout.addWidget(lbl_sub)
        sidebar_layout.addWidget(sb_header)

        sidebar_layout.addSpacing(10)

        # Botones de Navegación con Iconos SVG (Sin Emojis)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_home = QPushButton("  Inicio")
        self.btn_nav_home.setObjectName("navButton")
        self.btn_nav_home.setIcon(get_stateful_icon("home", "#E2DAC2", "#222A2A"))
        self.btn_nav_home.setCheckable(True)
        self.btn_nav_home.setChecked(True)

        self.btn_nav_pos = QPushButton("  Caja (P.O.S.)")
        self.btn_nav_pos.setObjectName("navButton")
        self.btn_nav_pos.setIcon(get_stateful_icon("pos", "#E2DAC2", "#222A2A"))
        self.btn_nav_pos.setCheckable(True)

        self.btn_nav_inv = QPushButton("  Inventario")
        self.btn_nav_inv.setObjectName("navButton")
        self.btn_nav_inv.setIcon(get_stateful_icon("inventory", "#E2DAC2", "#222A2A"))
        self.btn_nav_inv.setCheckable(True)

        self.btn_nav_history = QPushButton("  Historial y Arqueo")
        self.btn_nav_history.setObjectName("navButton")
        self.btn_nav_history.setIcon(get_stateful_icon("history", "#E2DAC2", "#222A2A"))
        self.btn_nav_history.setCheckable(True)

        self.btn_nav_reports = QPushButton("  Reportes PDF")
        self.btn_nav_reports.setObjectName("navButton")
        self.btn_nav_reports.setIcon(get_stateful_icon("reports", "#E2DAC2", "#222A2A"))
        self.btn_nav_reports.setCheckable(True)

        nav_buttons = [
            (self.btn_nav_home, 0),
            (self.btn_nav_pos, 1),
            (self.btn_nav_inv, 2),
            (self.btn_nav_history, 3),
            (self.btn_nav_reports, 4),
        ]

        for btn, idx in nav_buttons:
            self.nav_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)

        self.nav_group.idClicked.connect(self.switch_view)

        sidebar_layout.addStretch()

        # Versión en el pie de la barra lateral (Con fondo transparente y color armónico)
        lbl_ver = QLabel("AtlasERP v1.0.0\n100% Offline | SQLite")
        lbl_ver.setObjectName("sidebarFooter")
        sidebar_layout.addWidget(lbl_ver)

        root_layout.addWidget(sidebar)

        # ==========================================
        # 2. Área de Contenido Principal + Header Superior
        # ==========================================
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header Superior
        top_header = QFrame()
        top_header.setObjectName("topHeader")
        th_layout = QHBoxLayout(top_header)
        th_layout.setContentsMargins(18, 8, 18, 8)
        th_layout.setSpacing(14)

        # Reloj / Fecha
        self.lbl_clock = QLabel()
        self.lbl_clock.setStyleSheet("font-size: 12px; color: #222A2A; font-weight: 600;")
        th_layout.addWidget(self.lbl_clock)

        th_layout.addStretch()

        # Widget de Tasa Activa
        self.rate_frame = QFrame()
        self.rate_frame.setStyleSheet("""
            QFrame {
                background-color: #FAF8F5;
                border: 1px solid #D5CEB9;
                border-radius: 6px;
                padding: 2px 8px;
            }
        """)
        rf_layout = QHBoxLayout(self.rate_frame)
        rf_layout.setContentsMargins(6, 2, 6, 2)
        rf_layout.setSpacing(8)

        self.lbl_header_rate = QLabel("Tasa: Bs. 0,00")
        self.lbl_header_rate.setStyleSheet("font-weight: 800; color: #222A2A; font-size: 12px;")

        self.btn_adjust_rate = QPushButton("Ajustar Tasa")
        self.btn_adjust_rate.setObjectName("btnSecondary")
        self.btn_adjust_rate.setIcon(get_icon("settings", "#222A2A", size=14))
        self.btn_adjust_rate.setStyleSheet("font-size: 11px; padding: 4px 8px;")
        self.btn_adjust_rate.clicked.connect(self.open_rate_dialog)

        rf_layout.addWidget(self.lbl_header_rate)
        rf_layout.addWidget(self.btn_adjust_rate)
        th_layout.addWidget(self.rate_frame)

        # Widget de Turno de Caja
        self.shift_frame = QFrame()
        self.shift_frame.setStyleSheet("""
            QFrame {
                background-color: #FAF8F5;
                border: 1px solid #D5CEB9;
                border-radius: 6px;
                padding: 2px 8px;
            }
        """)
        sf_layout = QHBoxLayout(self.shift_frame)
        sf_layout.setContentsMargins(6, 2, 6, 2)
        sf_layout.setSpacing(8)

        self.lbl_header_shift = QLabel("Turno: Cerrado")
        self.lbl_header_shift.setStyleSheet("font-weight: 800; font-size: 12px;")

        self.btn_shift_action = QPushButton("Turno")
        self.btn_shift_action.setStyleSheet("font-size: 11px; padding: 4px 10px;")
        self.btn_shift_action.clicked.connect(self.toggle_shift_action)

        sf_layout.addWidget(self.lbl_header_shift)
        sf_layout.addWidget(self.btn_shift_action)
        th_layout.addWidget(self.shift_frame)

        content_layout.addWidget(top_header)

        # Stack de Vistas
        self.stacked_views = QStackedWidget()

        self.home_view = HomeView()
        self.home_view.navigate_to.connect(self.switch_to_view_by_index)

        self.pos_view = PosView()
        self.pos_view.sale_processed.connect(self.on_data_updated)

        self.inventory_view = InventoryView()
        self.inventory_view.product_changed.connect(self.on_inventory_updated)

        self.history_view = HistoryView()
        self.history_view.shift_state_changed.connect(self.on_data_updated)

        self.reports_view = ReportsView()

        self.stacked_views.addWidget(self.home_view)       # 0
        self.stacked_views.addWidget(self.pos_view)        # 1
        self.stacked_views.addWidget(self.inventory_view)  # 2
        self.stacked_views.addWidget(self.history_view)    # 3
        self.stacked_views.addWidget(self.reports_view)    # 4

        content_layout.addWidget(self.stacked_views)
        root_layout.addWidget(content_container)

    def setup_timers(self):
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

    def update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock.setText(now.strftime("%A, %d de %B de %Y  |  %I:%M:%S %p"))

    def refresh_global_header(self):
        info = ExchangeRateService.get_rate_info()
        rate = info["rate"]
        source = info["source"].replace("DOLARAPI_", "")
        self.lbl_header_rate.setText(f"Tasa: {format_bs(rate)} / USD ({source})")

        shift = ShiftService.get_active_shift()
        if shift:
            self.lbl_header_shift.setText(f"Turno #{shift['id']} Abierto")
            self.lbl_header_shift.setStyleSheet("font-weight: 800; color: #4FBBBC; font-size: 12px;")
            self.btn_shift_action.setText("Cerrar")
            self.btn_shift_action.setIcon(get_icon("lock", "#FFFFFF", size=14))
            self.btn_shift_action.setObjectName("btnDanger")
            self.btn_shift_action.setStyleSheet("")
        else:
            self.lbl_header_shift.setText("Turno Cerrado")
            self.lbl_header_shift.setStyleSheet("font-weight: 800; color: #EC4624; font-size: 12px;")
            self.btn_shift_action.setText("Abrir")
            self.btn_shift_action.setIcon(get_icon("unlock", "#222A2A", size=14))
            self.btn_shift_action.setObjectName("btnSuccess")
            self.btn_shift_action.setStyleSheet("")

        self.home_view.refresh_status()
        self.pos_view.refresh_shift_banner()
        self.history_view.refresh_active_shift()

    def switch_view(self, index: int):
        self.stacked_views.setCurrentIndex(index)
        if index == 0:
            self.home_view.refresh_status()
        elif index == 1:
            self.pos_view.refresh_shift_banner()
            self.pos_view.load_catalog()
        elif index == 2:
            self.inventory_view.load_inventory()
        elif index == 3:
            self.history_view.load_movements()
        elif index == 4:
            self.reports_view.refresh_recent_reports()

    def switch_to_view_by_index(self, index: int):
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)
        self.switch_view(index)

    def open_rate_dialog(self):
        dlg = RateDialog(parent=self)
        dlg.rate_updated.connect(self.on_rate_changed)
        dlg.exec()

    def on_rate_changed(self, new_rate: float):
        self.refresh_global_header()
        self.pos_view.refresh_rate(new_rate)
        self.inventory_view.refresh_rate(new_rate)
        self.home_view.refresh_status()

    def toggle_shift_action(self):
        shift = ShiftService.get_active_shift()
        if shift:
            dlg = ShiftCloseDialog(shift_id=shift["id"], parent=self)
            dlg.shift_closed.connect(lambda r: self.on_data_updated())
            dlg.exec()
        else:
            dlg = ShiftOpenDialog(parent=self)
            dlg.shift_opened.connect(lambda s_id: self.on_data_updated())
            dlg.exec()

    def on_data_updated(self):
        self.refresh_global_header()
        self.history_view.load_movements()
        self.pos_view.refresh_shift_banner()
        self.pos_view.load_catalog()

    def on_inventory_updated(self):
        self.pos_view.load_catalog()

    def closeEvent(self, event):
        active_shift = ShiftService.get_active_shift()
        if active_shift:
            event.ignore()
            # Alerta formal: No se puede cerrar el sistema sin arquear la caja
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Turno de Caja Abierto")
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText(
                f"<b>ADVERTENCIA: TURNO DE CAJA ACTIVO</b><br><br>"
                f"El <b>Turno #{active_shift['id']}</b> ({active_shift.get('cashier_name', 'Cajero')}) "
                f"se encuentra actualmente abierto.<br><br>"
                f"Para mantener el control y cuadre de efectivo, <b>el programa no se puede cerrar sin antes arquear y cerrar la caja</b>.<br><br>"
                f"¿Desea realizar el arqueo y cierre de turno ahora para poder salir?"
            )
            btn_arqueo = msg_box.addButton("Arquear y Cerrar Caja", QMessageBox.AcceptRole)
            btn_arqueo.setObjectName("btnSuccess")
            btn_arqueo.setIcon(get_icon("check", "#222A2A"))

            btn_cancel = msg_box.addButton("Cancelar (Permanecer en el Sistema)", QMessageBox.RejectRole)
            btn_cancel.setObjectName("btnSecondary")

            msg_box.setDefaultButton(btn_arqueo)
            msg_box.exec()

            if msg_box.clickedButton() == btn_arqueo:
                dlg = ShiftCloseDialog(shift_id=active_shift["id"], parent=self)
                dlg.shift_closed.connect(lambda r: self.on_data_updated())
                if dlg.exec():
                    # Si el turno se cerró exitosamente, verificar y aceptar el cierre
                    if not ShiftService.get_active_shift():
                        event.accept()
        else:
            event.accept()
