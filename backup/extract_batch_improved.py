#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor - IMPROVED VERSION
- Uses chase-manning/pokemon-tcg-pocket-cards API for better coverage
- Multiple OCR attempts with different contrast levels and languages
- Comprehensive card detection with multiple fallback strategies
- 99% success rate target
"""

import os
import re
import csv
import glob
import sys
import json
import time
import requests
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

# === CONFIG ===
SCREENSHOT_DIR = "screenshots/to_process"
CAPTURED_DIR = "screenshots/captured"
FAILED_DIR = "screenshots/failed_to_capture"
OUTPUT_CSV = "my_cards_full.csv"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25

# Use TCGdex API for complete card data
API_BASE = "https://api.tcgdex.net/v2/de/cards"
API_CACHE = {}

# TCG Pocket sets
TCGP_SETS = ['A1', 'A1a', 'A2', 'A2a', 'A2b', 'A3', 'A3a', 'A3b', 'A4', 'A4a', 'Pikachu', 'PA']

# === PREPROCESSING CONFIG ===
CROP_SIDES = 0.085  # 8.5% from each side
CROP_HEIGHT = 555   # Fixed height
SCALE = 4  # Scale factor for OCR (increased from 3)

# Pokemon card zones in order from TOP to BOTTOM (heights in pixels)
ZONES_POKEMON = {
    1: (0, 55),      # Phase + Name + KP + Energy
    2: (55, 65),      # Evolution
    3: (65, 263),     # Artwork
    4: (263, 282),    # Card Number
    5: (282, 475),    # Attacks & Abilities
    6: (475, 494),   # Weakness + Retreat
    7: (494, 555),   # Info (not needed)
}

# Trainer card zones (different layout)
ZONES_TRAINER = {
    1: (0, 41),       # Type (Item, Stadium, Unterstützung)
    2: (41, 81),      # Name
    3: (81, 289),     # Description/Effect
    4: (289, 480),    # Special rules
    5: (480, 554),    # Extra (not used)
}

# Crop percentages (based on original image)
CROP = {
    'top': 0.14,      # 14% from top
    'bottom': 0.32,    # 32% from bottom
    'sides': 0.085,   # 8.5% from each side
}

# === FUNCTIONS ===

def search_card_api(name_or_id):
    """Search TCGdex API for card by name or ID"""
    if name_or_id in API_CACHE:
        return API_CACHE[name_or_id]
    
    url = f"{API_BASE}/{name_or_id}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            card = resp.json()
            API_CACHE[name_or_id] = card
            return card
    except Exception as e:
        print(f"  [API] Error: {e}")
    return None


def search_cards_by_name(name):
    """Search TCGdex API for cards by name - returns list"""
    cache_key = f"search:{name.lower()}"
    if cache_key in API_CACHE:
        return API_CACHE[cache_key]
    
    url = f"{API_BASE}?name={name}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            cards = resp.json()
            # Filter for TCG Pocket sets
            tcgp_cards = [c for c in cards if c.get('id', '').split('-')[0] in TCGP_SETS]
            API_CACHE[cache_key] = tcgp_cards
            return tcgp_cards
    except Exception as e:
        print(f"  [API] Search error: {e}")
    return []


def load_card_by_id(set_id, card_num):
    """Load card by set ID and number"""
    # Convert card_num to int if it's a string
    if isinstance(card_num, str):
        try:
            card_num = int(card_num)
        except ValueError:
            card_num = 1
    card_id = f"{set_id}-{card_num:03d}"
    return search_card_api(card_id)


def preprocess_image(image_path):
    """Crop sides, crop to 555px height, return image ready for zone extraction"""
    img = Image.open(image_path)
    w, h = img.size
    
    # Step 0: Detect and fix orientation
    # If width > height, the card is rotated 90°
    if w > h:
        img = img.rotate(-90, expand=True)
        w, h = h, w  # Swap dimensions
    
    # Step 1: Crop sides (8.5% from each side)
    left = int(w * CROP_SIDES)
    right = w - left
    img = img.crop((left, 0, right, h))
    
    # Step 2: Crop to 555px height from top (14% from top)
    top = int(h * 0.14)
    img = img.crop((0, top, img.width, top + CROP_HEIGHT))
    
    # Now img is 555px height, return it
    return img


def extract_zone(img, zone_num, is_trainer=False):
    """Extract a zone at 555px size, scale for OCR"""
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    if zone_num not in zones:
        return None
    w, h = img.size  # h should be 555
    y1, y2 = zones[zone_num]
    zone = img.crop((0, y1, w, y2))
    # Scale 4x for better OCR
    return zone.resize((zone.width * SCALE, zone.height * SCALE))


def ocr_zone(zone_img, contrast_levels=[2.0, 2.5, 3.0], languages=['deu', 'eng']):
    """OCR a zone - try multiple methods for better text extraction"""
    if zone_img is None:
        return None
    
    # Try multiple contrast levels and languages
    for contrast in contrast_levels:
        gray = zone_img.convert('L')
        gray = ImageEnhance.Contrast(gray).enhance(contrast)
        
        for lang in languages:
            try:
                text = pytesseract.image_to_string(gray, lang=lang)
                text = text.strip()
                if text and len(text) > 2:
                    return text, lang, contrast
            except:
                continue
    
    return None, None, None


def has_text(zone_img):
    """Check if zone has readable text"""
    text, _, _ = ocr_zone(zone_img)
    return text is not None and len(text) > 2


def detect_card_type(img):
    """Detect if card is Trainer or Pokemon based on Zone 1 text"""
    # Try Pokemon zone 1 (0-55px)
    zone1 = extract_zone(img, 1, is_trainer=False)
    if zone1:
        text, lang, contrast = ocr_zone(zone1, contrast_levels=[2.5, 3.0], languages=['deu', 'eng'])
        if text:
            print(f"  [DEBUG] Zone1 Pokemon OCR: {text[:60]}")
            
            # Pokemon indicators: HP/KP, Energy symbols, Pokemon names
            if 'KP' in text.upper() or 'HP' in text.upper():
                return False
    
    # Try Trainer zone 1 (0-41px) as fallback
    zone1_trn = extract_zone(img, 1, is_trainer=True)
    if zone1_trn:
        text, lang, contrast = ocr_zone(zone1_trn, contrast_levels=[2.5, 3.0], languages=['deu', 'eng'])
        if text:
            print(f"  [DEBUG] Zone1 Trainer OCR: {text[:60]}")
            
            trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL', 'ITEM']
            for keyword in trainer_keywords:
                if keyword in text.upper():
                    return True
    
    # Default to Pokemon if uncertain
    return False


def extract_card_number(text):
    """Extract card number from text like 'Nr. 123' or '123'"""
    if not text:
        return None
    
    # Look for patterns like 'Nr. 123', '123', 'Card 456'
    patterns = [
        r'Nr\.?\s*(\d+)',
        r'(\d+)',
        r'Card\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return None


def search_card_by_name(name):
    """Search API for card by name - returns full card data"""
    if not name:
        return None
    
    name_lower = name.lower().strip()
    
    # Search by name
    cards = search_cards_by_name(name_lower)
    if cards:
        return cards[0]
    
    # Try partial matches
    all_cards = search_cards_by_name('')
    for card in all_cards[:100]:
        card_name = card.get('name', '').lower()
        if name_lower in card_name:
            return card
    
    return None


def search_card_by_number(set_id, card_num):
    """Search API for card by set and number"""
    return load_card_by_id(set_id, card_num)


def extract_card_info_from_zones(img, is_trainer=False):
    """Extract detailed card information from zones"""
    card_info = {
        'name': '',
        'hp': '',
        'type': '',
        'attacks': [],
        'ability': {},
        'weakness': '',
        'resistance': '',
        'retreat': '',
        'category': '',
        'rarity': '',
        'pack': '',
    }
    
    # Extract from Zone 1 (Pokemon: name + HP + Energy, Trainer: type + name)
    zone1 = extract_zone(img, 1, is_trainer)
    if zone1:
        text, lang, contrast = ocr_zone(zone1, contrast_levels=[2.5, 3.0], languages=['deu', 'eng'])
        if text:
            print(f"  [DEBUG] Zone1 OCR: {text[:60]}")
            
            if not is_trainer:
                # Extract name and HP from "Name 100"
                match = re.search(r'([\w\s\p{Pd}]+)\s+(\d+)', text)
                if match:
                    card_info['name'] = match.group(1).strip()
                    card_info['hp'] = match.group(2).strip()
                else:
                    # Try simpler extraction
                    words = text.split()
                    if len(words) >= 2:
                        card_info['name'] = ' '.join(words[:-1])
                        card_info['hp'] = words[-1]
            else:
                # Trainer card - extract type and name
                words = text.split()
                if len(words) >= 2:
                    card_info['category'] = words[0]
                    card_info['name'] = ' '.join(words[1:])
    
    # Extract from Zone 5 (Pokemon: attacks/abilities, Trainer: special rules)
    zone5 = extract_zone(img, 5, is_trainer)
    if zone5:
        text, lang, contrast = ocr_zone(zone5, contrast_levels=[2.5, 3.0], languages=['deu', 'eng'])
        if text:
            print(f"  [DEBUG] Zone5 OCR: {text[:100]}")
            
            if not is_trainer:
                # Look for ability first (usually starts with "Wenn" or "If")
                ability_match = re.search(r'(wenn|if|ability|ability:|fähigkeit|fähigkeit:|\*\*)(.+?)(?=\*\*|$)', text, re.IGNORECASE)
                if ability_match:
                    card_info['ability'] = {
                        'name': ability_match.group(1).strip(),
                        'effect': ability_match.group(2).strip()
                    }
                
                # Look for attacks (usually have damage numbers)
                attack_patterns = [
                    r'([\w\s\-\(\)\u2019]+?)\s*(\d+\+?)\s*(\w*)\s*(.*?)(?=\*\*|$)',
                    r'([\w\s\-\(\)\u2019]+?)\s*(\d+\+?)\s*(\w*)\s*(.*?)(?=\*\*|$)',
                ]
                
                for pattern in attack_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        attack_name = match[0].strip()
                        attack_damage = match[1].strip()
                        attack_cost = match[2].strip()
                        attack_effect = match[3].strip()
                        
                        # Clean up attack name (remove "Attack" prefix)
                        if 'attack' in attack_name.lower():
                            attack_name = attack_name.lower().replace('attack', '').strip()
                        
                        card_info['attacks'].append({
                            'name': attack_name,
                            'damage': attack_damage,
                            'cost': [attack_cost] if attack_cost else [],
                            'effect': attack_effect
                        })
            else:
                # Trainer card - extract special rules
                card_info['ability'] = {
                    'name': 'Special Rule',
                    'effect': text.strip()
                }
    
    # Extract from Zone 4 (Card number)
    zone4 = extract_zone(img, 4, is_trainer)
    if zone4:
        text, lang, contrast = ocr_zone(zone4, contrast_levels=[2.5, 3.0], languages=['deu', 'eng'])
        if text:
            print(f"  [DEBUG] Zone4 OCR: {text[:60]}")
            # Extract card number if available
            num_match = re.search(r'Nr\.?\s*(\d+)', text, re.IGNORECASE)
            if num_match:
                card_info['number'] = num_match.group(1).strip()
    
    return card_info


def process_card(image_path):
    """Process a single card with detailed extraction"""
    filename = os.path.basename(image_path)
    print(f"\n[Processing] {filename}")
    
    # Preprocess
    img = preprocess_image(image_path)
    
    # Detect card type
    is_trainer = detect_card_type(img)
    print(f"  -> Detected: {'Trainer' if is_trainer else 'Pokemon'}")
    
    # Extract detailed card information from zones
    card_info = extract_card_info_from_zones(img, is_trainer)
    
    # Try to find card by name if we have it
    if card_info['name']:
        card_data = search_card_by_name(card_info['name'])
        if card_data:
            print(f"  [API] Found: {card_info['name']} -> {card_data.get('name')}")
            # Update with API data
            card_info.update({
                'id': card_data.get('id', ''),
                'rarity': card_data.get('rarity', ''),
                'set': card_data.get('set', {}).get('name', ''),
                'types': card_data.get('types', []),
                'hp': card_data.get('hp', ''),
                'weaknesses': card_data.get('weaknesses', []),
                'retreat': card_data.get('retreat', ''),
                'attacks': card_data.get('attacks', []),
                'abilities': card_data.get('abilities', []),
                'stage': card_data.get('stage', ''),
                'category': card_data.get('category', ''),
            })
        else:
            print(f"  [API] Could not find: {card_info['name']}")
    
    if not card_info['name']:
        print(f"  [ERROR] Could not extract card name")
        return False, None
    
    # Get card info
    card_id = card_info.get('id', '')
    set_id, card_num = card_id.split('-') if '-' in card_id else ('', 0)
    try:
        card_num = int(card_num) if card_num.isdigit() else 0
    except:
        card_num = 0
    
    # Handle duplicates
    new_filename = f"{card_info['name']}_{set_id}_{card_num}.png"
    new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    dup = 1
    while os.path.exists(new_path):
        dup += 1
        new_filename = f"{card_info['name']}_{set_id}_{card_num}_{dup-1}.png"
        new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    # Move file
    os.rename(image_path, new_path)
    
    # Append to CSV
    append_to_csv(card_info)
    
    print(f"  [SUCCESS] {card_info['name']} ({set_id}-{card_num})")
    
    return True, {
        'filename': new_filename,
        'name': card_info.get('name', ''),
        'set': card_info.get('set', ''),
        'set_id': set_id,
        'card_num': card_num,
        'hp': card_info.get('hp', ''),
        'energy': card_info.get('types', []),
        'rarity': card_info.get('rarity', ''),
        'stage': card_info.get('stage', ''),
    }


def append_to_csv(card_data):
    """Append a single card to CSV with all available information"""
    file_exists = os.path.exists(OUTPUT_CSV)
    
    # Extract all available card data from API
    name = card_data.get('name', '')
    card_id = card_data.get('id', '')
    
    # Attacks (up to 2)
    attacks = card_data.get('attacks', [])
    attack1 = attacks[0] if len(attacks) > 0 else {}
    attack2 = attacks[1] if len(attacks) > 1 else {}
    
    # Abilities (if exists)
    abilities = card_data.get('abilities', [])
    ability = abilities[0] if abilities else {}
    
    # Weakness
    weaknesses = card_data.get('weaknesses', [])
    weakness = ''
    if weaknesses:
        w = weaknesses[0]
        weakness = f"{w.get('type', '')} {w.get('value', '')}"
    
    # Types/Energy
    types = card_data.get('types', [])
    energy_type = ', '.join(types) if types else ''
    
    # Retreat cost
    retreat = card_data.get('retreat', '')
    if retreat:
        retreat = str(retreat)
    
    card = {
        'Card Name': name,
        'HP': card_data.get('hp', ''),
        'Energy Type': energy_type,
        'Weakness': weakness,
        'Resistance': '',
        'Retreat Cost': retreat,
        'Category': card_data.get('category', ''),
        'Ability Name': ability.get('name', ''),
        'Ability Description': ability.get('effect', ''),
        'Attack 1 Name': attack1.get('name', ''),
        'Attack 1 Cost': ', '.join(attack1.get('cost', [])),
        'Attack 1 Damage': attack1.get('damage', ''),
        'Attack 1 Description': attack1.get('effect', ''),
        'Attack 2 Name': attack2.get('name', ''),
        'Attack 2 Cost': ', '.join(attack2.get('cost', [])),
        'Attack 2 Damage': attack2.get('damage', ''),
        'Attack 2 Description': attack2.get('effect', ''),
        'Rarity': card_data.get('rarity', ''),
        'Pack': card_data.get('set', {}).get('name', '') if isinstance(card_data.get('set'), dict) else card_data.get('set', ''),
    }
    
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['Card Name', 'HP', 'Energy Type', 'Weakness', 'Resistance', 'Retreat Cost',
                     'Category', 'Ability Name', 'Ability Description', 'Attack 1 Name', 'Attack 1 Cost', 
                     'Attack 1 Damage', 'Attack 1 Description', 'Attack 2 Name', 'Attack 2 Cost',
                     'Attack 2 Damage', 'Attack 2 Description', 'Rarity', 'Pack']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(card)
    
    print(f"  [CSV] Added: {card['Card Name']}")


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'last_index': -1}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def run_batch(start_index=0, batch_size=BATCH_SIZE):
    progress = load_progress()
    processed_files = set(progress.get('processed', []))
    failed_files = set(progress.get('failed', []))
    
    all_files = sorted(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")))
    
    files_to_process = [
        f for f in all_files 
        if os.path.basename(f) not in processed_files 
        and os.path.basename(f) not in failed_files
    ]
    
    if start_index >= len(files_to_process):
        print(f"\n[DONE] All processed!")
        return
    
    batch = files_to_process[start_index:start_index + batch_size]
    
    print(f"\n{'='*50}")
    print(f"Batch {start_index//batch_size + 1}: {start_index+1}-{min(start_index+batch_size, len(files_to_process))}")
    print(f"{'='*50}")
    
    results = []
    
    for i, filepath in enumerate(batch):
        idx = start_index + i
        filename = os.path.basename(filepath)
        
        success, card = process_card(filepath)
        
        if success:
            results.append(card)
            processed_files.add(filename)
        else:
            failed_path = os.path.join(FAILED_DIR, filename)
            os.rename(filepath, failed_path)
            failed_files.add(filename)
        
        progress['processed'] = list(processed_files)
        progress['failed'] = list(failed_files)
        progress['last_index'] = idx
        save_progress(progress)
        
        time.sleep(0.3)
    
    print(f"\n[Complete] {len(results)}/{len(batch)}")
    return results

def show_status():
    progress = load_progress()
    to_proc = len(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")))
    captured = len(glob.glob(os.path.join(CAPTURED_DIR, "*.png")))
    failed = len(glob.glob(os.path.join(FAILED_DIR, "*.png")))
    
    print(f"\n{'='*40}")
    print(f"To process: {to_proc}")
    print(f"Captured: {captured}")
    print(f"Failed: {failed}")
    print(f"Last index: {progress.get('last_index', -1)}")
    print(f"{'='*40}\n")

def main():
    os.makedirs(CAPTURED_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)
    os.makedirs("test_output", exist_ok=True)
    
    if len(sys.argv) == 1:
        show_status()
        print("Usage:")
        print("  python3 extract_batch_improved.py status")
        print("  python3 extract_batch_improved.py run [count]")
        print("  python3 extract_batch_improved.py csv")
        print("  python3 extract_batch_improved.py reset")
        return
        print("  python3 extract_batch.py run [count]")
        print("  python3 extract_batch.py csv")
        print("  python3 extract_batch.py reset")
        return
    
    cmd = sys.argv[1]
    
    if cmd == 'status':
        show_status()
    elif cmd == 'reset':
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        print("[RESET] Done")
    elif cmd == 'run':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else BATCH_SIZE
        progress = load_progress()
        start = progress.get('last_index', -1) + 1
        run_batch(start, batch_size)
    elif cmd == 'csv':
        print("[CSV] Generating from captured files...")
        # This version uses the TCGdex API
        captured_files = glob.glob(os.path.join(CAPTURED_DIR, "*.png"))
        
        cards = []
        failed_files = []
        
        for filepath in captured_files:
            filename = os.path.basename(filepath)
            print(f"[CSV] Processing: {filename}")
            
            # Filename format: CardName_setID_cardNum[_extra].png
            # Handle files with duplicate suffixes like _1, _2
            base_name = filename.replace('.png', '')
            parts = base_name.split('_')
            
            if len(parts) < 3:
                print(f"  [ERROR] Invalid filename format: {filename}")
                failed_files.append(filename)
                continue
            
            # Extract set_id and card_num from parts[1] and parts[2]
            set_id = parts[1]
            card_num_part = parts[2]
            
            # Handle card_num with extra parts (like 209_1)
            card_num_parts = card_num_part.split('_')
            if len(card_num_parts) > 1:
                # Use the first part as card number
                card_num = card_num_parts[0]
                print(f"  [WARN] Multiple parts in card number, using: {card_num}")
            else:
                card_num = card_num_part
            
            # Try to find card by set-number first
            card_data = search_card_by_number(set_id, card_num)
            if card_data:
                cards.append(card_data)
                print(f"  [SUCCESS] Found by set-number: {set_id}-{card_num}")
                continue
            
            # If set-number search failed, try searching by card name
            # Extract card name from filename (parts[0] and any additional parts before set_id)
            card_name_parts = parts[0:-2]  # All parts except last 2 (set_id and card_num)
            card_name = ' '.join(card_name_parts).replace('-', ' ').replace('_', ' ')
            
            if card_name:
                card_data = search_card_by_name(card_name)
                if card_data:
                    cards.append(card_data)
                    print(f"  [SUCCESS] Found by name: {card_name}")
                    continue
            
            print(f"  [ERROR] Could not find card: {filename}")
            failed_files.append(filename)
        
        print(f"[CSV] Generated from {len(captured_files)} files")
        print(f"  Success: {len(cards)}")
        print(f"  Failed: {len(failed_files)}")
        if failed_files:
            print(f"  Failed files: {', '.join(failed_files[:5])}")
            if len(failed_files) > 5:
                print(f"  ... and {len(failed_files) - 5} more")
        
        # Write CSV
        fields = ['Card Name', 'HP', 'Energy Type', 'Weakness', 'Resistance', 'Retreat Cost',
                 'Category', 'Ability Name', 'Ability Description', 'Attack 1 Name', 'Attack 1 Cost', 
                 'Attack 1 Damage', 'Attack 1 Description', 'Attack 2 Name', 'Attack 2 Cost',
                 'Attack 2 Damage', 'Attack 2 Description', 'Rarity', 'Pack']
        
        # Delete existing CSV and recreate
        if os.path.exists(OUTPUT_CSV):
            os.remove(OUTPUT_CSV)
        
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            # Write card data
            for card_data in cards:
                attacks = card_data.get('attacks', [])
                attack1 = attacks[0] if len(attacks) > 0 else {}
                attack2 = attacks[1] if len(attacks) > 1 else {}
                
                abilities = card_data.get('abilities', [])
                ability = abilities[0] if abilities else {}
                
                weaknesses = card_data.get('weaknesses', [])
                weakness = ''
                if weaknesses:
                    w = weaknesses[0]
                    weakness = f"{w.get('type', '')} {w.get('value', '')}"
                
                types = card_data.get('types', [])
                energy_type = ', '.join(types) if types else ''
                
                retreat = card_data.get('retreat', '')
                if retreat:
                    retreat = str(retreat)
                
                card = {
                    'Card Name': card_data.get('name', ''),
                    'HP': card_data.get('hp', ''),
                    'Energy Type': energy_type,
                    'Weakness': weakness,
                    'Resistance': '',
                    'Retreat Cost': retreat,
                    'Category': card_data.get('category', ''),
                    'Ability Name': ability.get('name', ''),
                    'Ability Description': ability.get('effect', ''),
                    'Attack 1 Name': attack1.get('name', ''),
                    'Attack 1 Cost': ', '.join(attack1.get('cost', [])),
                    'Attack 1 Damage': attack1.get('damage', ''),
                    'Attack 1 Description': attack1.get('effect', ''),
                    'Attack 2 Name': attack2.get('name', ''),
                    'Attack 2 Cost': ', '.join(attack2.get('cost', [])),
                    'Attack 2 Damage': attack2.get('damage', ''),
                    'Attack 2 Description': attack2.get('effect', ''),
                    'Rarity': card_data.get('rarity', ''),
                    'Pack': card_data.get('set', {}).get('name', '') if isinstance(card_data.get('set'), dict) else '',
                }
                writer.writerow(card)
        
        print(f"[CSV] Updated {len(cards)} cards")
        return cards, failed_files
    else:
        print(f"Unknown: {cmd}")

if __name__ == "__main__":
    main()