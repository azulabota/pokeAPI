"""
Target store stock checker using Playwright (headless browser).

Target's internal APIs require a proper browser session with cookies and JS context,
so we use Playwright to load the product page and intercept the network response
that contains store-level availability data.

This avoids paying for RedCircle API ($66/mo).
"""
import json
import os
import time
import traceback
from datetime import datetime, timezone

from tracker.products import TARGET_PRODUCTS
from tracker.db import log_snapshot, get_last_stock
from tracker.notifier import notify_restock


def build_product_url(tcin):
    return f"https://www.target.com/p/-/A-{tcin}"


def intercept_store_data(response):
    """
    Playwright response interceptor.
    When the sapphire API returns product data, we capture it.
    """
    url = response.url
    if "sapphire-api.target.com" in url and "/raw/www.target.com/p/" in url:
        try:
            data = response.json()
            # sapphire wraps the actual page response in pages[0]
            pages = data.get("pages", [])
            if pages:
                page_data = pages[0]
                product = page_data.get("product", {})
                if product:
                    fulfillment = product.get("fulfillment", {})
                    item = product.get("item", {})
                    price = product.get("price", {})
                    
                    store_options = fulfillment.get("store_options", [])
                    pickup_options = fulfillment.get("order_pickup_options", [])
                    
                    stores = []
                    for store in store_options:
                        stores.append({
                            "store_id": str(store.get("store_id", "")),
                            "name": store.get("location_name", ""),
                            "address": store.get("location_address", ""),
                            "city": store.get("location_city", ""),
                            "state": store.get("location_state", ""),
                            "zip": store.get("location_zip", ""),
                            "distance": store.get("distance", ""),
                            "in_stock": store.get("in_stock", False),
                            "stock_level": store.get("stock", ""),
                            "price": store.get("formatted_price", price.get("formatted_current_price", "")),
                        })
                    
                    # Also check pickup options
                    for p in pickup_options:
                        sid = str(p.get("store_id", ""))
                        # Avoid duplicates
                        if not any(s["store_id"] == sid for s in stores):
                            stores.append({
                                "store_id": sid,
                                "name": p.get("store_name", ""),
                                "address": p.get("store_address", ""),
                                "city": p.get("store_city", ""),
                                "state": p.get("store_state", ""),
                                "zip": "",
                                "distance": "",
                                "in_stock": p.get("is_available", False),
                                "stock_level": "IN_STOCK" if p.get("is_available") else "OUT_OF_STOCK",
                                "price": p.get("price", price.get("formatted_current_price", "")),
                            })
                    
                    return {
                        "product_name": item.get("product_description", {}).get("title", ""),
                        "tcin": item.get("tcin", ""),
                        "dpci": item.get("dpci", ""),
                        "upc": item.get("upc", ""),
                        "price": price.get("formatted_current_price", ""),
                        "stores": stores,
                        "has_shipping": len(fulfillment.get("shipping_options", [])) > 0,
                        "has_pickup": len(pickup_options) > 0,
                    }
        except Exception:
            pass
    return None


def check_zip_for_product(product_name, product_info, zip_code, page, results_holder):
    """
    Check if a product is available at stores near a ZIP code.
    Uses Playwright to load the page and intercept the sapphire API response.
    """
    tcin = product_info["tcin"]
    url = build_product_url(tcin)
    product_key = f"{tcin}:{zip_code}"
    
    def on_response(response):
        data = intercept_store_data(response)
        if data and product_key not in results_holder["done"]:
            results_holder["done"].add(product_key)
            results_holder["data"][product_key] = {
                "product_name": product_name,
                "product_id": tcin,
                "price": data.get("price", ""),
                "stores": data.get("stores", []),
            }
    
    try:
        page.on("response", on_response)
        print(f"  Loading {product_name} (TCIN {tcin})...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Wait for the sapphire API response (it usually loads within 3-5s)
        for _ in range(30):  # up to 15 seconds
            if product_key in results_holder["done"]:
                break
            time.sleep(0.5)
        
        # Unregister listener
        page.remove_listener("response", on_response)
        
        if product_key in results_holder["done"]:
            print(f"  ✅ Got store data for {product_name}")
        else:
            print(f"  ⚠️  No API response captured for {product_name}")
            results_holder["data"][product_key] = {
                "product_name": product_name,
                "product_id": tcin,
                "price": "",
                "stores": [],
            }
        
    except Exception as e:
        print(f"  Error checking {product_name}: {e}")
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass
        results_holder["data"][product_key] = {
            "product_name": product_name,
            "product_id": tcin,
            "price": "",
            "stores": [],
        }


def run_target_check(zip_codes, products=None, headless=True):
    """
    Main entry point: check Target stock for all products at all ZIP codes.
    
    Args:
        zip_codes: List of ZIP codes to check
        products: Dict of products to check (default: TARGET_PRODUCTS)
        headless: Whether to run browser headless
    
    Returns: List of restock events found
    """
    if products is None:
        products = TARGET_PRODUCTS
    
    from playwright.sync_api import sync_playwright
    
    results_holder = {"done": set(), "data": {}}
    restock_alerts = []
    
    print(f"\n{'='*50}")
    print(f"TARGET — {len(products)} products × {len(zip_codes)} ZIPs")
    print(f"{'='*50}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="America/Denver",
        )
        page = context.new_page()
        
        for zip_code in zip_codes:
            print(f"\n--- ZIP {zip_code} ---")
            for prod_name, prod_info in products.items():
                check_zip_for_product(prod_name, prod_info, zip_code, page, results_holder)
        
        browser.close()
    
    # Process all results
    for key, data in results_holder["data"].items():
        stores = data.get("stores", [])
        product_name = data["product_name"]
        product_id = data["product_id"]
        price = data.get("price", "")
        
        if not stores:
            print(f"  ⚠️  No store data for {product_name}")
            log_snapshot("target", "unknown", "Target (no data)", product_name, product_id, False, "NO_DATA", price)
            continue
        
        for store in stores:
            store_id = store.get("store_id", "unknown")
            store_name = f"{store.get('name', '')} - {store.get('city', '')}"
            in_stock = store.get("in_stock", False)
            stock_level = store.get("stock_level", "")
            
            log_snapshot(
                "target", store_id, store_name, product_name, product_id,
                in_stock, stock_level, store.get("price", price),
            )
            
            if in_stock:
                last = get_last_stock(product_id, "target", store_id)
                prev_out = last and last["in_stock"] == 0
                
                status = f"  ✅ {product_name} IN STOCK at {store_name}"
                if store.get("price"):
                    status += f" ({store['price']})"
                print(status)
                
                if prev_out:
                    restock_alerts.append((product_name, store_name, product_id, store.get("price", price)))
                    print(f"  ** RESTOCK EVENT! **")
            else:
                if stock_level not in ("UNKNOWN", "NO_DATA", "ERROR", ""):
                    print(f"  ❌ {product_name} at {store_name} — {stock_level or 'out'}")
    
    # Send Telegram alerts
    for alert_data in restock_alerts:
        prod_name, store_name, product_id, price = alert_data
        store_link = build_product_url(product_id)
        notify_restock("target", store_name, prod_name, price, store_link)
    
    return restock_alerts
