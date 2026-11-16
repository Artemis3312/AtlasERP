import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication
from app.database.db import init_db
from app.services.shift_service import ShiftService
from app.services.inventory_service import InventoryService
from app.ui.main_window import MainWindow

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

init_db()

# Asegurar turno abierto para ver cómo luce en operación
if not ShiftService.get_active_shift():
    ShiftService.open_shift(50.0, 5000.0, "Cajero Principal")

win = MainWindow()
win.resize(1240, 780)
win.show()

out_dir = Path("data/screenshots")
out_dir.mkdir(parents=True, exist_ok=True)

# POS con items
win.switch_to_view_by_index(1)
prods = InventoryService.list_products(active_only=True)
if prods:
    win.pos_view.add_product_to_cart(prods[0])
    if len(prods) > 1:
        win.pos_view.add_product_to_cart(prods[1])
app.processEvents()
win.grab().save(str(out_dir / "02_pos_view_open_shift.png"))

print("Captured open shift POS screenshot!")
app.quit()
