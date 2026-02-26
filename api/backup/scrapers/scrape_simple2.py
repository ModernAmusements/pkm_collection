#!/usr/bin/env python3
"""
Simple German card scraper with Cloudflare bypass.
"""

import curl_cffi
from bs4 import BeautifulSoup
import re
import json
import time
import os

BASE_URL = 'https://pocket.pokemongohub.net'
OUTPUT_FILE = 'api/cache/german_cards_scraped_v2.json'

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

def parse_card_simple(html, url):
    """Simple card parser."""
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    data = {'url': url}
    
    # German name
    match = re.search(r'/de/card/[^/]+-([^-]+)$', url)
    if match:
        data['german_name'] = match.group(1).replace('-', ' ').title()
    
    # HP
    hp_match = re.search(r'(\d+)\s*KP', text)
    data['hp'] = hp_match.group(1) if hp_match else ''
    
    # Card number
    num_match = re.search(r'#\s*(\d+)\s*/\s*(\d+)', text)
    data['card_number'] = num_match.group(1) if num_match else ''
    
    # Energy type
    energy_match = re.search(r'Energie-Typ.*?/eng-(\w+)\.png', text)
    data['energy_type'] = energy_match.group(1).capitalize() if energy_match else ''
    
    # Stage
    stage_match = re.search(r'Entwicklungsstufe.*?<strong>([^<]+)', text, re.DOTALL)
    data['stage'] = stage_match.group(1).strip() if stage_match else ''
    
    # Rarity
    rarity_match = re.search(r'(\d+)-Diamant', text)
    data['rarity'] = f"{rarity_match.group(1)} Diamond" if rarity_match else ''
    
    # Weakness - look in text directly
    weak_match = re.search(r'Schw.*?/eng-(\w+).*?\+(\d+)', text, re.DOTALL)
    if weak_match:
        data['weakness'] = f"{weak_match.group(1).capitalize()}+{weak_match.group(2)}"
    else:
        # Try without damage
        weak_type_match = re.search(r'Schw.*?/eng-(\w+)', text)
        if weak_type_match:
            data['weakness'] = weak_type_match.group(1).capitalize()
    
    # Retreat
    retreat_match = re.search(r'Rückzugskosten.*?/eng-(\w+).*?(\d+)', text, re.DOTALL)
    if retreat_match:
        data['retreat'] = f"{retreat_match.group(2)}{retreat_match.group(1).capitalize()}"
    else:
        # Try without energy
        retreat_num_match = re.search(r'Rückzugskosten.*?(\d+)', text)
        if retreat_num_match:
            data['retreat'] = retreat_num_match.group(1)
    
    # Illustrator
    illust_match = re.search(r'Illustrator[:\s]*\*\*([^*]+)\*\*', text)
    data['illustrator'] = illust_match.group(1).strip() if illust_match else ''
    
    return data

def main():
    print("=" * 60)
    print("SIMPLE GERMAN SCRAPER")
    print("=" * 60)
    
    session = curl_cffi.Session(impersonate="chrome")
    
    # Warmup
    print("\n[1] Warming up...")
    session.get(BASE_URL + '/de', timeout=30)
    time.sleep(5)
    print("  OK")
    
    all_cards = []
    
    print("\n[2] Scraping...")
    for set_id, slug in SETS:
        print(f"\n  [{set_id}] Getting cards...", end=" ", flush=True)
        
        try:
            # Get set page
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
                        data = parse_card_simple(card_resp.text, card_url)
                        all_cards.append(data)
                except:
                    pass
                
                time.sleep(0.8)
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(3)
    
    # Save
    print(f"\n{'=' * 60}")
    print(f"COMPLETE! {len(all_cards)} cards")
    print(f"{'=' * 60}")
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_cards, f, indent=2)
    
    # Stats
    with_weak = len([c for c in all_cards if c.get('weakness')])
    with_retreat = len([c for c in all_cards if c.get('retreat')])
    print(f"With weakness: {with_weak}")
    print(f"With retreat: {with_retreat}")

if __name__ == "__main__":
    main()
