from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame, QSplitter, QAbstractItemView, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from ..services.inventory_service import InventoryService
from ..services.exchange_rate import ExchangeRateService
from ..services.shift_service import ShiftService
from ..utils.helpers import format_usd, format_bs, format_qty
from ..utils.icon_helper import get_icon
from .dialogs.payment_dialog import PaymentDialog
from .dialogs.cash_advance_dialog import CashAdvanceDialog
from .dialogs.shift_open_dialog import ShiftOpenDialog


class PosView(QWidget):
    sale_processed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cart: List[Dict[str, Any]] = []
        self.rate = ExchangeRateService.get_active_rate()
        self.setup_ui()
        self.load_catalog()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Banner discreto de Turno Cerrado (solo visible si la caja está cerrada)
        self.shift_banner = QFrame()
        self.shift_banner.setObjectName("cardWarning")
        self.shift_banner.setFixedHeight(38)
        self.shift_banner.setStyleSheet("padding: 2px 10px; margin: 0px;")
        self.banner_layout = QHBoxLayout(self.shift_banner)
        self.banner_layout.setContentsMargins(10, 2, 10, 2)

        self.lbl_shift_status = QLabel("Caja Cerrada: Debe abrir un turno para facturar o realizar avances.")
        self.lbl_shift_status.setStyleSheet("font-weight: 700; color: #EC4624; font-size: 12px; background: transparent; border: none;")

        self.btn_open_shift_quick = QPushButton("Abrir Turno")
        self.btn_open_shift_quick.setObjectName("btnSuccess")
        self.btn_open_shift_quick.setIcon(get_icon("unlock", "#222A2A", size=14))
        self.btn_open_shift_quick.setStyleSheet("padding: 4px 12px; font-size: 11px;")
        self.btn_open_shift_quick.clicked.connect(self.open_shift_dialog)

        self.banner_layout.addWidget(self.lbl_shift_status)
        self.banner_layout.addStretch()
        self.banner_layout.addWidget(self.btn_open_shift_quick)
        main_layout.addWidget(self.shift_banner, 0)

        # Splitter principal: Catálogo (Izquierda) y Carrito (Derecha)
        splitter = QSplitter(Qt.Horizontal)

        # ==========================================
        # Panel Izquierdo: Catálogo y Búsqueda
        # ==========================================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(8)

        # Buscador con lector de barra / Enter
        search_card = QFrame()
        search_card.setObjectName("card")
        sc_layout = QHBoxLayout(search_card)
        sc_layout.setContentsMargins(8, 6, 8, 6)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(get_icon("search", "#4FBBBC").pixmap(18, 18))

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar producto o escanear código (Enter para agregar)...")
        self.txt_search.setStyleSheet("font-size: 13px; font-weight: 500;")
        self.txt_search.returnPressed.connect(self.on_search_enter)
        self.txt_search.textChanged.connect(self.filter_catalog)

        btn_clear_search = QPushButton()
        btn_clear_search.setObjectName("btnSecondary")
        btn_clear_search.setIcon(get_icon("close", "#222A2A", size=14))
        btn_clear_search.setFixedSize(28, 28)
        btn_clear_search.clicked.connect(self.txt_search.clear)

        sc_layout.addWidget(lbl_icon)
        sc_layout.addWidget(self.txt_search)
        sc_layout.addWidget(btn_clear_search)
        left_layout.addWidget(search_card)

        # Tabla del Catálogo
        self.tbl_catalog = QTableWidget()
        self.tbl_catalog.setColumnCount(5)
        self.tbl_catalog.setHorizontalHeaderLabels(["Código", "Producto", "Stock", "Precio USD", "Precio BS"])
        self.tbl_catalog.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_catalog.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_catalog.setColumnWidth(0, 95)
        self.tbl_catalog.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_catalog.setColumnWidth(2, 70)
        self.tbl_catalog.setColumnWidth(3, 75)
        self.tbl_catalog.setColumnWidth(4, 95)
        self.tbl_catalog.doubleClicked.connect(self.on_catalog_double_clicked)
        left_layout.addWidget(self.tbl_catalog)

        splitter.addWidget(left_widget)

        # ==========================================
        # Panel Derecho: Carrito de Compras & Totales
        # ==========================================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(8)

        # Encabezado del carrito
        cart_header = QHBoxLayout()
        lbl_cart_title = QLabel("Carrito de Compras / Ticket")
        lbl_cart_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #222A2A;")

        self.btn_clear_cart = QPushButton("Vaciar")
        self.btn_clear_cart.setObjectName("btnSecondary")
        self.btn_clear_cart.setIcon(get_icon("trash", "#222A2A", size=16))
        self.btn_clear_cart.clicked.connect(self.clear_cart)

        cart_header.addWidget(lbl_cart_title)
        cart_header.addStretch()
        cart_header.addWidget(self.btn_clear_cart)
        right_layout.addLayout(cart_header)

        # Tabla del Carrito
        self.tbl_cart = QTableWidget()
        self.tbl_cart.setColumnCount(6)
        self.tbl_cart.setHorizontalHeaderLabels(["Producto", "Cant.", "P. USD", "P. BS", "Total USD", "Total BS"])
        self.tbl_cart.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_cart.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_cart.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_cart.setColumnWidth(1, 75)
        self.tbl_cart.setColumnWidth(2, 80)
        self.tbl_cart.setColumnWidth(3, 105)
        self.tbl_cart.setColumnWidth(4, 85)
        self.tbl_cart.setColumnWidth(5, 110)
        self.tbl_cart.doubleClicked.connect(self.set_custom_cart_qty)
        right_layout.addWidget(self.tbl_cart)

        # Botones de modificación de cantidad rápida
        qty_box = QHBoxLayout()
        btn_qty_minus = QPushButton("Disminuir")
        btn_qty_minus.setObjectName("btnSecondary")
        btn_qty_minus.clicked.connect(lambda: self.modify_cart_qty(-1))

        btn_qty_plus = QPushButton("Aumentar")
        btn_qty_plus.setObjectName("btnSecondary")
        btn_qty_plus.clicked.connect(lambda: self.modify_cart_qty(1))

        btn_set_exact = QPushButton("Editar Cantidad")
        btn_set_exact.setObjectName("btnSecondary")
        btn_set_exact.setIcon(get_icon("edit", "#222A2A", size=15))
        btn_set_exact.clicked.connect(self.set_custom_cart_qty)

        btn_remove_item = QPushButton("Quitar")
        btn_remove_item.setObjectName("btnDanger")
        btn_remove_item.setIcon(get_icon("trash", "#FFFFFF", size=15))
        btn_remove_item.clicked.connect(self.remove_cart_item)

        qty_box.addWidget(btn_qty_minus)
        qty_box.addWidget(btn_qty_plus)
        qty_box.addWidget(btn_set_exact)
        qty_box.addWidget(btn_remove_item)
        right_layout.addLayout(qty_box)

        # Tarjeta de Totales Grandes
        total_card = QFrame()
        total_card.setObjectName("cardHighlight")
        tc_layout = QHBoxLayout(total_card)
        tc_layout.setContentsMargins(16, 10, 16, 10)

        box_usd = QVBoxLayout()
        lbl_tu = QLabel("TOTAL USD:")
        lbl_tu.setStyleSheet("font-size: 11px; font-weight: 700; color: #222A2A; opacity: 0.8;")
        self.lbl_total_usd = QLabel("$ 0.00")
        self.lbl_total_usd.setStyleSheet("font-size: 26px; font-weight: 900; color: #222A2A;")
        box_usd.addWidget(lbl_tu)
        box_usd.addWidget(self.lbl_total_usd)

        box_bs = QVBoxLayout()
        lbl_tb = QLabel("TOTAL BOLIVARES:")
        lbl_tb.setStyleSheet("font-size: 11px; font-weight: 700; color: #222A2A; opacity: 0.8;")
        self.lbl_total_bs = QLabel("Bs. 0,00")
        self.lbl_total_bs.setStyleSheet("font-size: 26px; font-weight: 900; color: #4FBBBC;")
        box_bs.addWidget(lbl_tb)
        box_bs.addWidget(self.lbl_total_bs)

        tc_layout.addLayout(box_usd)
        tc_layout.addLayout(box_bs)
        right_layout.addWidget(total_card)

        # Botones Principales de Operación
        actions_layout = QHBoxLayout()

        self.btn_advance = QPushButton("Avance de Efectivo")
        self.btn_advance.setObjectName("btnWarning")
        self.btn_advance.setIcon(get_icon("advance", "#FFFFFF", size=18))
        self.btn_advance.setStyleSheet("font-size: 13px; font-weight: 700; padding: 12px 16px;")
        self.btn_advance.clicked.connect(self.open_cash_advance_dialog)

        self.btn_checkout = QPushButton("Cobrar / Facturar (F12)")
        self.btn_checkout.setObjectName("btnSuccess")
        self.btn_checkout.setIcon(get_icon("card", "#222A2A", size=18))
        self.btn_checkout.setStyleSheet("font-size: 14px; font-weight: 800; padding: 12px 24px;")
        self.btn_checkout.clicked.connect(self.open_checkout_dialog)

        actions_layout.addWidget(self.btn_advance, 1)
        actions_layout.addWidget(self.btn_checkout, 2)
        right_layout.addLayout(actions_layout)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([580, 420])
        main_layout.addWidget(splitter, 1)

        self.refresh_shift_banner()

    def refresh_rate(self, new_rate: float):
        self.rate = new_rate
        self.load_catalog()
        self.update_cart_table()

    def refresh_shift_banner(self):
        shift = ShiftService.get_active_shift()
        if shift:
            # Turno abierto: ocultar banner para no consumir espacio
            self.shift_banner.setVisible(False)
            self.btn_checkout.setEnabled(True)
            self.btn_advance.setEnabled(True)
        else:
            # Turno cerrado: mostrar pequeño aviso
            self.shift_banner.setVisible(True)
            self.lbl_shift_status.setText("Caja Cerrada: Abra turno para comenzar a facturar o realizar avances.")
            self.btn_checkout.setEnabled(False)
            self.btn_advance.setEnabled(False)

    def load_catalog(self):
        search_text = self.txt_search.text().strip()
        products = InventoryService.list_products(search_text, active_only=True)
        self.tbl_catalog.setRowCount(len(products))

        for row, p in enumerate(products):
            price_usd = float(p["price_usd"])
            price_bs = price_usd * self.rate
            stock = float(p["stock"])
            unit = p.get("unit", "UND") or "UND"

            item_code = QTableWidgetItem(str(p["code"]))
            item_name = QTableWidgetItem(str(p["name"]))
            item_stock = QTableWidgetItem(format_qty(stock, unit))
            item_p_usd = QTableWidgetItem(format_usd(price_usd))
            item_p_bs = QTableWidgetItem(format_bs(price_bs))

            item_code.setData(Qt.UserRole, p)

            item_stock.setTextAlignment(Qt.AlignCenter)
            item_p_usd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_p_bs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if stock <= float(p.get("min_stock", 5.0)):
                item_stock.setForeground(Qt.red)

            self.tbl_catalog.setItem(row, 0, item_code)
            self.tbl_catalog.setItem(row, 1, item_name)
            self.tbl_catalog.setItem(row, 2, item_stock)
            self.tbl_catalog.setItem(row, 3, item_p_usd)
            self.tbl_catalog.setItem(row, 4, item_p_bs)

    def filter_catalog(self):
        self.load_catalog()

    def on_search_enter(self):
        query = self.txt_search.text().strip()
        if not query:
            return

        exact = InventoryService.get_by_code(query)
        if exact:
            self.add_product_to_cart(exact)
            self.txt_search.clear()
            return

        if self.tbl_catalog.rowCount() > 0:
            item_0 = self.tbl_catalog.item(0, 0)
            if item_0:
                prod = item_0.data(Qt.UserRole)
                if prod:
                    self.add_product_to_cart(prod)
                    self.txt_search.clear()

    def on_catalog_double_clicked(self, index):
        row = index.row()
        item = self.tbl_catalog.item(row, 0)
        if item:
            prod = item.data(Qt.UserRole)
            if prod:
                self.add_product_to_cart(prod)

    def add_product_to_cart(self, prod: Dict[str, Any]):
        prod_id = prod["id"]
        stock = float(prod.get("stock", 0.0))
        unit = prod.get("unit", "UND") or "UND"

        step = 1.0

        for item in self.cart:
            if item["product_id"] == prod_id:
                if item["qty"] + step > stock:
                    QMessageBox.warning(self, "Stock Insuficiente",
                                        f"No hay mas existencias para '{prod['name']}'. Disponible: {format_qty(stock, unit)}")
                    return
                item["qty"] += step
                self.update_cart_table()
                return

        if stock <= 0:
            QMessageBox.warning(self, "Producto Agotado", f"El producto '{prod['name']}' no tiene existencias disponibles.")
            return

        self.cart.append({
            "product_id": prod_id,
            "code": prod["code"],
            "name": prod["name"],
            "unit": unit,
            "qty": step,
            "price_usd": float(prod["price_usd"])
        })
        self.update_cart_table()

    def modify_cart_qty(self, delta: float):
        selected_rows = self.tbl_cart.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.cart):
            return

        item = self.cart[row]
        prod = InventoryService.get_by_id(item["product_id"])
        stock = float(prod.get("stock", 0.0)) if prod else 999999.0
        unit = item.get("unit", "UND")

        step = 0.5 if unit == "KG" else 1.0
        new_qty = round(item["qty"] + (delta * step), 3)

        if new_qty <= 0:
            self.cart.pop(row)
        elif new_qty > stock:
            QMessageBox.warning(self, "Stock Insuficiente", f"Stock disponible: {format_qty(stock, unit)}")
            return
        else:
            item["qty"] = new_qty

        self.update_cart_table()
        if row < len(self.cart):
            self.tbl_cart.selectRow(row)

    def set_custom_cart_qty(self):
        selected_rows = self.tbl_cart.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        if row < 0 or row >= len(self.cart):
            return

        item = self.cart[row]
        prod = InventoryService.get_by_id(item["product_id"])
        stock = float(prod.get("stock", 0.0)) if prod else 999999.0
        unit = item.get("unit", "UND")

        decimals = 3 if unit == "KG" else 0
        val, ok = QInputDialog.getDouble(
            self,
            "Editar Cantidad",
            f"Ingrese cantidad para '{item['name']}' ({unit}):",
            item["qty"], 0.001 if unit == "KG" else 1.0, stock, decimals
        )

        if ok and val > 0:
            item["qty"] = val
            self.update_cart_table()
            self.tbl_cart.selectRow(row)

    def remove_cart_item(self):
        selected_rows = self.tbl_cart.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self.update_cart_table()

    def clear_cart(self):
        if not self.cart:
            return
        reply = QMessageBox.question(self, "Vaciar Carrito", "Desea eliminar todos los productos del carrito actual?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.cart.clear()
            self.update_cart_table()

    def update_cart_table(self):
        self.tbl_cart.setRowCount(len(self.cart))
        total_usd = 0.0

        for row, item in enumerate(self.cart):
            qty = item["qty"]
            unit = item.get("unit", "UND")
            p_usd = item["price_usd"]
            p_bs = p_usd * self.rate
            sub_usd = qty * p_usd
            sub_bs = sub_usd * self.rate
            total_usd += sub_usd

            it_name = QTableWidgetItem(str(item["name"]))
            it_qty = QTableWidgetItem(format_qty(qty, unit))
            it_pusd = QTableWidgetItem(format_usd(p_usd))
            it_pbs = QTableWidgetItem(format_bs(p_bs))
            it_subusd = QTableWidgetItem(format_usd(sub_usd))
            it_subbs = QTableWidgetItem(format_bs(sub_bs))

            it_qty.setTextAlignment(Qt.AlignCenter)
            it_pusd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_pbs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_subusd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_subbs.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.tbl_cart.setItem(row, 0, it_name)
            self.tbl_cart.setItem(row, 1, it_qty)
            self.tbl_cart.setItem(row, 2, it_pusd)
            self.tbl_cart.setItem(row, 3, it_pbs)
            self.tbl_cart.setItem(row, 4, it_subusd)
            self.tbl_cart.setItem(row, 5, it_subbs)

        total_usd = round(total_usd, 2)
        total_bs = round(total_usd * self.rate, 2)

        self.lbl_total_usd.setText(format_usd(total_usd))
        self.lbl_total_bs.setText(format_bs(total_bs))

    def open_checkout_dialog(self):
        if not self.cart:
            QMessageBox.information(self, "Carrito Vacio", "Agregue al menos un producto al carrito para facturar.")
            return

        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            QMessageBox.warning(self, "Turno Requerido", "Debe abrir un turno de caja antes de facturar.")
            self.open_shift_dialog()
            return

        total_usd = sum(item["qty"] * item["price_usd"] for item in self.cart)

        dlg = PaymentDialog(items=self.cart, total_usd=total_usd, parent=self)
        dlg.sale_completed.connect(self.on_sale_completed)
        dlg.exec()

    def on_sale_completed(self, sale_data: dict):
        self.cart.clear()
        self.update_cart_table()
        self.load_catalog()
        self.sale_processed.emit()

    def open_cash_advance_dialog(self):
        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            QMessageBox.warning(self, "Turno Requerido", "Debe abrir un turno de caja antes de realizar un avance.")
            self.open_shift_dialog()
            return

        dlg = CashAdvanceDialog(parent=self)
        dlg.advance_completed.connect(lambda d: self.sale_processed.emit())
        dlg.exec()

    def open_shift_dialog(self):
        dlg = ShiftOpenDialog(parent=self)
        dlg.shift_opened.connect(lambda s_id: self.refresh_shift_banner())
        dlg.exec()
