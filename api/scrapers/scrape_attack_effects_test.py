#!/usr/bin/env python3
"""
Test scraper for attack effects - fetches from pokewiki.de
"""

import json
import time
import requests
from bs4 import BeautifulSoup
import re
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

def get_page(url: str) -> BeautifulSoup:
    """Fetch a page and return BeautifulSoup object."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def extract_attack_effects(soup: BeautifulSoup) -> dict:
    """Extract attack names and their effects."""
    effects = {}
    
    # Find the attacks table
    attacks_table = soup.find("table", class_="karte-angriffe")
    if not attacks_table:
        return effects
    
    rows = attacks_table.find_all("tr")
    
    # Track current attack to associate with effect
    current_attack = None
    
    for row in rows:
        row_class = row.get("class", [])
        
        if "attack-zeile" in row_class:
            # This is an attack row - get the attack name
            cells = row.find_all("td")
            if len(cells) >= 2:
                name_cell = cells[1]
                attack_name_tag = name_cell.find("a")
                attack_name = attack_name_tag.get_text(strip=True) if attack_name_tag else name_cell.get_text(strip=True)
                current_attack = attack_name
                
        elif "beschreibung-zeile" in row_class and current_attack:
            # This is an effect row - get the effect text
            effect_cell = row.find("td")
            if effect_cell:
                effect_text = effect_cell.get_text(strip=True)
                if effect_text:
                    effects[current_attack] = effect_text
    
    return effects


def get_card_attack_effects(url: str) -> dict:
    """Get attack effects for a card."""
    soup = get_page(url)
    if not soup:
        return {}
    return extract_attack_effects(soup)


# Test cards - cards known to have attack effects
TEST_CARDS = [
    "https://www.pokewiki.de/Bisaflor-ex_(Unschlagbare_Gene_004)",
    "https://www.pokewiki.de/Darkrai-ex_(Kollision_von_Raum_und_Zeit_110)",
    "https://www.pokewiki.de/Mewtu-ex_(Unschlagbare_Gene_129)",
    "https://www.pokewiki.de/Glurak-ex_(Unschlagbare_Gene_036)",
    "https://www.pokewiki.de/Lavados-ex_(Unschlagbare_Gene_047)",
]


if __name__ == "__main__":
    print("=== Testing Attack Effects Scraper ===\n")
    
    results = {}
    
    for url in TEST_CARDS:
        card_name = url.split("/")[-1].split("(")[0]
        print(f"Fetching: {card_name}...")
        
        time.sleep(0.5)
        effects = get_card_attack_effects(url)
        
        if effects:
            results[url] = effects
            print(f"  Found {len(effects)} attack(s) with effects:")
            for name, effect in effects.items():
                print(f"    - {name}: {effect[:80]}...")
        else:
            print(f"  No effects found")
        print()
    
    # Save test results
    with open("api/cache/attack_effects_test.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(results)} cards to api/cache/attack_effects_test.json")
