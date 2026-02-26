#!/usr/bin/env python3
"""
Efficient scraper for pokemongohub.net German Pokemon TCG Pocket cards.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os

BASE_URL = 'https://pocket.pokemongohub.net'

SETS = [
    ("A1", "t3hb77i3xy08no0-unschlagbare-gene", "Unschlagbare Gene"),
    ("A1a", "bh6swrnbnb0xqp7-mysterise-insel", "Mysteriöse Insel"),
    ("A2", "i344270g8xo3wb9-kollision-von-raum-und-zeit", "Kollision von Raum und Zeit"),
    ("A2a", "j6yh136n6ar7m1q-licht-des-triumphs", "Licht des Triumphs"),
    ("A2b", "48r74kv8tun9j02-glnzendes-festival", "Glänzendes Festival"),
    ("A3", "797ubb2z58mtxl1-hter-des-firmaments", "Hüter des Firmaments"),
    ("A3a", "n112zho988s4v74-extradimensional-crisis", "Extradimensional Crisis"),
    ("A3b", "0g49s62r1wb1p2b-evoli-hain", "Evoli-Hain"),
    ("A4", "h61dsk33evt45mp-weisheit-von-meer-und-himmel", "Weisheit von Meer und Himmel"),
    ("A4a", "h5n4a0fs0kvgztc-verborgene-quelle", "Verborgene Quelle"),
    ("A4b", "dzswkhwwfk811kd-deluxepack-ex", "Deluxepack-ex"),
    ("PROMO-A", "hrvgwu3dwxaboc7-promo-a", "PROMO-A"),
    ("PROMO-B", "vxunkwyap88g5jr-promo-b", "PROMO-B"),
    ("B1", "0guapr9h7we56l3-mega-aufstieg", "Mega-Aufstieg"),
    ("B1a", "t8vwgpxthcklr0n-crimson-blaze", "Crimson Blaze"),
]

def get_session():
    """Create a session with proper headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    })
    return session

def get_card_urls(session, set_id, set_slug):
    """Get all card URLs from a set page."""
    url = f"{BASE_URL}/de/set/{set_slug}"
    response = session.get(url, timeout=30)
    
    if response.status_code != 200:
        print(f"  Error: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=re.compile(r'/de/card/'))
    
    # Extract unique card URLs
    card_urls = list(set([link.get('href') for link in links]))
    return card_urls

def parse_card(session, card_url):
    """Parse a single card page."""
    url = BASE_URL + card_url if card_url.startswith('/') else card_url
    response = session.get(url, timeout=30)
    
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    
    data = {
        'url': card_url,
        'german_name': '',
        'set_id': '',
        'card_number': '',
        'set_total': '',
        'hp': '',
        'energy_type': '',
        'stage': '',
        'rarity': '',
        'weakness': '',
        'retreat': '',
        'illustrator': '',
        'pack_points': '',
        'release_date': '',
        'attacks': [],
    }
    
    # Extract from URL
    match = re.search(r'/de/card/[^/]+-([^-]+)$', card_url)
    if match:
        data['german_name'] = match.group(1).replace('-', ' ').title()
    
    # HP
    hp_match = re.search(r'(\d+)\s*KP', text)
    if hp_match:
        data['hp'] = hp_match.group(1)
    
    # Card number
    num_match = re.search(r'#\s*(\d+)\s*/\s*(\d+)', text)
    if num_match:
        data['card_number'] = num_match.group(1)
        data['set_total'] = num_match.group(2)
    
    # Energy type
    energy_match = re.search(r'Energie-Typ.*?(\w+)-Karte', text)
    if energy_match:
        data['energy_type'] = energy_match.group(1).capitalize()
    
    # Stage
    stage_match = re.search(r'Entwicklungsstufe.*?<strong>([^<]+)', text, re.DOTALL)
    if stage_match:
        data['stage'] = stage_match.group(1).strip()
    
    # Rarity
    rarity_match = re.search(r'(\d+)-Diamant', text)
    if rarity_match:
        data['rarity'] = f"{rarity_match.group(1)} Diamond"
    
    # Weakness with damage
    weak_section = soup.find(string=re.compile(r'Schwäche'))
    if weak_section:
        parent = weak_section.parent
        parent_text = parent.get_text() if parent else ''
        
        # Find weakness type
        weak_icon = parent.find('img', {'src': re.compile(r'eng-')}) if parent else None
        weak_type = ''
        if weak_icon:
            src = weak_icon.get('src', '')
            type_match = re.search(r'eng-(\w+)', src)
            if type_match:
                weak_type = type_match.group(1).capitalize()
        
        # Find damage
        damage_match = re.search(r'\+(\d+)', parent_text)
        damage = damage_match.group(1) if damage_match else ''
        
        if weak_type:
            data['weakness'] = f"{weak_type}+{damage}" if damage else weak_type
    
    # Retreat cost
    retreat_section = soup.find(string=re.compile(r'Rückzugskosten'))
    if retreat_section:
        parent = retreat_section.parent
        parent_text = parent.get_text() if parent else ''
        
        # Find retreat energy type
        retreat_icon = parent.find('img', {'src': re.compile(r'eng-')}) if parent else None
        retreat_energy = ''
        if retreat_icon:
            src = retreat_icon.get('src', '')
            type_match = re.search(r'eng-(\w+)', src)
            if type_match:
                retreat_energy = type_match.group(1).capitalize()
        
        # Find cost number
        cost_match = re.search(r'(\d+)', parent_text)
        cost = cost_match.group(1) if cost_match else ''
        
        if retreat_energy or cost:
            data['retreat'] = f"{cost}{retreat_energy}" if retreat_energy else cost
    
    # Illustrator
    illust_match = re.search(r'Illustrator[:\s]*\*\*([^*]+)\*\*', text)
    if illust_match:
        data['illustrator'] = illust_match.group(1).strip()
    
    # Pack points
    points_match = re.search(r'(\d+)\s*Booster-Punkte', text)
    if points_match:
        data['pack_points'] = points_match.group(1)
    
    # Release date
    date_match = re.search(r'Verfügbar seit\s*(\d{2}/\d{2}/\d{4})', text)
    if date_match:
        data['release_date'] = date_match.group(1)
    
    # Attacks - find all attack headers
    attack_headers = soup.find_all('h3')
    for header in attack_headers:
        name = header.get_text().strip()
        if name and len(name) < 50:  # Reasonable attack name length
            # Find damage in sibling or nearby
            damage = ''
            sibling = header.find_next_sibling()
            if sibling:
                dmg_match = re.search(r'(\d+)\s*$', sibling.get_text())
                if dmg_match:
                    damage = dmg_match.group(1)
            
            # Find energy cost icons
            costs = []
            # Look in parent for energy icons
            parent = header.parent
            if parent:
                icons = parent.find_all('img', {'src': re.compile(r'/eng-')})
                for icon in icons[:4]:
                    src = icon.get('src', '')
                    match = re.search(r'/eng-(\w+)', src)
                    if match:
                        costs.append(match.group(1).capitalize())
            
            # Find effect text
            effect = ''
            if sibling:
                effect = sibling.get_text().strip()
                effect = re.sub(r'\d+\s*$', '', effect).strip()
            
            data['attacks'].append({
                'name': name,
                'damage': damage,
                'cost': costs,
                'effect': effect[:200] if effect else ''
            })
    
    return data

def main():
    print("=" * 60)
    print("Pokemon TCG Pocket - German Card Scraper")
    print("=" * 60)
    
    session = get_session()
    
    # First visit homepage to establish session
    print("\n[1/3] Establishing session...")
    session.get(BASE_URL + "/de", timeout=30)
    print("  Session ready")
    
    # Get all card URLs
    print("\n[2/3] Collecting card URLs...")
    all_cards = []
    for set_id, set_slug, set_name in SETS:
        print(f"  {set_id}: {set_name}...", end=" ")
        card_urls = get_card_urls(session, set_id, set_slug)
        print(f"{len(card_urls)} cards")
        all_cards.extend(card_urls)
        time.sleep(0.5)
    
    all_cards = list(set(all_cards))
    print(f"  Total: {len(all_cards)} cards")
    
    # Parse each card
    print("\n[3/3] Parsing card details...")
    scraped = []
    total = len(all_cards)
    
    for i, card_url in enumerate(all_cards):
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{total}")
        
        data = parse_card(session, card_url)
        if data:
            scraped.append(data)
        
        time.sleep(0.3)  # Rate limiting
    
    # Save
    output_file = 'api/cache/german_cards_complete.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(scraped, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"Complete! Scraped {len(scraped)} cards")
    print(f"Saved to: {output_file}")
    print(f"{'=' * 60}")
    
    # Show sample
    if scraped:
        print("\nSample (first card):")
        print(json.dumps(scraped[0], indent=2, ensure_ascii=False)[:1500])

if __name__ == "__main__":
    main()
