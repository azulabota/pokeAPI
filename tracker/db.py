"""
SQLite database for tracking stock history and detecting restock events.
"""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "stock_history.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stock_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_chain TEXT NOT NULL,       -- 'target', 'bestbuy'
            store_id TEXT NOT NULL,           -- store identifier
            store_name TEXT,                  -- human-readable store name
            product_name TEXT NOT NULL,
            product_id TEXT NOT NULL,         -- TCIN or SKU
            in_stock INTEGER NOT NULL,       -- 1 = in stock, 0 = out
            stock_level TEXT,                 -- 'IN_STOCK', 'OUT_OF_STOCK', 'LIMITED'
            price TEXT,                       -- formatted price string
            checked_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_product ON stock_snapshots(product_id, store_chain);
        CREATE INDEX IF NOT EXISTS idx_snapshots_time ON stock_snapshots(checked_at);
        CREATE INDEX IF NOT EXISTS idx_snapshots_store ON stock_snapshots(store_chain, store_id);
    """)
    conn.commit()
    conn.close()


def log_snapshot(store_chain, store_id, store_name, product_name, product_id,
                 in_stock, stock_level=None, price=None):
    conn = get_conn()
    conn.execute(
        """INSERT INTO stock_snapshots
           (store_chain, store_id, store_name, product_name, product_id,
            in_stock, stock_level, price)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (store_chain, str(store_id), store_name, product_name, str(product_id),
         1 if in_stock else 0, stock_level, price)
    )
    conn.commit()
    conn.close()


def get_last_stock(product_id, store_chain, store_id):
    """Get the most recent stock status for a product at a store."""
    conn = get_conn()
    row = conn.execute(
        """SELECT in_stock, stock_level, checked_at FROM stock_snapshots
           WHERE product_id = ? AND store_chain = ? AND store_id = ?
           ORDER BY id DESC LIMIT 1""",
        (str(product_id), store_chain, str(store_id))
    ).fetchone()
    conn.close()
    return row


def get_restock_events(days=14):
    """Find all restock events (0 -> 1 transitions) in the last N days."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT a.* FROM stock_snapshots a
           WHERE a.in_stock = 1
           AND a.checked_at > datetime('now', ?)
           AND NOT EXISTS (
               SELECT 1 FROM stock_snapshots b
               WHERE b.product_id = a.product_id
               AND b.store_chain = a.store_chain
               AND b.store_id = a.store_id
               AND b.id < a.id
               AND b.checked_at > datetime(a.checked_at, '-6 hours')
               AND b.in_stock = 1
           )
           ORDER BY a.checked_at DESC""",
        (f"-{days} days",)
    ).fetchall()
    conn.close()
    return rows


def get_store_pattern(store_chain, store_id, days=30):
    """Get stock pattern for a store to learn restock days/times."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT checked_at, product_name, in_stock
           FROM stock_snapshots
           WHERE store_chain = ? AND store_id = ?
           AND checked_at > datetime('now', ?)
           ORDER BY checked_at ASC""",
        (store_chain, store_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return rows


def close_old_connections():
    pass
