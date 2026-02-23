#!/usr/bin/env python3
import os
import csv
import glob
import requests
import re
from PIL import Image
import pytesseract
from rapidfuzz import fuzz

UNCAPTURED_DIR = "screenshots/hard_to_capture"
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
        
        # Damage
        dmg_match = re.search(r'(\d{2,3})\s*$', text, re.MULTILINE)
        if dmg_match:
            dmg = int(dmg_match.group(1))
            if 10 <= dmg <= 150:
                features['damage'] = dmg
        
        # Weakness
        weak_match = re.search(r'(@\+?\d+)', text)
        if weak_match:
            features['weakness'] = weak_match.group(1)
        
        # Retreat
        retreat_match = re.search(r'(\d+)\s*Items\s*erhalten', text)
        if retreat_match:
            features['retreat'] = int(retreat_match.group(1))
        
        # Name
        for line in text.split('\n'):
            words = re.findall(r'([A-Z][a-z]+)', line)
            for w in words:
                if len(w) >= 4 and w not in ['Pokemon', 'Items', 'Will', 'Nicht', 'Dieses', 'Wenn', 'Basis', 'Nr']:
                    features['name'] = w
                    break
            if features.get('name'):
                break
        
        return features
    except:
        return None

def find_card(features, cards):
    if not features or (not features.get('name') and not features.get('hp')):
        return None, 0
    
    best, best_score = None, 0
    for card in cards:
        score = 0
        
        if features.get('hp') and card.get('health'):
            if features['hp'] == card['health']:
                score += 30
            elif abs(features['hp'] - card['health']) <= 10:
                score += 15
        
        if features.get('damage'):
            for atk in card.get('attacks', []):
                if atk.get('damage') and features['damage'] == int(atk.get('damage', 0)):
                    score += 20
                    break
        
        if features.get('name') and card.get('name'):
            score += fuzz.ratio(features['name'].lower(), card['name'].lower())
        
        if features.get('retreat') and card.get('retreatCost'):
            if features['retreat'] == card['retreatCost']:
                score += 15
        
        if score > best_score and score >= 20:
            best_score = score
            best = card
    
    return best, best_score

def main():
    cards_db = load_db()
    
    # Load existing cards
    existing = set()
    existing_data = []
    with open(OUTPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row['Card Name'])
            existing_data.append(row)
    print(f'Existing: {len(existing)} cards')
    
    # Process uncaptured
    screenshots = sorted(glob.glob(f'{UNCAPTURED_DIR}/*.png'))
    print(f'Processing {len(screenshots)} uncaptured screenshots...')
    
    new_cards = []
    
    for i, s in enumerate(screenshots):
        if i % 100 == 0:
            print(f'{i}/{len(screenshots)}')
        
        features = extract_features(s)
        card, score = find_card(features, cards_db)
        
        if card and card['name'] not in existing:
            existing.add(card['name'])
            
            # Get details
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
                        'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
                    }
                    new_cards.append(card_data)
                    
                    # Rename file
                    safe_name = re.sub(r'[^\w\-]', '_', card['name'])
                    new_name = f"{safe_name}_{card['set']}_{card['number']:03d}.png"
                    os.rename(s, os.path.join('screenshots/captured', new_name))
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
