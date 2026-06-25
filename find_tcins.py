"""Quick TCIN finder - searches Target for Pokemon products via Playwright."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

SEARCH = "pokemon trading card game booster bundle elite trainer box"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True,
        args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
    url = "https://www.target.com/s?searchTerm=" + SEARCH.replace(" ", "+")
    print("Searching:", url)
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    
    for i in range(30):
        n = page.evaluate("document.querySelectorAll('a').length")
        print(f"  Wait {i+1}s... {n} links on page")
        if n > 20:
            break
        page.wait_for_timeout(1000)
    
    data = page.evaluate("""() => {
        const links = document.querySelectorAll('a');
        const seen = new Set();
        const results = [];
        links.forEach(a => {
            const m = (a.href || '').match(/A-(\\d+)/);
            if (m && !seen.has(m[1])) {
                seen.add(m[1]);
                const text = a.textContent || a.getAttribute('aria-label') || '';
                results.push({tcin: m[1], text: text.trim().substring(0, 100)});
            }
        });
        return results.slice(0, 25);
    }""")
    
    print(f"\nFound {len(data)} product TCINs:\n")
    for d in data:
        print(f"  A-{d['tcin']:>8}  {d['text'][:80]}")
    
    print(f"\nPage title: {page.title()}")
    browser.close()
