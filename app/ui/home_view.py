from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from ..services.exchange_rate import ExchangeRateService
from ..services.shift_service import ShiftService
from ..utils.helpers import format_bs


class HomeView(QWidget):
    navigate_to = Signal(int)  # 1: POS, 2: Inventory, 3: History, 4: Reports

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(30)

        # Contenedor central elegante centrado
        main_layout.addStretch(1)

        center_card = QFrame()
        center_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0F172A, stop:1 #1E293B);
                border-radius: 16px;
                padding: 40px;
                border: 1px solid #334155;
            }
        """)
        center_layout = QVBoxLayout(center_card)
        center_layout.setSpacing(20)
        center_layout.setAlignment(Qt.AlignCenter)

        # Nombre del Sistema (Requisito fundamental)
        self.lbl_system_name = QLabel("AtlasERP")
        self.lbl_system_name.setAlignment(Qt.AlignCenter)
        self.lbl_system_name.setStyleSheet("""
            font-size: 56px;
            font-weight: 900;
            color: #FFFFFF;
            letter-spacing: 2px;
            margin-bottom: 0px;
        """)
        center_layout.addWidget(self.lbl_system_name)

        # Subtítulo y estado offline
        self.lbl_subtitle = QLabel("SISTEMA DE GESTIÓN & PUNTO DE VENTA | 100% OFFLINE")
        self.lbl_subtitle.setAlignment(Qt.AlignCenter)
        self.lbl_subtitle.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #38BDF8;
            letter-spacing: 3px;
        """)
        center_layout.addWidget(self.lbl_subtitle)

        center_layout.addSpacing(15)

        # Tarjetas de estado rápido en el centro
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        # Tarjeta 1: Tasa
        card_tasa = QFrame()
        card_tasa.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border-radius: 10px; padding: 12px;")
        l_tasa = QVBoxLayout(card_tasa)
        lbl_t1 = QLabel("TASA ACTIVA")
        lbl_t1.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.lbl_tasa_val = QLabel("Bs. 0,00")
        self.lbl_tasa_val.setStyleSheet("color: #34D399; font-size: 18px; font-weight: 800;")
        l_tasa.addWidget(lbl_t1)
        l_tasa.addWidget(self.lbl_tasa_val)
        stats_layout.addWidget(card_tasa)

        # Tarjeta 2: Estado de Caja
        card_caja = QFrame()
        card_caja.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border-radius: 10px; padding: 12px;")
        l_caja = QVBoxLayout(card_caja)
        lbl_c1 = QLabel("ESTADO DE CAJA")
        lbl_c1.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        self.lbl_caja_val = QLabel("Verificando...")
        self.lbl_caja_val.setStyleSheet("color: #F8FAFC; font-size: 18px; font-weight: 800;")
        l_caja.addWidget(lbl_c1)
        l_caja.addWidget(self.lbl_caja_val)
        stats_layout.addWidget(card_caja)

        # Tarjeta 3: Base de Datos
        card_db = QFrame()
        card_db.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border-radius: 10px; padding: 12px;")
        l_db = QVBoxLayout(card_db)
        lbl_db1 = QLabel("BASE DE DATOS")
        lbl_db1.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 600;")
        lbl_db2 = QLabel("SQLite Local (WAL)")
        lbl_db2.setStyleSheet("color: #60A5FA; font-size: 18px; font-weight: 800;")
        l_db.addWidget(lbl_db1)
        l_db.addWidget(lbl_db2)
        stats_layout.addWidget(card_db)

        center_layout.addLayout(stats_layout)
        center_layout.addSpacing(15)

        # Botones de Acceso Rápido
        nav_row = QHBoxLayout()
        nav_row.setSpacing(15)

        btn_pos = QPushButton("🛒 Ir a Caja (Punto de Venta)")
        btn_pos.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-size: 14px;
                font-weight: 700;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        btn_pos.clicked.connect(lambda: self.navigate_to.emit(1))

        btn_inv = QPushButton("📦 Gestionar Inventario")
        btn_inv.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-size: 14px;
                font-weight: 700;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #047857; }
        """)
        btn_inv.clicked.connect(lambda: self.navigate_to.emit(2))

        btn_rep = QPushButton("📊 Ver Reportes PDF")
        btn_rep.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: white;
                font-size: 14px;
                font-weight: 700;
                padding: 12px 20px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        btn_rep.clicked.connect(lambda: self.navigate_to.emit(4))

        nav_row.addWidget(btn_pos)
        nav_row.addWidget(btn_inv)
        nav_row.addWidget(btn_rep)
        center_layout.addLayout(nav_row)

        main_layout.addWidget(center_card)
        main_layout.addStretch(1)

    def refresh_status(self):
        # Tasa
        rate = ExchangeRateService.get_active_rate()
        self.lbl_tasa_val.setText(f"{format_bs(rate)} / USD")

        # Turno de caja
        shift = ShiftService.get_active_shift()
        if shift:
            self.lbl_caja_val.setText(f"🟢 Turno #{shift['id']} Abierto")
            self.lbl_caja_val.setStyleSheet("color: #34D399; font-size: 18px; font-weight: 800;")
        else:
            self.lbl_caja_val.setText("🔴 Turno Cerrado")
            self.lbl_caja_val.setStyleSheet("color: #F87171; font-size: 18px; font-weight: 800;")
