#!/usr/bin/env python3
"""
Simple scraper for pokemongohub.net using requests.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

BASE_URL = "https://pocket.pokemongohub.net"

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

def get_page(url):
    """Get page with retries."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    }
    
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None

def parse_card_page(html, url):
    """Parse a single card page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    data = {
        'url': url,
        'german_name': '',
        'set_id': '',
        'set_name': '',
        'card_number': '',
        'set_total': '',
        'hp': '',
        'energy_type': '',
        'stage': '',
        'rarity': '',
        'rarity_diamonds': '',
        'weakness_type': '',
        'weakness_damage': '',
        'retreat_energy': '',
        'retreat_cost': '',
        'illustrator': '',
        'pack_points': '',
        'release_date': '',
        'attacks': [],
    }
    
    # Extract from URL
    match = re.search(r'/de/card/[^/]+-([^-]+)$', url)
    if match:
        data['german_name'] = match.group(1).replace('-', ' ').title()
    
    # Get full page text
    text = soup.get_text()
    
    # Extract HP
    hp_match = re.search(r'(\d+)\s*KP', text)
    if hp_match:
        data['hp'] = hp_match.group(1)
    
    # Extract card number
    num_match = re.search(r'#\s*(\d+)\s*/\s*(\d+)', text)
    if num_match:
        data['card_number'] = num_match.group(1)
        data['set_total'] = num_match.group(2)
    
    # Extract energy type from icons
    energy_icons = soup.find_all('img', {'src': re.compile(r'eng-(lightning|fire|water|grass|psychic|fighting|darkness|metal|dragon|fairy|colorless)')})
    if energy_icons:
        for icon in energy_icons:
            src = icon.get('src', '')
            match = re.search(r'eng-(\w+)', src)
            if match:
                energy = match.group(1)
                # Check if this is the main energy type (first one)
                if not data['energy_type']:
                    data['energy_type'] = energy.capitalize()
    
    # Extract stage
    stage_match = re.search(r'Entwicklungsstufe.*?<strong>([^<]+)', text, re.DOTALL)
    if stage_match:
        data['stage'] = stage_match.group(1).strip()
    
    # Extract weakness with damage
    weak_section = soup.find(string=re.compile(r'Schwäche'))
    if weak_section:
        parent = weak_section.parent
        parent_text = parent.get_text() if parent else ''
        
        # Find weakness type icon
        weak_icon = parent.find('img', {'src': re.compile(r'eng-')}) if parent else None
        if weak_icon:
            src = weak_icon.get('src', '')
            match = re.search(r'eng-(\w+)', src)
            if match:
                data['weakness_type'] = match.group(1).capitalize()
        
        # Find damage value
        damage_match = re.search(r'\+(\d+)', parent_text)
        if damage_match:
            data['weakness_damage'] = damage_match.group(1)
    
    # Extract retreat cost
    retreat_section = soup.find(string=re.compile(r'Rückzugskosten'))
    if retreat_section:
        parent = retreat_section.parent
        parent_text = parent.get_text() if parent else ''
        
        # Find retreat icon
        retreat_icon = parent.find('img', {'src': re.compile(r'eng-')}) if parent else None
        if retreat_icon:
            src = retreat_icon.get('src', '')
            match = re.search(r'eng-(\w+)', src)
            if match:
                data['retreat_energy'] = match.group(1).capitalize()
        
        # Find retreat cost number
        cost_match = re.search(r'(\d+)\s*', parent_text)
        if cost_match:
            data['retreat_cost'] = cost_match.group(1)
    
    # Extract illustrator
    illust_match = re.search(r'Illustrator[:\s*]\*\*([^*]+)\*\*', text)
    if illust_match:
        data['illustrator'] = illust_match.group(1).strip()
    
    # Extract pack points
    points_match = re.search(r'(\d+)\s*Booster-Punkte', text)
    if points_match:
        data['pack_points'] = points_match.group(1)
    
    # Extract release date
    date_match = re.search(r'Verfügbar seit\s*(\d{2}/\d{2}/\d{4})', text)
    if date_match:
        data['release_date'] = date_match.group(1)
    
    # Extract attacks
    attack_headers = soup.find_all('h3', string=re.compile(r'Thunder|Shock|Attack|Crack|Bite|Strike|Punch|Slash|Blast|Burn|Freeze|Spark|Beam|Gust|Swift|Quick|Slam|Double|Hyper|Aqua|Solar|Psycho|Razor|Rock|Sand|Spike|Drain|Flail|Reversal|Takedown|Rollout|Icicle|Spark|Horn|Peck|Growl|Sing|Sleep|Powder|Spore|Stun|Switch|Retreat|Evade|Protect|Block|Rush|Press|Drive|Force|Reckless|Break|Impact|Crisis|Split|Various'))
    for header in attack_headers[:3]:
        attack_name = header.get_text().strip()
        
        # Find damage near this attack
        damage = ''
        sibling = header.find_next_sibling()
        if sibling:
            dmg_match = re.search(r'(\d+)\s*$', sibling.get_text())
            if dmg_match:
                damage = dmg_match.group(1)
        
        # Find energy cost icons
        energy_costs = []
        parent = header.parent
        if parent:
            icons = parent.find_all('img', {'src': re.compile(r'eng-')})
            for icon in icons[:4]:
                src = icon.get('src', '')
                match = re.search(r'eng-(\w+)', src)
                if match:
                    energy_costs.append(match.group(1).capitalize())
        
        # Find effect text
        effect = ''
        if sibling:
            effect = sibling.get_text().strip()
            # Remove damage number from effect
            effect = re.sub(r'\d+\s*$', '', effect).strip()
        
        data['attacks'].append({
            'name': attack_name,
            'damage': damage,
            'cost': energy_costs,
            'effect': effect
        })
    
    return data

def get_cards_from_set_page(set_id, set_slug):
    """Get all card URLs from a set page."""
    url = f"{BASE_URL}/de/set/{set_slug}"
    html = get_page(url)
    
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    
    # Find all card links
    links = soup.find_all('a', href=re.compile(r'/de/card/'))
    for link in links:
        href = link.get('href', '')
        if href and href not in cards:
            cards.append(href)
    
    return list(set(cards))

def main():
    print("=" * 60)
    print("Pokemon TCG Pocket - German Card Scraper (Simple)")
    print("=" * 60)
    
    all_cards = []
    
    # Step 1: Get all card URLs from all sets
    print("\n[1/2] Fetching card URLs from all sets...")
    
    for i, (set_id, set_slug, set_name) in enumerate(SETS):
        print(f"  Set {i+1}/{len(SETS)}: {set_id} ({set_name})...")
        cards = get_cards_from_set_page(set_id, set_slug)
        print(f"    -> Found {len(cards)} cards")
        all_cards.extend(cards)
        time.sleep(1)
    
    all_cards = list(set(all_cards))
    print(f"\nTotal cards: {len(all_cards)}")
    
    # Step 2: Parse each card
    print("\n[2/2] Parsing card details...")
    scraped_data = []
    
    for i, card_url in enumerate(all_cards):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(all_cards)}")
        
        full_url = card_url if card_url.startswith('http') else f"{BASE_URL}{card_url}"
        html = get_page(full_url)
        
        if html:
            data = parse_card_page(html, full_url)
            scraped_data.append(data)
        
        time.sleep(0.5)
    
    # Save
    with open('api/cache/german_cards_scraped.json', 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"Complete! Scraped {len(scraped_data)} cards")
    print(f"Saved to: api/cache/german_cards_scraped.json")
    print(f"{'=' * 60}")
    
    # Show sample
    if scraped_data:
        print("\nSample card:")
        print(json.dumps(scraped_data[0], indent=2, ensure_ascii=False)[:1000])

if __name__ == "__main__":
    main()
