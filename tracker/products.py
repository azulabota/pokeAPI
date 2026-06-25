# Products we care about: {name: {tcin: Target TCIN, sku: Best Buy SKU, ...}}
# TCINs found by searching target.com for the product and noting the A-XXXXX number
# SKUs found by searching bestbuy.com product URLs

TARGET_PRODUCTS = {
    "151 Booster Bundle": {
        "tcin": "89531271",
        "dpci": "207-04-0119",
        "category": "booster_bundle",
        "priority": 1,
    },
    "151 Booster Pack": {
        "tcin": "89657716",
        "dpci": "207-04-0121",
        "category": "booster_pack",
        "priority": 2,
    },
    "151 Poster Collection": {
        "tcin": "89244673",
        "dpci": "207-04-0108",
        "category": "collection_box",
        "priority": 3,
    },
    "151 Elite Trainer Box": {
        "tcin": "89237079",
        "dpci": "207-04-0111",
        "category": "etb",
        "priority": 1,
    },
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
    "Prismatic Evolutions Poster Collection": {
        "tcin": "90526810",
        "dpci": "207-04-0167",
        "category": "collection_box",
        "priority": 2,
    },
    "Twilight Masquerade Booster Bundle": {
        "tcin": "89531276",
        "dpci": "207-04-0120",
        "category": "booster_bundle",
        "priority": 3,
    },
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
    "Paldean Fates Booster Bundle": {
        "tcin": "89344422",
        "dpci": "207-04-0126",
        "category": "booster_bundle",
        "priority": 3,
    },
    "Paldean Fates ETB": {
        "tcin": "89344421",
        "dpci": "207-04-0132",
        "category": "etb",
        "priority": 2,
    },
}

# Products tracked at Best Buy (by SKU)
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
