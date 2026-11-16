from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QDoubleSpinBox, QComboBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from ...services.inventory_service import InventoryService
from ...services.exchange_rate import ExchangeRateService
from ...utils.helpers import format_bs, parse_float
from ...utils.icon_helper import get_icon


class ProductDialog(QDialog):
    def __init__(self, product: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.product = product
        self.rate = ExchangeRateService.get_active_rate()
        is_edit = product is not None

        self.setWindowTitle("Editar Producto" if is_edit else "Nuevo Producto")
        self.setMinimumWidth(460)
        self.setup_ui()

        if is_edit:
            self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QFormLayout(form_card)
        form_layout.setSpacing(10)

        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText("Ej: 7591001001 o código de barras")

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ej: Harina Pan 1kg o Papas Lavadas")

        self.txt_category = QLineEdit()
        self.txt_category.setPlaceholderText("Ej: Víveres, Vegetales, Charcutería, Bebidas")

        self.cmb_unit = QComboBox()
        self.cmb_unit.addItem("Unidad (UND)", "UND")
        self.cmb_unit.addItem("Kilogramo (KG - Granel)", "KG")
        self.cmb_unit.currentIndexChanged.connect(self.on_unit_changed)

        self.spn_cost_usd = QDoubleSpinBox()
        self.spn_cost_usd.setPrefix("$ ")
        self.spn_cost_usd.setRange(0.0, 999999.0)
        self.spn_cost_usd.setDecimals(2)
        self.spn_cost_usd.setValue(0.0)

        self.spn_price_usd = QDoubleSpinBox()
        self.spn_price_usd.setPrefix("$ ")
        self.spn_price_usd.setRange(0.01, 999999.0)
        self.spn_price_usd.setDecimals(2)
        self.spn_price_usd.setValue(1.0)
        self.spn_price_usd.valueChanged.connect(self.update_price_bs_preview)

        # Etiqueta de precio aproximado en Bolívares
        self.lbl_price_bs_calc = QLabel()
        self.lbl_price_bs_calc.setStyleSheet("font-weight: 700; color: #4FBBBC;")
        self.update_price_bs_preview()

        self.spn_stock = QDoubleSpinBox()
        self.spn_stock.setRange(0.0, 999999.0)
        self.spn_stock.setDecimals(0)
        self.spn_stock.setSingleStep(1.0)
        self.spn_stock.setSuffix(" UND")
        self.spn_stock.setValue(10.0)

        self.spn_min_stock = QDoubleSpinBox()
        self.spn_min_stock.setRange(0.0, 999999.0)
        self.spn_min_stock.setDecimals(0)
        self.spn_min_stock.setSingleStep(1.0)
        self.spn_min_stock.setSuffix(" UND")
        self.spn_min_stock.setValue(5.0)

        form_layout.addRow("Código / SKU *:", self.txt_code)
        form_layout.addRow("Nombre del Producto *:", self.txt_name)
        form_layout.addRow("Categoría:", self.txt_category)
        form_layout.addRow("Unidad de Medida *:", self.cmb_unit)
        form_layout.addRow("Costo (USD):", self.spn_cost_usd)
        form_layout.addRow("Precio de Venta (USD) *:", self.spn_price_usd)
        form_layout.addRow("Equiv. en Bolívares:", self.lbl_price_bs_calc)
        form_layout.addRow("Existencia Actual:", self.spn_stock)
        form_layout.addRow("Stock Mínimo:", self.spn_min_stock)

        layout.addWidget(form_card)

        # Botones
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Guardar Producto")
        self.btn_save.setObjectName("btnSuccess")
        self.btn_save.setIcon(get_icon("check", "#222A2A"))
        self.btn_save.clicked.connect(self.save)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def on_unit_changed(self):
        unit = self.cmb_unit.currentData()
        if unit == "KG":
            self.spn_stock.setDecimals(3)
            self.spn_stock.setSingleStep(0.5)
            self.spn_stock.setSuffix(" KG")

            self.spn_min_stock.setDecimals(3)
            self.spn_min_stock.setSingleStep(0.5)
            self.spn_min_stock.setSuffix(" KG")
        else:
            self.spn_stock.setDecimals(0)
            self.spn_stock.setSingleStep(1.0)
            self.spn_stock.setSuffix(" UND")

            self.spn_min_stock.setDecimals(0)
            self.spn_min_stock.setSingleStep(1.0)
            self.spn_min_stock.setSuffix(" UND")

    def update_price_bs_preview(self):
        val = self.spn_price_usd.value()
        bs_val = val * self.rate
        self.lbl_price_bs_calc.setText(f"{format_bs(bs_val)} (a tasa Bs. {self.rate:,.2f})")

    def load_data(self):
        if not self.product:
            return
        self.txt_code.setText(str(self.product.get("code", "")))
        self.txt_name.setText(str(self.product.get("name", "")))
        self.txt_category.setText(str(self.product.get("category", "")))

        unit = str(self.product.get("unit", "UND")).upper()
        idx = self.cmb_unit.findData(unit)
        if idx >= 0:
            self.cmb_unit.setCurrentIndex(idx)
        self.on_unit_changed()

        self.spn_cost_usd.setValue(float(self.product.get("cost_usd", 0.0) or 0.0))
        self.spn_price_usd.setValue(float(self.product.get("price_usd", 1.0) or 1.0))
        self.spn_stock.setValue(float(self.product.get("stock", 0.0) or 0.0))
        self.spn_min_stock.setValue(float(self.product.get("min_stock", 5.0) or 5.0))
        self.update_price_bs_preview()

    def save(self):
        code = self.txt_code.text().strip()
        name = self.txt_name.text().strip()
        cat = self.txt_category.text().strip()
        unit = self.cmb_unit.currentData()
        cost = self.spn_cost_usd.value()
        price = self.spn_price_usd.value()
        stock = self.spn_stock.value()
        min_stock = self.spn_min_stock.value()

        prod_id = self.product["id"] if self.product else None
        ok, msg = InventoryService.save_product(prod_id, code, name, cat, cost, price, stock, min_stock, unit)

        if ok:
            QMessageBox.information(self, "Exito", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Atencion", msg)
