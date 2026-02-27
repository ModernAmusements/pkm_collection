#!/usr/bin/env python3
"""
German Card Scraper - Resumable
Scrapes weakness, retreat, attacks from pokemongohub.net
Saves progress incrementally - can be aborted and resumed
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import sys

BASE_URL = 'https://pocket.pokemongohub.net'
INPUT_FILE = 'api/cache/german_cards_complete.json'
OUTPUT_FILE = 'api/cache/german_cards_complete.json'

JUNK_ATTACKS = {
    'aus einem regulären booster', 'aus einem seltenen booster', 
    'set', 'hintergrund', 'full-art', 'verfügbar in', 'nicht verfügbar',
    'plus', 'regulärer booster', 'seltener booster', 'sonderkarte', 'promo', 'karte'
}

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept-Language': 'de-DE,de;q=0.9',
    })
    return session

def parse_card(session, card):
    url = BASE_URL + card['url']
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return card, False
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Weakness with +damage
        weak_section = soup.find(string=re.compile(r'Schwäche'))
        if weak_section:
            parent = weak_section.parent
            grandparent = parent.parent if parent else None
            if grandparent:
                text = grandparent.get_text()
                
                weak_icon = grandparent.find('img', src=re.compile(r'eng-'))
                weak_type = ''
                if weak_icon:
                    src = weak_icon.get('src', '')
                    type_match = re.search(r'eng-(\w+)', src)
                    if type_match:
                        weak_type = type_match.group(1).capitalize()
                
                damage_match = re.search(r'\+(\d+)', text)
                damage = damage_match.group(1) if damage_match else ''
                
                if weak_type:
                    card['weakness'] = f'{weak_type}+{damage}' if damage else weak_type
        
        # Retreat with energy type
        retreat_section = soup.find(string=re.compile(r'Rückzug'))
        if retreat_section:
            parent = retreat_section.parent
            grandparent = parent.parent if parent else None
            if grandparent:
                text = grandparent.get_text()
                
                retreat_icon = grandparent.find('img', src=re.compile(r'eng-'))
                retreat_energy = ''
                if retreat_icon:
                    src = retreat_icon.get('src', '')
                    type_match = re.search(r'/eng-(\w+)', src)
                    if type_match:
                        retreat_energy = type_match.group(1).capitalize()
                
                cost_match = re.search(r'(\d+)', text)
                cost = cost_match.group(1) if cost_match else ''
                
                if retreat_energy or cost:
                    card['retreat'] = f'{cost}{retreat_energy}' if retreat_energy else cost
        
        # Attacks - German names
        attack_headers = soup.find_all('h3')
        attacks = []
        for header in attack_headers:
            name = header.get_text().strip()
            if name and len(name) < 50:
                name_lower = name.lower()
                if any(j in name_lower for j in JUNK_ATTACKS):
                    continue
                
                damage = ''
                sibling = header.find_next_sibling()
                if sibling:
                    dmg_match = re.search(r'(\d+)\s*$', sibling.get_text())
                    if dmg_match:
                        damage = dmg_match.group(1)
                
                costs = []
                parent = header.parent
                if parent:
                    icons = parent.find_all('img', {'src': re.compile(r'/eng-')})
                    for icon in icons[:4]:
                        src = icon.get('src', '')
                        match = re.search(r'/eng-(\w+)', src)
                        if match:
                            costs.append(match.group(1).capitalize())
                
                attacks.append({'name': name, 'damage': damage, 'cost': costs})
        
        if attacks:
            card['attacks'] = attacks
        
    except Exception as e:
        return card, False
    
    return card, True

def main():
    print("=" * 60)
    print("GERMAN CARD SCRAPER - Scraping Details")
    print("=" * 60)
    print(f"Loading cards from {INPUT_FILE}...")
    
    # Load existing
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    total = len(cards)
    print(f"Total cards: {total}")
    
    # Stats before
    weak_before = len([c for c in cards if c.get('weakness')])
    retreat_before = len([c for c in cards if c.get('retreat')])
    attacks_before = len([c for c in cards if c.get('attacks')])
    print(f"\n[BEFORE] weakness={weak_before}, retreat={retreat_before}, attacks={attacks_before}")
    
    # Find cards that need updating
    indices_to_update = []
    for i, c in enumerate(cards):
        needs_weakness = not c.get('weakness') or '+' not in c.get('weakness', '')
        needs_retreat = not c.get('retreat')
        needs_attacks = not c.get('attacks') or len(c.get('attacks', [])) == 0
        
        if needs_weakness or needs_retreat or needs_attacks:
            indices_to_update.append(i)
    
    print(f"Cards needing update: {len(indices_to_update)}")
    print(f"\n{'='*60}")
    print("STARTING SCRAPE...")
    print(f"{'='*60}\n")
    
    session = get_session()
    
    # Process
    processed = 0
    save_interval = 50
    
    # Current stats for progress
    current_weak = weak_before
    current_retreat = retreat_before
    current_attacks = attacks_before
    
    for idx in indices_to_update:
        card = cards[idx]
        old_weakness = card.get('weakness', '')
        old_retreat = card.get('retreat', '')
        old_attacks = card.get('attacks', [])
        
        # Parse card
        updated_card, success = parse_card(session, card)
        cards[idx] = updated_card
        
        if not success:
            time.sleep(0.5)  # Wait longer on failure
            continue
            
        processed += 1
        
        # Update current stats
        if card.get('weakness') and not old_weakness:
            current_weak += 1
        if card.get('retreat') and not old_retreat:
            current_retreat += 1
        if card.get('attacks') and len(card.get('attacks', [])) > len(old_attacks):
            current_attacks += 1
        
        # Progress with live stats
        if processed % 25 == 0:
            pct = (processed / len(indices_to_update)) * 100
            print(f"[{pct:5.1f}%] Processed {processed}/{len(indices_to_update)} | weakness={current_weak}, retreat={current_retreat}, attacks={current_attacks}")
        
        # Save periodically
        if processed % save_interval == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(cards, f, indent=2, ensure_ascii=False)
        
        # Rate limit
        time.sleep(0.03)
    
    # Final save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    
    # Stats after
    weak_after = len([c for c in cards if c.get('weakness')])
    retreat_after = len([c for c in cards if c.get('retreat')])
    attacks_after = len([c for c in cards if c.get('attacks')])
    
    print(f"\n{'='*60}")
    print("DONE!")
    print(f"{'='*60}")
    print(f"Processed: {processed} cards")
    print(f"Before -> After:")
    print(f"  weakness: {weak_before} -> {weak_after}")
    print(f"  retreat:  {retreat_before} -> {retreat_after}")
    print(f"  attacks:  {attacks_before} -> {attacks_after}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
