"""Extract product names from TCINs by visiting each product page."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

# TCINs found from search
TCINS = [
    "1008746912", "1001304528", "93565639", "92955640",
    "1005452393", "1004842404", "93605824", "1011613450",
    "1009318827", "1010767187", "1001148307", "1005449303",
    "1003298523", "1003557564", "1007918679", "1011165569",
    "1003688229", "1006188659", "1003560274", "1004842209",
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True,
        args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
    # First establish session
    page.goto("https://www.target.com", wait_until="domcontentloaded", timeout=10000)
    
    results = []
    for tcin in TCINS:
        url = f"https://www.target.com/p/-/A-{tcin}"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=10000)
            time.sleep(1.5)
            
            info = page.evaluate("""() => {
                // Try multiple sources for product name
                const title = document.title;
                const h1 = document.querySelector('h1');
                const ogTitle = document.querySelector('meta[property=\"og:title\"]');
                
                return {
                    title: title,
                    h1: h1 ? h1.textContent.trim().substring(0, 100) : '',
                    ogTitle: ogTitle ? ogTitle.content : '',
                    isPokemon: title.toLowerCase().includes('pokemon') || 
                               (h1 && h1.textContent.toLowerCase().includes('pokemon'))
                };
            }""")
            
            if info.get('isPokemon') or 'pokemon' in url.lower():
                name = info['h1'] or info['ogTitle'] or info['title']
                name = name.replace(' : Target', '').strip()
                results.append((tcin, name, '✅ POKEMON'))
                print(f"  ✅ A-{tcin}: {name[:80]}")
            else:
                print(f"  ❌ A-{tcin}: {info['title'][:60]}")
                
        except Exception as e:
            print(f"  ⚠️  A-{tcin}: error - {e}")
    
    browser.close()
    
    print(f"\n\n=== POKEMON PRODUCTS FOUND: {len([r for r in results if 'POKEMON' in r[2]])} ===\n")
    for tcin, name, tag in results:
        if 'POKEMON' in tag:
            print(f'    "tcin": "{tcin}",  # {name}')
