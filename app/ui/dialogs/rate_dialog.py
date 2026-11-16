from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QThread
from ...services.exchange_rate import ExchangeRateService
from ...utils.helpers import format_bs, parse_float


class RateFetchThread(QThread):
    finished_signal = Signal(bool, float, str)

    def __init__(self, source_type: str):
        super().__init__()
        self.source_type = source_type

    def run(self):
        success, rate, msg = ExchangeRateService.fetch_from_dolarapi(self.source_type, auto_save=False)
        self.finished_signal.emit(success, rate, msg)


class RateDialog(QDialog):
    rate_updated = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Tasa de Cambio (USD a Bolívares)")
        self.setMinimumWidth(460)
        self.setup_ui()
        self.load_current_info()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Tarjeta informativa actual
        self.info_card = QFrame()
        self.info_card.setObjectName("cardHighlight")
        card_layout = QVBoxLayout(self.info_card)

        self.lbl_current_rate = QLabel()
        self.lbl_current_rate.setStyleSheet("font-size: 20px; font-weight: 700; color: #166534;")
        self.lbl_source = QLabel()
        self.lbl_source.setStyleSheet("color: #4B5563; font-size: 11px;")

        card_layout.addWidget(self.lbl_current_rate)
        card_layout.addWidget(self.lbl_source)
        layout.addWidget(self.info_card)

        # Opción 1: Consulta a DolarAPI
        group_api = QGroupBox("Actualizar desde DolarAPI (Requiere Internet / Fallback Offline)")
        group_api.setStyleSheet("font-weight: 600; color: #1E293B;")
        api_layout = QVBoxLayout(group_api)

        api_desc = QLabel("Obtiene en tiempo real el valor oficial (BCV) o paralelo de dolarapi.com.")
        api_desc.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal;")
        api_desc.setWordWrap(True)
        api_layout.addWidget(api_desc)

        btn_row = QHBoxLayout()
        self.btn_fetch_bcv = QPushButton("🏛️ Consultar Tasa Oficial (BCV)")
        self.btn_fetch_bcv.setObjectName("btnSecondary")
        self.btn_fetch_bcv.clicked.connect(lambda: self.fetch_rate("oficial"))

        self.btn_fetch_paralelo = QPushButton("📈 Consultar Tasa Paralelo")
        self.btn_fetch_paralelo.setObjectName("btnSecondary")
        self.btn_fetch_paralelo.clicked.connect(lambda: self.fetch_rate("paralelo"))

        btn_row.addWidget(self.btn_fetch_bcv)
        btn_row.addWidget(self.btn_fetch_paralelo)
        api_layout.addLayout(btn_row)

        self.lbl_api_status = QLabel("")
        self.lbl_api_status.setStyleSheet("font-size: 11px; font-weight: normal; color: #2563EB;")
        self.lbl_api_status.setWordWrap(True)
        api_layout.addWidget(self.lbl_api_status)

        layout.addWidget(group_api)

        # Opción 2: Establecer Manualmente
        group_manual = QGroupBox("Establecer Tasa Manual (100% Offline)")
        group_manual.setStyleSheet("font-weight: 600; color: #1E293B;")
        manual_layout = QVBoxLayout(group_manual)

        manual_desc = QLabel("Ingresa directamente el valor en Bolívares por cada 1 USD:")
        manual_desc.setStyleSheet("font-size: 11px; color: #64748B; font-weight: normal;")
        manual_layout.addWidget(manual_desc)

        manual_row = QHBoxLayout()
        self.txt_manual_rate = QLineEdit()
        self.txt_manual_rate.setPlaceholderText("Ejemplo: 911.62")
        self.txt_manual_rate.setStyleSheet("font-size: 15px; font-weight: 600;")

        self.btn_save_manual = QPushButton("💾 Guardar Tasa Manual")
        self.btn_save_manual.setObjectName("btnSuccess")
        self.btn_save_manual.clicked.connect(self.save_manual_rate)

        manual_row.addWidget(self.txt_manual_rate, 2)
        manual_row.addWidget(self.btn_save_manual, 1)
        manual_layout.addLayout(manual_row)

        layout.addWidget(group_manual)

        # Botón Cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("btnSecondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def load_current_info(self):
        info = ExchangeRateService.get_rate_info()
        rate = info["rate"]
        source = info["source"]
        updated = info["updated_at"]
        self.lbl_current_rate.setText(f"Tasa Activa: {format_bs(rate)} / USD")
        self.lbl_source.setText(f"Fuente actual: {source} | Última actualización: {updated}")
        self.txt_manual_rate.setText(f"{rate:.2f}")

    def fetch_rate(self, source_type: str):
        self.btn_fetch_bcv.setEnabled(False)
        self.btn_fetch_paralelo.setEnabled(False)
        self.lbl_api_status.setText(f"Consultando DolarAPI ({source_type})...")

        self.thread = RateFetchThread(source_type)
        self.thread.finished_signal.connect(lambda ok, r, msg: self.on_rate_fetched(ok, r, msg, source_type))
        self.thread.start()

    def on_rate_fetched(self, success: bool, rate: float, message: str, source_type: str):
        self.btn_fetch_bcv.setEnabled(True)
        self.btn_fetch_paralelo.setEnabled(True)

        if success:
            reply = QMessageBox.question(
                self,
                "Tasa Obtenida de DolarAPI",
                f"Se obtuvo la tasa {source_type.upper()}: {format_bs(rate)} por USD.\n\n"
                f"¿Desea aplicarla como la tasa activa del sistema?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                ExchangeRateService.set_rate(rate, source=f"DOLARAPI_{source_type.upper()}")
                self.load_current_info()
                self.lbl_api_status.setText(f"✅ Tasa actualizada exitosamente a {format_bs(rate)}")
                self.rate_updated.emit(rate)
        else:
            self.lbl_api_status.setText(f"⚠️ {message}")
            QMessageBox.warning(self, "Aviso DolarAPI", message)

    def save_manual_rate(self):
        val = parse_float(self.txt_manual_rate.text(), 0.0)
        if val <= 0:
            QMessageBox.warning(self, "Error", "Debe ingresar una tasa mayor a 0.")
            return

        if ExchangeRateService.set_rate(val, source="MANUAL"):
            self.load_current_info()
            self.rate_updated.emit(val)
            QMessageBox.information(self, "Éxito", f"Tasa manual configurada en {format_bs(val)} / USD.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo actualizar la tasa manual.")
