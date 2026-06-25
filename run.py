#!/usr/bin/env python3
"""
Run script for PokeAPI — Pokémon stock tracker.
Checks Target (Playwright) and Best Buy (API) for restocks.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracker.main import main

if __name__ == "__main__":
    main()
