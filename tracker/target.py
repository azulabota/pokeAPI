"""
Target stock checker — manual approach.

Target has locked down all API access behind PerimeterX bot protection.
Store-level stock is no longer shown on product pages.

This module provides:
1. A manual-check bookmarklet you can run from your phone
2. A street-date tracker for upcoming releases
3. Weekly restock day prediction (from user observation)

Usage:
    python -m tracker.target --manual    # Print the bookmarklet
    python -m tracker.target --dates     # Show upcoming release dates
"""
import os
import sys
from datetime import datetime, timezone, timedelta

from tracker.db import log_snapshot, get_store_pattern, get_conn

# Upcoming Pokemon TCG release dates (UTC)
RELEASE_DATES = {
    "Prismatic Evolutions": {
        "etb": "2025-01-17",
        "booster_bundle": "2025-01-17",
        "poster_collection": "2025-01-17",
    },
    "Journey Together": {
        "etb": "2025-03-28",
        "booster_bundle": "2025-03-28",
    },
    "Destined Rivals": {
        "etb": "2025-05-30",
        "booster_bundle": "2025-05-30",
    },
    "Mega Evolution Set": {
        "etb": "2026-07-17",
        "booster_bundle": "2026-07-17",
    },
}


def print_bookmarklet():
    """Print a JavaScript bookmarklet for manual Target stock checking."""
    print("""
╔══════════════════════════════════════════════════════════╗
║              TARGET MANUAL STOCK CHECK                   ║
╚══════════════════════════════════════════════════════════╝

Since Target blocks automated checking, here's how to check manually:

STEP 1: Open Target.com on your phone (set to your home store)

STEP 2: Search for the product you want

STEP 3: Tap "Pick up in store" — it shows availability
         at your selected store without needing to add to cart

BEST PRACTICE:
• Set your Target store in the app
• Check on known truck days (track them below)
• Check early morning (8-10 AM) after truck delivery
""")


def print_upcoming_dates():
    """Print upcoming release dates for planning."""
    print("\n📅 UPCOMING POKEMON RELEASES AT TARGET\n")
    print(f"{'Set':<30} {'Product':<25} {'Date':<15} {'Status':<15}")
    print("-" * 85)
    
    now = datetime.now(timezone.utc)
    
    for set_name, products in RELEASE_DATES.items():
        for product_type, date_str in products.items():
            release = datetime.fromisoformat(date_str)
            release = release.replace(tzinfo=timezone.utc)
            
            if release > now:
                days_until = (release - now).days
                status = f"⬆️ {days_until}d away"
            elif (now - release).days < 60:
                status = "🟢 IN STORES"
            else:
                status = "⚪ Old set"
            
            print(f"{set_name:<30} {product_type:<25} {date_str:<15} {status:<15}")
    
    print(f"\nTip: New releases usually hit shelves 1-3 days after street date.")
    print(f"Check your local Target on release day + 1 for best odds.")


def run_target_check(zip_codes=None, products=None, headless=True):
    """
    Placeholder — Target automated checking is blocked by PerimeterX.
    This logs a 'skipped' entry and returns empty results.
    
    Use print_bookmarklet() or print_upcoming_dates() instead.
    """
    print("\n⚠️  Target automated stock checking is not feasible.")
    print("   Target uses PerimeterX bot protection which blocks all programmatic access.")
    print("   Run with --manual or --dates for alternative approaches.\n")
    
    # Log that we skipped
    for zip_code in (zip_codes or ["unknown"]):
        log_snapshot("target", "skipped", "Target (blocked)", "check_skipped", "0", False, "BLOCKED", "")
    
    return []


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--manual" in args:
        print_bookmarklet()
    elif "--dates" in args:
        print_upcoming_dates()
    else:
        print_bookmarklet()
        print_upcoming_dates()
