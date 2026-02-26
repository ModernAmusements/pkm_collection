#!/usr/bin/env python3
"""
German card scraper using curl_cffi to bypass Cloudflare.
"""

import curl_cffi
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
import os

BASE_URL = 'https://pocket.pokemongohub.net'
OUTPUT_FILE = 'api/cache/german_cards_complete.json'

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

def get_session():
    """Create curl_cffi session."""
    return curl_cffi.Session(impersonate="chrome")

def parse_card(html, url):
    """Parse a single card page."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    data = {'url': url}
    
    # German name from URL
    match = re.search(r'/de/card/[^/]+-([^-]+)$', url)
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
    
    # Weakness - use grandparent text directly
    weak_section = soup.find(string=re.compile(r'Schwäche'))
    if weak_section:
        parent = weak_section.parent
        grandparent = parent.parent if parent else None
        
        weak_type = ''
        if grandparent:
            grandparent_text = str(grandparent.get_text())
            # Find energy icon
            weak_icon = grandparent.find('img', src=re.compile(r'/eng-'))
            if weak_icon:
                src = str(weak_icon.get('src', ''))
                type_match = re.search(r'/eng-(\w+)', src)
                if type_match:
                    weak_type = type_match.group(1).capitalize()
            
            # Look for damage in text (format: "Schwäche+20")
            damage_match = re.search(r'\+(\d+)', grandparent_text)
            damage = damage_match.group(1) if damage_match else ''
            
            if weak_type:
                data['weakness'] = f"{weak_type}+{damage}" if damage else weak_type
    
    # Retreat - use grandparent text directly
    retreat_section = soup.find(string=re.compile(r'Rückzugskosten'))
    if retreat_section:
        parent = retreat_section.parent
        grandparent = parent.parent if parent else None
        
        retreat_energy = ''
        if grandparent:
            grandparent_text = str(grandparent.get_text())
            retreat_icon = grandparent.find('img', src=re.compile(r'/eng-'))
            if retreat_icon:
                src = str(retreat_icon.get('src', ''))
                type_match = re.search(r'/eng-(\w+)', src)
                if type_match:
                    retreat_energy = type_match.group(1).capitalize()
            
            # Look for cost number
            cost_match = re.search(r'(\d+)', grandparent_text)
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
    
    # Attacks
    attack_headers = soup.find_all('h3')
    attacks = []
    for header in attack_headers:
        name = header.get_text().strip()
        if name and len(name) < 50:
            damage = ''
            sibling = header.find_next_sibling()
            if sibling:
                dmg_match = re.search(r'(\d+)\s*$', sibling.get_text())
                if dmg_match:
                    damage = dmg_match.group(1)
            
            costs = []
            parent = header.parent
            if parent:
                icons = parent.find_all('img', src=re.compile(r'/eng-'))
                for icon in icons[:4]:
                    src = icon.get('src', '')
                    match = re.search(r'/eng-(\w+)', src)
                    if match:
                        costs.append(match.group(1).capitalize())
            
            attacks.append({'name': name, 'damage': damage, 'cost': costs})
    
    if attacks:
        data['attacks'] = attacks
    
    return data

def main():
    print("=" * 60)
    print("GERMAN CARD SCRAPER (Cloudflare Bypass)")
    print("=" * 60)
    
    session = get_session()
    
    # Warm up
    print("\n[1] Warming up session...")
    try:
        session.get(BASE_URL + '/de', timeout=30)
        time.sleep(2)
        print("  OK")
    except Exception as e:
        print(f"  Warning: {e}")
    
    # Get cards from each set
    print("\n[2] Scraping sets...")
    all_cards = []
    
    for set_id, slug in SETS:
        print(f"\n  [{set_id}] Getting cards...", end=" ", flush=True)
        
        try:
            url = f"{BASE_URL}/de/set/{slug}"
            resp = session.get(url, timeout=60)
            
            if resp.status_code != 200:
                print(f"Failed: {resp.status_code}")
                continue
            
            # Get card URLs
            matches = re.findall(r'/de/card/[^\"]+', resp.text)
            card_urls = list(set(matches))
            print(f"{len(card_urls)} cards")
            
            # Parse each card
            for i, card_url in enumerate(card_urls):
                if (i + 1) % 50 == 0:
                    print(f"    {i+1}/{len(card_urls)}")
                
                try:
                    card_resp = session.get(BASE_URL + card_url, timeout=30)
                    if card_resp.status_code == 200:
                        data = parse_card(card_resp.text, card_url)
                        all_cards.append(data)
                except:
                    pass
                
                time.sleep(0.2)
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(1)
    
    # Save
    print(f"\n{'=' * 60}")
    print(f"COMPLETE! Scraped {len(all_cards)} cards")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'=' * 60}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    
    # Sample
    if all_cards:
        print("\nSample:")
        for c in all_cards[:3]:
            print(f"  {c.get('german_name')}: HP={c.get('hp')}, Weak={c.get('weakness')}, Retreat={c.get('retreat')}")

if __name__ == "__main__":
    main()
