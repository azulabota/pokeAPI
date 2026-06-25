"""
PokeAPI — Pokémon stock tracker

Orchestrates checking Target (Playwright) and Best Buy (API) stores
for Pokémon card restocks and sends Telegram alerts.

Usage:
    python -m tracker.main                     # Full check of all stores
    python -m tracker.main --target-only       # Only check Target
    python -m tracker.main --bestbuy-only      # Only check Best Buy
    python -m tracker.main --pattern-report    # Show restock patterns from DB
"""
import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load env before any imports that depend on it
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from tracker.db import init_db, get_restock_events, get_store_pattern
from tracker.bestbuy import run_bestbuy_check
from tracker.products import BESTBUY_PRODUCTS


def get_zip_codes():
    """Get ZIP codes from env var."""
    zips = []
    for key in ["HOME_ZIP", "WORK_ZIP", "COMMUTE_ZIP_1", "COMMUTE_ZIP_2"]:
        val = os.getenv(key, "").strip()
        if val and val.isdigit():
            zips.append(val)
    
    # Default fallback
    if not zips:
        print("⚠️  No ZIP codes configured in .env! Using 80238 (Denver) as default.")
        zips = ["80238"]
    
    return zips


def print_pattern_report():
    """Print a report of observed restock patterns from the database."""
    events = get_restock_events(days=30)
    
    print(f"\n{'='*60}")
    print("RESTOCK PATTERN REPORT (last 30 days)")
    print(f"{'='*60}")
    
    if not events:
        print("No restock events recorded yet. Keep checking!")
        return
    
    print(f"\n{len(events)} restock events found:\n")
    
    # Group by store
    by_store = {}
    for event in events:
        key = f"{event['store_chain']}:{event['store_name']}"
        if key not in by_store:
            by_store[key] = []
        by_store[key].append(event)
    
    from collections import Counter
    from datetime import datetime
    
    for store_key, store_events in sorted(by_store.items()):
        chain, name = store_key.split(":", 1)
        print(f"📍 {chain.upper()} — {name}")
        
        # Count by day of week
        days = Counter()
        for e in store_events:
            ts = e["checked_at"]
            try:
                dt = datetime.fromisoformat(ts)
                days[dt.strftime("%A")] += 1
            except Exception:
                pass
        
        if days:
            print(f"   Restock days: {', '.join(f'{d}({c})' for d, c in days.most_common())}")
        
        # Recent events
        print(f"   Recent: {', '.join(e['product_name'] for e in store_events[:5])}")
        print()


def main():
    init_db()
    
    args = sys.argv[1:]
    target_only = "--target-only" in args
    bestbuy_only = "--bestbuy-only" in args
    pattern_report = "--pattern-report" in args
    
    if pattern_report:
        print_pattern_report()
        return
    
    zip_codes = get_zip_codes()
    
    print(f"\n{'#'*55}")
    print(f"#  PokeAPI Stock Checker")
    print(f"#  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"#  ZIPs: {', '.join(zip_codes)}")
    print(f"{'#'*55}")
    
    total_restocks = []
    
    # Target check — manually disabled (PerimeterX blocks automated access)
    if not bestbuy_only:
        print("\n⚠️  Target check skipped — site uses PerimeterX bot protection.")
        print("   Use the dashboard's manual checklist or release calendar instead.")
        print('   Or check Target on your phone via target.com -> set your store -> "Pick up in store"')
    
    # Best Buy check (simple API calls)
    if not target_only:
        try:
            restocks = run_bestbuy_check(zip_codes)
            total_restocks.extend(restocks)
        except Exception as e:
            print(f"\n❌ Best Buy check failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*50}")
    print(f"CHECK COMPLETE — {len(total_restocks)} restock(s) found")
    print(f"{'='*50}")
    
    if not total_restocks:
        print("\nNo restocks detected this cycle. Set up a cron job to check regularly!")
        print("  Schedule suggestion: check every 20-30 minutes during restock windows")


if __name__ == "__main__":
    main()
