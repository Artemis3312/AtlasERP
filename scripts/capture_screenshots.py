import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from app.database.db import init_db
from app.ui.main_window import MainWindow
from app.ui.dialogs.payment_dialog import PaymentDialog

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

init_db()

win = MainWindow()
win.resize(1240, 780)
win.show()

out_dir = Path("data/screenshots")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Home View
win.switch_to_view_by_index(0)
app.processEvents()
win.grab().save(str(out_dir / "01_home_view.png"))

# 2. POS View
win.switch_to_view_by_index(1)
app.processEvents()
win.grab().save(str(out_dir / "02_pos_view.png"))

# 3. Inventory View
win.switch_to_view_by_index(2)
app.processEvents()
win.grab().save(str(out_dir / "03_inventory_view.png"))

# 4. Payment Dialog
test_items = [{"product_id": 1, "code": "7591001001", "name": "Harina Pan 1kg", "qty": 1.0, "price_usd": 1.25}]
dlg = PaymentDialog(items=test_items, total_usd=1.25, parent=win)
dlg.show()
dlg.spn_usd_cash.setValue(20.0) # simulate $20 bill for $1.25 purchase to show change
app.processEvents()
dlg.grab().save(str(out_dir / "04_payment_dialog.png"))
dlg.close()

print("Screenshots captured successfully in data/screenshots/")
app.quit()
