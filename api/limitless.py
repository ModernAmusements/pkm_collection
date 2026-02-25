#!/usr/bin/env python3
"""
Scrape card data from Limitless TCG Pocket website.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from typing import Optional
from .models import CardData, MatchResult


BASE_URL = "https://pocket.limitlesstcg.com/cards"


def scrape_card(set_id: str, card_num: str) -> Optional[CardData]:
    """
    Scrape card data from Limitless website.
    
    Example: scrape_card('A2a', '38') -> Donphan data
    """
    url = f"{BASE_URL}/{set_id}/{card_num}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find card name (usually in title or heading)
        # Format: "Donphan • Triumphant Light (A2a) #38"
        title = soup.find('title')
        title_text = title.get_text() if title else ""
        
        # Extract name (before the •)
        name = title_text.split('•')[0].strip() if '•' in title_text else ""
        
        # Find HP, Type, Stage, etc.
        # Look for specific patterns in the page
        page_text = soup.get_text()
        
        # Extract HP (e.g., "120 HP")
        hp_match = re.search(r'(\d+)\s*HP', page_text)
        hp = int(hp_match.group(1)) if hp_match else None
        
        # Extract Type
        energy_type = ""
        types = ['Fighting', 'Fire', 'Water', 'Grass', 'Lightning', 
                 'Psychic', 'Darkness', 'Metal', 'Fairy', 'Dragon', 'Colorless']
        for t in types:
            if t.lower() in page_text.lower():
                energy_type = t
                break
        
        # Extract Stage (Basic, Stage 1, Stage 2)
        stage = ""
        if 'basic' in page_text.lower():
            stage = "Basic"
        elif 'stage 1' in page_text.lower():
            stage = "Stage 1"
        elif 'stage 2' in page_text.lower():
            stage = "Stage 2"
        
        # Extract Evolution
        evolution_from = ""
        evolve_match = re.search(r'evolves?\s+from\s+\[?([^\]]+)\]?', page_text, re.I)
        if evolve_match:
            evolution_from = evolve_match.group(1).strip()
        
        # Extract Weakness
        weakness = ""
        weak_match = re.search(r'weakness:\s*(\w+)', page_text, re.I)
        if weak_match:
            weakness = weak_match.group(1).strip()
        
        # Extract Retreat
        retreat = 0
        retreat_match = re.search(r'retreat:\s*(\d+)', page_text, re.I)
        if retreat_match:
            retreat = int(retreat_match.group(1))
        
        # Extract Illustrator
        illustrator = ""
        illus_match = re.search(r'illustrated?\s+by\s+\[?([^\]]+)\]?', page_text, re.I)
        if illus_match:
            illustrator = illus_match.group(1).strip()
        
        # Extract Attacks (simplified - look for pattern)
        attacks = []
        # Look for attack damage pattern: "NAME DAMAGE"
        attack_matches = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(\d+)\s*$', 
                                   page_text, re.MULTILINE)
        for attack_name, damage in attack_matches[:3]:  # Max 3 attacks
            attacks.append({
                'name': attack_name.strip(),
                'damage': damage,
                'cost': '',  # Would need more complex parsing
                'effect': ''   # Would need more complex parsing
            })
        
        # Extract Rarity
        rarity = ""
        rarity_match = re.search(r'([◊☆]+)', page_text)
        if rarity_match:
            rarity = rarity_match.group(1)
        
        # Get set name from page
        set_name = ""
        set_match = re.search(r'\(([A-Z][0-9a-z]+)\)\s*#\d+', title_text)
        if set_match:
            set_name = set_match.group(1)
        
        return CardData(
            id=f"{set_id}-{card_num}",
            name=name,
            hp=hp,
            energy_type=energy_type,
            stage=stage,
            evolution_from=evolution_from,
            card_number=card_num,
            set_id=set_id,
            set_name=set_name,
            rarity=rarity,
            attacks=attacks,
            weakness=weakness,
            retreat=retreat,
            illustrator=illustrator,
            api_source='limitless'
        )
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


def search_by_name(name: str) -> Optional[CardData]:
    """
    Search for card by name on Limitless.
    This requires scraping search results or using the sets pages.
    """
    # Would need to implement search functionality
    # For now, return None - user must provide set_id and card_num
    return None


def lookup_from_limitless(name: str = None, set_id: str = None, 
                         card_num: str = None) -> Optional[CardData]:
    """
    Main entry point for Limitless lookup.
    
    Requires either:
    - set_id + card_num (direct lookup)
    - name (search - not implemented)
    """
    if set_id and card_num:
        return scrape_card(set_id, card_num)
    
    # Would implement name search here
    return None


if __name__ == "__main__":
    # Test scraping Donphan (A2a, #38)
    print("Testing Limitless scrape...")
    
    card = scrape_card('A2a', '38')
    if card:
        print(f"Name: {card.name}")
        print(f"HP: {card.hp}")
        print(f"Type: {card.energy_type}")
        print(f"Stage: {card.stage}")
        print(f"Evolves from: {card.evolution_from}")
        print(f"Weakness: {card.weakness}")
        print(f"Retreat: {card.retreat}")
        print(f"Illustrator: {card.illustrator}")
        print(f"Attacks: {card.attacks}")
    else:
        print("Failed to fetch card")
