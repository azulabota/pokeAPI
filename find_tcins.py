"""
Helper: Find Target product TCINs by searching Target's website.

Opens Target in Chrome, searches for a product, and shows you the TCIN.
Use this to find/verify TCINs for the products you want to track.

Usage:
    python find_tcins.py --search "pokemon 151 booster bundle"
    python find_tcins.py --list         # Show current products
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracker.products import TARGET_PRODUCTS


def search_and_extract(search_term, headless=False):
    """Open Target in Chrome, search for a term, and extract product TCINs."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        
        url = f"https://www.target.com/s?searchTerm={search_term.replace(' ', '+')}"
        print(f"Loading {url}...")
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            print("Page loaded. Waiting for results...")
            
            # Wait for products to appear (up to 15 seconds)
            for i in range(30):
                products = page.evaluate("""() => {
                    const cards = document.querySelectorAll('[data-test="product-card"], .styles__ProductCard, a[href*="/p/A-"]');
                    return cards.length;
                }""")
                if products > 0:
                    break
                page.wait_for_timeout(500)
            
            products = page.evaluate("""() => {
                const cards = document.querySelectorAll('[data-test="product-card"], a[href*="/p/A-"]');
                const results = [];
                const seen = new Set();
                cards.forEach(c => {
                    const href = c.getAttribute('href') || c.querySelector('a')?.getAttribute('href') || '';
                    const m = href.match(/A-(\d+)/);
                    if (m && !seen.has(m[1])) {
                        seen.add(m[1]);
                        const title = c.getAttribute('aria-label') || 
                                     c.querySelector('[data-test="product-title"]')?.textContent ||
                                     c.querySelector('img')?.getAttribute('alt') || '';
                        results.push({tcin: m[1], title: title.trim().substring(0, 80)});
                    }
                });
                return results;
            }""")
            
            if products:
                print(f"\nFound {len(products)} products:\n")
                for p in products[:15]:
                    print(f"  A-{p['tcin']}  {p['title']}")
            else:
                print("\nNo products found. The page might need you to complete a captcha.")
                print("Try running with --visible to see the browser window:")
                print(f"  python find_tcins.py --search \"{search_term}\" --visible")
                page.wait_for_timeout(10000)  # Give time to see the page
                
        except Exception as e:
            print(f"Error: {e}")
            page.wait_for_timeout(5000)
        
        browser.close()


def list_products():
    """List current products in the config."""
    print("Current Target products configured:\n")
    for name, info in TARGET_PRODUCTS.items():
        print(f"  {name}")
        print(f"    TCIN: {info['tcin']}")
        print(f"    DPCI: {info.get('dpci', '?')}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find Target product TCINs")
    parser.add_argument("--search", help="Search term to look up on Target")
    parser.add_argument("--list", action="store_true", help="List current products")
    parser.add_argument("--visible", action="store_true", help="Show browser (not headless)")
    args = parser.parse_args()
    
    if args.list:
        list_products()
    elif args.search:
        search_and_extract(args.search, headless=not args.visible)
    else:
        parser.print_help()
