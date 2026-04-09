#!/usr/bin/env python3
"""
Full scraper for attack effects - fetches from pokewiki.de
"""

import json
import time
import requests
from bs4 import BeautifulSoup
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
    
    attacks_table = soup.find("table", class_="karte-angriffe")
    if not attacks_table:
        return effects
    
    rows = attacks_table.find_all("tr")
    current_attack = None
    
    for row in rows:
        row_class = row.get("class", [])
        
        if "attack-zeile" in row_class:
            cells = row.find_all("td")
            if len(cells) >= 2:
                name_cell = cells[1]
                attack_name_tag = name_cell.find("a")
                attack_name = attack_name_tag.get_text(strip=True) if attack_name_tag else name_cell.get_text(strip=True)
                current_attack = attack_name
                
        elif "beschreibung-zeile" in row_class and current_attack:
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


if __name__ == "__main__":
    print("Loading card data...")
    
    with open("api/cache/pokewiki_scraped_all.json", "r", encoding="utf-8") as f:
        card_data = json.load(f)
    
    print(f"Found {len(card_data)} cards")
    
    results = {}
    total = len(card_data)
    effects_found = 0
    
    for i, card in enumerate(card_data):
        if i % 50 == 0:
            print(f"Progress: {i}/{total} ({effects_found} effects found)")
        
        url = card.get("url", "")
        if not url:
            continue
        
        time.sleep(0.3)
        
        effects = get_card_attack_effects(url)
        
        if effects:
            results[url] = effects
            effects_found += len(effects)
    
    print(f"\nTotal: {effects_found} attack effects found")
    
    with open("api/cache/attack_effects.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"Saved to api/cache/attack_effects.json")
