#!/usr/bin/env python3
import os
import csv
import glob
import requests
import re
from PIL import Image, ImageEnhance
import pytesseract
from rapidfuzz import fuzz
from rapidfuzz.process import cdist

UNCAPTURED_DIR = "screenshots/hard_to_capture"
CAPTURED_DIR = "screenshots/captured"
OUTPUT_CSV = "my_cards_full.csv"

# German to English Pokemon name mapping (common ones)
GERMAN_TO_ENGLISH = {
    'Arktos': 'Articuno',
    'Evoli': 'Eevee',
    'Glumanda': 'Charmander',
    'Glurak': 'Charizard',
    'Bisasam': 'Bulbasaur',
    'Bisaflor': 'Venusaur',
    'Pikachu': 'Pikachu',
    'Piepi': 'Pichu',
    'Mauzi': 'Meowth',
    'Rattfratz': 'Rattata',
    'Rattinaro': 'Raticate',
    'Habitak': 'Spearow',
    'Ibitak': 'Fearow',
    'Taubsi': 'Pidgey',
    'Tauboss': 'Pidgeot',
    'Karnimani': 'Mankey',
    'Torgamorus': 'Primeape',
    'Menki': 'Machop',
    'Masquain': 'Machoke',
    'Machollo': 'Machamp',
    'Geodude': 'Geodude',
    'Kleinstein': 'Geodude',
    'Onix': 'Onix',
    'Voltobal': 'Voltorb',
    'Lektrobal': 'Electrode',
    'Laufe': 'Magikarp',
    'Gyarados': 'Gyarados',
    'Lavados': 'Moltres',
    'Dratini': 'Dratini',
    'Dragonir': 'Dragonair',
    'Dragoran': 'Dragonite',
    'Mewtu': 'Mewtwo',
    'Mew': 'Mew',
    'Chimra': 'Chimchar',
    'Panferno': 'Monferno',
    'Panploon': 'Infernape',
    'Panpyra': 'Piplup',
    'Panpera': 'Prinplup',
    'Pantarus': 'Empoleon',
    'Schiggy': 'Squirtle',
    'Schillok': 'Wartortle',
    'Turtok': 'Blastoise',
}

def load_db():
    resp = requests.get('https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json', timeout=60)
    cards = resp.json()
    
    # Add German names to lookup
    for card in cards:
        # Store both English and potential German names
        card['search_names'] = [card['name'].lower()]
    
    return cards

def extract_features(path):
    try:
        img = Image.open(path)
        
        # Try multiple OCR settings
        texts = []
        
        # Original
        texts.append(pytesseract.image_to_string(img, config='--psm 6'))
        
        # Try with enhanced contrast
        gray = img.convert('L')
        texts.append(pytesseract.image_to_string(gray, config='--psm 6'))
        
        # Try different PSM
        texts.append(pytesseract.image_to_string(img, config='--psm 4'))
        
        # Combine best results
        features = {'hp': None, 'damage': None, 'name': None}
        
        for text in texts:
            # HP
            hp_match = re.search(r'(\d{2,3})\s*(?:KP|HP|@)', text, re.IGNORECASE)
            if hp_match and not features.get('hp'):
                hp = int(hp_match.group(1))
                if 30 <= hp <= 300:
                    features['hp'] = hp
            
            # Name - look for Pokemon-like words
            for line in text.split('\n'):
                words = re.findall(r'([A-Z][a-z]{3,})', line)
                for w in words:
                    if len(w) >= 4 and w not in ['Pokemon', 'Items', 'Will', 'Nicht', 'Dieses', 'Wenn', 'Basis', 'Attack', 'Gewicht', 'Schaden', 'Gegner']:
                        if not features.get('name'):
                            features['name'] = w
        
        return features
    except:
        return None

def find_card(features, cards):
    if not features:
        return None, 0
    
    best, best_score = None, 0
    
    for card in cards:
        score = 0
        
        # HP match - very important
        if features.get('hp') and card.get('health'):
            if features['hp'] == card['health']:
                score += 40
            elif abs(features['hp'] - card['health']) <= 10:
                score += 25
        
        # Name match - try English and German
        if features.get('name') and card.get('name'):
            name = features['name']
            
            # Direct match
            name_score = fuzz.ratio(name.lower(), card['name'].lower())
            
            # Check if it's a known German name
            if name in GERMAN_TO_ENGLISH:
                german_name = name
                english_name = GERMAN_TO_ENGLISH[name]
                name_score = max(name_score, fuzz.ratio(german_name.lower(), english_name.lower()))
            
            if name_score >= 40:
                score += name_score
        
        if score > best_score and score >= 30:
            best_score = score
            best = card
    
    return best, best_score

def main():
    cards_db = load_db()
    
    # Load existing
    existing = set()
    existing_data = []
    with open(OUTPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row['Card Name'].strip())
            existing_data.append(row)
    print(f'Existing: {len(existing)} cards')
    
    # Process
    screenshots = sorted(glob.glob(f'{UNCAPTURED_DIR}/*.png'))
    print(f'Processing {len(screenshots)} hard screenshots...')
    
    new_cards = []
    matched = 0
    
    for i, s in enumerate(screenshots):
        if i % 50 == 0:
            print(f'{i}/{len(screenshots)} - Found: {matched}')
        
        features = extract_features(s)
        card, score = find_card(features, cards_db)
        
        if card and card['name'] not in existing:
            existing.add(card['name'])
            matched += 1
            
            # Get details
            card_set = card["set"]
            card_num = card["number"]
            url = f"https://api.tcgdex.net/v2/en/cards/{card_set}-{card_num:03d}"
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    details = resp.json()
                    atks = details.get('attacks', [])
                    a1 = atks[0] if len(atks) > 0 else {}
                    a2 = atks[1] if len(atks) > 1 else {}
                    w = details.get('weaknesses', [])
                    
                    card_data = {
                        'Card Name': details.get('name', card['name']),
                        'HP': str(details.get('hp', card.get('health', ''))),
                        'Energy Type': details.get('types', [''])[0] if details.get('types') else card.get('element', '').capitalize(),
                        'Weakness': f"{w[0].get('type', '')} {w[0].get('value', '')}" if w else '',
                        'Resistance': '',
                        'Retreat Cost': str(details.get('retreat', card.get('retreatCost', ''))),
                        'Ability Name': '',
                        'Ability Description': details.get('description', '')[:200],
                        'Attack 1 Name': a1.get('name', ''),
                        'Attack 1 Cost': ','.join(a1.get('cost', [])) if a1.get('cost') else '',
                        'Attack 1 Damage': str(a1.get('damage', '')),
                        'Attack 1 Description': a1.get('effect', '')[:100] if a1.get('effect') else '',
                        'Attack 2 Name': a2.get('name', ''),
                        'Attack 2 Cost': ','.join(a2.get('cost', [])) if a2.get('cost') else '',
                        'Attack 2 Damage': str(a2.get('damage', '')),
                        'Attack 2 Description': a2.get('effect', '')[:100] if a2.get('effect') else '',
                        'Rarity': details.get('rarity', card.get('rarity', '')),
                        'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
                    }
                    new_cards.append(card_data)
                    
                    # Move to captured
                    safe_name = re.sub(r'[^\w\-]', '_', card['name'])
                    new_name = f"{safe_name}_{card['set']}_{card['number']:03d}.png"
                    os.rename(s, os.path.join(CAPTURED_DIR, new_name))
            except:
                pass
    
    print(f'Found {len(new_cards)} new cards')
    
    # Merge
    all_cards = existing_data + new_cards
    
    # Write
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_cards[0].keys())
        writer.writeheader()
        writer.writerows(all_cards)
    
    print(f'✅ Total: {len(all_cards)} unique cards')

if __name__ == "__main__":
    main()
