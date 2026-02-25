#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor
- Zone-based extraction from card image
- Percentage-based cropping (works for any resolution)
- OCR only - no API calls
- SQLite database for collection tracking
"""

import os
import re
import glob
import sys
import json
import time
import csv
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import database

# === CONFIG ===
SCREENSHOT_DIR = "screenshots/to_process"
CAPTURED_DIR = "screenshots/captured"
FAILED_DIR = "screenshots/failed_to_capture"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25

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

# Energy colors (RGB ranges) - more precise ranges
# Note: Ground is brown/orange, Fighting is orange
ENERGY_COLORS = {
    'Feuer': ((180, 30, 30), (255, 80, 80)),       # Red
    'Wasser': ((30, 80, 180), (90, 150, 255)),     # Blue
    'Elektro': ((200, 200, 30), (255, 255, 80)),   # Yellow
    'Pflanze': ((30, 130, 30), (90, 220, 90)),      # Green (Plant/Grass)
    'Kampf': ((180, 100, 30), (230, 170, 80)),      # Orange (Fighting)
    'Psycho': ((140, 30, 160), (200, 80, 230)),    # Purple
    'Unlicht': ((30, 30, 80), (80, 80, 130)),       # Dark
    'Metall': ((110, 110, 130), (160, 160, 190)),  # Gray
    'Fee': ((200, 120, 180), (250, 170, 220)),     # Pink
    'Drache': ((140, 70, 40), (200, 120, 90)),     # Brown
    'Farblos': ((200, 200, 200), (250, 250, 250)), # Light gray/white
    'Kampf_Ground': ((130, 80, 30), (200, 150, 80)),  # Brown/Orange (Ground)
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
    'Kampf_Ground': 'Fighting',
}

def detect_energy_type(zone_img):
    """
    Detect energy type from Zone 1 by analyzing dominant colors.
    Energy symbols appear throughout the zone (HP area, attack costs, etc.)
    """
    if zone_img is None:
        return None
    
    img = zone_img.convert('RGB')
    w, h = img.size
    
    # Scan the WHOLE zone for energy colors
    pixels = list(img.getdata())
    
    # Count pixels matching each energy color
    energy_votes = {}
    
    for energy, ((r1, g1, b1), (r2, g2, b2)) in ENERGY_COLORS.items():
        count = 0
        for pr, pg, pb in pixels:
            # Check if pixel is in color range
            if (min(r1, r2) <= pr <= max(r1, r2) and
                min(g1, g2) <= pg <= max(g1, g2) and
                min(b1, b2) <= pb <= max(b1, b2)):
                count += 1
        energy_votes[energy] = count
    
    # Get the energy type with most matching pixels
    max_votes = max(energy_votes.values())
    
    # If Farblos (Colorless/white) wins but other energies have significant votes,
    # choose the second-best non-Farblos energy
    if max_votes > 30:
        detected = max(energy_votes, key=energy_votes.get)
        
        # If Farblos wins but other energy has decent votes, use that instead
        if detected == 'Farblos':
            if energy_votes['Kampf'] > 5000:
                detected = 'Kampf'
            elif energy_votes['Kampf_Ground'] > 3000:
                detected = 'Kampf_Ground'
            elif energy_votes['Pflanze'] > 3000:
                detected = 'Pflanze'
            elif energy_votes['Wasser'] > 3000:
                detected = 'Wasser'
            elif energy_votes['Feuer'] > 3000:
                detected = 'Feuer'
            elif energy_votes['Psycho'] > 3000:
                detected = 'Psycho'
            elif energy_votes['Elektro'] > 3000:
                detected = 'Elektro'
        
        return GERMAN_TO_ENERGY.get(detected, detected)
    
    return None

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

def preprocess_for_ocr(zone_img):
    """
    Preprocess zone image for better OCR:
    - Convert to grayscale
    - Increase contrast
    """
    if zone_img is None:
        return None
    
    # Convert to grayscale
    img = zone_img.convert('L')
    
    # Increase contrast to make text more readable
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # Sharpen to help with text edges
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    
    return img


def ocr_zone(zone_img, lang=None, preprocess=True):
    """
    OCR a zone with preprocessing and multiple passes.
    Returns (text, confidence) tuple.
    """
    if zone_img is None:
        return None, 0
    
    # Only preprocess for zones with lots of text (not Zone 1 with name)
    img_to_use = preprocess_for_ocr(zone_img) if preprocess else zone_img
    
    # Try multiple PSM modes for better accuracy
    psm_modes = ['6', '4', '3', '11']
    
    best_text = None
    best_confidence = 0
    all_results = []
    
    # First pass: try with preprocessed image
    for psm in psm_modes:
        config = f'--psm {psm}'
        
        # Try without language
        try:
            text = pytesseract.image_to_string(img_to_use, config=config)
            if text and len(text.strip()) > 2:
                # Get confidence
                data = pytesseract.image_to_data(img_to_use, config=config, output_type=pytesseract.Output.DICT)
                conf = sum([int(c) for c in data['conf'] if int(c) > 0]) / max(len([c for c in data['conf'] if int(c) > 0]), 1)
                all_results.append((text.strip(), conf, 'en'))
        except:
            pass
        
        # Try German
        try:
            text = pytesseract.image_to_string(img_to_use, lang='deu', config=config)
            if text and len(text.strip()) > 2:
                data = pytesseract.image_to_data(img_to_use, lang='deu', config=config, output_type=pytesseract.Output.DICT)
                conf = sum([int(c) for c in data['conf'] if int(c) > 0]) / max(len([c for c in data['conf'] if int(c) > 0]), 1)
                all_results.append((text.strip(), conf, 'de'))
        except:
            pass
    
    # Also try raw image (sometimes preprocessing loses info)
    for psm in ['6', '4']:
        config = f'--psm {psm}'
        try:
            text = pytesseract.image_to_string(zone_img, config=config)
            if text and len(text.strip()) > 2:
                data = pytesseract.image_to_data(zone_img, config=config, output_type=pytesseract.Output.DICT)
                conf = sum([int(c) for c in data['conf'] if int(c) > 0]) / max(len([c for c in data['conf'] if int(c) > 0]), 1)
                all_results.append((text.strip(), conf, 'raw'))
        except:
            pass
    
    # Select best result by confidence
    if all_results:
        best_text, best_confidence, _ = max(all_results, key=lambda x: x[1])
        return best_text, best_confidence
    
    return None, 0

def has_text(zone_img):
    """Check if zone has readable text"""
    text, conf = ocr_zone(zone_img)
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
    
    card_data = {}
    
    # ==================== TRAINER CARDS ====================
    if is_trainer:
        # Zone 2: Name
        zone_img = extract_zone(img, 2, True)
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 2 (Name):\033[0m {text[:50]}...")
                lines = text.strip().split('\n')
                trainer_name = lines[0].strip() if lines else text.strip()
                trainer_name = ' '.join(trainer_name.split())
                if trainer_name:
                    card_data['name'] = trainer_name
                    card_data['category'] = 'Trainer'
                    print(f"  \033[92m[✓] Trainer name:\033[0m {trainer_name}")
        
        # Zone 4: Effect
        zone_img = extract_zone(img, 4, True)
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 4 (Effect):\033[0m {text[:80]}...")
                card_data['effect'] = text.strip()
        
        # Zone 5: Set Info
        zone_img = extract_zone(img, 5, True)
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 5 (Set Info):\033[0m {text[:50]}...")
                # Try to extract set name and card number
                set_match = re.search(r'([A-Za-z]+\s*\d*)', text)
                if set_match:
                    card_data['set'] = {'name': set_match.group(1)}
                else:
                    card_data['set'] = {'name': 'Unknown'}
                
                # Try to find card number
                num_match = re.search(r'[\/¥]?\s*(\d+)', text)
                if num_match:
                    card_data['card_number'] = num_match.group(1)
        
        if not card_data.get('name'):
            print(f"  [91m[✗] ERROR: Could not find trainer name[0m")
            return False, None
    
    # ==================== POKEMON CARDS ====================
    else:
        # Zone 1: Name, HP, Stage, Energy Type
        zone_img = extract_zone(img, 1, False)
        if zone_img:
            text, _ = ocr_zone(zone_img, preprocess=False)  # Don't preprocess Zone 1 - keeps name readable
            if text:
                print(f"  \033[90m  [~] Zone 1 (Name/HP):\033[0m {text[:80]}...")
                
                # Extract name - look for capitalized words
                lines = text.strip().split('\n')[:4]
                found_name = None
                found_hp = None
                found_stage = None
                
                for line in lines:
                    words = line.split()
                    for word in words:
                        clean = ''.join(c for c in word if c.isalpha())
                        if len(clean) >= 4 and clean[0].isupper() and not found_name:
                            found_name = clean
                            break
                    
                    # Look for HP - German (KP) or English (HP) + number, or standalone 2-3 digit after name
                    hp_match = re.search(r'[Kk][Pp]?\s*(\d{2,3})|[Hh][Pp]\s*(\d{2,3})|(\d{2,3})\s*[Kk][Pp]?|Donphan\s+(\d{2,3})', line)
                    if hp_match and not found_hp:
                        val_str = hp_match.group(1) or hp_match.group(2) or hp_match.group(3) or hp_match.group(4)
                        if val_str:
                            val = int(val_str)
                            if 30 <= val <= 250:  # Reasonable HP range
                                found_hp = str(val)
                    
                    # Look for stage (German: Basis, Phase 1/2, Stufe 1/2)
                    stage_match = re.search(r'(Basis|Phase\s*1|Phase\s*2|Stufe\s*1|Stufe\s*2|Basic)', line, re.I)
                    if stage_match:
                        found_stage = stage_match.group(1)
                
                if found_name:
                    card_data['name'] = found_name
                    card_data['category'] = 'Pokemon'
                    print(f"  \033[92m[✓] Pokemon name:\033[0m {found_name}")
                
                if found_hp:
                    card_data['hp'] = found_hp
                    print(f"  \033[92m[✓] HP:\033[0m {found_hp}")
                
                if found_stage:
                    card_data['stage'] = found_stage
                    print(f"  \033[92m[✓] Stage:\033[0m {found_stage}")
                
                # Look for energy type - first try OCR text, then color detection
                full_text = text.upper()
                energy_found = False
                for ger, eng in GERMAN_TO_ENERGY.items():
                    if ger.upper() in full_text or eng.upper() in full_text:
                        card_data['energy_type'] = eng
                        print(f"  \033[92m[✓] Energy Type (text):\033[0m {eng}")
                        energy_found = True
                        break
                
                # If not found in text, try color detection
                if not energy_found and zone_img:
                    detected_energy = detect_energy_type(zone_img)
                    if detected_energy:
                        card_data['energy_type'] = detected_energy
                        print(f"  \033[92m[✓] Energy Type (color):\033[0m {detected_energy}")
        
        # Zone 5: Attacks
        zone_img = extract_zone(img, 5, False)
        attacks = []
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 5 (Attacks):\033[0m {text[:100]}...")
                
                # Look for damage numbers in text - format: "Name ... +XX" or "Name ... XX"
                damage_matches = re.findall(r'\+\s*(\d+)|(\d+)\s*$', text)
                for dmg_match in damage_matches[:3]:
                    dmg = dmg_match[0] or dmg_match[1]
                    if dmg:
                        attacks.append({
                            'name': '',
                            'damage': dmg
                        })
                
                # Try to find attack names (capitalized words followed by damage)
                attack_lines = re.findall(r'([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+)?)\s*[+\-]?\s*(\d+)', text)
                attacks = []
                for name, dmg in attack_lines[:3]:
                    if len(name) > 2:
                        attacks.append({
                            'name': name.strip(),
                            'damage': dmg
                        })
                
                if attacks:
                    card_data['attacks'] = attacks
                    print(f"  \033[92m[✓] Attacks found:\033[0m {len(attacks)}")
        
        # Zone 4: Card Number + Rarity (Pokemon only)
        zone_img = extract_zone(img, 4, False)
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 4 (Card #):\033[0m {text[:80]}...")
                
                # Extract card number (e.g., "123/198" or "123" or "Nr. 123")
                card_num_match = re.search(r'(?:Nr\.?\s*)?(\d+)\s*[\/¥]?', text)
                if card_num_match:
                    card_data['card_number'] = card_num_match.group(1)
                    print(f"  \033[92m[✓] Card Number:\033[0m {card_data['card_number']}")
                
                # Extract rarity (R, U, C, or German: Rare Holo, etc)
                rarity_match = re.search(r'([RUC])\b|(Rare Holo)|(Rare Ultra)|★', text)
                if rarity_match:
                    card_data['rarity'] = rarity_match.group(0)
                    print(f"  \033[92m[✓] Rarity:\033[0m {card_data['rarity']}")
        
        # Zone 6: Weakness, Resistance, Retreat (Pokemon only)
        zone_img = extract_zone(img, 6, False)
        if zone_img:
            text, _ = ocr_zone(zone_img)
            if text:
                print(f"  \033[90m  [~] Zone 6 (Bottom Info):\033[0m {text[:80]}...")
                
                # Extract weakness (German: Schwäche/Schwache)
                weakness_match = re.search(r'[Ss]chw[äa]ch[ae]\s*[@]?\s*\+?(\d+)', text)
                if weakness_match:
                    card_data['weakness'] = weakness_match.group(1)
                    print(f"  \033[92m[✓] Weakness:\033[0m {card_data['weakness']}")
                
                # Extract resistance (German: Widerstand)
                resistance_match = re.search(r'[Ww]iderstand[:\s]*([A-Za-z@]+)', text)
                if resistance_match:
                    card_data['resistance'] = resistance_match.group(1).replace('@', '').strip()
                    print(f"  \033[92m[✓] Resistance:\033[0m {card_data['resistance']}")
                
                # Extract retreat cost (German: Rückzug)
                retreat_match = re.search(r'[Rr][üu]ckzug.*?(\d)', text)
                if retreat_match:
                    card_data['retreat_cost'] = retreat_match.group(1)
                    print(f"  \033[92m[✓] Retreat Cost:\033[0m {card_data['retreat_cost']}")
        
        if not card_data.get('name'):
            print(f"  [91m[✗] ERROR: Could not find Pokemon name[0m")
            return False, None
    
    # Set default values if not found
    if 'set' not in card_data:
        card_data['set'] = {'name': 'OCR'}
    if 'card_number' not in card_data:
        card_data['card_number'] = '0'
    
    # Get card info
    set_id = card_data.get('set', {}).get('name', 'OCR')
    card_num = card_data.get('card_number', '0')
    
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
    
    # Add to database
    add_to_collection(card_data)
    
    hp_val = card_data.get('hp', 'N/A')
    print(f"  \033[92m  ═══════════════════════════════════\033[0m")
    print(f"  \033[92m  [✓] CAPTURED: {card_data['name']}\033[0m")
    print(f"  \033[90m      Set: {set_id} | Card: #{card_num} | HP: {hp_val}\033[0m")
    print(f"  \033[92m  ═══════════════════════════════════\033[0m")
    
    return True, {
        'filename': new_filename,
        'name': card_data.get('name', ''),
        'set': card_data.get('set', {}).get('name', ''),
        'set_id': set_id,
        'card_num': card_num,
        'hp': card_data.get('hp', ''),
        'energy': card_data.get('energy_type', ''),
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
            # Record failed capture in database
            database.add_failed_capture(filename)
        
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

def add_to_collection(card_data):
    """Add card to SQLite database collection."""
    set_val = card_data.get('set', {})
    if isinstance(set_val, dict):
        set_val = set_val.get('name', '')
    
    card = {
        'name': card_data.get('name', ''),
        'category': card_data.get('category', 'Pokemon'),
        'set': set_val,
        'card_number': card_data.get('card_number', ''),
        'hp': card_data.get('hp', ''),
        'stage': card_data.get('stage', ''),
        'energy_type': card_data.get('energy_type', ''),
        'evolution_from': card_data.get('evolution_from', ''),
        'ability': card_data.get('ability', ''),
        'attacks': card_data.get('attacks', []),
        'weakness': card_data.get('weakness', ''),
        'resistance': card_data.get('resistance', ''),
        'retreat_cost': card_data.get('retreat_cost', ''),
        'regulation_mark': card_data.get('regulation_mark', ''),
        'rarity': card_data.get('rarity', ''),
        'illustrator': card_data.get('illustrator', ''),
        'effect': card_data.get('effect', ''),
    }
    database.add_card(card)
    print(f"  [DB] Added to collection: {card['name']}")

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
