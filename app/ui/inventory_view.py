from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QAbstractItemView, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from ..services.inventory_service import InventoryService
from ..services.exchange_rate import ExchangeRateService
from ..utils.helpers import format_usd, format_bs, format_qty
from .dialogs.product_dialog import ProductDialog


class InventoryView(QWidget):
    product_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rate = ExchangeRateService.get_active_rate()
        self.setup_ui()
        self.load_inventory()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # KPIs superiores
        kpi_card = QFrame()
        kpi_card.setObjectName("card")
        kpi_layout = QGridLayout(kpi_card)
        kpi_layout.setSpacing(12)

        # KPI 1: Total Productos
        b1 = QVBoxLayout()
        l1 = QLabel("TOTAL PRODUCTOS")
        l1.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_kpi_total = QLabel("0")
        self.lbl_kpi_total.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        b1.addWidget(l1)
        b1.addWidget(self.lbl_kpi_total)
        kpi_layout.addLayout(b1, 0, 0)

        # KPI 2: Total Unidades
        b2 = QVBoxLayout()
        l2 = QLabel("UNIDADES EN STOCK")
        l2.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_kpi_units = QLabel("0")
        self.lbl_kpi_units.setStyleSheet("font-size: 20px; font-weight: 800; color: #2563EB;")
        b2.addWidget(l2)
        b2.addWidget(self.lbl_kpi_units)
        kpi_layout.addLayout(b2, 0, 1)

        # KPI 3: Valor al Costo USD
        b3 = QVBoxLayout()
        l3 = QLabel("VALOR AL COSTO")
        l3.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_kpi_cost = QLabel("$ 0.00")
        self.lbl_kpi_cost.setStyleSheet("font-size: 20px; font-weight: 800; color: #475569;")
        b3.addWidget(l3)
        b3.addWidget(self.lbl_kpi_cost)
        kpi_layout.addLayout(b3, 0, 2)

        # KPI 4: Valor de Venta USD
        b4 = QVBoxLayout()
        l4 = QLabel("VALOR DE VENTA (USD)")
        l4.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_kpi_retail = QLabel("$ 0.00")
        self.lbl_kpi_retail.setStyleSheet("font-size: 20px; font-weight: 800; color: #059669;")
        b4.addWidget(l4)
        b4.addWidget(self.lbl_kpi_retail)
        kpi_layout.addLayout(b4, 0, 3)

        # KPI 5: Stock Bajo
        b5 = QVBoxLayout()
        l5 = QLabel("ALERTAS STOCK BAJO")
        l5.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        self.lbl_kpi_low = QLabel("0")
        self.lbl_kpi_low.setStyleSheet("font-size: 20px; font-weight: 800; color: #E11D48;")
        b5.addWidget(l5)
        b5.addWidget(self.lbl_kpi_low)
        kpi_layout.addLayout(b5, 0, 4)

        layout.addWidget(kpi_card)

        # Barra de Acciones y Búsqueda
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.txt_filter = QLineEdit()
        self.txt_filter.setPlaceholderText("🔍 Filtrar productos por nombre, código o categoría...")
        self.txt_filter.textChanged.connect(self.load_inventory)

        btn_new = QPushButton("➕ Nuevo Producto")
        btn_new.setObjectName("btnSuccess")
        btn_new.clicked.connect(self.open_new_product_dialog)

        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setObjectName("btnSecondary")
        btn_edit.clicked.connect(self.open_edit_product_dialog)

        btn_delete = QPushButton("🗑️ Eliminar")
        btn_delete.setObjectName("btnDanger")
        btn_delete.clicked.connect(self.delete_product)

        btn_refresh = QPushButton("🔄 Refrescar")
        btn_refresh.setObjectName("btnSecondary")
        btn_refresh.clicked.connect(self.load_inventory)

        action_bar.addWidget(self.txt_filter, 2)
        action_bar.addWidget(btn_new)
        action_bar.addWidget(btn_edit)
        action_bar.addWidget(btn_delete)
        action_bar.addWidget(btn_refresh)
        layout.addLayout(action_bar)

        # Tabla de Productos
        self.tbl_products = QTableWidget()
        self.tbl_products.setColumnCount(9)
        self.tbl_products.setHorizontalHeaderLabels([
            "ID", "Código / SKU", "Nombre del Producto", "Categoría",
            "Costo USD", "Precio USD", "Precio Bolívares", "Stock", "Estado"
        ])
        self.tbl_products.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_products.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_products.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_products.doubleClicked.connect(self.open_edit_product_dialog)
        layout.addWidget(self.tbl_products)

    def refresh_rate(self, new_rate: float):
        self.rate = new_rate
        self.load_inventory()

    def load_inventory(self):
        search_term = self.txt_filter.text().strip()
        products = InventoryService.list_products(search_term, active_only=True)
        summary = InventoryService.get_inventory_summary()

        # Actualizar KPIs
        self.lbl_kpi_total.setText(str(summary["total_items"]))
        self.lbl_kpi_units.setText(format_qty(summary["total_units"]))
        self.lbl_kpi_cost.setText(format_usd(summary["total_cost_usd"]))
        self.lbl_kpi_retail.setText(format_usd(summary["total_retail_usd"]))
        self.lbl_kpi_low.setText(str(summary["low_stock_count"]))

        # Llenar Tabla
        self.tbl_products.setRowCount(len(products))

        for row, p in enumerate(products):
            price_usd = float(p["price_usd"])
            price_bs = price_usd * self.rate
            cost_usd = float(p.get("cost_usd", 0.0) or 0.0)
            stock = float(p.get("stock", 0.0) or 0.0)
            min_stock = float(p.get("min_stock", 5.0) or 5.0)

            it_id = QTableWidgetItem(str(p["id"]))
            it_id.setData(Qt.UserRole, p)
            it_code = QTableWidgetItem(str(p["code"]))
            it_name = QTableWidgetItem(str(p["name"]))
            it_cat = QTableWidgetItem(str(p["category"]))
            it_cost = QTableWidgetItem(format_usd(cost_usd))
            it_price_usd = QTableWidgetItem(format_usd(price_usd))
            it_price_bs = QTableWidgetItem(format_bs(price_bs))
            it_stock = QTableWidgetItem(f"{format_qty(stock)} / {format_qty(min_stock)}")

            # Badge de Estado
            if stock <= 0:
                it_status = QTableWidgetItem("Agotado")
                it_status.setForeground(Qt.red)
            elif stock <= min_stock:
                it_status = QTableWidgetItem("Stock Bajo")
                it_status.setForeground(Qt.darkYellow)
            else:
                it_status = QTableWidgetItem("En Stock")
                it_status.setForeground(Qt.darkGreen)

            it_id.setTextAlignment(Qt.AlignCenter)
            it_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_price_usd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_price_bs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_stock.setTextAlignment(Qt.AlignCenter)
            it_status.setTextAlignment(Qt.AlignCenter)

            self.tbl_products.setItem(row, 0, it_id)
            self.tbl_products.setItem(row, 1, it_code)
            self.tbl_products.setItem(row, 2, it_name)
            self.tbl_products.setItem(row, 3, it_cat)
            self.tbl_products.setItem(row, 4, it_cost)
            self.tbl_products.setItem(row, 5, it_price_usd)
            self.tbl_products.setItem(row, 6, it_price_bs)
            self.tbl_products.setItem(row, 7, it_stock)
            self.tbl_products.setItem(row, 8, it_status)

    def open_new_product_dialog(self):
        dlg = ProductDialog(parent=self)
        if dlg.exec():
            self.load_inventory()
            self.product_changed.emit()

    def open_edit_product_dialog(self):
        selected_rows = self.tbl_products.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Seleccionar", "Seleccione un producto de la lista para editar.")
            return

        row = selected_rows[0].row()
        item = self.tbl_products.item(row, 0)
        if not item:
            return
        prod = item.data(Qt.UserRole)

        dlg = ProductDialog(product=prod, parent=self)
        if dlg.exec():
            self.load_inventory()
            self.product_changed.emit()

    def delete_product(self):
        selected_rows = self.tbl_products.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Seleccionar", "Seleccione un producto de la lista para eliminar.")
            return

        row = selected_rows[0].row()
        item = self.tbl_products.item(row, 0)
        if not item:
            return
        prod = item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar el producto '{prod['name']}' ({prod['code']})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok, msg = InventoryService.delete_product(prod["id"])
            if ok:
                QMessageBox.information(self, "Resultado", msg)
                self.load_inventory()
                self.product_changed.emit()
            else:
                QMessageBox.warning(self, "Error", msg)
