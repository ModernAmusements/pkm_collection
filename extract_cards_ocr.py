#!/usr/bin/env python3
import os
import csv
import re
import glob
import requests
from collections import Counter
from PIL import Image
import pytesseract

SCREENSHOT_DIR = "screenshots/20260221_225701"
OUTPUT_CSV = "my_cards_full.csv"

CARD_DB_URL = "https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json"

card_cache = {}

def load_card_database():
    print("Loading card database...")
    resp = requests.get(CARD_DB_URL, timeout=60)
    cards = resp.json()
    
    for card in cards:
        name = card.get('name', '')
        if name:
            if name not in card_cache:
                card_cache[name] = []
            card_cache[name].append(card)
    
    print(f"Loaded {len(card_cache)} unique card names")
    return card_cache

def get_tcgdex_card(set_id, card_num):
    card_id = f"{set_id}-{card_num:03d}"
    url = f"https://api.tcgdex.net/v2/en/cards/{card_id}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def extract_card_names():
    screenshot_files = sorted(glob.glob(os.path.join(SCREENSHOT_DIR, "screenshot_*.png")))
    
    # Process all screenshots
    detail_files = screenshot_files
    
    print(f"Processing {len(detail_files)} detail screenshots...")
    
    all_names = []
    skip_words = ['Nr', 'Items', 'Pokemon', 'Gewicht', 'Gr', 'Gemeinsam', 'Dieses', 'Wenn', 'Dieser', 'Diese', 
                  'Wird', 'Dies', 'Punkte', 'GPItemserhalten', 'GGPtemserhalten', 'Schwiche', 'Bmem', 'Igastarnish',
                  'Bsmone', 'GGPtemserhatten']
    
    for i, f in enumerate(detail_files):
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1}/{len(detail_files)}...")
        
        try:
            img = Image.open(f)
            w, h = img.size
            
            # Crop bottom portion where card name appears
            crop = img.crop((0, h - 400, w, h))
            text = pytesseract.image_to_string(crop, config='--psm 6')
            
            # Get all lines and look for potential names
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                clean = ''.join(c for c in line if c.isalpha() or c == '-' or c == ' ')
                clean = clean.strip()
                
                if 3 <= len(clean) <= 18 and clean[0].isupper():
                    # Skip common non-card words
                    if not any(clean.startswith(s) or clean == s for s in skip_words):
                        # Clean up
                        clean = clean.split()[0] if ' ' in clean else clean
                        if len(clean) >= 3:
                            all_names.append(clean)
        except Exception as e:
            pass
    
    return all_names

def find_matching_cards(names, card_db):
    from rapidfuzz import fuzz
    
    matched_cards = []
    seen = set()
    
    # Also create a reverse index for matching with common variations
    name_to_db = {}
    for db_name in card_db:
        # Direct lowercase
        name_to_db[db_name.lower()] = db_name
        # Without hyphens
        name_to_db[db_name.lower().replace('-', '')] = db_name
        # Without spaces
        name_to_db[db_name.lower().replace(' ', '')] = db_name
        # Alolan variants
        if 'alolan' in db_name.lower():
            name_to_db[db_name.lower().replace('alolan ', 'alola-')] = db_name
        # Galarian variants  
        if 'galarian' in db_name.lower():
            name_to_db[db_name.lower().replace('galarian ', 'galar-')] = db_name
    
    for name in names:
        name_clean = name.lower().replace('-', '').replace(' ', '')
        
        # Direct match
        if name in card_db:
            for card in card_db[name]:
                key = f"{card['set']}-{card['number']:03d}"
                if key not in seen:
                    matched_cards.append((key, card))
                    seen.add(key)
            continue
        
        if name_clean in name_to_db:
            db_name = name_to_db[name_clean]
            for card in card_db[db_name]:
                key = f"{card['set']}-{card['number']:03d}"
                if key not in seen:
                    matched_cards.append((key, card))
                    seen.add(key)
            continue
        
        # Fuzzy match with lower threshold
        best_match = None
        best_score = 0
        
        for db_name in card_db:
            score = fuzz.ratio(name.lower(), db_name.lower())
            if score > best_score:
                best_score = score
                best_match = db_name
        
        if best_score >= 50 and best_match:
            for card in card_db[best_match]:
                key = f"{card['set']}-{card['number']:03d}"
                if key not in seen:
                    matched_cards.append((key, card))
                    seen.add(key)
    
    return matched_cards

def main():
    card_db = load_card_database()
    
    # Extract names
    names = extract_card_names()
    name_counts = Counter(names)
    print(f"\nExtracted {len(name_counts)} unique name candidates")
    
    # Print top candidates
    print("\nTop 30 extracted names:")
    for name, count in name_counts.most_common(30):
        print(f"  {name}: {count}")
    
    # Match cards
    matched = find_matching_cards(name_counts.keys(), card_db)
    print(f"\nMatched {len(matched)} unique cards from database")
    
    # Fetch details and write CSV
    all_cards_data = []
    
    for i, (key, card) in enumerate(matched):
        if (i + 1) % 20 == 0:
            print(f"Fetching details {i + 1}/{len(matched)}...")
        
        set_id = card['set']
        card_num = card['number']
        
        details = get_tcgdex_card(set_id, card_num)
        
        if details:
            attacks = details.get('attacks', [])
            attack1 = attacks[0] if len(attacks) > 0 else {}
            attack2 = attacks[1] if len(attacks) > 1 else {}
            
            weaknesses = details.get('weaknesses', [])
            weakness_str = ""
            if weaknesses:
                w = weaknesses[0]
                weakness_str = f"{w.get('type', '')} {w.get('value', '')}"
            
            card_data = {
                'Card Name': details.get('name', card.get('name', '')),
                'HP': str(details.get('hp', card.get('health', ''))),
                'Energy Type': details.get('types', [''])[0] if details.get('types') else card.get('element', '').capitalize(),
                'Weakness': weakness_str,
                'Resistance': '',
                'Retreat Cost': str(details.get('retreat', card.get('retreatCost', ''))),
                'Ability Name': '',
                'Ability Description': details.get('description', '')[:200],
                'Attack 1 Name': attack1.get('name', ''),
                'Attack 1 Cost': ', '.join(attack1.get('cost', [])) if attack1.get('cost') else '',
                'Attack 1 Damage': str(attack1.get('damage', '')),
                'Attack 1 Description': '',
                'Attack 2 Name': attack2.get('name', ''),
                'Attack 2 Cost': ', '.join(attack2.get('cost', [])) if attack2.get('cost') else '',
                'Attack 2 Damage': str(attack2.get('damage', '')),
                'Attack 2 Description': '',
                'Rarity': details.get('rarity', card.get('rarity', '')),
                'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
            }
            all_cards_data.append(card_data)
        else:
            card_data = {
                'Card Name': card.get('name', ''),
                'HP': str(card.get('health', '')),
                'Energy Type': card.get('element', '').capitalize(),
                'Weakness': card.get('weakness', ''),
                'Resistance': '',
                'Retreat Cost': str(card.get('retreatCost', '')),
                'Ability Name': '',
                'Ability Description': '',
                'Attack 1 Name': '',
                'Attack 1 Cost': '',
                'Attack 1 Damage': '',
                'Attack 1 Description': '',
                'Attack 2 Name': '',
                'Attack 2 Cost': '',
                'Attack 2 Damage': '',
                'Attack 2 Description': '',
                'Rarity': card.get('rarity', ''),
                'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
            }
            all_cards_data.append(card_data)
    
    if not all_cards_data:
        print("No cards extracted!")
        return
    
    # Write CSV
    fieldnames = ['Card Name', 'HP', 'Energy Type', 'Weakness', 'Resistance', 'Retreat Cost', 
                  'Ability Name', 'Ability Description', 
                  'Attack 1 Name', 'Attack 1 Cost', 'Attack 1 Damage', 'Attack 1 Description',
                  'Attack 2 Name', 'Attack 2 Cost', 'Attack 2 Damage', 'Attack 2 Description',
                  'Rarity', 'Pack']
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_cards_data)
    
    print(f"\nDone! Extracted {len(all_cards_data)} cards to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
