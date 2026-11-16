from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from ..services.exchange_rate import ExchangeRateService
from ..services.shift_service import ShiftService
from ..utils.helpers import format_bs
from ..utils.icon_helper import get_icon


class HomeView(QWidget):
    navigate_to = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_status()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(10)

        main_layout.addStretch(1)

        # Contenedor central elegante centrado
        center_card = QFrame()
        center_card.setObjectName("homeCenterCard")
        center_card.setStyleSheet("""
            QFrame#homeCenterCard {
                background-color: #222A2A;
                border-radius: 16px;
                padding: 36px 30px;
                border: 1.5px solid #4FBBBC;
            }
        """)
        center_layout = QVBoxLayout(center_card)
        center_layout.setSpacing(14)
        center_layout.setAlignment(Qt.AlignCenter)

        # Logo opcional si existe
        logo_path = Path("img/atlaserp-icon-sin-fondo.svg")
        if logo_path.exists():
            lbl_logo_img = QLabel()
            lbl_logo_img.setAlignment(Qt.AlignCenter)
            lbl_logo_img.setStyleSheet("background: transparent; border: none;")
            lbl_logo_img.setPixmap(get_icon("inventory", "#4FBBBC", size=60).pixmap(60, 60))
            center_layout.addWidget(lbl_logo_img)

        # Nombre del Sistema
        self.lbl_system_name = QLabel("AtlasERP")
        self.lbl_system_name.setAlignment(Qt.AlignCenter)
        self.lbl_system_name.setStyleSheet("""
            font-size: 50px;
            font-weight: 900;
            color: #FFFFFF;
            letter-spacing: 2px;
            background: transparent;
            border: none;
            padding: 4px;
        """)
        center_layout.addWidget(self.lbl_system_name)

        # Subtítulo y estado offline
        self.lbl_subtitle = QLabel("SISTEMA DE GESTION & PUNTO DE VENTA | 100% OFFLINE")
        self.lbl_subtitle.setAlignment(Qt.AlignCenter)
        self.lbl_subtitle.setStyleSheet("""
            font-size: 13px;
            font-weight: 800;
            color: #4FBBBC;
            letter-spacing: 3px;
            background: transparent;
            border: none;
        """)
        center_layout.addWidget(self.lbl_subtitle)

        center_layout.addSpacing(10)

        # Tarjetas de estado (Solo Tasa y Caja)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)

        # Tarjeta 1: Tasa
        card_tasa = QFrame()
        card_tasa.setObjectName("homeCardTasa")
        card_tasa.setMinimumWidth(260)
        card_tasa.setStyleSheet("""
            QFrame#homeCardTasa {
                background-color: #2D3838;
                border: 1px solid rgba(79, 187, 188, 0.4);
                border-radius: 10px;
                padding: 14px 18px;
            }
        """)
        l_tasa = QVBoxLayout(card_tasa)
        l_tasa.setSpacing(4)
        lbl_t1 = QLabel("TASA ACTIVA DEL DIA")
        lbl_t1.setStyleSheet("color: #E2DAC2; font-size: 11px; font-weight: 700; background: transparent; border: none; letter-spacing: 1px;")
        self.lbl_tasa_val = QLabel("Bs. 0,00 / USD")
        self.lbl_tasa_val.setStyleSheet("color: #4FBBBC; font-size: 20px; font-weight: 900; background: transparent; border: none;")
        l_tasa.addWidget(lbl_t1)
        l_tasa.addWidget(self.lbl_tasa_val)
        stats_layout.addWidget(card_tasa)

        # Tarjeta 2: Estado de Caja
        card_caja = QFrame()
        card_caja.setObjectName("homeCardCaja")
        card_caja.setMinimumWidth(260)
        card_caja.setStyleSheet("""
            QFrame#homeCardCaja {
                background-color: #2D3838;
                border: 1px solid rgba(226, 218, 194, 0.3);
                border-radius: 10px;
                padding: 14px 18px;
            }
        """)
        l_caja = QVBoxLayout(card_caja)
        l_caja.setSpacing(4)
        lbl_c1 = QLabel("ESTADO DE CAJA")
        lbl_c1.setStyleSheet("color: #E2DAC2; font-size: 11px; font-weight: 700; background: transparent; border: none; letter-spacing: 1px;")
        self.lbl_caja_val = QLabel("Verificando...")
        self.lbl_caja_val.setStyleSheet("color: #F8FAFC; font-size: 20px; font-weight: 900; background: transparent; border: none;")
        l_caja.addWidget(lbl_c1)
        l_caja.addWidget(self.lbl_caja_val)
        stats_layout.addWidget(card_caja)

        center_layout.addLayout(stats_layout)
        center_layout.addSpacing(16)

        # Botones de Acceso Rápido con Iconos SVG
        nav_row = QHBoxLayout()
        nav_row.setSpacing(16)

        btn_pos = QPushButton("  Ir a Caja (Punto de Venta)")
        btn_pos.setIcon(get_icon("pos", "#222A2A", size=20))
        btn_pos.setStyleSheet("""
            QPushButton {
                background-color: #4FBBBC;
                color: #222A2A;
                font-size: 14px;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #43A5A6; }
        """)
        btn_pos.clicked.connect(lambda: self.navigate_to.emit(1))

        btn_inv = QPushButton("  Gestionar Inventario")
        btn_inv.setIcon(get_icon("inventory", "#FFFFFF", size=20))
        btn_inv.setStyleSheet("""
            QPushButton {
                background-color: #F39120;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #DD8015; }
        """)
        btn_inv.clicked.connect(lambda: self.navigate_to.emit(2))

        btn_rep = QPushButton("  Ver Reportes PDF")
        btn_rep.setIcon(get_icon("reports", "#222A2A", size=20))
        btn_rep.setStyleSheet("""
            QPushButton {
                background-color: #E2DAC2;
                color: #222A2A;
                font-size: 14px;
                font-weight: 800;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #D5CDAF; }
        """)
        btn_rep.clicked.connect(lambda: self.navigate_to.emit(4))

        nav_row.addWidget(btn_pos)
        nav_row.addWidget(btn_inv)
        nav_row.addWidget(btn_rep)
        center_layout.addLayout(nav_row)

        main_layout.addWidget(center_card)
        main_layout.addStretch(1)

    def refresh_status(self):
        rate = ExchangeRateService.get_active_rate()
        self.lbl_tasa_val.setText(f"{format_bs(rate)} / USD")

        shift = ShiftService.get_active_shift()
        if shift:
            self.lbl_caja_val.setText(f"Turno #{shift['id']} Abierto")
            self.lbl_caja_val.setStyleSheet("color: #4FBBBC; font-size: 20px; font-weight: 900; background: transparent; border: none;")
        else:
            self.lbl_caja_val.setText("Turno Cerrado")
            self.lbl_caja_val.setStyleSheet("color: #EC4624; font-size: 20px; font-weight: 900; background: transparent; border: none;")
