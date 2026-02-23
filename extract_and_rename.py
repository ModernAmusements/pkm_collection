#!/usr/bin/env python3
import os
import csv
import glob
import requests
import re
from PIL import Image
import pytesseract
from rapidfuzz import fuzz

CAPTURED_DIR = "screenshots/captured"
OUTPUT_CSV = "my_cards_full.csv"

def load_db():
    resp = requests.get('https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json', timeout=60)
    return resp.json()

def extract_features(path):
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, config='--psm 6')
        
        features = {'hp': None, 'damage': None, 'name': None, 'weakness': None, 'retreat': None}
        
        # HP - German KP or number before @
        hp_match = re.search(r'(\d+)\s*(?:KP|HP|@)', text, re.IGNORECASE)
        if hp_match:
            hp = int(hp_match.group(1))
            if 30 <= hp <= 300:
                features['hp'] = hp
        
        # Damage - number at end of line
        dmg_match = re.search(r'(\d{2,3})\s*$', text, re.MULTILINE)
        if dmg_match:
            dmg = int(dmg_match.group(1))
            if 10 <= dmg <= 150:
                features['damage'] = dmg
        
        # Weakness value
        weak_match = re.search(r'(@\+?\d+)', text)
        if weak_match:
            features['weakness'] = weak_match.group(1)
        
        # Retreat - number before "Items erhalten"
        retreat_match = re.search(r'(\d+)\s*Items\s*erhalten', text)
        if retreat_match:
            features['retreat'] = int(retreat_match.group(1))
        
        # Name - capitalized word
        for line in text.split('\n'):
            words = re.findall(r'([A-Z][a-z]+)', line)
            for w in words:
                if len(w) >= 4 and w not in ['Pokemon', 'Items', 'Will', 'Nicht', 'Dieses', 'Wenn', 'Basis', 'Nr']:
                    features['name'] = w
                    break
            if features.get('name'):
                break
        
        return features
    except Exception as e:
        return None

def find_card(features, cards):
    if not features or (not features.get('name') and not features.get('hp')):
        return None, 0
    
    best, best_score = None, 0
    
    for card in cards:
        score = 0
        
        # HP match
        if features.get('hp') and card.get('health'):
            if features['hp'] == card['health']:
                score += 30
            elif abs(features['hp'] - card['health']) <= 10:
                score += 15
        
        # Damage match
        if features.get('damage'):
            for atk in card.get('attacks', []):
                if atk.get('damage') and features['damage'] == int(atk.get('damage', 0)):
                    score += 20
                    break
        
        # Name match
        if features.get('name') and card.get('name'):
            name_score = fuzz.ratio(features['name'].lower(), card['name'].lower())
            if name_score >= 50:
                score += name_score
        
        # Retreat match
        if features.get('retreat') and card.get('retreatCost'):
            if features['retreat'] == card['retreatCost']:
                score += 15
        
        if score > best_score and score >= 20:
            best_score = score
            best = card
    
    return best, best_score

def main():
    cards_db = load_db()
    
    # Get all screenshots
    screenshots = sorted(glob.glob(f'{CAPTURED_DIR}/*.png'))
    print(f'Processing {len(screenshots)} screenshots...')
    
    results = []
    
    for i, s in enumerate(screenshots):
        if i % 50 == 0:
            print(f'{i}/{len(screenshots)}')
        
        features = extract_features(s)
        card, score = find_card(features, cards_db)
        
        if card:
            # Get full details from API
            url = f'https://api.tcgdex.net/v2/en/cards/{card["set"]}-{card["number"]:03d}'
            try:
                resp = requests.get(url, timeout=10)
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
                        'Attack 1 Description': '',
                        'Attack 2 Name': a2.get('name', ''),
                        'Attack 2 Cost': ','.join(a2.get('cost', [])) if a2.get('cost') else '',
                        'Attack 2 Damage': str(a2.get('damage', '')),
                        'Attack 2 Description': '',
                        'Rarity': details.get('rarity', card.get('rarity', '')),
                        'Pack': card.get('packs', [''])[0] if card.get('packs') else '',
                        'Source File': os.path.basename(s),
                        'Match Score': score
                    }
                    results.append(card_data)
                    
                    # Rename file to card name
                    safe_name = re.sub(r'[^\w\-]', '_', card['name'])
                    new_name = f"{safe_name}_{card['set']}_{card['number']:03d}.png"
                    new_path = os.path.join(CAPTURED_DIR, new_name)
                    
                    counter = 1
                    while os.path.exists(new_path):
                        new_name = f"{safe_name}_{card['set']}_{card['number']:03d}_{counter}.png"
                        new_path = os.path.join(CAPTURED_DIR, new_name)
                        counter += 1
                    
                    os.rename(s, new_path)
            except Exception as e:
                pass
    
    print(f'\nExtracted: {len(results)} cards')
    
    # Write CSV
    if results:
        fieldnames = [k for k in results[0].keys() if k not in ['Source File', 'Match Score']]
        fieldnames.extend(['Source File', 'Match Score'])
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        
        print(f'CSV saved: {OUTPUT_CSV}')

if __name__ == "__main__":
    main()
