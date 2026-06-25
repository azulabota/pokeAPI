"""
Products to track at each retailer.

⚠️  Target TCINs need periodic verification — these are community-sourced
    and may change when products sell out and are delisted.
    Run `python find_tcins.py --search "pokemon 151" --visible` to find current TCINs.
"""

# Target products tracked by TCIN (Target's internal product ID)
# Find TCINs from the URL: target.com/p/-/A-XXXXXXXX
TARGET_PRODUCTS = {
    # === Scarlet & Violet 151 ===
    "151 Booster Bundle": {
        "tcin": "89531271",
        "dpci": "207-04-0119",
        "category": "booster_bundle",
        "priority": 1,
    },
    # === Prismatic Evolutions ===
    "Prismatic Evolutions ETB": {
        "tcin": "90526805",
        "dpci": "207-04-0165",
        "category": "etb",
        "priority": 1,
    },
    "Prismatic Evolutions Booster Bundle": {
        "tcin": "90600304",
        "dpci": "207-04-0169",
        "category": "booster_bundle",
        "priority": 1,
    },
    # === Surging Sparks ===
    "Surging Sparks Booster Bundle": {
        "tcin": "90435360",
        "dpci": "207-04-0159",
        "category": "booster_bundle",
        "priority": 2,
    },
    "Surging Sparks ETB": {
        "tcin": "90435359",
        "dpci": "207-04-0158",
        "category": "etb",
        "priority": 2,
    },
    # === Twilight Masquerade ===
    "Twilight Masquerade Booster Bundle": {
        "tcin": "89531276",
        "dpci": "207-04-0120",
        "category": "booster_bundle",
        "priority": 3,
    },
    # === Paldean Fates ===
    "Paldean Fates Booster Bundle": {
        "tcin": "89344422",
        "dpci": "207-04-0126",
        "category": "booster_bundle",
        "priority": 3,
    },
}

# Best Buy products tracked by SKU
# Find SKU from the URL: bestbuy.com/site/-/XXXXXXXX.p
BESTBUY_PRODUCTS = {
    "Prismatic Evolutions ETB": {
        "sku": "6591754",
        "category": "etb",
        "priority": 1,
    },
    "151 Booster Bundle": {
        "sku": "6570508",
        "category": "booster_bundle",
        "priority": 1,
    },
}
