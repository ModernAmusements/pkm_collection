#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor - V2
Minimal OCR + API Match = 100% Confidence

Workflow:
1. MINIMAL OCR: Extract only NAME from card image
2. API MATCH: Find card by OCR name in scraped database
3. VERIFY: If name matches → 100% confidence, use ALL API data
4. SAVE: Store complete card data from API (not OCR)
"""

import os
import re
import glob
import sys
import json
import time
from PIL import Image
import pytesseract

from preprocessing import CardCropper, preprocess_image
from extraction import (
    CardType, 
    ZoneExtractor, 
    detect_card_type, 
    DetectionResult
)
import database
from api.local_lookup import lookup_card, load_cards
from api.german_mappings import GERMAN_TO_ENGLISH


def translate_to_english(text: str) -> str:
    """Translate German card names to English using mapping."""
    text_lower = text.lower().strip()
    
    # Check for "ex" suffix before translation
    has_ex = text_lower.endswith(' ex') or ' ex' in text_lower
    
    # Try direct match first
    if text_lower in GERMAN_TO_ENGLISH:
        result = GERMAN_TO_ENGLISH[text_lower]
        if has_ex and 'ex' not in result.lower():
            result = result + ' ex'
        return result.title() if result[0].islower() else result
    
    # Try partial match - look for German substring
    for ger, eng in GERMAN_TO_ENGLISH.items():
        if ger in text_lower:
            result = eng
            if has_ex and 'ex' not in result.lower():
                result = result + ' ex'
            return result.title() if result[0].islower() else result
    
    return text


# Continue with rest of imports/classes
from api.limitless import scrape_card


SCREENSHOT_DIR = "screenshots/to_process"
CAPTURED_DIR = "screenshots/captured"
CROPPED_DIR = "screenshots/cropped"
FAILED_DIR = "screenshots/failed_to_capture"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'failed': [], 'last_index': -1}


def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)


def minimal_ocr_name(img: Image.Image, card_type: CardType) -> str | None:
    """
    MINIMAL OCR: Extract only the card NAME.
    This is all we need to match against the API database.
    
    Tries multiple zones as fallback for full art cards.
    """
    extractor = ZoneExtractor()
    
    # Define zones to try in order of preference
    # For Pokemon: name -> card_number -> bottom edge
    # For Trainer: name -> type
    zones_to_try = []
    
    if card_type == CardType.POKEMON:
        zones_to_try = [
            ('name', CardType.POKEMON),
            ('card_number', CardType.POKEMON),
            ('evolution', CardType.POKEMON),
        ]
    else:
        zones_to_try = [
            ('name', CardType.TRAINER),
            ('type', CardType.TRAINER),
        ]
    
    for zone_name, ctype in zones_to_try:
        zone = extractor.extract(img, zone_name, ctype)
        
        if zone is None:
            continue
        
        # Try multiple PSM modes for better OCR
        for psm in ['6', '4', '11']:
            text = pytesseract.image_to_string(zone, config=f'--psm {psm}')
            
            if not text:
                continue
            
            # Extract name - find capitalized words
            lines = text.strip().split('\n')[:5]
            for line in lines:
                words = line.split()
                for word in words:
                    clean = ''.join(c for c in word if c.isalpha())
                    # Skip OCR artifacts and short words
                    if len(clean) >= 3 and clean[0].isupper():
                        clean = clean.upper()
                        # Skip common OCR artifacts
                        if clean.startswith('EAS'):
                            continue
                        if clean in ['THE', 'AND', 'FOR', 'BUT', 'NOT', 'YOU', 'ARE', 'HAS', 'HAD', 'WAS', 'WERE']:
                            continue
                        # Valid name found
                        return clean
    
    # Last resort: try full image OCR for very different card layouts
    # This is slower but might catch full art cards
    for psm in ['6', '3']:
        text = pytesseract.image_to_string(img, config=f'--psm {psm}')
        if text:
            # Look for Pokemon-like names (capitalized words)
            words = text.split()
            for i, word in enumerate(words):
                clean = ''.join(c for c in word if c.isalpha())
                if len(clean) >= 4 and clean[0].isupper():
                    # Check if next word might be 'ex' or similar
                    next_word = words[i+1] if i+1 < len(words) else ''
                    next_clean = ''.join(c for c in next_word if c.isalpha())
                    if next_clean.lower() in ['ex', 'gx', 'vmax', 'v']:
                        return clean + ' ex'
                    return clean
    
    return None


def match_with_api(ocr_name: str, card_type: str) -> tuple[dict | None, float]:
    """
    Match OCR name with API database.
    Returns: (matched_card_data, confidence)
    
    If name matches EXACTLY → 100% confidence
    If name matches FUZZY → 90% confidence  
    If name matches CLOSEST → 80% confidence
    If no match → None, 0%
    """
    if not ocr_name:
        return None, 0.0
    
    # Try local JSON database first (fast, offline)
    result = lookup_card(ocr_name)
    
    if result.success and result.card:
        # Check match type and assign confidence
        if result.match_type == 'exact':
            return card_to_dict(result.card), 1.0  # 100% confidence
        elif result.match_type == 'fuzzy':
            return card_to_dict(result.card), 0.9  # 90% confidence
        elif result.match_type == 'closest':
            # Check if names are similar enough (case-insensitive)
            if result.card.name.lower() == ocr_name.lower():
                return card_to_dict(result.card), 0.95  # Very likely match
            return card_to_dict(result.card), 0.7  # Lower confidence
        else:
            return card_to_dict(result.card), result.confidence
    
    return None, 0.0


def card_to_dict(card) -> dict:
    """Convert API CardData to dict for database."""
    attacks_list = []
    if card.attacks:
        for att in card.attacks:
            if isinstance(att, dict):
                attacks_list.append(att)
            else:
                attacks_list.append({'name': str(att), 'damage': '', 'effect': ''})
    
    # Format weakness with + damage (non-EX = 2x, EX = 1x)
    weakness = card.weakness or ''
    if weakness and card.hp:
        # Calculate weakness damage: non-EX = 2xHP, EX = 1xHP
        damage = card.hp * 2 if 'ex' not in card.name.lower() else card.hp
        weakness = f"{weakness}+{damage}"
    
    return {
        'name': card.name,
        'category': 'Pokemon' if card.energy_type else 'Trainer',
        'set': card.set_name or card.set_id,
        'set_id': card.set_id,
        'card_number': card.card_number,
        'hp': str(card.hp) if card.hp else '',
        'stage': card.stage or '',
        'energy_type': card.energy_type or '',
        'evolution_from': card.evolution_from or '',
        'attacks': attacks_list,
        'weakness': weakness,
        'retreat_cost': str(card.retreat) if card.retreat else '',
        'rarity': card.rarity or '',
        'illustrator': card.illustrator or '',
    }


def process_card_v2(image_path: str) -> tuple[bool, dict | None]:
    """
    Process a single card using Minimal OCR + API Match.
    Goal: 100% confidence by matching with scraped API data.
    """
    filename = os.path.basename(image_path)
    print(f"\n\033[1;36m[Processing V2]\033[0m {filename}")
    
    # Step 1: Preprocess - crop to card
    print(f"  \033[90m[1/4] Preprocessing...\033[0m")
    img = preprocess_image(image_path)
    print(f"       -> Size: {img.size}")
    
    # Step 2: Detect card type
    print(f"  \033[90m[2/4] Detecting card type...\033[0m")
    card_type = detect_card_type(img)
    print(f"       -> {card_type.value}")
    
    # Step 3: MINIMAL OCR - Extract ONLY name
    print(f"  \033[90m[3/4] Minimal OCR (name only)...\033[0m")
    ocr_name = minimal_ocr_name(img, card_type)
    
    if not ocr_name:
        print(f"  \033[91m[✗] ERROR: Could not extract name\033[0m")
        return False, None
    
    print(f"       -> OCR Name: {ocr_name}")
    
    # Translate German to English if needed
    translated_name = translate_to_english(ocr_name)
    if translated_name != ocr_name:
        print(f"       -> Translated: {translated_name}")
        ocr_name = translated_name
    
    # Step 4: API Match
    print(f"  \033[90m[4/4] API Match...\033[0m")
    api_data, confidence = match_with_api(ocr_name, card_type.value)
    
    if api_data and confidence >= 0.9:
        # 100% confidence - use ALL API data
        card_data = api_data
        card_data['category'] = card_type.value.title()
        print(f"  \033[92m[✓] MATCH FOUND: {card_data['name']}\033[0m")
        print(f"       -> Confidence: {confidence*100:.0f}%")
        print(f"       -> HP: {card_data.get('hp', 'N/A')}")
        print(f"       -> Set: {card_data.get('set', 'N/A')} #{card_data.get('card_number', 'N/A')}")
        if card_data.get('attacks'):
            print(f"       -> Attacks: {len(card_data['attacks'])}")
    else:
        # No match - use minimal OCR data, flag for review
        print(f"  \033[93m[!] NO API MATCH\033[0m")
        print(f"       -> Using OCR data only (low confidence)")
        card_data = {
            'name': ocr_name,
            'category': card_type.value.title(),
            'set': 'OCR',
            'card_number': '0',
            'confidence': 0.0,
        }
        confidence = 0.0
    
    # Save to database
    add_to_collection(card_data)
    
    # Get set and card number for filenames
    set_id = card_data.get('set', 'OCR')
    card_num = card_data.get('card_number', '0')
    
    # Save cropped image
    os.makedirs(CROPPED_DIR, exist_ok=True)
    cropped_filename = f"{card_data['name']}_{set_id}_{card_num}_cropped.png"
    cropped_path = os.path.join(CROPPED_DIR, cropped_filename)
    img.save(cropped_path)
    
    # Move original to captured
    new_filename = f"{card_data['name']}_{set_id}_{card_num}.png"
    new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    dup = 1
    while os.path.exists(new_path):
        dup += 1
        new_filename = f"{card_data['name']}_{set_id}_{card_num}_{dup-1}.png"
        new_path = os.path.join(CAPTURED_DIR, new_filename)
    
    os.rename(image_path, new_path)
    
    print(f"  \033[92m[✓] SAVED: {card_data['name']}\033[0m")
    
    return True, {
        'filename': new_filename,
        'name': card_data['name'],
        'set': set_id,
        'card_num': card_num,
        'hp': card_data.get('hp', ''),
        'confidence': confidence,
    }


def add_to_collection(card_data: dict):
    """Add card to SQLite database."""
    import json
    
    attacks_json = None
    if card_data.get('attacks'):
        attacks_json = json.dumps(card_data['attacks'])
    
    card = {
        'name': card_data.get('name', ''),
        'category': card_data.get('category', 'Pokemon'),
        'set': card_data.get('set', ''),
        'card_number': card_data.get('card_number', ''),
        'hp': card_data.get('hp', ''),
        'stage': card_data.get('stage', ''),
        'energy_type': card_data.get('energy_type', ''),
        'evolution_from': card_data.get('evolution_from', ''),
        'attacks': attacks_json,
        'weakness': card_data.get('weakness', ''),
        'resistance': '',
        'retreat_cost': card_data.get('retreat_cost', ''),
        'rarity': card_data.get('rarity', ''),
        'illustrator': card_data.get('illustrator', ''),
    }
    database.add_card(card)
    print(f"       [DB] Added: {card['name']}")


def run_batch_v2(start_index=0, batch_size=BATCH_SIZE):
    progress = load_progress()
    processed_files = set(progress.get('processed', []))
    failed_files = set(progress.get('failed', []))
    
    all_files = sorted(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")) + 
                      glob.glob(os.path.join(SCREENSHOT_DIR, "*.PNG")))
    
    files_to_process = [
        f for f in all_files 
        if os.path.basename(f) not in processed_files 
        and os.path.basename(f) not in failed_files
    ]
    
    if batch_size >= len(files_to_process):
        batch = files_to_process
        start_index = 0
    else:
        batch = files_to_process[start_index:start_index + batch_size]
    
    if not batch:
        print(f"\n\033[92m[✓] All cards already processed!\033[0m")
        return
    
    print(f"\n\033[1;36m{'═'*50}\033[0m")
    print(f"\033[1;36m  BATCH V2 - Minimal OCR + API Match\033[0m")
    print(f"\033[90m  Cards {start_index+1}-{min(start_index+batch_size, len(files_to_process))} of {len(files_to_process)}\033[0m")
    print(f"\033[1;36m{'═'*50}\033[0m")
    
    # Pre-load API database
    print(f"\033[90m  Loading API database...\033[0m")
    cards = load_cards()
    print(f"\033[90m  Loaded {len(cards)} cards from local cache\033[0m\n")
    
    results = []
    
    for i, filepath in enumerate(batch):
        idx = start_index + i
        filename = os.path.basename(filepath)
        
        success, card = process_card_v2(filepath)
        
        if success:
            results.append(card)
            processed_files.add(filename)
        else:
            failed_path = os.path.join(FAILED_DIR, filename)
            os.rename(filepath, failed_path)
            failed_files.add(filename)
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
    print(f"\n\033[1;36m{'═'*50}\033[0m")
    return results


def show_status():
    progress = load_progress()
    to_proc = len(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")) + 
                 glob.glob(os.path.join(SCREENSHOT_DIR, "*.PNG")))
    captured = len(glob.glob(os.path.join(CAPTURED_DIR, "*.png")))
    failed = len(glob.glob(os.path.join(FAILED_DIR, "*.png")))
    
    print(f"\n\033[1;36m{'═'*40}\033[0m")
    print(f"  \033[1;37mPOKEMON TCG POCKET - V2\033[0m")
    print(f"\033[1;36m{'─'*40}\033[0m")
    print(f"  \033[33m[●] To process:\033[0m   {to_proc}")
    print(f"  \033[92m[✓] Captured:\033[0m    {captured}")
    print(f"  \033[91m[✗] Failed:\033[0m      {failed}")
    print(f"\n\033[90m  Minimal OCR + API Match\033[0m")
    print(f"\033[1;36m{'═'*40}\033[0m\n")


def main():
    os.makedirs(CAPTURED_DIR, exist_ok=True)
    os.makedirs(CROPPED_DIR, exist_ok=True)
    os.makedirs(FAILED_DIR, exist_ok=True)
    
    if len(sys.argv) == 1:
        show_status()
        print("Usage:")
        print("  python3 extract_batch_v2.py status")
        print("  python3 extract_batch_v2.py run [count]")
        print("  python3 extract_batch_v2.py reset")
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
        run_batch_v2(start, batch_size)
    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
