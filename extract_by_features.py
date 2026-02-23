#!/usr/bin/env python3
import os
import csv
import re
import glob
import requests
from PIL import Image
import pytesseract
from rapidfuzz import fuzz

SCREENSHOT_DIR = "screenshots/captured"
OUTPUT_CSV = "my_cards_full.csv"

def load_db():
    resp = requests.get('https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json', timeout=60)
    return resp.json()

def extract_features(path):
    img = Image.open(path)
    text = pytesseract.image_to_string(img, config='--psm 6')
    
    features = {
        'hp': None,
        'damage': None,
        'weakness_type': None,
        'weakness_value': None,
        'retreat': None,
        'name': None,
        'stage': None
    }
    
    # HP - look for number before KP or HP
    hp_match = re.search(r'(\d+)\s*(?:KP|HP)', text, re.IGNORECASE)
    if hp_match:
        hp = int(hp_match.group(1))
        if 30 <= hp <= 300:
            features['hp'] = hp
    
    # Card Number - look for Nr. XXX pattern
    nr_match = re.search(r'Nr\.\s*(\d+)', text)
    if nr_match:
        features['card_nr'] = nr_match.group(1)
    
    # Damage - look for attack name followed by number
    dmg_match = re.search(r'([A-Za-z]+)\s+(\d{2,3})\s*$', text, re.MULTILINE)
    if dmg_match:
        dmg = int(dmg_match.group(2))
        if 10 <= dmg <= 200:
            features['damage'] = dmg
    
    # Weakness - German: Schwäche +20 Feuer
    weak_val_match = re.search(r'(@\+?\d+|[✕×]\d+)', text)
    if weak_val_match:
        features['weakness_value'] = weak_val_match.group(1)
    
    weak_types = ['Feuer', 'Fire', 'Wasser', 'Water', 'Pflanze', 'Grass', 
                  'Elektro', 'Electric', 'Psycho', 'Psychic', 'Kampf', 'Fighting',
                  'Unlicht', 'Darkness', 'Metall', 'Metal', 'Drache', 'Dragon', 'Fee', 'Fairy']
    for wt in weak_types:
        if wt.lower() in text.lower():
            features['weakness_type'] = wt
            break
    
    # Retreat - German: number before "Items erhalten"
    retreat_match = re.search(r'(\d+)\s*(?:GP\s*)?Items\s+erhalten', text)
    if retreat_match:
        features['retreat'] = int(retreat_match.group(1))
    
    # Stage - German: Basic = Basis
    if 'Basis' in text or 'basis' in text.lower():
        features['stage'] = 'basic'
    elif 'Phase 1' in text or 'Phase 2' in text:
        features['stage'] = 'stage1'
    
    # Name - look for Pokemon name (capitalized word)
    for line in text.split('\n'):
        words = re.findall(r'([A-Z][a-z]+)', line)
        for w in words:
            if len(w) >= 4 and w not in ['Pokemon', 'Items', 'Will', 'Nicht', 'Dieses', 'Wenn', 'Basis', 'Phase', 'Nr']:
                features['name'] = w
                break
        if features.get('name'):
            break
    
    return features

def find_card(features, cards):
    if not features:
        return None
    
    best, best_score = None, 0
    
    for card in cards:
        score = 0
        
        # Match HP
        if features.get('hp') and card.get('health'):
            if features['hp'] == card['health']:
                score += 30
            elif abs(features['hp'] - card['health']) <= 10:
                score += 15
        
        # Match retreat
        if features.get('retreat') and card.get('retreatCost'):
            if features['retreat'] == card['retreatCost']:
                score += 20
        
        # Match weakness type
        if features.get('weakness_type') and card.get('weakness'):
            if features['weakness_type'].lower() in card['weakness'].lower():
                score += 15
        
        # Match name
        if features.get('name') and card.get('name'):
            name_score = fuzz.ratio(features['name'].lower(), card['name'].lower())
            if name_score >= 50:
                score += name_score / 3
        
        if score > best_score and score >= 20:
            best_score = score
            best = card
    
    return best

def get_details(set_id, num):
    url = f'https://api.tcgdex.net/v2/en/cards/{set_id}-{num:03d}'
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def main():
    cards_db = load_db()
    screenshots = sorted(glob.glob(f'{SCREENSHOT_DIR}/*.png'))
    
    print(f'Processing {len(screenshots)} screenshots...')
    
    extracted = []
    seen = set()
    
    for i, s in enumerate(screenshots):
        if i % 50 == 0:
            print(f'{i}/{len(screenshots)}')
        
        features = extract_features(s)
        
        if features.get('name') or features.get('hp'):
            card = find_card(features, cards_db)
            if card:
                key = f"{card['set']}-{card['number']}"
                if key not in seen:
                    seen.add(key)
                    details = get_details(card['set'], card['number'])
                    if details:
                        atks = details.get('attacks', [])
                        a1 = atks[0] if len(atks) > 0 else {}
                        a2 = atks[1] if len(atks) > 1 else {}
                        w = details.get('weaknesses', [])
                        
                        extracted.append({
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
                            'Attack 1 Description': '',
                            'Attack 2 Name': a2.get('name', ''),
                            'Attack 2 Cost': ','.join(a2.get('cost', [])) if a2.get('cost') else '',
                            'Attack 2 Damage': str(a2.get('damage', '')),
                            'Attack 2 Description': '',
                            'Rarity': details.get('rarity', card.get('rarity', '')),
                            'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
                        })
    
    # Write CSV
    if extracted:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=extracted[0].keys())
            writer.writeheader()
            writer.writerows(extracted)
    
    print(f'\n✅ Extracted: {len(extracted)} cards')

if __name__ == "__main__":
    main()
