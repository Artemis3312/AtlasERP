import unittest
import os
import sqlite3
from app.database.db import get_connection, init_db
from app.services.exchange_rate import ExchangeRateService
from app.services.inventory_service import InventoryService
from app.services.shift_service import ShiftService
from app.services.pos_service import PosService
from app.services.movement_service import MovementService
from app.services.report_service import ReportService


class TestAtlasERP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_exchange_rate(self):
        # Establecer tasa manual
        ok = ExchangeRateService.set_rate(950.0, source="MANUAL_TEST")
        self.assertTrue(ok)
        rate = ExchangeRateService.get_active_rate()
        self.assertEqual(rate, 950.0)

        info = ExchangeRateService.get_rate_info()
        self.assertEqual(info["source"], "MANUAL_TEST")

    def test_02_inventory_crud(self):
        # Limpiar si ya existía para idempotencia
        code = "TEST-PROD-999"
        existing = InventoryService.get_by_code(code)
        if existing:
            InventoryService.delete_product(existing["id"])

        # Crear producto
        ok, msg = InventoryService.save_product(
            product_id=None,
            code=code,
            name="Producto de Prueba",
            category="Pruebas",
            cost_usd=1.0,
            price_usd=2.5,
            stock=20.0,
            min_stock=5.0
        )
        self.assertTrue(ok, msg)

        # Buscar producto
        prod = InventoryService.get_by_code(code)
        self.assertIsNotNone(prod)
        self.assertEqual(prod["name"], "Producto de Prueba")
        self.assertEqual(prod["price_usd"], 2.5)

        # Editar producto
        ok, msg = InventoryService.save_product(
            product_id=prod["id"],
            code=code,
            name="Producto de Prueba Modificado",
            category="Pruebas",
            cost_usd=1.2,
            price_usd=3.0,
            stock=25.0,
            min_stock=5.0
        )
        self.assertTrue(ok, msg)

        prod_updated = InventoryService.get_by_id(prod["id"])
        self.assertEqual(prod_updated["name"], "Producto de Prueba Modificado")
        self.assertEqual(prod_updated["price_usd"], 3.0)

    def test_03_shift_and_pos_multi_payment(self):
        # Asegurar que si hay un turno abierto se use o se abra uno nuevo
        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            ok, msg, shift_id = ShiftService.open_shift(initial_usd=50.0, initial_bs=5000.0, cashier_name="Tester")
            self.assertTrue(ok, msg)
            active_shift = ShiftService.get_active_shift()

        self.assertIsNotNone(active_shift)
        shift_id = active_shift["id"]

        rate = ExchangeRateService.get_active_rate()  # 950.0

        # Obtener un producto con stock
        products = InventoryService.list_products(active_only=True)
        self.assertTrue(len(products) > 0)
        p = products[0]
        initial_stock = p["stock"]

        # Venta con múltiples métodos de pago:
        # Total venta = 1 * p['price_usd']
        total_usd = round(p["price_usd"], 2)
        total_bs = round(total_usd * rate, 2)

        # Dividir pago: Mitad en USD efectivo, cuarta parte en BS Tarjeta, cuarta parte en BS Pago Móvil
        usd_cash_pay = round(total_usd / 2.0, 2)
        remain_bs = round((total_usd - usd_cash_pay) * rate, 2)
        card_bs_pay = round(remain_bs / 2.0, 2)
        pm_bs_pay = round(remain_bs - card_bs_pay, 2)

        items = [{"product_id": p["id"], "code": p["code"], "name": p["name"], "qty": 1.0, "price_usd": p["price_usd"]}]
        payments = [
            {"method": "USD_EFECTIVO", "amount": usd_cash_pay, "currency": "USD", "reference": ""},
            {"method": "BS_TARJETA", "amount": card_bs_pay, "currency": "BS", "reference": "VOUCH-001"},
            {"method": "BS_PAGO_MOVIL", "amount": pm_bs_pay, "currency": "BS", "reference": "PM-998877"},
        ]

        ok, msg, sale_result = PosService.process_sale(
            items=items,
            payments=payments,
            client_name="Cliente Prueba Multi-Pago",
            client_id_doc="V-12345678"
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(sale_result)

        # Verificar descuento de inventario
        p_after = InventoryService.get_by_id(p["id"])
        self.assertEqual(p_after["stock"], initial_stock - 1.0)

    def test_04_cash_advance(self):
        active_shift = ShiftService.get_active_shift()
        self.assertIsNotNone(active_shift)

        # Realizar avance de 200 Bs entregados en efectivo, cobrados por Pago Móvil con 5% de comisión
        dispensed_bs = 200.0
        ok, msg, data = PosService.process_cash_advance(
            amount_cash_dispensed_bs=dispensed_bs,
            payment_method="BS_PAGO_MOVIL",
            reference="REF-AVANCE-1234",
            commission_pct=5.0,
            client_name="Cliente Avance Prueba"
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(data)
        self.assertEqual(data["dispensed_bs"], 200.0)
        self.assertEqual(data["charged_bs"], 210.0)

    def test_05_shift_close_and_arqueo(self):
        active_shift = ShiftService.get_active_shift()
        self.assertIsNotNone(active_shift)
        shift_id = active_shift["id"]

        # Calcular métricas esperadas
        metrics = ShiftService.get_shift_metrics(shift_id)
        self.assertIn("expected_cash_usd", metrics)
        self.assertIn("expected_cash_bs", metrics)
        self.assertIn("total_card_bs", metrics)
        self.assertIn("total_pago_movil_bs", metrics)

        # Cerrar el turno con conteo físico exacto
        real_usd = metrics["expected_cash_usd"]
        real_bs = metrics["expected_cash_bs"]

        ok, msg, close_res = ShiftService.close_shift(
            shift_id=shift_id,
            real_cash_usd=real_usd,
            real_cash_bs=real_bs,
            notes="Cierre de prueba unitaria cuadrado"
        )
        self.assertTrue(ok, msg)
        self.assertEqual(close_res["diff_usd"], 0.0)
        self.assertEqual(close_res["diff_bs"], 0.0)

        # Verificar que el turno ahora está cerrado
        self.assertIsNone(ShiftService.get_active_shift())

    def test_06_reports_generation(self):
        # Reporte de Operaciones
        rep_ops = ReportService.generate_operations_report("2026-01-01", "2026-12-31")
        self.assertTrue(os.path.exists(rep_ops))
        self.assertTrue(os.path.getsize(rep_ops) > 1000)

        # Reporte de Inventario
        rep_inv = ReportService.generate_inventory_report()
        self.assertTrue(os.path.exists(rep_inv))
        self.assertTrue(os.path.getsize(rep_inv) > 1000)

    def test_07_multiple_change_and_shift_reconciliation(self):
        """Prueba venta con vuelto múltiple (parte USD y parte Bs) y cuadre de caja."""
        # 1. Abrir turno nuevo
        ok, msg, shift_id = ShiftService.open_shift(initial_usd=100.0, initial_bs=5000.0, cashier_name="Cajero Vueltos")
        self.assertTrue(ok)

        # 2. Venta con vuelto múltiple
        p = InventoryService.list_products(search_term="Harina Pan")[0]
        items = [{"product_id": p["id"], "code": p["code"], "name": p["name"], "qty": 2.0, "price_usd": 2.50}]
        rate = ExchangeRateService.get_active_rate()

        # Cliente paga con billete de $10 USD para compra de $5.00
        payments = [{"method": "USD_EFECTIVO", "amount": 10.0, "currency": "USD", "reference": ""}]
        # Vuelto total a entregar: $5.00
        # Cajero entrega: $2.00 en USD y el restante ($3.00 * rate) en Bs
        change_usd = 2.00
        change_bs = round(3.00 * rate, 2)

        ok, msg, sale_res = PosService.process_sale(
            items=items,
            payments=payments,
            client_name="Cliente Vuelto Mixto",
            change_usd=change_usd,
            change_bs=change_bs
        )
        self.assertTrue(ok, msg)
        self.assertEqual(sale_res["change_usd"], 2.00)
        self.assertEqual(sale_res["change_bs"], change_bs)

        # 3. Validar métricas de arqueo
        metrics = ShiftService.get_shift_metrics(shift_id)
        # Esperado USD: 100 inicial + 10 pago - 2 vuelto = 108.0
        self.assertAlmostEqual(metrics["expected_cash_usd"], 108.0, places=2)
        # Esperado BS: 5000 inicial + 0 pago - change_bs vuelto = 5000 - change_bs
        expected_bs = round(5000.0 - change_bs, 2)
        self.assertAlmostEqual(metrics["expected_cash_bs"], expected_bs, places=2)

        # 4. Cerrar turno cuadrado
        ok, msg, close_res = ShiftService.close_shift(
            shift_id=shift_id,
            real_cash_usd=108.0,
            real_cash_bs=expected_bs
        )
        self.assertTrue(ok)
        self.assertAlmostEqual(close_res["diff_usd"], 0.0, places=2)
        self.assertAlmostEqual(close_res["diff_bs"], 0.0, places=2)


if __name__ == "__main__":
    unittest.main()
