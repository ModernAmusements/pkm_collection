#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor
- Zone-based extraction from card image
- Percentage-based cropping (works for any resolution)
- OCR only - no API calls
"""

import os
import re
import csv
import glob
import sys
import json
import time
from PIL import Image, ImageEnhance, ImageFilter
# import requests  # Disabled - using OCR only
import pytesseract

# === CONFIG ===
SCREENSHOT_DIR = "screenshots/to_process"
CAPTURED_DIR = "screenshots/captured"
FAILED_DIR = "screenshots/failed_to_capture"
OUTPUT_CSV = "my_cards_full.csv"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25
# API_BASE = "https://api.tcgdex.net/v2/de/cards"  # Disabled

# TCG Pocket sets - prioritized by commonality
TCGP_SETS_PRIORITY = {
    'A1': 10, 'A1a': 10, 'A2': 9, 'A2a': 9, 'A2b': 8, 'A3': 8, 'A3a': 7, 'A3b': 7, 'A4': 6, 'A4a': 6,
    'Pikachu': 9, 'B1': 7, 'B1a': 6, 'B2': 6, 'B2a': 5,
    'swsh': 5, 'swsh6': 4, 'swsh7': 4, 'swsh8': 3, 'swsh9': 3, 'swsh10': 2, 'swsh11': 2, 'swsh12': 2,
    'sv': 4, 'sv01': 3, 'sv02': 3, 'sv03': 2, 'sv04': 2, 'sv05': 2, 'sv06': 2,
    'sm': 3, 'sm1': 2, 'sm2': 2, 'sm3': 2, 'sm4': 1, 'sm5': 1,
    'xy': 2, 'xy1': 1, 'xy2': 1, 'bw': 1,
}

# Sorted by priority (highest first)
TCGP_SETS = sorted(TCGP_SETS_PRIORITY.keys(), key=lambda x: TCGP_SETS_PRIORITY[x], reverse=True)

# API cache
API_CACHE = {}

# === PREPROCESSING CONFIG ===
# Crop percentages (works for any image with same aspect ratio)
CROP_LEFT_PCT = 0.0855   # 8.55% from left
CROP_RIGHT_PCT = 0.0855  # 8.55% from right
CROP_TOP_PCT = 0.1386     # 13.86% from top
CROP_BOTTOM_PCT = 0.3164  # 31.64% from bottom

# Base resolution for zone definitions: 1170x2532 -> cropped: 970x1380
# Zones defined for 1380px height (maintains aspect ratio)
CARD_HEIGHT = 1380

# Pokemon zones (percentages of cropped card height)
ZONES_POKEMON = {
    1: (0.00, 0.10),   # Top Bar: Stage + Name + HP - OCR
    2: (0.10, 0.12),   # Evolution Info - IGNORED
    3: (0.12, 0.47),   # Artwork Box - IGNORED
    4: (0.47, 0.51),   # Pokedex Info - IGNORED
    5: (0.51, 0.84),   # Attacks - OCR
    6: (0.84, 1.00),   # Bottom Info: Card# + Weakness/Resistance/Retreat - OCR
}

# Trainer zones (percentages of cropped card height)
ZONES_TRAINER = {
    1: (0.00, 0.06),   # Top Label - DETECTION ONLY
    2: (0.06, 0.15),   # Name - OCR
    3: (0.15, 0.43),   # Artwork - IGNORED
    4: (0.43, 0.87),   # Effect Text - OCR
    5: (0.87, 1.00),   # Set Info - OCR
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
    """
    Preprocess screenshot for zone extraction.
    Flow: Original → Crop (percentages) → Scaled card crop
    
    - Crop 8.55% from left and right
    - Crop 13.86% from top  
    - Crop 31.64% from bottom
    """
    img = Image.open(image_path)
    w, h = img.size
    
    # Detect and fix orientation
    if w > h:
        img = img.rotate(-90, expand=True)
        w, h = h, w
    
    # Apply crop values as percentages (relative to original dimensions)
    left = int(w * CROP_LEFT_PCT)
    right = w - int(w * CROP_RIGHT_PCT)
    top = int(h * CROP_TOP_PCT)
    bottom = h - int(h * CROP_BOTTOM_PCT)
    
    img = img.crop((left, top, right, bottom))
    
    return img

def extract_zone(img, zone_num, is_trainer=False):
    """
    Extract zone from card image.
    Returns raw cropped zone - no processing applied.
    """
    zones = ZONES_TRAINER if is_trainer else ZONES_POKEMON
    if zone_num not in zones:
        return None
    
    w, h = img.size
    
    # Zones are percentages of image height
    y1_pct, y2_pct = zones[zone_num]
    y1 = int(y1_pct * h)
    y2 = int(y2_pct * h)
    
    # Crop zone - return raw, no processing
    zone = img.crop((0, y1, w, y2))
    
    return zone
    
    return zone

def ocr_zone(zone_img, lang=None):
    """OCR a zone - image already preprocessed by extract_zone"""
    if zone_img is None:
        return None
    
    # Try without language spec first (more reliable)
    text = pytesseract.image_to_string(zone_img, config='--psm 6')
    if text and len(text.strip()) > 2:
        return text.strip()
    
    # Try German
    text_de = pytesseract.image_to_string(zone_img, lang='deu', config='--psm 6')
    if text_de and len(text_de.strip()) > 2:
        return text_de.strip()
    
    # Try English as fallback
    text_en = pytesseract.image_to_string(zone_img, lang='eng', config='--psm 6')
    if text_en and len(text_en.strip()) > 2:
        return text_en.strip()
    
    return None

def has_text(zone_img):
    """Check if zone has readable text"""
    text = ocr_zone(zone_img)
    return text is not None and len(text) > 2

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


# === API FUNCTIONS - DISABLED (Using OCR only) ===
# def search_card_by_name(name):
#     """Search API for card by name - returns full card data with caching"""
#     if not name:
#         return None
#     
#     # Check cache first
#     cache_key = f"name:{name.lower()}"
#     if cache_key in API_CACHE:
#         return API_CACHE[cache_key]
#     
#     url = f"{API_BASE}?name={name}"
#     try:
#         resp = requests.get(url, timeout=10)
#         if resp.status_code == 200:
#             results = resp.json()
#             for card in results:
#                 set_id = card.get('id', '').split('-')[0]
#                 if set_id in TCGP_SETS:
#                     # Fetch full card data by ID
#                     card_id = card.get('id')
#                     full_url = f"{API_BASE}/{card_id}"
#                     full_resp = requests.get(full_url, timeout=10)
#                     if full_resp.status_code == 200:
#                         result = full_resp.json()
#                         API_CACHE[cache_key] = result
#                         return result
#                     # Fallback to partial but don't cache
#                     API_CACHE[cache_key] = card
#                     return card
#     except:
#         pass
#     return None

# def search_card_by_number(set_id, card_num):
#     """Search API for card by set and number with caching"""
#     # Check cache first
#     cache_key = f"{set_id}:{card_num}"
#     if cache_key in API_CACHE:
#         return API_CACHE[cache_key]
#     
#     url = f"{API_BASE}/{set_id}-{card_num:03d}"
#     try:
#         resp = requests.get(url, timeout=10)
#         if resp.status_code == 200:
#             result = resp.json()
#             API_CACHE[cache_key] = result
#             return result
#     except:
#         pass
#     return None


def detect_card_type(img):
    """Detect if card is Trainer or Pokemon"""
    w, h = img.size
    
    # Pokemon Zone 1: 0-10% of height
    z1_pokemon = img.crop((0, 0, w, int(h * 0.10)))
    gray = z1_pokemon.convert('L')
    text_pkm = pytesseract.image_to_string(gray, config='--psm 6').upper()
    print(f"  [DEBUG] Pokemon Zone 1: {text_pkm[:60]}")
    
    # Check for Pokemon indicators (HP/KP)
    if 'KP' in text_pkm or 'HP' in text_pkm:
        return False  # Pokemon
    
    # Check for Trainer indicators
    trainer_keywords = ['TRAINER', 'ARTIKEL', 'STADION', 'UNTERSTÜTZUNG', 'SPEZIAL', 'ITEM']
    for keyword in trainer_keywords:
        if keyword in text_pkm:
            return True  # Trainer
    
    # Try Trainer zone 1: 0-6% of height
    z1_trainer = img.crop((0, 0, w, int(h * 0.06)))
    gray = z1_trainer.convert('L')
    text_trn = pytesseract.image_to_string(gray, config='--psm 6').upper()
    print(f"  [DEBUG] Trainer Zone 1: {text_trn[:60]}")
    
    for keyword in trainer_keywords:
        if keyword in text_trn:
            return True  # Trainer
    
    # Check Pokemon indicators in trainer zone
    if 'KP' in text_trn or 'HP' in text_trn:
        return False  # Pokemon
    
    # Default to Pokemon
    return False

def process_card(image_path):
    """Process a single card - OCR only, no filename parsing"""
    filename = os.path.basename(image_path)
    print(f"\n\033[1;36m[Processing]\033[0m {filename}")
    
    # OCR extraction only - no filename parsing!
    print(f"  \033[90m[OCR] Extracting from image...\033[0m")
    
    # Preprocess
    img = preprocess_image(image_path)
    
    # Detect card type
    is_trainer = detect_card_type(img)
    print(f"  \033[1;90m->\033[0m Detected: {'\033[1;33mTrainer\033[0m' if is_trainer else '\033[1;32mPokemon\033[0m'}")
    
    # Pokemon: Zone 1, 5, 6 for OCR (Top Bar, Attacks, Bottom Info)
    # Trainer: Zone 2, 4, 5 for OCR (Name, Effect, Set Info)
    if is_trainer:
        zones_to_try = [2, 4, 5]
    else:
        zones_to_try = [1, 5, 6]
    
    card_data = None
    
    # For Trainer cards, use Zone 2 name directly without API
    if is_trainer:
        zone_img = extract_zone(img, 2, True)
        if zone_img:
            text = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 2:\033[0m {text[:50]}...")
                # Extract name from text - take first significant line
                lines = text.strip().split('\n')
                trainer_name = lines[0].strip() if lines else text.strip()
                # Clean up name
                trainer_name = ' '.join(trainer_name.split())
                if trainer_name:
                    print(f"  \033[92m[✓] Trainer name:\033[0m {trainer_name}")
                    # Create minimal card data from OCR
                    card_data = {
                        'name': trainer_name,
                        'id': f"trainer_{hash(trainer_name)}",
                        'set': {'name': 'Unknown'},
                        'category': 'Trainer',
                    }
    
    # For Pokemon cards, use Zone 1 name directly
    if not card_data and not is_trainer:
        zone_img = extract_zone(img, 1, False)
        if zone_img:
            text = ocr_zone(zone_img)
            if text:
                print(f"  [90m  [~] Zone 1:[0m {text[:60]}...")
                
                # Find Pokemon name - look for capitalized words in first few lines
                lines = text.strip().split('\n')[:3]
                found_name = None
                for line in lines:
                    words = line.split()
                    for word in words:
                        # Clean and check if looks like Pokemon name
                        clean = ''.join(c for c in word if c.isalpha())
                        if len(clean) >= 4 and clean[0].isupper():
                            found_name = clean
                            break
                    if found_name:
                        break
                
                if found_name:
                    print(f"  [92m[✓] Pokemon name:[0m {found_name}")
                    card_data = {
                        'name': found_name,
                        'id': f"pokemon_{found_name.lower()}",
                        'set': {'name': 'OCR'},
                        'category': 'Pokemon',
                    }
    
    if not card_data:
        print(f"  [91m[✗] ERROR: Could not find card[0m")
        return False, None
    
    # Get card info
    card_id = card_data.get('id', '')
    set_id = card_data.get('set', {}).get('name', 'OCR')
    card_num = 0
    
    # Handle duplicates
    card_name = card_data.get('name', 'unknown')
    new_filename = f"{card_name}_{set_id}_{card_num}.png"
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
    
    print(f"  \033[92m  ═══════════════════════════════════\033[0m")
    print(f"  \033[92m  [✓] CAPTURED: {card_data['name']}\033[0m")
    print(f"  \033[90m      Set: {set_id} | Card: #{card_num} | HP: {card_data.get('hp', 'N/A')}\033[0m")
    print(f"  \033[92m  ═══════════════════════════════════\033[0m")
    
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
    
    all_files = sorted(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")) + glob.glob(os.path.join(SCREENSHOT_DIR, "*.PNG")))
    
    files_to_process = [
        f for f in all_files 
        if os.path.basename(f) not in processed_files 
        and os.path.basename(f) not in failed_files
    ]
    
    # If batch_size is large (>= len), process all remaining files
    if batch_size >= len(files_to_process):
        batch = files_to_process
        start_index = 0
    else:
        batch = files_to_process[start_index:start_index + batch_size]
    
    if not batch:
        print(f"\n\033[92m[✓] All cards already processed!\033[0m")
        return
    
    print(f"\n\033[1;36m{'═'*50}\033[0m")
    print(f"\033[1;36m  BATCH {start_index//batch_size + 1}\033[0m")
    print(f"\033[90m  Cards {start_index+1}-{min(start_index+batch_size, len(files_to_process))} of {len(files_to_process)}\033[0m")
    print(f"\033[1;36m{'═'*50}\033[0m")
    
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
    
    success_count = len(results)
    fail_count = len(batch) - success_count
    
    print(f"\n\033[1;36m{'═'*50}\033[0m")
    print(f"  \033[92m[✓] Success: {success_count}\033[0m  \033[91m[✗] Failed: {fail_count}\033[0m")
    print(f"  \033[90m  Total captured: {len(processed_files)} | Total failed: {len(failed_files)}\033[0m")
    print(f"\033[1;36m{'═'*50}\033[0m")
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
    """Generate CSV from captured files - OCR only, no API needed"""
    captured_files = glob.glob(os.path.join(CAPTURED_DIR, "*.png"))
    
    cards = []
    for filepath in captured_files:
        filename = os.path.basename(filepath)
        # Parse filename to get card name
        name = filename.replace('.png', '').rsplit('_', 2)[0] if '_' in filename else filename.replace('.png', '')
        
        cards.append({
            'Card Name': name,
            'HP': '',
            'Energy Type': '',
            'Weakness': '',
            'Resistance': '',
            'Retreat Cost': '',
            'Category': '',
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
            'Rarity': '',
            'Pack': '',
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
    to_proc = len(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")) + glob.glob(os.path.join(SCREENSHOT_DIR, "*.PNG")))
    captured = len(glob.glob(os.path.join(CAPTURED_DIR, "*.png")))
    failed = len(glob.glob(os.path.join(FAILED_DIR, "*.png")))
    
    print(f"\n\033[1;36m{'═'*40}\033[0m")
    print(f"  \033[1;37mPOKEMON TCG POCKET - EXTRACTION STATUS\033[0m")
    print(f"\033[1;36m{'─'*40}\033[0m")
    print(f"  \033[33m[●] To process:\033[0m   {to_proc}")
    print(f"  \033[92m[✓] Captured:\033[0m    {captured}")
    print(f"  \033[91m[✗] Failed:\033[0m      {failed}")
    print(f"\033[1;36m{'─'*40}\033[0m")
    total = to_proc + captured + failed
    if total > 0:
        pct = (captured / total) * 100
        print(f"  \033[90mProgress: {captured}/{total} ({pct:.1f}%)\033[0m")
    print(f"\033[1;36m{'═'*40}\033[0m\n")

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
