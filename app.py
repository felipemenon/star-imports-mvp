import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from flask import Flask, abort, flash, redirect, render_template, request, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-demo-change-me"),
        DATABASE=os.environ.get("STAR_DB", str(Path(app.instance_path) / "star.sqlite3")),
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect_db():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def init_db():
        with connect_db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY, name TEXT NOT NULL,
                    stock INTEGER NOT NULL CHECK (stock >= 0)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    code TEXT PRIMARY KEY,
                    status TEXT NOT NULL CHECK (status IN ('separando', 'coletado', 'cancelado'))
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY,
                    order_code TEXT NOT NULL REFERENCES orders(code),
                    sku TEXT NOT NULL REFERENCES products(sku),
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    cancelled INTEGER NOT NULL DEFAULT 0 CHECK (cancelled IN (0, 1)),
                    UNIQUE(order_code, sku)
                );
            """)
            if db.execute("SELECT 1 FROM products LIMIT 1").fetchone() is None:
                db.execute("INSERT INTO products VALUES (?, ?, ?)", ("SKU-AX7", "Organizador modular", 8))
                db.execute("INSERT INTO products VALUES (?, ?, ?)", ("SKU-BK2", "Caixa organizadora", 14))
                db.execute("INSERT INTO orders VALUES (?, ?)", ("DS-1042", "separando"))
                db.execute("INSERT INTO order_items(order_code, sku, quantity) VALUES (?, ?, ?)", ("DS-1042", "SKU-AX7", 2))
                db.execute("INSERT INTO order_items(order_code, sku, quantity) VALUES (?, ?, ?)", ("DS-1042", "SKU-BK2", 1))

    init_db()

    def get_order(code):
        with connect_db() as db:
            order = db.execute("SELECT * FROM orders WHERE code = ?", (code.strip().upper(),)).fetchone()
            if order is None:
                return None
            items = db.execute(
                """SELECT oi.id, oi.sku, p.name, oi.quantity, oi.cancelled, p.stock
                   FROM order_items oi JOIN products p ON p.sku = oi.sku
                   WHERE oi.order_code = ? ORDER BY oi.id""",
                (order["code"],),
            ).fetchall()
            return {"code": order["code"], "status": order["status"], "items": items}

    @app.get("/")
    def home():
        code = request.args.get("code", "").strip()
        order = get_order(code) if code else None
        if code and order is None:
            flash("Não encontramos esse pedido. Confira o código e tente novamente.", "error")
        return render_template("index.html", order=order, query=code)

    @app.post("/orders/<code>/cancel/<int:item_id>")
    def cancel_item(code, item_id):
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT status FROM orders WHERE code = ?", (code.upper(),)).fetchone()
            item = db.execute(
                "SELECT sku, quantity, cancelled FROM order_items WHERE id = ? AND order_code = ?",
                (item_id, code.upper()),
            ).fetchone()
            if order is None or item is None:
                abort(404)
            if order["status"] != "separando":
                flash("Cancelamento indisponível: o pedido já foi coletado ou encerrado.", "error")
            elif item["cancelled"]:
                flash("Este item já foi cancelado; o estoque não foi alterado novamente.", "notice")
            else:
                db.execute("UPDATE order_items SET cancelled = 1 WHERE id = ?", (item_id,))
                db.execute("UPDATE products SET stock = stock + ? WHERE sku = ?", (item["quantity"], item["sku"]))
                flash("Item cancelado e saldo reposto.", "success")
        return redirect(url_for("home", code=code.upper()))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
