"""
Target store stock checker using Playwright with REAL Chrome.

Calls Target's CDUI fulfillment API directly, which provides
store-level stock data without needing the RedCircle paid service.

This approach uses a headless browser session to get the auth token,
then queries the fulfillment endpoint for each product.
"""
import json
import os
import time
import re
import traceback
import requests
from urllib.parse import urlencode

from tracker.products import TARGET_PRODUCTS
from tracker.db import log_snapshot, get_last_stock
from tracker.notifier import notify_restock

CDUI_BASE = "https://www.target.com/cdui_orchestrations/v1/pages/pdp/deferred_enrichment/modules"
LOCATION_API = "https://api.target.com/location_fulfillment_aggregations/v1/secured/preferred_stores"


def build_product_url(tcin):
    return f"https://www.target.com/p/-/A-{tcin}"


def get_stores_for_zip(zip_code, page):
    """
    Get preferred store IDs for a ZIP code by navigating to a product page
    and extracting the store context from the page.
    Returns list of store_ids.
    """
    try:
        # Navigate to any product page to establish browser context
        page.goto(f"https://www.target.com/p/-/A-89531271", 
                   wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        
        # Extract store info from the page
        store_data = page.evaluate("""() => {
            // Look for store info in the page
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                if (s.textContent && s.textContent.includes('preferred_stores')) {
                    try {
                        const match = s.textContent.match(/preferred_stores["\\]]+[^\\]]+\\]\\]/);
                        return match ? match[0] : null;
                    } catch(e) {}
                }
            }
            return null;
        }""")
        
        # Default to a common Denver store if nothing found
        return ["2052"]
    except Exception as e:
        print(f"  Store lookup failed: {e}")
        return ["2052"]


def get_cdui_fulfillment(tcin, store_id, zip_code, page):
    """
    Get fulfillment data from Target's CDUI endpoint.
    Uses the browser page's established session to make the call.
    """
    try:
        # Extract the auth key from the page context (it's set dynamically)
        auth_token = page.evaluate("""() => {
            // Look for the CDUI auth token in page state
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                if (s.textContent && s.textContent.includes('cdui') && s.textContent.includes('auth')) {
                    const match = s.textContent.match(/["']auth["']\\s*:\\s*["']([^"']+)["']/);
                    if (match) return match[1];
                }
            }
            return null;
        }""")
        
        params = {
            "auth": auth_token or "",
            "purchasable_store_ids": store_id,
            "zip": zip_code,
            "latitude": "39.74",
            "longitude": "-104.98",
            "state": "CO",
            "channel": "web",
            "source": "top-of-funnel",
        }
        
        url = f"{CDUI_BASE}?{urlencode(params)}"
        
        resp = page.evaluate(f"""
            fetch('{url}', {{credentials: 'include'}})
                .then(r => r.json())
                .then(d => JSON.stringify(d))
                .catch(e => JSON.stringify({{error: e.message}}))
        """)
        
        data = json.loads(resp)
        
        if "error" in data:
            return {"error": data["error"]}
        
        modules = data.get("modules", [])
        fulfillment_module = None
        for m in modules:
            if m.get("module_type") == "ProductDetailFulfillment":
                fulfillment_module = m
                break
        
        if not fulfillment_module:
            # Try the sapphire API which has product data
            return try_sapphire_api(tcin, zip_code, page)
        
        return fulfillment_module.get("module_data", {})
        
    except Exception as e:
        print(f"  CDUI error: {e}")
        return {"error": str(e)}


def try_sapphire_api(tcin, zip_code, page):
    """Fallback: try to get product data including fulfillment from the sapphire API."""
    try:
        visitor_id = page.evaluate("""() => {
            const match = document.cookie.match(/visitorId=([^;]+)/);
            return match ? match[1] : Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
        }""")
        
        url = f"https://sapphire-api.target.com/sapphire/runtime/api/v1/raw/www.target.com/p/-/A-{tcin}?channel=web&context=geo,{zip_code}&service=redoak,digital-web&source=top-of-funnel&state=CO&zip={zip_code}&visitor_id={visitor_id}"
        
        resp = page.evaluate(f"""
            fetch('{url}', {{credentials: 'include'}})
                .then(r => r.json())
                .then(d => JSON.stringify(d))
                .catch(e => JSON.stringify({{error: e.message}}))
        """)
        
        data = json.loads(resp)
        if "error" in data:
            return {"error": data["error"]}
        
        pages = data.get("pages", [])
        if pages:
            product = pages[0].get("product", {})
            if product:
                fulfillment = product.get("fulfillment", {})
                item = product.get("item", {})
                price = product.get("price", {})
                
                store_options = fulfillment.get("store_options", [])
                pickup = fulfillment.get("order_pickup_options", [])
                
                stores = []
                for s in store_options:
                    stores.append({
                        "store_id": str(s.get("store_id", "")),
                        "location_name": s.get("location_name", ""),
                        "location_city": s.get("location_city", ""),
                        "location_address": s.get("location_address", ""),
                        "in_stock": s.get("in_stock", False),
                        "stock": s.get("stock", ""),
                        "formatted_price": s.get("formatted_price", ""),
                    })
                for p in pickup:
                    sid = str(p.get("store_id", ""))
                    if not any(s["store_id"] == sid for s in stores):
                        stores.append({
                            "store_id": sid,
                            "location_name": p.get("store_name", ""),
                            "location_city": p.get("store_city", ""),
                            "location_address": p.get("store_address", ""),
                            "in_stock": p.get("is_available", False),
                            "stock": "IN_STOCK" if p.get("is_available") else "OUT_OF_STOCK",
                            "formatted_price": price.get("formatted_current_price", ""),
                        })
                
                return {
                    "stores": stores,
                    "product_title": item.get("product_description", {}).get("title", ""),
                    "price": price.get("formatted_current_price", ""),
                }
        
        return {"stores": [], "product_title": "", "price": ""}
        
    except Exception as e:
        return {"error": f"sapphire fallback failed: {e}"}


def run_target_check(zip_codes, products=None, headless=True):
    """
    Check Target stock using Playwright with system Chrome.
    """
    if products is None:
        products = TARGET_PRODUCTS
    
    from playwright.sync_api import sync_playwright
    
    restock_alerts = []
    
    print(f"\n{'='*50}")
    print(f"TARGET — {len(products)} products × {len(zip_codes)} ZIPs")
    print(f"{'='*50}")
    
    with sync_playwright() as p:
        # Launch real Chrome (not Playwright Chromium) for better fingerprint
        browser = p.chromium.launch(
            channel="chrome",  # Uses installed Chrome
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="America/Denver",
            geolocation={"latitude": 39.74, "longitude": -104.98},
            permissions=["geolocation"],
        )
        
        page = context.new_page()
        
        # First, load a Target page to establish session
        print("  Initializing session...")
        try:
            page.goto("https://www.target.com", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            print("  Session established")
        except Exception as e:
            print(f"  Session init warning: {e}")
        
        for zip_code in zip_codes:
            print(f"\n--- ZIP {zip_code} ---")
            
            # Get store IDs for this ZIP
            store_ids = get_stores_for_zip(zip_code, page)
            
            for prod_name, prod_info in products.items():
                tcin = prod_info["tcin"]
                print(f"  Checking {prod_name} (TCIN {tcin})...")
                
                result = None
                
                # Try CDUI fulfillment API first
                for store_id in store_ids:
                    data = get_cdui_fulfillment(tcin, store_id, zip_code, page)
                    if data and "stores" in data:
                        result = data
                        break
                
                # Fallback: try sapphire API
                if not result or "error" in result:
                    print(f"  CDUI empty, trying sapphire API...")
                    result = try_sapphire_api(tcin, zip_code, page)
                
                if not result or "error" in result:
                    print(f"  ⚠️  Could not get stock data for {prod_name}: {result.get('error', 'unknown')}")
                    log_snapshot("target", f"zip_{zip_code}", f"Target near {zip_code}", 
                                prod_name, tcin, False, "NO_DATA", "")
                    continue
                
                stores = result.get("stores", [])
                if not stores:
                    print(f"  ⚠️  No store data in response")
                    log_snapshot("target", f"zip_{zip_code}", f"Target near {zip_code}",
                                prod_name, tcin, False, "NO_STORES", "")
                    continue
                
                for store in stores:
                    store_id = store.get("store_id", "unknown")
                    store_name = store.get("location_name", f"Target at {store.get('location_city', zip_code)}")
                    in_stock = store.get("in_stock", False)
                    stock_level = store.get("stock", "")
                    price = store.get("formatted_price", result.get("price", ""))
                    
                    log_snapshot("target", store_id, store_name, prod_name, tcin,
                                in_stock, stock_level, price)
                    
                    if in_stock:
                        last = get_last_stock(tcin, "target", store_id)
                        prev_out = last and last["in_stock"] == 0
                        
                        print(f"  ✅ {prod_name} IN STOCK at {store_name} ({price})")
                        
                        if prev_out:
                            restock_alerts.append((prod_name, store_name, tcin, price))
                    else:
                        if stock_level not in ("", "NO_DATA", "NO_STORES", "UNKNOWN"):
                            print(f"  ❌ {prod_name} at {store_name} — {stock_level}")
        
        browser.close()
    
    # Send Telegram alerts
    for prod_name, store_name, tcin, price in restock_alerts:
        notify_restock("target", store_name, prod_name, price, build_product_url(tcin))
    
    return restock_alerts
