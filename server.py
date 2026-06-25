"""
PokeAPI Web Dashboard — serves stock data as JSON + an HTML dashboard.

Usage:
    python server.py            # Runs on http://localhost:8080
    python server.py --port 9090
    python server.py --open     # Opens browser automatically
"""
import os
import sys
import json
import sqlite3
import argparse
import http.server
import socketserver
from datetime import datetime, timezone
from urllib.parse import urlparse

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracker.db import DB_PATH, get_conn


def get_current_status():
    """Get the latest stock snapshot for every product-store combo."""
    conn = get_conn()
    
    # Latest snapshot per (product_id, store_chain, store_id)
    rows = conn.execute("""
        SELECT s1.* FROM stock_snapshots s1
        INNER JOIN (
            SELECT product_id, store_chain, store_id, MAX(id) as max_id
            FROM stock_snapshots
            GROUP BY product_id, store_chain, store_id
        ) s2 ON s1.id = s2.max_id
        ORDER BY s1.in_stock DESC, s1.store_chain, s1.store_name
    """).fetchall()
    
    conn.close()
    
    return [{
        "product": r["product_name"],
        "store_chain": r["store_chain"],
        "store_name": r["store_name"],
        "in_stock": bool(r["in_stock"]),
        "stock_level": r["stock_level"],
        "price": r["price"],
        "checked_at": r["checked_at"],
    } for r in rows]


def get_recent_events(days=7):
    """Get recent restock events and notable changes."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM stock_snapshots
        WHERE checked_at > datetime('now', ?)
        ORDER BY checked_at DESC
        LIMIT 100
    """, (f"-{days} days",)).fetchall()
    conn.close()
    
    return [{
        "product": r["product_name"],
        "store_chain": r["store_chain"],
        "store_name": r["store_name"],
        "in_stock": bool(r["in_stock"]),
        "checked_at": r["checked_at"],
    } for r in rows]


def get_summary():
    """Get summary stats for the dashboard."""
    conn = get_conn()
    
    total_checks = conn.execute("SELECT COUNT(*) FROM stock_snapshots").fetchone()[0]
    stores = conn.execute("""
        SELECT store_chain, store_name, COUNT(*) as checks
        FROM stock_snapshots
        GROUP BY store_chain, store_name
        ORDER BY store_chain
    """).fetchall()
    
    products = conn.execute("""
        SELECT product_name, COUNT(*) as checks, 
               SUM(in_stock) as in_stock_count
        FROM stock_snapshots
        GROUP BY product_name
        ORDER BY product_name
    """).fetchall()
    
    last_check = conn.execute(
        "SELECT MAX(checked_at) FROM stock_snapshots"
    ).fetchone()[0]
    
    conn.close()
    
    return {
        "total_checks": total_checks,
        "last_check": last_check,
        "stores": [{"chain": r["store_chain"], "name": r["store_name"], "checks": r["checks"]} for r in stores],
        "products": [{"name": r["product_name"], "checks": r["checks"], "in_stock_count": r["in_stock_count"]} for r in products],
    }


# ── HTTP Handler ─────────────────────────────────────────────

HTML_PAGE = None  # Loaded at startup


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/status":
            self._json_response(get_current_status())
        elif path == "/api/events":
            self._json_response(get_recent_events())
        elif path == "/api/summary":
            self._json_response(get_summary())
        elif path == "/":
            self._serve_html()
        else:
            super().do_GET()
    
    def _json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())
    
    def log_message(self, format, *args):
        if "/api/" in args[0] if len(args) > 0 else False:
            pass  # Silence API poll spam
        else:
            super().log_message(format, *args)


def load_html():
    global HTML_PAGE
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    if not os.path.exists(html_path):
        print(f"⚠️  dashboard.html not found at {html_path}")
        HTML_PAGE = "<html><body><h1>Dashboard not found</h1></body></html>"
        return
    with open(html_path) as f:
        HTML_PAGE = f.read()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PokeAPI Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    args = parser.parse_args()
    
    load_html()
    
    print(f"\n{'='*50}")
    print(f"  PokeAPI Dashboard")
    print(f"  http://localhost:{args.port}")
    print(f"{'='*50}")
    print(f"\n  API endpoints:")
    print(f"    /api/summary   - Stats overview")
    print(f"    /api/status    - Current stock status")
    print(f"    /api/events    - Recent events")
    print(f"\n  Press Ctrl+C to stop\n")
    
    if args.open:
        import webbrowser
        webbrowser.open(f"http://localhost:{args.port}")
    
    with socketserver.TCPServer(("", args.port), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
