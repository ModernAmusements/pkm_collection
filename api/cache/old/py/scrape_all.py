#!/usr/bin/env python3
"""
Efficient scraper for Limitless TCG Pocket.
Scrapes ALL cards from ALL sets and saves to api/cache/limitless_cards.json
"""

import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

BASE_URL = "https://pocket.limitlesstcg.com/cards"
CACHE_DIR = Path("api/cache")
OUTPUT_FILE = CACHE_DIR / "limitless_cards.json"

REQUEST_DELAY = 0.3  # seconds between requests


def get_card_count(set_id: str) -> int:
    """Get the total number of cards in a set by probing."""
    # Try different sizes - most sets have 70-250 cards
    for size in [100, 150, 200, 250, 300]:
        url = f"{BASE_URL}/{set_id}?page=1&pageSize={size}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for pagination info
                text = soup.get_text()
                # Try to find total count
                match = re.search(r'(\d+)\s*results|(\d+)\s*cards', text, re.I)
                if match:
                    return int(match.group(1) or match.group(2))
        except:
            pass
    return 100  # Default fallback


def scrape_card(set_id: str, card_num: str) -> dict | None:
    """Scrape a single card from Limitless."""
    url = f"{BASE_URL}/{set_id}/{card_num}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()
        
        # Extract name from title
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        name = title_text.split('•')[0].strip() if '•' in title_text else ""
        
        if not name:
            return None
        
        # Extract HP
        hp_match = re.search(r'(\d+)\s*HP', page_text)
        hp = int(hp_match.group(1)) if hp_match else None
        
        # Extract Type/Energy
        energy_type = ""
        types = ['Fighting', 'Fire', 'Water', 'Grass', 'Lightning', 
                 'Psychic', 'Darkness', 'Metal', 'Fairy', 'Dragon', 'Colorless']
        for t in types:
            if t.lower() in page_text.lower():
                energy_type = t
                break
        
        # Extract Stage
        stage = ""
        text_lower = page_text.lower()
        if 'stage 2' in text_lower:
            stage = "Stage 2"
        elif 'stage 1' in text_lower:
            stage = "Stage 1"
        elif 'basic' in text_lower:
            stage = "Basic"
        
        # Extract Evolution
        evolution_from = ""
        evolve_match = re.search(r'evolves?\s+from\s+\[?([^\]\n]+)\]?', page_text, re.I)
        if evolve_match:
            evolution_from = evolve_match.group(1).strip()
        
        # Extract Weakness - include the +damage value
        weakness = ""
        weak_match = re.search(r'weakness[:\s]+(\w+)\s*\+(\d+)', page_text, re.I)
        if weak_match:
            weakness = f"{weak_match.group(1)}+{weak_match.group(2)}"
        else:
            # Try without damage
            weak_match = re.search(r'weakness[:\s]+(\w+)', page_text, re.I)
            if weak_match:
                weakness = weak_match.group(1)
        
        # Extract Retreat
        retreat_match = re.search(r'retreat[:\s]+(\d+)', page_text, re.I)
        retreat = int(retreat_match.group(1)) if retreat_match else 0
        
        # Extract Attacks - look for attack name followed by damage
        attacks = []
        # Pattern: Attack Name followed by damage number
        attack_patterns = [
            r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]*)?)\s+(\d+)\s+(?=During|If|You|Your|This|He|She|It|They|Can|Will)',
            r'([A-Z][a-zA-Z]+)\s+(\d+)\s*$',  # End of section
        ]
        for pattern in attack_patterns:
            matches = re.findall(pattern, page_text)
            for attack_name, damage in matches:
                # Filter out non-attack words
                if attack_name.lower() not in ['weakness', 'resistance', 'retreat', 'illustrated', 'hp']:
                    attacks.append({
                        'name': attack_name.strip(),
                        'damage': damage
                    })
            if attacks:
                break
        
        # Deduplicate attacks
        seen = set()
        unique_attacks = []
        for att in attacks:
            key = (att['name'], att['damage'])
            if key not in seen:
                seen.add(key)
                unique_attacks.append(att)
        attacks = unique_attacks[:3]  # Max 3 attacks
        
        # Extract Illustrator
        illustrator = ""
        illus_match = re.search(r'illustrated?\s+by\s+\[?([^\]\n]+)\]?', page_text, re.I)
        if illus_match:
            illustrator = illus_match.group(1).strip()
        
        # Extract Rarity
        rarity_match = re.search(r'([◊☆]+)', page_text)
        rarity = rarity_match.group(1) if rarity_match else ""
        
        # Extract set name
        set_name = ""
        set_match = re.search(r'\(([A-Z][0-9a-z]+)\)\s*#\d+', title_text)
        if set_match:
            set_name = set_match.group(1)
        
        # Extract card number properly
        card_match = re.search(r'#\s*(\d+)', title_text)
        card_number = card_match.group(1) if card_match else card_num
        
        return {
            'id': f"{set_id}-{card_number}",
            'set_id': set_id,
            'set_name': set_name,
            'card_number': card_number,
            'name': name,
            'hp': hp,
            'energy_type': energy_type,
            'stage': stage,
            'evolution_from': evolution_from,
            'weakness': weakness,
            'retreat': retreat,
            'attacks': attacks,
            'illustrator': illustrator,
            'rarity': rarity,
        }
        
    except Exception as e:
        return None


def scrape_set(set_id: str, set_name: str, max_cards: int = 200) -> list:
    """Scrape all cards from a single set."""
    cards = []
    print(f"  Scraping {set_id} ({set_name})...", flush=True)
    
    for card_num in range(1, max_cards + 1):
        card = scrape_card(set_id, str(card_num))
        
        if card:
            cards.append(card)
            print(f"    ✓ {card_num}: {card['name']}", flush=True)
        else:
            # If we got some cards and now hit empty, likely end of set
            if len(cards) > 0 and card_num > len(cards) + 10:
                break
        
        time.sleep(REQUEST_DELAY)
    
    print(f"    -> {len(cards)} cards")
    return cards


def scrape_all_sets():
    """Scrape all sets."""
    # Load expansions
    with open('api/cache/expansions.json', 'r') as f:
        expansions = json.load(f)
    
    all_cards = []
    
    print(f"Scraping {len(expansions)} sets...\n")
    
    for exp in expansions:
        set_id = exp.get('id')
        set_name = exp.get('name', '')
        
        cards = scrape_set(set_id, set_name)
        all_cards.extend(cards)
    
    return all_cards


def save_cards(cards: list):
    """Save cards to JSON file."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(cards)} cards to {OUTPUT_FILE}")


def load_limitless_cards() -> list:
    """Load cards from limitless cache."""
    if not OUTPUT_FILE.exists():
        return []
    with open(OUTPUT_FILE, 'r') as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("LIMITLESS TCG POCKET - FULL SCRAPER")
    print("=" * 60)
    
    # Check if already scraped
    existing = load_limitless_cards()
    if existing:
        print(f"\nFound {len(existing)} existing cards")
        # Auto-continue scraping if --resume flag is passed
        if len(sys.argv) > 1 and sys.argv[1] == '--resume':
            print("Resuming scrape (--resume flag)...")
        else:
            resp = input("Scrape again? (y/n): ")
            if resp.lower() != 'y':
                print("Using existing cache")
                exit(0)
    
    # Scrape all
    all_cards = scrape_all_sets()
    
    # Save
    save_cards(all_cards)
    
    # Stats
    sets = defaultdict(int)
    for card in all_cards:
        sets[card['set_id']] += 1
    
    print("\n" + "=" * 60)
    print(f"Total cards: {len(all_cards)}")
    print("\nCards per set:")
    for set_id, count in sorted(sets.items()):
        print(f"  {set_id}: {count}")
