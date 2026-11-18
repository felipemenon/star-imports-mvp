import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager

from app import create_app


class OrderAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-key",
            "DATABASE": os.path.join(self.tmp.name, "test.sqlite3"),
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def test_lookup_displays_order_and_items(self):
        response = self.client.get("/?code=DS-1042")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SKU-AX7", response.data)
        self.assertIn("Em separação".encode(), response.data)

    def test_missing_order_shows_not_found_message(self):
        response = self.client.get("/?code=nao-existe")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Não encontramos esse pedido".encode(), response.data)

    def test_cancel_before_pickup_returns_stock_once(self):
        response = self.client.post("/orders/DS-1042/cancel/1", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Item cancelado e saldo reposto".encode(), response.data)
        with self.db() as db:
            stock = db.execute("SELECT stock FROM products WHERE sku='SKU-AX7'").fetchone()[0]
            cancelled = db.execute("SELECT cancelled FROM order_items WHERE id=1").fetchone()[0]
        self.assertEqual(stock, 10)
        self.assertEqual(cancelled, 1)
        self.client.post("/orders/DS-1042/cancel/1", follow_redirects=True)
        with self.db() as db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE sku='SKU-AX7'").fetchone()[0], 10)

    def test_cancel_after_pickup_is_blocked(self):
        with self.db() as db:
            db.execute("UPDATE orders SET status='coletado' WHERE code='DS-1042'")
        response = self.client.post("/orders/DS-1042/cancel/1", follow_redirects=True)
        self.assertIn("Cancelamento indisponível".encode(), response.data)
        with self.db() as db:
            self.assertEqual(db.execute("SELECT stock FROM products WHERE sku='SKU-AX7'").fetchone()[0], 8)

    def test_health_endpoint(self):
        self.assertEqual(self.client.get("/health").json, {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
