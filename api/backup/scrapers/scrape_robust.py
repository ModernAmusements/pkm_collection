#!/usr/bin/env python3
"""
Robust German card scraper with progress saving.
Run in background: nohup python3 api/scrape_robust.py &
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os
from datetime import datetime

BASE_URL = 'https://pocket.pokemongohub.net'
OUTPUT_FILE = 'api/cache/german_cards_robust.json'
PROGRESS_FILE = 'api/cache/scrape_progress.json'

SETS = [
    ("A1", "t3hb77i3xy08no0-unschlagbare-gene"),
    ("A1a", "bh6swrnbnb0xqp7-mysterise-insel"),
    ("A2", "i344270g8xo3wb9-kollision-von-raum-und-zeit"),
    ("A2a", "j6yh136n6ar7m1q-licht-des-triumphs"),
    ("A2b", "48r74kv8tun9j02-glnzendes-festival"),
    ("A3", "797ubb2z58mtxl1-hter-des-firmaments"),
    ("A3a", "n112zho988s4v74-extradimensional-crisis"),
    ("A3b", "0g49s62r1wb1p2b-evoli-hain"),
    ("A4", "h61dsk33evt45mp-weisheit-von-meer-und-himmel"),
    ("A4a", "h5n4a0fs0kvgztc-verborgene-quelle"),
    ("A4b", "dzswkhwwfk811kd-deluxepack-ex"),
    ("PROMO-A", "hrvgwu3dwxaboc7-promo-a"),
    ("PROMO-B", "vxunkwyap88g5jr-promo-b"),
    ("B1", "0guapr9h7we56l3-mega-aufstieg"),
    ("B1a", "t8vwgpxthcklr0n-crimson-blaze"),
]

def load_progress():
    """Load progress from file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed_sets': [], 'parsed_cards': [], 'last_update': None}

def save_progress(progress):
    """Save progress to file."""
    progress['last_update'] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def get_session():
    """Create session with headers."""
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })
    return s

def warmup_session(session):
    """Warm up session by visiting homepage."""
    try:
        session.get(BASE_URL + '/de', timeout=10)
        time.sleep(2)
        return True
    except:
        return False

def get_card_urls(session, set_id, slug):
    """Get card URLs from a set."""
    try:
        url = f"{BASE_URL}/de/set/{slug}"
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        
        matches = re.findall(r'/de/card/[^\"]+', resp.text)
        return list(set(matches))
    except Exception as e:
        print(f"  Error getting URLs for {set_id}: {e}")
        return []

def parse_card(session, card_url):
    """Parse a single card."""
    try:
        resp = session.get(BASE_URL + card_url, timeout=30)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        text = soup.get_text()
        
        data = {'url': card_url}
        
        # Name
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
        
        # Energy type
        energy_match = re.search(r'Energie-Typ.*?/eng-(\w+)\.png', text)
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
        
        # Weakness
        weak_section = soup.find(string=re.compile(r'Schwäche'))
        if weak_section:
            parent = weak_section.parent
            grandparent = parent.parent if parent else None
            
            weak_type = ''
            if grandparent:
                weak_icon = grandparent.find('img', src=re.compile(r'/eng-'))
                if weak_icon:
                    src = weak_icon.get('src', '')
                    type_match = re.search(r'/eng-(\w+)', src)
                    if type_match:
                        weak_type = type_match.group(1).capitalize()
            
            if parent:
                parent_text = parent.get_text()
                damage_match = re.search(r'\+(\d+)', parent_text)
                damage = damage_match.group(1) if damage_match else ''
                
                if weak_type:
                    data['weakness'] = f"{weak_type}+{damage}" if damage else weak_type
        
        # Retreat
        retreat_section = soup.find(string=re.compile(r'Rückzugskosten'))
        if retreat_section:
            parent = retreat_section.parent
            grandparent = parent.parent if parent else None
            
            retreat_energy = ''
            if grandparent:
                retreat_icon = grandparent.find('img', src=re.compile(r'/eng-'))
                if retreat_icon:
                    src = retreat_icon.get('src', '')
                    type_match = re.search(r'/eng-(\w+)', src)
                    if type_match:
                        retreat_energy = type_match.group(1).capitalize()
            
            if parent:
                parent_text = parent.get_text()
                cost_match = re.search(r'(\d+)', parent_text)
                cost = cost_match.group(1) if cost_match else ''
                
                if retreat_energy or cost:
                    data['retreat'] = f"{cost}{retreat_energy}" if retreat_energy else cost
        
        # Illustrator
        illust_match = re.search(r'Illustrator[:\s]*\*\*([^*]+)\*\*', text)
        if illust_match:
            data['illustrator'] = illust_match.group(1).strip()
        
        return data
        
    except Exception as e:
        return None

def main():
    print("=" * 60)
    print("ROBUST GERMAN CARD SCRAPER")
    print("=" * 60)
    
    # Load progress
    progress = load_progress()
    print(f"\nLoaded progress: {len(progress.get('parsed_cards', []))} cards parsed")
    
    # Create session
    session = get_session()
    
    # Warm up
    print("\nWarming up session...")
    if not warmup_session(session):
        print("WARNING: Session warmup failed, continuing anyway...")
    
    # Process sets
    all_cards = progress.get('parsed_cards', [])
    
    for set_id, slug in SETS:
        if set_id in progress.get('completed_sets', []):
            print(f"\n[{set_id}] Already completed, skipping")
            continue
            
        print(f"\n[{set_id}] Processing...")
        
        # Get card URLs
        card_urls = get_card_urls(session, set_id, slug)
        print(f"  Found {len(card_urls)} cards")
        
        if not card_urls:
            print(f"  WARNING: No cards found, may be blocked")
            time.sleep(10)
            continue
        
        # Parse cards
        set_cards = []
        for i, card_url in enumerate(card_urls):
            if (i + 1) % 25 == 0:
                print(f"    Progress: {i+1}/{len(card_urls)}")
            
            data = parse_card(session, card_url)
            if data:
                set_cards.append(data)
            
            time.sleep(0.3)  # Rate limit
        
        all_cards.extend(set_cards)
        progress['parsed_cards'] = all_cards
        progress['completed_sets'].append(set_id)
        
        # Save progress
        save_progress(progress)
        
        # Save to output file
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(all_cards, f, indent=2)
        
        print(f"  Parsed {len(set_cards)} cards, total: {len(all_cards)}")
        
        time.sleep(2)  # Delay between sets
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETE! Total cards: {len(all_cards)}")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
