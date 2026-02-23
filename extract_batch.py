#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor - NEW VERSION
- Zone-based extraction from card image
- Percentage-based cropping (works for any resolution)
- TCG Pocket only sets
- Complete card database from API
- Energy color detection
"""

import os
import re
import csv
import glob
import sys
import json
import time
from PIL import Image, ImageEnhance, ImageFilter
import requests
import pytesseract

# === CONFIG ===
SCREENSHOT_DIR = "screenshots/to_process"
CAPTURED_DIR = "screenshots/captured"
FAILED_DIR = "screenshots/failed_to_capture"
OUTPUT_CSV = "my_cards_full.csv"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25
API_BASE = "https://api.tcgdex.net/v2/de/cards"

# TCG Pocket sets only
TCGP_SETS = ['A1', 'A1a', 'A2', 'A2a', 'A2b', 'A3', 'A3a', 'A3b', 'A4', 'A4a', 'Pikachu', 'B1', 'B1a', 'B2', 'B2a']

# === PREPROCESSING CONFIG ===
CROP_SIDES = 0.085  # 8.5% from each side
CROP_HEIGHT = 555   # Fixed height
SCALE = 3  # Scale factor for OCR

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
    1: (0, 41),       # Trainer card type (Item, Stadium, etc.)
    2: (41, 81),      # Name (40px)
    3: (81, 289),     # Artwork (208px)
    4: (289, 480),    # Effect (191px)
    5: (480, 554),    # Special trainer rule (74px)
}

# Crop percentages (based on original image)
CROP = {
    'top': 0.14,      # 14% from top
    'bottom': 0.32,    # 32% from bottom
    'sides': 0.085,   # 8.5% from each side
}

# Energy colors (RGB ranges)
ENERGY_COLORS = {
    'Feuer': [(200, 50, 50), (255, 100, 100)],      # Red
    'Wasser': [(50, 100, 200), (100, 150, 255)],     # Blue
    'Elektro': [(200, 200, 50), (255, 255, 100)],    # Yellow
    'Pflanze': [(50, 200, 50), (100, 255, 100)],     # Green
    'Kampf': [(200, 150, 50), (255, 200, 100)],      # Orange
    'Psycho': [(150, 50, 200), (200, 100, 255)],     # Purple
    'Unlicht': [(50, 50, 100), (100, 100, 150)],     # Dark/Black
    'Metall': [(150, 150, 150), (200, 200, 200)],    # Gray
    'Fee': [(200, 150, 200), (255, 200, 255)],       # Pink
    'Drache': [(150, 100, 50), (200, 150, 100)],    # Brown
    'Farblos': [(200, 200, 200), (255, 255, 255)],   # White/Gray
}

# German to English energy type mapping
GERMAN_TO_ENERGY = {
    'Feuer': 'Fire',
    'Wasser': 'Water',
    'Elektro': 'Lightning',
    'Pflanze': 'Grass',
    'Kampf': 'Fighting',
    'Psycho': 'Psychic',
    'Unlicht': 'Darkness',
    'Metall': 'Metal',
    'Fee': 'Fairy',
    'Drache': 'Dragon',
    'Farblos': 'Colorless',
}

# Zone expectations (what to find in each zone)
ZONE_EXPECTATIONS = {
    'pokemon': {
        1: 'Pokemon name + HP + Energy symbol (e.g., "Endivie 60")',
        2: 'Evolution stage (Basis, Phase 1, Phase 2)',
        3: 'Artwork (image)',
        4: 'Card number (e.g., "Nr. 001")',
        5: 'Attacks/Abilities text',
        6: 'Weakness + Retreat cost',
    },
    'trainer': {
        1: 'Card type (Item, Stadium, Unterstützung)',
        2: 'Card name (e.g., "Hyper-Raketen")',
        3: 'Artwork',
        4: 'Effect description',
        5: 'Special rule (if any)',
    }
}

# === FUNCTIONS ===

def preprocess_image(image_path):
    """Crop sides, crop to 555px height, return image ready for zone extraction"""
    img = Image.open(image_path)
    w, h = img.size
    
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
    w, h = img.size  # h should be 555
    y1, y2 = zones[zone_num]
    zone = img.crop((0, y1, w, y2))
    # Scale 3x for better OCR
    return zone.resize((zone.width * SCALE, zone.height * SCALE))

def ocr_zone(zone_img, lang='deu'):
    """OCR a zone - convert to grayscale for text"""
    gray = zone_img.convert('L')
    # Increase contrast for better OCR
    gray = ImageEnhance.Contrast(gray).enhance(2)
    text = pytesseract.image_to_string(gray, lang=lang)
    return text.strip()

def detect_energy_color(zone_img):
    """Detect energy type from color in energy zone"""
    # Convert to RGB if needed
    if zone_img.mode != 'RGB':
        zone_img = zone_img.convert('RGB')
    
    # Get average color
    pixels = list(zone_img.getdata())
    avg_r = sum(p[0] for p in pixels) // len(pixels)
    avg_g = sum(p[1] for p in pixels) // len(pixels)
    avg_b = sum(p[2] for p in pixels) // len(pixels)
    
    # Simple color matching
    for energy, (low, high) in ENERGY_COLORS.items():
        if (low[0] <= avg_r <= high[0] and 
            low[1] <= avg_g <= high[1] and 
            low[2] <= avg_b <= high[2]):
            return energy
    
    return None

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'last_index': -1}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def search_card_by_name(name):
    """Search API for card by name - returns full card data"""
    if not name:
        return None
    
    url = f"{API_BASE}?name={name}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = resp.json()
            for card in results:
                set_id = card.get('id', '').split('-')[0]
                if set_id in TCGP_SETS:
                    # Fetch full card data by ID
                    card_id = card.get('id')
                    full_url = f"{API_BASE}/{card_id}"
                    full_resp = requests.get(full_url, timeout=10)
                    if full_resp.status_code == 200:
                        return full_resp.json()
                    return card  # Fallback to partial
    except:
        pass
    return None

def search_card_by_number(set_id, card_num):
    """Search API for card by set and number"""
    url = f"{API_BASE}/{set_id}-{card_num:03d}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def detect_card_type(img):
    """Detect if card is Trainer or Pokemon based on Zone 1 text"""
    # Use larger zone to catch both Pokemon (0-55) and Trainer (0-41)
    zone1 = img.crop((0, 0, img.width, 60))
    gray = zone1.convert('L')
    text = pytesseract.image_to_string(gray, lang='deu').upper()
    
    print(f"  [DEBUG] Zone1 text: {text[:60]}")
    
    trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL', 'ITEM']
    for keyword in trainer_keywords:
        if keyword in text:
            return True
    
    # Pokemon indicator - look for HP/KP
    if 'KP' in text or 'HP' in text:
        return False
    
    return False
    
    # Try Trainer zone 1 (0-41px) as fallback
    zone1_trn = img.crop((0, 0, img.width, 41))
    gray = zone1_trn.convert('L')
    text = pytesseract.image_to_string(gray, lang='deu').upper()
    
    for keyword in trainer_keywords:
        if keyword in text:
            return True
    
    return False

def process_card(image_path):
    """Process a single card"""
    filename = os.path.basename(image_path)
    print(f"\n[Processing] {filename}")
    
    # Preprocess
    img = preprocess_image(image_path)
    
    # Detect card type
    is_trainer = detect_card_type(img)
    print(f"  -> Detected: {'Trainer' if is_trainer else 'Pokemon'}")
    
    # Extract text from ALL zones and combine
    all_text = ""
    
    # Zone 1 - Name/Type
    z1 = extract_zone(img, 1, is_trainer)
    all_text += " " + ocr_zone(z1)
    
    # Zone 2 - Evolution/Name
    z2 = extract_zone(img, 2, is_trainer)
    all_text += " " + ocr_zone(z2)
    
    # Zone 4 - Card number (Pokemon) or Effect (Trainer)
    z4 = extract_zone(img, 4, is_trainer)
    all_text += " " + ocr_zone(z4)
    
    # Zone 5 - Attacks/Effect
    z5 = extract_zone(img, 5 if not is_trainer else 99, is_trainer)
    if z5:
        all_text += " " + ocr_zone(z5)
    
    # Clean up text
    all_text = ' '.join(all_text.split())
    print(f"  [OCR] Combined: {all_text[:80]}...")
    
    # Extract Pokemon/Trainer name from combined text
    # Look for German Pokemon names (usually capitalized words)
    words = all_text.split()
    card_data = None
    
    for word in words:
        # Clean word - remove special chars
        clean_word = ''.join(c for c in word if c.isalnum())
        if len(clean_word) >= 3:
            # Try searching by this word
            card_data = search_card_by_name(clean_word)
            if card_data:
                print(f"  [API] Found: {clean_word} -> {card_data.get('name')}")
                break
    
    if not card_data:
        print(f"  [ERROR] Could not find card")
        return False, None
    
    # Get card info
    card_id = card_data.get('id', '')
    set_id, card_num = card_id.split('-') if '-' in card_id else ('', 0)
    card_num = int(card_num)
    
    # Handle duplicates
    new_filename = f"{card_data['name']}_{set_id}_{card_num}.png"
    new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    dup = 1
    while os.path.exists(new_path):
        dup += 1
        new_filename = f"{card_data['name']}_{set_id}_{card_num}_{dup-1}.png"
        new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    # Move file
    os.rename(image_path, new_path)
    
    # Append to CSV
    append_to_csv(card_data)
    
    print(f"  [SUCCESS] {card_data['name']} ({set_id}-{card_num})")
    
    return True, {
        'filename': new_filename,
        'name': card_data.get('name', ''),
        'set': card_data.get('set', {}).get('name', ''),
        'set_id': set_id,
        'card_num': card_num,
        'hp': card_data.get('hp', ''),
        'energy': ', '.join(card_data.get('types', [])),
        'rarity': card_data.get('rarity', ''),
        'stage': card_data.get('stage', ''),
    }

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

OUTPUT_CSV = "my_cards_full.csv"

CSV_FIELDS = ['Card Name', 'HP', 'Energy Type', 'Weakness', 'Resistance', 'Retreat Cost',
              'Category', 'Ability Name', 'Ability Description', 'Attack 1 Name', 'Attack 1 Cost', 
              'Attack 1 Damage', 'Attack 1 Description', 'Attack 2 Name', 'Attack 2 Cost',
              'Attack 2 Damage', 'Attack 2 Description', 'Rarity', 'Pack']

def append_to_csv(card_data):
    """Append a single card to CSV"""
    file_exists = os.path.exists(OUTPUT_CSV)
    
    card = {
        'Card Name': card_data.get('name', ''),
        'HP': card_data.get('hp', ''),
        'Energy Type': ', '.join(card_data.get('types', [])),
        'Weakness': f"{card_data.get('weaknesses', [{}])[0].get('type', '')} {card_data.get('weaknesses', [{}])[0].get('value', '')}",
        'Resistance': '',
        'Retreat Cost': card_data.get('retreat', ''),
        'Category': card_data.get('category', ''),
        'Ability Name': card_data.get('abilities', [{}])[0].get('name', '') if card_data.get('abilities') else '',
        'Ability Description': card_data.get('abilities', [{}])[0].get('effect', '') if card_data.get('abilities') else '',
        'Attack 1 Name': card_data.get('attacks', [{}])[0].get('name', '') if card_data.get('attacks') else '',
        'Attack 1 Cost': ', '.join(card_data.get('attacks', [{}])[0].get('cost', [])) if card_data.get('attacks') else '',
        'Attack 1 Damage': card_data.get('attacks', [{}])[0].get('damage', '') if card_data.get('attacks') else '',
        'Attack 1 Description': card_data.get('attacks', [{}])[0].get('effect', '') if card_data.get('attacks') else '',
        'Attack 2 Name': card_data.get('attacks', [{}])[1].get('name', '') if len(card_data.get('attacks', [])) > 1 else '',
        'Attack 2 Cost': ', '.join(card_data.get('attacks', [{}])[1].get('cost', [])) if len(card_data.get('attacks', [])) > 1 else '',
        'Attack 2 Damage': card_data.get('attacks', [{}])[1].get('damage', '') if len(card_data.get('attacks', [])) > 1 else '',
        'Attack 2 Description': card_data.get('attacks', [{}])[1].get('effect', '') if len(card_data.get('attacks', [])) > 1 else '',
        'Rarity': card_data.get('rarity', ''),
        'Pack': card_data.get('set', {}).get('name', ''),
    }
    
    with open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(card)
    
    print(f"  [CSV] Added: {card['Card Name']}")

def generate_csv():
    captured_files = glob.glob(os.path.join(CAPTURED_DIR, "*.png"))
    
    cards = []
    for filepath in captured_files:
        filename = os.path.basename(filepath)
        match = re.match(r'^(.+?)_([A-Za-z0-9]+)_(\d+)', filename.replace('.png', ''))
        if match:
            name, set_id, card_num = match.group(1), match.group(2), int(match.group(3))
            
            card_data = search_card_by_number(set_id, card_num)
            if card_data:
                abilities = card_data.get('abilities', [])
                attacks = card_data.get('attacks', [])
                
                cards.append({
                    'Card Name': card_data.get('name', ''),
                    'HP': card_data.get('hp', ''),
                    'Energy Type': ', '.join(card_data.get('types', [])),
                    'Weakness': f"{card_data.get('weaknesses', [{}])[0].get('type', '')} {card_data.get('weaknesses', [{}])[0].get('value', '')}",
                    'Resistance': '',
                    'Retreat Cost': card_data.get('retreat', ''),
                    'Category': card_data.get('category', ''),
                    'Ability Name': abilities[0].get('name', '') if abilities else '',
                    'Ability Description': abilities[0].get('effect', '') if abilities else '',
                    'Attack 1 Name': attacks[0].get('name', '') if len(attacks) > 0 else '',
                    'Attack 1 Cost': ', '.join(attacks[0].get('cost', [])) if len(attacks) > 0 else '',
                    'Attack 1 Damage': attacks[0].get('damage', '') if len(attacks) > 0 else '',
                    'Attack 1 Description': attacks[0].get('effect', '') if len(attacks) > 0 else '',
                    'Attack 2 Name': attacks[1].get('name', '') if len(attacks) > 1 else '',
                    'Attack 2 Cost': ', '.join(attacks[1].get('cost', [])) if len(attacks) > 1 else '',
                    'Attack 2 Damage': attacks[1].get('damage', '') if len(attacks) > 1 else '',
                    'Attack 2 Description': attacks[1].get('effect', '') if len(attacks) > 1 else '',
                    'Rarity': card_data.get('rarity', ''),
                    'Pack': card_data.get('set', {}).get('name', ''),
                })
    
    fields = ['Card Name', 'HP', 'Energy Type', 'Weakness', 'Resistance', 'Retreat Cost',
               'Category', 'Ability Name', 'Ability Description', 'Attack 1 Name', 'Attack 1 Cost', 
               'Attack 1 Damage', 'Attack 1 Description', 'Attack 2 Name', 'Attack 2 Cost',
               'Attack 2 Damage', 'Attack 2 Description', 'Rarity', 'Pack']
    
    if os.path.exists(OUTPUT_CSV):
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.rename(OUTPUT_CSV, f"my_cards_full_{ts}.csv")
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()
        csv.DictWriter(f, fieldnames=fields).writerows(cards)
    
    print(f"[CSV] Wrote {len(cards)} cards")

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
    
    if len(sys.argv) == 1:
        show_status()
        print("Usage:")
        print("  python3 extract_batch.py status")
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
        generate_csv()
    else:
        print(f"Unknown: {cmd}")

if __name__ == "__main__":
    main()
