#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor - V2
EasyOCR + API Match = High Confidence

Workflow:
1. EASYOCR: Extract multiple signals (name, HP, attacks, weakness, retreat)
2. CROSS-REFERENCE: Match against german_cards_complete.json
3. CONFIDENCE CHECK: 
   - >=60% -> Save to collection.db + captured folder + processed list
   - <60% -> Move to failed_to_capture/ (NOT added to processed list - reprocessable)
4. SAVE: Only high-confidence cards added to processed list

Input Folders:
- screenshots/to_process/ (fallback)
- PKM_CARDS/{SET}/ (organized by set, prioritized)
"""

import os
import re
import glob
import sys
import json
import time
from PIL import Image
import pytesseract
import easyocr

from preprocessing import CardCropper, preprocess_image
from extraction import (
    CardType, 
    ZoneExtractor, 
    detect_card_type, 
    DetectionResult
)
import database
from api.local_lookup import lookup_card, load_cards
from PIL import ImageEnhance


def correct_hp_ocr(hp_str: str) -> int | None:
    """
    Correct common OCR errors in HP values.
    Examples: 502→50, 802→80, 0→8, 52→50, 58→50
    """
    if not hp_str:
        return None
    
    # First try direct conversion
    try:
        hp = int(hp_str)
        if 20 <= hp <= 340:
            return hp
    except ValueError:
        pass
    
    # Try removing trailing zeros/Os (502→5→50, 802→8→80)
    for _ in range(2):
        cleaned = hp_str.rstrip('0OQ')
        if cleaned and cleaned != hp_str:
            try:
                hp = int(cleaned)
                if 20 <= hp <= 340:
                    return hp
            except ValueError:
                pass
        hp_str = cleaned
    
    # Try fixing specific common errors
    # 52→50, 58→50, 5S→50
    if len(hp_str) == 2:
        replacements = {'5': '5', '2': '0', '8': '0', 'S': '5'}
        # If second char is close to 0, replace it
        if hp_str[1] in ['2', '7', '1']:
            hp_str = hp_str[0] + '0'
        elif hp_str[1] in ['8', '6', '3']:
            hp_str = hp_str[0] + '0'
        try:
            hp = int(hp_str)
            if 20 <= hp <= 340:
                return hp
        except:
            pass
    
    # Try just the first digit if length > 1
    if len(hp_str) >= 1:
        try:
            hp = int(hp_str[0])
            if hp >= 2 and hp <= 3:  # Valid first digits for HP
                return hp * 10  # 2→20, 3→30, etc
        except:
            pass
    
    return None


def enhance_for_ocr(img: Image.Image) -> Image.Image:
    """
    Enhance image for better OCR results.
    Increases contrast and applies gamma correction.
    """
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)
    
    # Slight sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    return img


# EasyOCR reader (lazy init)
_easyocr_reader = None

def get_easyocr_reader():
    """Get or create EasyOCR reader."""
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['de', 'en'], gpu=True)
    return _easyocr_reader


def easyocr_extract(img: Image.Image) -> dict:
    """Extract card signals using EasyOCR. Format: 'TUSKA KP 60' or 'BASIS PIKACHU KP 60'"""
    reader = get_easyocr_reader()
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        img.save(tmp.name)
        results = reader.readtext(tmp.name)
        os.unlink(tmp.name)
    
    signals = {'name': None, 'hp': None, 'attacks': [], 'weakness': None, 'retreat': None, 'pokedex_number': None}
    
    all_text = ' '.join([text.strip() for bbox, text, conf in results if float(conf) > 0.3])
    print(f"EasyOCR: {all_text[:100]}...")
    
    # Stage words to skip
    stage_words = {'BASIS', 'PHASE', '1', '2', 'STAGE', 'EX', 'GX', 'VMAX', 'VSTAR', 'PROMO'}
    
    # Format: "BASIS TUSKA KP 60" or "TUSKA KP 60" - find word before KP
    # Pattern: WORD KP NUMBER
    words = all_text.split()
    for i, word in enumerate(words):
        word_clean = ''.join(c for c in word if c.isalpha())
        if word_clean.upper() == 'KP' and i > 0:
            # Previous word is the name
            prev_word = words[i-1]
            prev_clean = ''.join(c for c in prev_word if c.isalpha())
            if prev_clean.upper() not in stage_words:
                signals['name'] = prev_clean.upper()
                # Next word is HP
                if i + 1 < len(words):
                    hp_word = words[i + 1]
                    hp_match = re.search(r'(\d{2,3})', hp_word)
                    if hp_match:
                        signals['hp'] = hp_match.group(1)
                break
    
    # Extract attacks
    attack_matches = re.findall(r'([A-ZÄÖÜ][a-zäöüßA-Za-z]{2,})\s+(\d+)(?:\s|$)', all_text)
    skip = {signals['name'], 'KP', 'HP', 'NR', 'FIG', 'SCHWÄCHE', 'RÜCKZUG'}
    for attack_name, damage in attack_matches:
        if attack_name.upper() not in skip and attack_name not in signals['attacks']:
            signals['attacks'].append(f"{attack_name} {damage}")
    
    # Weakness
    weak = re.search(r'Schw[äa]che.*?([A-Za-z]+).*?(\d+)', all_text, re.IGNORECASE)
    if weak:
        signals['weakness'] = f"{weak.group(1)}+{weak.group(2)}"
    
    # Retreat
    retreat = re.search(r'R[üu]ck[gu]?z?\s*(\d+)', all_text, re.IGNORECASE)
    if retreat:
        signals['retreat'] = retreat.group(1)
    
    # Pokédex
    pokedex = re.search(r'Nr\.\s*(\d+)', all_text, re.IGNORECASE)
    if pokedex:
        signals['pokedex_number'] = pokedex.group(1)
    
    return signals


SCREENSHOT_DIR = "screenshots/to_process"
PKM_CARDS_DIR = "PKM_CARDS"  # Folder with set subdirectories (e.g., PKM_CARDS/B1/)
CAPTURED_DIR = "screenshots/captured"
CROPPED_DIR = "screenshots/cropped"
FAILED_DIR = "screenshots/failed_to_capture"
PROGRESS_FILE = "extraction_progress.json"
BATCH_SIZE = 25


def get_all_images():
    """Get all images from both to_process and PKM_CARDS/*/ folders."""
    files = []
    
    # Check PKM_CARDS first (prioritize this)
    if os.path.exists(PKM_CARDS_DIR):
        for set_folder in os.listdir(PKM_CARDS_DIR):
            set_path = os.path.join(PKM_CARDS_DIR, set_folder)
            if os.path.isdir(set_path):
                set_files = glob.glob(os.path.join(set_path, "*.png")) + \
                           glob.glob(os.path.join(set_path, "*.PNG"))
                for f in set_files:
                    files.append((f, set_folder))  # (filepath, set_name)
    
    # Also check to_process
    to_proc = glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")) + \
              glob.glob(os.path.join(SCREENSHOT_DIR, "*.PNG"))
    for f in to_proc:
        files.append((f, None))  # No set info
    
    return sorted(files)


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


def enhanced_ocr_extract(img: Image.Image, card_type: CardType) -> dict:
    """
    EasyOCR: Extract multiple signals from the card using EasyOCR.
    EasyOCR is much better than Tesseract for German text.
    """
    signals = easyocr_extract(img)
    signals['set_id'] = None
    signals['card_number'] = None
    return signals


def match_with_api(ocr_name: str | None, card_type: str, target_set: str | None = None) -> tuple[dict | None, float]:
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
    
    # Try local JSON database first (fast, offline) - with set filter
    set_filter = target_set if target_set else ""
    result = lookup_card(ocr_name, target_set=set_filter)
    
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


def process_card_v2(image_path: str, target_set: str | None = None) -> tuple[bool, dict | None]:
    """
    Process a single card using EasyOCR + Multi-Signal API Match.
    
    Extraction signals:
    1. Name (OCR)
    2. HP (parse from text)
    3. Attack names (OCR)
    4. Weakness (energy type + damage)
    5. Retreat cost
    
    Matching priority:
    1. Exact name match (100%)
    2. Fuzzy name + HP match (90%)
    3. HP + Attack + Set match (85%)
    4. HP + Weakness + Set match (80%)
    5. HP + Retreat + Set match (75%)
    6. Manual review (0%)
    """
    filename = os.path.basename(image_path)
    print(f"\n\033[1;36m[Processing V2]\033[0m {filename}")
    
    # Step 1: Preprocess - crop to card
    print(f"  \033[90m[1/5] Preprocessing...\033[0m")
    img = preprocess_image(image_path)
    print(f"       -> Size: {img.size}")
    
    # Step 2: Detect card type
    print(f"  \033[90m[2/5] Detecting card type...\033[0m")
    card_type = detect_card_type(img)
    print(f"       -> {card_type.value}")
    
    # Step 3: EasyOCR - Extract multiple signals
    print(f"  \033[90m[3/5] EasyOCR (multiple signals)...\033[0m")
    signals = enhanced_ocr_extract(img, card_type)
    print(f"       -> Name: {signals.get('name')}")
    print(f"       -> HP: {signals.get('hp')}")
    print(f"       -> Weakness: {signals.get('weakness')}")
    print(f"       -> Retreat: {signals.get('retreat')}")
    print(f"       -> Attacks: {len(signals.get('attacks', []))}")
    
    ocr_name = signals.get('name')
    
    if not ocr_name:
        print(f"  \033[91m[✗] ERROR: Could not extract name\033[0m")
        return False, None
    
    # Use German name directly for matching
    signals['name'] = ocr_name
    
    # Step 4: Cross-reference OCR with german_cards_complete.json
    print(f"  \033[90m[4/5] Cross-referencing with database...\033[0m")
    
    from api.local_lookup import lookup_card
    
    # Direct lookup first (simple name match)
    set_arg = target_set if target_set else ""
    result = lookup_card(ocr_name, target_set=set_arg)
    
    # Fall back to multi-signal if direct lookup fails
    if not result.success or result.confidence < 0.5:
        from api.local_lookup import match_by_signals
        result = match_by_signals(signals, set_arg)
    
    if result.success and result.confidence >= 0.6 and result.card:
        # Use matched card data
        api_data = card_to_dict(result.card)
        api_data['category'] = card_type.value.title()
        
        match_method = result.match_type.replace('_', ' ').title()
        print(f"  \033[92m[✓] MATCH FOUND: {result.card.name}\033[0m")
        print(f"       -> Method: {match_method}")
        print(f"       -> Confidence: {result.confidence*100:.0f}%")
        print(f"       -> HP: {api_data.get('hp', 'N/A')}")
        print(f"       -> Set: {api_data.get('set', 'N/A')} #{api_data.get('card_number', 'N/A')}")
        if api_data.get('attacks'):
            print(f"       -> Attacks: {len(api_data['attacks'])}")
        
        card_data = api_data
        confidence = result.confidence
        high_confidence = True
    else:
        # No match - NOT added to collection, goes to failed
        print(f"  \033[91m[✗] NO MATCH - Low confidence ({result.confidence if result.confidence else 0:.0f}%)\033[0m")
        print(f"       -> OCR name: {ocr_name}")
        print(f"       -> Moving to failed_to_capture/")
        
        # Move to failed folder
        failed_path = os.path.join(FAILED_DIR, os.path.basename(image_path))
        os.rename(image_path, failed_path)
        
        return False, None
    
    # Save to database ONLY if high confidence
    add_to_collection(card_data)
    
    # Get set and card number for filenames
    set_id = card_data.get('set', 'UNK')
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


def run_batch_v2(start_index=0, batch_size=BATCH_SIZE, target_set=None):
    progress = load_progress()
    processed_files = set(progress.get('processed', []))
    failed_files = set(progress.get('failed', []))
    
    # Get all images with set info
    all_files_with_set = get_all_images()
    
    # Filter by set if specified
    if target_set:
        all_files_with_set = [(f, s) for f, s in all_files_with_set if s and s.upper() == target_set.upper()]
        print(f"\n[FILTER] Processing set: {target_set}")
    
    # Extract just filepaths for filtering
    all_files = [f for f, s in all_files_with_set]
    
    files_to_process = [
        (f, s) for f, s in all_files_with_set 
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
    if target_set:
        print(f"\033[90m  Set filter: {target_set}\033[0m")
    print(f"\033[1;36m{'═'*50}\033[0m")
    
    # Pre-load API database
    print(f"\033[90m  Loading API database...\033[0m")
    cards = load_cards()
    print(f"\033[90m  Loaded {len(cards)} cards from local cache\033[0m\n")
    
    results = []
    
    for i, (filepath, set_name) in enumerate(batch):
        idx = start_index + i
        filename = os.path.basename(filepath)
        
        success, card = process_card_v2(filepath, target_set=set_name)
        
        if success:
            results.append(card)
            processed_files.add(filename)
        else:
            # File already moved to failed inside process_card_v2
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
        print("  python3 extract_batch_v2.py run [count] [--set SET]")
        print("  python3 extract_batch_v2.py reset")
        return
    
    cmd = sys.argv[1]
    target_set = None
    
    # Check for --set flag
    if '--set' in sys.argv:
        set_idx = sys.argv.index('--set')
        if set_idx + 1 < len(sys.argv):
            target_set = sys.argv[set_idx + 1]
    
    if cmd == 'status':
        show_status()
    elif cmd == 'reset':
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
        print("[RESET] Done")
    elif cmd == 'run':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else BATCH_SIZE
        progress = load_progress()
        start = progress.get('last_index', -1) + 1
        run_batch_v2(start, batch_size, target_set)
    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
