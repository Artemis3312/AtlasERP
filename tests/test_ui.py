import sys
import unittest
from PySide6.QtWidgets import QApplication
from app.database.db import init_db
from app.ui.main_window import MainWindow
from app.ui.dialogs import (
    RateDialog, ProductDialog, CashAdvanceDialog, PaymentDialog, ShiftCloseDialog, ShiftOpenDialog, ManualMovementDialog
)

# Crear QApplication única para pruebas
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_main_window_and_views(self):
        win = MainWindow()
        self.assertIsNotNone(win)
        self.assertEqual(win.stacked_views.count(), 5)

        # Probar navegación a cada vista
        for idx in range(5):
            win.switch_to_view_by_index(idx)
            self.assertEqual(win.stacked_views.currentIndex(), idx)

    def test_dialogs_instantiation(self):
        # 1. RateDialog
        dlg_rate = RateDialog()
        self.assertIsNotNone(dlg_rate)
        dlg_rate.close()

        # 2. ProductDialog
        dlg_prod = ProductDialog()
        self.assertIsNotNone(dlg_prod)
        dlg_prod.close()

        # 3. CashAdvanceDialog
        dlg_adv = CashAdvanceDialog()
        self.assertIsNotNone(dlg_adv)
        dlg_adv.close()

        # 4. PaymentDialog
        test_items = [{"product_id": 1, "code": "7591001001", "name": "Harina Pan", "qty": 2.0, "price_usd": 1.25}]
        dlg_pay = PaymentDialog(items=test_items, total_usd=2.50)
        self.assertIsNotNone(dlg_pay)
        dlg_pay.close()

        # 5. ShiftOpenDialog
        dlg_open = ShiftOpenDialog()
        self.assertIsNotNone(dlg_open)
        dlg_open.close()

        # 6. ShiftCloseDialog
        dlg_close = ShiftCloseDialog(shift_id=1)
        self.assertIsNotNone(dlg_close)
        dlg_close.close()

        # 7. ManualMovementDialog
        dlg_move = ManualMovementDialog()
        self.assertIsNotNone(dlg_move)
        dlg_move.close()


if __name__ == "__main__":
    unittest.main()
