"""
Products to track at each retailer.

TCINs verified working as of June 25, 2026.
Run `python3 find_tcins.py` or `python3 verify_tcins.py` to refresh.
"""

# Target products tracked by TCIN (internal product ID from Target.com URLs)
TARGET_PRODUCTS = {
    # === HIGH PRIORITY - Prismatic Evolutions ===
    "Prismatic Evolutions ETB": {
        "tcin": "1008746912",
        "category": "etb",
        "priority": 1,
    },
    # === HIGH PRIORITY - Scarlet & Violet 151 ===
    "151 Booster Pack": {
        "tcin": "1001304528",
        "category": "booster_pack",
        "priority": 1,
    },
    # === MEDIUM PRIORITY ===
    "Stellar Crown Art Bundle": {
        "tcin": "93605824",
        "category": "collection_box",
        "priority": 2,
    },
    "Masks of Ogerpon Premium Collection": {
        "tcin": "1004842404",
        "category": "collection_box",
        "priority": 2,
    },
    "Mega Evolution Perfect Order ETB": {
        "tcin": "1010767187",
        "category": "etb",
        "priority": 2,
    },
    # === LOWER PRIORITY / NICHE ===
    "Astral Radiance Build & Battle Box": {
        "tcin": "92955640",
        "category": "build_battle",
        "priority": 3,
    },
    "SV1 Booster Pack (Koraidon)": {
        "tcin": "1001148307",
        "category": "booster_pack",
        "priority": 3,
    },
}

# Best Buy products tracked by SKU
# Find SKU from: bestbuy.com/site/-/XXXXXXXX.p
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
