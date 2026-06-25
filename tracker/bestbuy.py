"""
Best Buy store stock checker.

Best Buy has a free public developer API (developer.bestbuy.com).
We query store-level availability by SKU and ZIP.
"""
import os
import json
import requests
from dotenv import load_dotenv

from tracker.products import BESTBUY_PRODUCTS
from tracker.db import log_snapshot, get_last_stock
from tracker.notifier import notify_restock

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

API_KEY = os.getenv("BESTBUY_API_KEY", "")
BASE_URL = "https://api.bestbuy.com/v1"


def get_store_id(zip_code):
    """Get the Best Buy store ID nearest to a ZIP code."""
    if not API_KEY:
        print("  ⚠️  BESTBUY_API_KEY not set. Skipping Best Buy check.")
        return None
    
    try:
        resp = requests.get(
            f"{BASE_URL}/stores(area({zip_code},25))",
            params={
                "format": "json",
                "apiKey": API_KEY,
                "show": "storeId,name,city,address",
                "pageSize": "3",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            stores = data.get("stores", [])
            if stores:
                return stores[0]
            else:
                print(f"  No Best Buy stores near {zip_code}")
                return None
        else:
            print(f"  Best Buy store lookup failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  Best Buy store lookup error: {e}")
        return None


def check_store_stock(sku, store_id, product_name):
    """Check if a product SKU is in stock at a specific Best Buy store."""
    if not API_KEY:
        return None
    
    try:
        resp = requests.get(
            f"{BASE_URL}/products/{sku}/stores(storeId={store_id})",
            params={
                "format": "json",
                "apiKey": API_KEY,
                "show": "sku,name,storeId,quantityOnHand,quantitySold,addToCartUrl",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            stores = data.get("stores", [])
            if stores:
                store = stores[0]
                quantity = store.get("quantityOnHand", 0)
                return {
                    "in_stock": quantity > 0,
                    "quantity": quantity,
                    "store_id": str(store.get("storeId", store_id)),
                }
            return {"in_stock": False, "quantity": 0, "store_id": str(store_id)}
        else:
            print(f"  Best Buy stock check failed ({product_name}): {resp.status_code}")
            return None
    except Exception as e:
        print(f"  Best Buy stock check error ({product_name}): {e}")
        return None


def run_bestbuy_check(zip_codes, products=None):
    """
    Check Best Buy stock for all products at all ZIP codes.
    
    Returns: List of restock events
    """
    if products is None:
        products = BESTBUY_PRODUCTS
    
    if not API_KEY:
        print("\n⚠️  BESTBUY_API_KEY not configured — skipping Best Buy")
        print("   Get a free key at https://developer.bestbuy.com")
        return []
    
    restock_alerts = []
    
    print(f"\n{'='*50}")
    print(f"BEST BUY — {len(products)} products × {len(zip_codes)} ZIPs")
    print(f"{'='*50}")
    
    # Find nearest store for each ZIP
    store_info = {}
    for zip_code in zip_codes:
        store = get_store_id(zip_code)
        if store:
            store_info[zip_code] = store
            print(f"  ZIP {zip_code} → Store #{store['storeId']}: {store.get('name','')}")
        else:
            print(f"  No Best Buy near ZIP {zip_code}")
    
    if not store_info:
        print("  No Best Buy stores found near any ZIP code.")
        return []
    
    # Check each product at the first matching store
    primary_store = list(store_info.values())[0]
    store_id = primary_store["storeId"]
    store_name = f"Best Buy #{store_id} - {primary_store.get('city','')}"
    
    print(f"\n--- Checking at {store_name} ---")
    
    for prod_name, prod_info in products.items():
        sku = prod_info.get("sku", "")
        if not sku:
            continue
        
        result = check_store_stock(sku, store_id, prod_name)
        if result is None:
            continue
        
        in_stock = result["in_stock"]
        quantity = result.get("quantity", 0)
        
        log_snapshot(
            "bestbuy", str(store_id), store_name, prod_name, sku,
            in_stock, f"qty_{quantity}" if in_stock else "OUT_OF_STOCK",
            "",
        )
        
        if in_stock:
            print(f"  ✅ {prod_name} IN STOCK! (qty: {quantity})")
            
            last = get_last_stock(sku, "bestbuy", str(store_id))
            prev_out = last and last["in_stock"] == 0
            
            if prev_out:
                restock_alerts.append((prod_name, store_name, sku, ""))
                print(f"  ** RESTOCK EVENT! **")
        else:
            print(f"  ❌ {prod_name} — out of stock")
    
    # Send Telegram alerts
    for prod_name, store_name, sku, price in restock_alerts:
        url = f"https://www.bestbuy.com/site/-/{sku}.p"
        notify_restock("bestbuy", store_name, prod_name, price, url)
    
    return restock_alerts
