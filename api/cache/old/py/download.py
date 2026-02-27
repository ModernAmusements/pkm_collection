#!/usr/bin/env python3
"""
Download and cache chase-manning Pokemon TCG Pocket card database.
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path


CACHE_DIR = Path("api/cache")
CARD_DATA_FILE = CACHE_DIR / "cards.json"
EXPANSIONS_FILE = CACHE_DIR / "expansions.json"

CARD_DATA_URL = "https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/v4.json"
EXPANSIONS_URL = "https://raw.githubusercontent.com/chase-manning/pokemon-tcg-pocket-cards/refs/heads/main/expansions.json"


def ensure_cache_dir():
    """Create cache directory if not exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def download_json(url: str, output_path: Path) -> bool:
    """Download JSON from URL and save to cache."""
    import requests
    
    try:
        print(f"Downloading: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2, ensure_ascii=False)
        
        print(f"Saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def load_cards() -> list:
    """Load card data from cache or download."""
    ensure_cache_dir()
    
    # Try to load from cache
    if CARD_DATA_FILE.exists():
        with open(CARD_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Download if not cached
    if download_json(CARD_DATA_URL, CARD_DATA_FILE):
        with open(CARD_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return []


def load_expansions() -> list:
    """Load expansions/sets data from cache or download."""
    ensure_cache_dir()
    
    if EXPANSIONS_FILE.exists():
        with open(EXPANSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    if download_json(EXPANSIONS_URL, EXPANSIONS_FILE):
        with open(EXPANSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return []


def refresh():
    """Force refresh the cache."""
    ensure_cache_dir()
    
    # Remove old files
    if CARD_DATA_FILE.exists():
        CARD_DATA_FILE.unlink()
    if EXPANSIONS_FILE.exists():
        EXPANSIONS_FILE.unlink()
    
    # Download fresh
    return load_cards(), load_expansions()


def get_cache_info() -> dict:
    """Get information about cached data."""
    info = {
        'cards_cached': False,
        'expansions_cached': False,
        'cards_count': 0,
        'expansions_count': 0,
    }
    
    if CARD_DATA_FILE.exists():
        cards = load_cards()
        info['cards_cached'] = True
        info['cards_count'] = len(cards)
        info['cards_file'] = str(CARD_DATA_FILE)
        info['cards_modified'] = datetime.fromtimestamp(
            CARD_DATA_FILE.stat().st_mtime
        ).isoformat()
    
    if EXPANSIONS_FILE.exists():
        expansions = load_expansions()
        info['expansions_cached'] = True
        info['expansions_count'] = len(expansions)
    
    return info


if __name__ == "__main__":
    print("=== Pokemon TCG Pocket Card Database ===\n")
    
    # Refresh cache
    print("Refreshing cache...")
    cards, expansions = refresh()
    
    print(f"\nCached {len(cards)} cards")
    print(f"Cached {len(expansions)} expansions/sets")
    
    # Show info
    info = get_cache_info()
    print(f"\nCache info: {info}")
