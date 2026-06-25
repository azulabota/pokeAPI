"""
Target store stock checker using Playwright with system Chrome.

Simple approach: load the product page, wait for the "Pick up in store"
section to render, then extract store-level availability from the DOM.
"""
import os
import time
import json
import traceback
from datetime import datetime, timezone

from tracker.products import TARGET_PRODUCTS
from tracker.db import log_snapshot, get_last_stock
from tracker.notifier import notify_restock

from playwright.sync_api import sync_playwright


def build_product_url(tcin):
    return f"https://www.target.com/p/-/A-{tcin}"


def check_product_stock(tcin, zip_code, browser, context):
    """
    Load a Target product page and extract store availability.
    Uses a fresh page per product to avoid stale state.
    """
    page = context.new_page()
    product_url = build_product_url(tcin)
    
    result = {
        "title": "",
        "price": "",
        "stores": [],
        "error": None,
    }
    
    try:
        # Navigate to product page
        page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
        
        # Wait for the page to settle and API calls to complete
        # Target loads store availability via JS after page load
        page.wait_for_timeout(5000)
        
        # Extract product info and store availability from the DOM
        info = page.evaluate("""() => {
            const data = {};
            
            // Product title
            const h1 = document.querySelector('h1');
            data.title = h1 ? h1.textContent.trim() : document.title.replace(' : Target', '');
            
            // Price
            const priceEl = document.querySelector('[data-test*="price"], [class*="price"], .styles__Price');
            data.price = priceEl ? priceEl.textContent.trim() : '';
            if (!data.price) {
                const scriptEls = document.querySelectorAll('script');
                for (const s of scriptEls) {
                    if (s.textContent && s.textContent.includes('formatted_current_price')) {
                        const m = s.textContent.match(/formatted_current_price["\\']?\\s*[:=]\\s*["\\']?([^"\\'\\n,}]+)/);
                        if (m) { data.price = m[1]; break; }
                    }
                }
            }
            
            // Store availability section - look for "Pick up" / store list
            const storeSections = [];
            const allText = document.body.innerText || '';
            
            // Look for the "Pick up in store" section
            const pickupSection = document.querySelector('[class*="fulfillment"], [data-test*="fulfillment"], [class*="store-availability"]');
            if (pickupSection) {
                storeSections.push(pickupSection.innerText.substring(0, 500));
            }
            
            // Look for store list in the page
            const storeOptions = document.querySelectorAll('[class*="store-option"], [data-test*="store"], li[class*="store"]');
            const stores = [];
            storeOptions.forEach(so => {
                stores.push(so.innerText.substring(0, 200));
            });
            
            // Check if any visible text says "in stock" or "available"
            const bodyText = document.body.innerText || '';
            data.availabilityText = '';
            
            // Find the fulfillment/pickup section text
            const lines = bodyText.split('\\n');
            let inFulfillment = false;
            const fulfillmentLines = [];
            for (const line of lines) {
                const lower = line.toLowerCase().trim();
                if (lower.includes('pick up') || lower.includes('get it') || lower.includes('shipping') || lower.includes('delivery') || lower.includes('fulfillment')) {
                    inFulfillment = true;
                }
                if (inFulfillment) {
                    fulfillmentLines.push(line);
                    if (fulfillmentLines.length > 20) break;
                }
            }
            data.fulfillmentSection = fulfillmentLines.join('\\n');
            
            // Check for stock indicators
            data.hasPickup = bodyText.toLowerCase().includes('pick up');
            data.pickupText = '';
            const pickupMatch = bodyText.match(/([^\\n]*pick up[^\\n]*)/gi);
            if (pickupMatch) data.pickupText = pickupMatch.slice(0, 3).join(' | ');
            
            return data;
        }""")
        
        result["title"] = info.get("title", "")
        result["price"] = info.get("price", "")
        result["info"] = info
        
        # Parse store availability from the fulfillment section text
        fulfillment_text = info.get("fulfillmentSection", "")
        pickup_text = info.get("pickupText", "")
        
        # Check if we can find store-level info
        in_stock_keywords = ["in stock", "available", "ready", "pickup"]
        delivery_options = []
        
        # Split fulfillment section into lines and check each
        for line in fulfillment_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Skip navigation/header lines
            if any(x in line.lower() for x in ["shipping", "delivery", "change", "enter zip"]):
                continue
            # Look for store-like lines
            if any(keyword in line.lower() for keyword in ["target", "store", "pickup", "get it", "available"]):
                in_stock = any(sk in line.lower() for sk in ["in stock", "available", "ready"])
                delivery_options.append({
                    "text": line[:150],
                    "in_stock": in_stock,
                    "stock_level": "IN_STOCK" if in_stock else "unknown",
                })
        
        if not delivery_options:
            # No store-level data found - use page-level availability
            result["stores"].append({
                "store_id": f"zip_{zip_code}",
                "store_name": f"Target near {zip_code}",
                "in_stock": False,
                "stock_level": "NO_DATA",
                "price": info.get("price", ""),
            })
        else:
            for opt in delivery_options:
                result["stores"].append({
                    "store_id": f"zip_{zip_code}",
                    "store_name": f"Target near {zip_code}",
                    "in_stock": opt["in_stock"],
                    "stock_level": opt["stock_level"],
                    "price": info.get("price", ""),
                })
        
    except Exception as e:
        result["error"] = str(e)
        result["stores"].append({
            "store_id": f"zip_{zip_code}",
            "store_name": f"Target near {zip_code}",
            "in_stock": False,
            "stock_level": "ERROR",
            "price": "",
        })
    finally:
        page.close()
    
    return result


def run_target_check(zip_codes, products=None, headless=True):
    """
    Check Target stock for all products at all ZIP codes.
    """
    if products is None:
        products = TARGET_PRODUCTS
    
    restock_alerts = []
    
    print(f"\n{'='*50}")
    print(f"TARGET — {len(products)} products × {len(zip_codes)} ZIPs")
    print(f"{'='*50}")
    
    with sync_playwright() as p:
        # Use system Chrome for best anti-bot compatibility
        browser = p.chromium.launch(
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/Denver",
        )
        
        # Establish session with Target homepage first
        print("  Warming up browser session...")
        warmup = context.new_page()
        try:
            warmup.goto("https://www.target.com", wait_until="domcontentloaded", timeout=15000)
            warmup.wait_for_timeout(2000)
        except Exception:
            pass
        warmup.close()
        print("  Session ready")
        
        for zip_code in zip_codes:
            print(f"\n--- ZIP {zip_code} ---")
            
            for prod_name, prod_info in products.items():
                tcin = prod_info["tcin"]
                print(f"  {prod_name} (A-{tcin})...", end=" ", flush=True)
                
                result = check_product_stock(tcin, zip_code, browser, context)
                
                stores = result.get("stores", [])
                price = result.get("price", "")
                title = result.get("title", prod_name)[:60]
                
                if result.get("error"):
                    print(f"⚠️ error: {result['error'][:60]}")
                    log_snapshot("target", f"zip_{zip_code}", f"Target near {zip_code}",
                                prod_name, tcin, False, "ERROR", price)
                    continue
                
                for store in stores:
                    in_stock = store["in_stock"]
                    stock_level = store["stock_level"]
                    
                    log_snapshot("target", store["store_id"], store["store_name"],
                                prod_name, tcin, in_stock, stock_level, store["price"])
                    
                    if in_stock:
                        last = get_last_stock(tcin, "target", store["store_id"])
                        prev_out = last and last["in_stock"] == 0
                        print(f"✅ IN STOCK!")
                        if prev_out:
                            restock_alerts.append((prod_name, store["store_name"], tcin, price))
                    else:
                        if stock_level not in ("NO_DATA", "ERROR", "NO_STORES", ""):
                            print(f"❌ {stock_level}")
                        else:
                            print(f"➖ no store data available")
        
        browser.close()
    
    # Send alerts
    for prod_name, store_name, tcin, price in restock_alerts:
        notify_restock("target", store_name, prod_name, price, build_product_url(tcin))
    
    return restock_alerts
