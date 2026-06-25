"""
Target checker — intercepts CDUI ProductDetailFulfillment API to detect stock.
Works with system Chrome (channel="chrome") to bypass PerimeterX.

When module_data is non-empty → product available for pickup (in stock)
When module_data is empty → product out of stock
"""
import json, traceback
from tracker.products import TARGET_PRODUCTS
from tracker.db import log_snapshot, get_last_stock
from tracker.notifier import notify_restock
from playwright.sync_api import sync_playwright


def build_product_url(tcin):
    return f"https://www.target.com/p/-/A-{tcin}"


def run_target_check(zip_codes, products=None, headless=True):
    if products is None:
        products = TARGET_PRODUCTS

    restock_alerts = []
    total = len(products)

    print(f"\n{'='*50}")
    print(f"TARGET — {total} products")
    print(f"{'='*50}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome", headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # Warm up session once
        page.goto("https://www.target.com", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1500)

        for prod_name, prod_info in products.items():
            tcin = prod_info["tcin"]
            print(f"  {prod_name} (A-{tcin})...", end=" ", flush=True)

            fulfillment_data = {}

            def capture(resp):
                if not fulfillment_data and "/cdui_orchestrations/" in resp.url:
                    try:
                        for m in resp.json().get("modules", []):
                            if m.get("module_type") == "ProductDetailFulfillment":
                                md = m.get("module_data", {})
                                if md:
                                    fulfillment_data["data"] = md
                    except:
                        pass

            page.on("response", capture)
            try:
                page.goto(f"https://www.target.com/p/-/A-{tcin}",
                           wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(4500)  # CDUI responds in ~3s
            except Exception as e:
                print(f"⚠️ nav error: {str(e)[:40]}")
                for z in zip_codes:
                    log_snapshot("target", z, f"Target {z}", prod_name, tcin, False, "NAV_ERROR", "")
                continue
            finally:
                page.remove_listener("response", capture)

            # Get page info
            info = page.evaluate("""() => {
                const t = document.title.replace(' : Target','');
                const m = document.body.innerText.match(/\\$\\d+\\.\\d{2}/);
                return {title: t, price: m ? m[0] : ''};
            }""")

            in_stock = "data" in fulfillment_data
            price = info.get("price", "")

            # Log for each ZIP
            for z in zip_codes:
                log_snapshot("target", z, f"Target {z}", prod_name, tcin,
                            in_stock, "IN_STOCK" if in_stock else "OUT_OF_STOCK", price)

            if in_stock:
                print(f"✅ IN STOCK!")
                for z in zip_codes:
                    last = get_last_stock(tcin, "target", z)
                    if last and last["in_stock"] == 0:
                        restock_alerts.append((prod_name, f"Target near {z}", tcin, price))
                        break
            else:
                print(f"❌ out of stock")

        browser.close()

    for prod_name, store_name, tcin, price in restock_alerts:
        notify_restock("target", store_name, prod_name, price, build_product_url(tcin))

    return restock_alerts
