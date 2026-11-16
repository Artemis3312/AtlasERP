import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDateEdit, QMessageBox, QFrame, QGridLayout, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QDesktopServices
from ..services.report_service import ReportService, REPORTS_DIR
from ..utils.icon_helper import get_icon


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_recent_reports()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Encabezado
        lbl_head = QLabel("Modulo de Reportes Oficiales en PDF")
        lbl_head.setStyleSheet("font-size: 20px; font-weight: 900; color: #222A2A;")
        layout.addWidget(lbl_head)

        grid = QGridLayout()
        grid.setSpacing(16)

        # ==========================================
        # Tarjeta 1: Reporte de Histórico de Operaciones
        # ==========================================
        card_ops = QFrame()
        card_ops.setObjectName("card")
        l_ops = QVBoxLayout(card_ops)
        l_ops.setSpacing(12)

        lbl_ops_title = QLabel("Historico de Operaciones y Ventas")
        lbl_ops_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #222A2A;")
        lbl_ops_desc = QLabel("Genera un documento PDF detallado con todas las ventas, recaudacion por metodo de pago (USD, BS Efectivo, Tarjeta, Pago Movil), avances de efectivo y movimientos de caja.")
        lbl_ops_desc.setWordWrap(True)
        lbl_ops_desc.setStyleSheet("font-size: 11px; color: #64748B;")

        l_ops.addWidget(lbl_ops_title)
        l_ops.addWidget(lbl_ops_desc)

        # Rango de Fechas
        date_box = QHBoxLayout()
        date_box.addWidget(QLabel("Desde:"))
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate.currentDate().addDays(-7))
        date_box.addWidget(self.dt_start)

        date_box.addWidget(QLabel("Hasta:"))
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())
        date_box.addWidget(self.dt_end)
        l_ops.addLayout(date_box)

        # Botones rápidos de rango
        quick_dates = QHBoxLayout()
        btn_today = QPushButton("Hoy")
        btn_today.setObjectName("btnSecondary")
        btn_today.clicked.connect(self.set_range_today)

        btn_week = QPushButton("Ultimos 7 Dias")
        btn_week.setObjectName("btnSecondary")
        btn_week.clicked.connect(self.set_range_week)

        btn_month = QPushButton("Este Mes")
        btn_month.setObjectName("btnSecondary")
        btn_month.clicked.connect(self.set_range_month)

        quick_dates.addWidget(btn_today)
        quick_dates.addWidget(btn_week)
        quick_dates.addWidget(btn_month)
        l_ops.addLayout(quick_dates)

        self.btn_gen_ops = QPushButton("Generar Reporte de Operaciones (PDF)")
        self.btn_gen_ops.setObjectName("btnSuccess")
        self.btn_gen_ops.setIcon(get_icon("reports", "#222A2A", size=18))
        self.btn_gen_ops.setStyleSheet("font-size: 13px; font-weight: 700; padding: 10px;")
        self.btn_gen_ops.clicked.connect(self.generate_operations_pdf)
        l_ops.addWidget(self.btn_gen_ops)

        grid.addWidget(card_ops, 0, 0)

        # ==========================================
        # Tarjeta 2: Reporte de Inventario Actual
        # ==========================================
        card_inv = QFrame()
        card_inv.setObjectName("card")
        l_inv = QVBoxLayout(card_inv)
        l_inv.setSpacing(12)

        lbl_inv_title = QLabel("Reporte de Inventario y Existencias")
        lbl_inv_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #222A2A;")
        lbl_inv_desc = QLabel("Genera un documento PDF con el listado completo de productos, stock disponible, valorizacion global al costo y a precio de venta tanto en USD como en Bolivares (usando la tasa activa), e identifica productos en alerta de stock minimo.")
        lbl_inv_desc.setWordWrap(True)
        lbl_inv_desc.setStyleSheet("font-size: 11px; color: #64748B;")

        l_inv.addWidget(lbl_inv_title)
        l_inv.addWidget(lbl_inv_desc)
        l_inv.addStretch()

        self.btn_gen_inv = QPushButton("Generar Reporte de Inventario (PDF)")
        self.btn_gen_inv.setObjectName("btnWarning")
        self.btn_gen_inv.setIcon(get_icon("inventory", "#FFFFFF", size=18))
        self.btn_gen_inv.setStyleSheet("font-size: 13px; font-weight: 700; padding: 10px;")
        self.btn_gen_inv.clicked.connect(self.generate_inventory_pdf)
        l_inv.addWidget(self.btn_gen_inv)

        grid.addWidget(card_inv, 0, 1)

        layout.addLayout(grid)

        # ==========================================
        # Sección Inferior: Reportes Generados Recientemente
        # ==========================================
        recent_card = QFrame()
        recent_card.setObjectName("card")
        l_recent = QVBoxLayout(recent_card)
        l_recent.setSpacing(10)

        top_recent = QHBoxLayout()
        lbl_rec_title = QLabel("Archivos PDF Generados")
        lbl_rec_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #222A2A;")

        btn_open_folder = QPushButton("Abrir Carpeta de Reportes")
        btn_open_folder.setObjectName("btnSecondary")
        btn_open_folder.setIcon(get_icon("folder", "#222A2A", size=16))
        btn_open_folder.clicked.connect(self.open_reports_folder)

        btn_refresh_list = QPushButton()
        btn_refresh_list.setObjectName("btnSecondary")
        btn_refresh_list.setIcon(get_icon("refresh", "#222A2A", size=15))
        btn_refresh_list.setFixedSize(32, 32)
        btn_refresh_list.clicked.connect(self.refresh_recent_reports)

        top_recent.addWidget(lbl_rec_title)
        top_recent.addStretch()
        top_recent.addWidget(btn_open_folder)
        top_recent.addWidget(btn_refresh_list)
        l_recent.addLayout(top_recent)

        self.list_reports = QListWidget()
        self.list_reports.setStyleSheet("background-color: #FAF8F5; border: 1px solid #E2DAC2; border-radius: 6px;")
        self.list_reports.itemDoubleClicked.connect(self.open_selected_report)
        l_recent.addWidget(self.list_reports)

        btn_open_selected = QPushButton("Abrir PDF Seleccionado")
        btn_open_selected.setObjectName("btnSecondary")
        btn_open_selected.clicked.connect(self.open_selected_report)
        l_recent.addWidget(btn_open_selected, alignment=Qt.AlignRight)

        layout.addWidget(recent_card)

    def set_range_today(self):
        today = QDate.currentDate()
        self.dt_start.setDate(today)
        self.dt_end.setDate(today)

    def set_range_week(self):
        today = QDate.currentDate()
        self.dt_start.setDate(today.addDays(-7))
        self.dt_end.setDate(today)

    def set_range_month(self):
        today = QDate.currentDate()
        self.dt_start.setDate(QDate(today.year(), today.month(), 1))
        self.dt_end.setDate(today)

    def generate_operations_pdf(self):
        d_start = self.dt_start.date().toString("yyyy-MM-dd")
        d_end = self.dt_end.date().toString("yyyy-MM-dd")

        try:
            pdf_path = ReportService.generate_operations_report(d_start, d_end)
            self.refresh_recent_reports()

            reply = QMessageBox.question(
                self,
                "Reporte Generado",
                f"Reporte de Operaciones generado exitosamente.\n\n"
                f"Ubicacion:\n{pdf_path}\n\n"
                f"Desea abrir el archivo PDF ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_file(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar Reporte", f"Ocurrio un error al crear el PDF:\n{str(e)}")

    def generate_inventory_pdf(self):
        try:
            pdf_path = ReportService.generate_inventory_report()
            self.refresh_recent_reports()

            reply = QMessageBox.question(
                self,
                "Reporte de Inventario Generado",
                f"Reporte de Inventario generado exitosamente.\n\n"
                f"Ubicacion:\n{pdf_path}\n\n"
                f"Desea abrir el archivo PDF ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.open_file(pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "Error al Generar Reporte", f"Ocurrio un error al crear el PDF:\n{str(e)}")

    def refresh_recent_reports(self):
        self.list_reports.clear()
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        pdf_files = sorted(REPORTS_DIR.glob("*.pdf"), key=os.path.getmtime, reverse=True)

        for f in pdf_files[:20]:
            item = QListWidgetItem(f.name)
            item.setIcon(get_icon("reports", "#4FBBBC", size=16))
            item.setData(Qt.UserRole, str(f))
            self.list_reports.addItem(item)

    def open_selected_report(self):
        current_item = self.list_reports.currentItem()
        if not current_item:
            return
        path = current_item.data(Qt.UserRole)
        if path:
            self.open_file(path)

    def open_reports_folder(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(REPORTS_DIR)))

    def open_file(self, filepath: str):
        if os.path.exists(filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(filepath))
        else:
            QMessageBox.warning(self, "Archivo No Encontrado", f"No se encontro el archivo:\n{filepath}")
