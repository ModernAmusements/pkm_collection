#!/usr/bin/env python3
"""
Pokemon TCG Pocket Card Extractor
- OCR extracts card data from screenshots
- Compares with tcgdex API for validation
- Outputs CSV with German card data
"""

import os
import re
import csv
import glob
import sys
from collections import Counter
from pathlib import Path
import requests
from PIL import Image
import pytesseract

# === CONFIG ===
SCREENSHOT_DIR = "screenshots/captured"
TEST_IMAGE = "test_card.png"
OUTPUT_CSV = "my_cards_full.csv"
OCR_FAILED_DIR = "screenshots/ocr_failed"
API_BASE = "https://api.tcgdex.net/v2/de/cards"

# Energy type mapping (German -> English)
ENERGY_MAP = {
    "Feuer": ("Fire", "red"),
    "Wasser": ("Water", "blue"),
    "Elektro": ("Lightning", "yellow"),
    "Pflanze": ("Grass", "green"),
    "Kampf": ("Fighting", "orange"),
    "Psycho": ("Psychic", "purple"),
    "Unlicht": ("Darkness", "black"),
    "Metall": ("Metal", "gray"),
    "Fee": ("Fairy", "pink"),
    "Drache": ("Dragon", "brown"),
    "Farblos": ("Colorless", "gray"),
}

# === FUNCTIONS ===

def parse_filename(filename):
    """
    Parse filename like 'Abra_A1_115.png' or 'Absol_A3_112_1.png'
    Returns: (name, set_id, card_number, duplicate_count)
    
    Examples:
      Abra_A1_115.png      → (Abra, A1, 115, 1)
      Absol_A3_112.png     → (Absol, A3, 112, 1)
      Absol_A3_112_1.png   → (Absol, A3, 112, 2) - duplicate (2nd copy)
      Absol_A3_112_2.png   → (Absol, A3, 112, 3) - duplicate (3rd copy)
      Icognito_A2a_34.png  → (Icognito, A2a, 34, 1)
    """
    import re
    name = os.path.splitext(filename)[0]
    
    # Pattern 1: name_SetID_cardNumber (no duplicate) e.g., "Abra_A1_115"
    # Letters only for name, then underscore, then set (alphanumeric), then underscore, then number
    match = re.match(r'^([A-Za-z]+)_([A-Za-z0-9]+)_(\d+)$', name)
    if match:
        card_name = match.group(1)
        set_id = match.group(2)
        card_num = int(match.group(3))
        return card_name, set_id, card_num, 1
    
    # Pattern 2: name_SetID_cardNumber_duplicateNumber e.g., "Absol_A3_112_1"
    match = re.match(r'^([A-Za-z]+)_([A-Za-z0-9]+)_\d+_(\d+)$', name)
    if match:
        card_name = match.group(1)
        set_id = match.group(2)
        card_num = int(match.group(3))
        # Extract the duplicate number from the full match
        dup_match = re.search(r'_(\d+)$', name)
        if dup_match:
            dup = int(dup_match.group(1)) + 1  # _1 = 2nd copy, _2 = 3rd copy
            return card_name, set_id, card_num, dup
    
    return None, None, None, None


def extract_card_data_ocr(image_path):
    """
    Extract card data from screenshot using OCR
    Returns dict with extracted fields
    """
    print(f"  [OCR] Processing: {os.path.basename(image_path)}")
    
    img = Image.open(image_path)
    width, height = img.size
    print(f"  [OCR] Image size: {width}x{height}")
    
    # Try eng first (fallback if deu not installed)
    try:
        full_text = pytesseract.image_to_string(img, lang='deu')
    except:
        print(f"  [OCR] German not available, using English...")
        full_text = pytesseract.image_to_string(img, lang='eng')
    
    print(f"  [OCR] Full text:\n{full_text[:500]}...")
    
    # Parse HP (KP in German) - look for number followed by KP
    hp_match = re.search(r'(\d+)\s*KP?', full_text, re.IGNORECASE)
    hp = hp_match.group(1) if hp_match else ""
    print(f"  [OCR] HP found: '{hp}'")
    
    # Parse card name - look for line after the HP area
    # German cards typically have name near the top
    lines = full_text.split('\n')
    card_name = ""
    
    # Look for Pokemon name (typically capitalized, 3+ chars)
    for i, line in enumerate(lines):
        line = line.strip()
        # Skip short lines, numbers, common UI
        if line and len(line) >= 3 and not line.isdigit():
            # Skip common UI text
            skip_words = ['Nr', 'Symbol', 'Pokemon', 'Grosse', 'Gewicht', 'Gr']
            if any(skip in line for skip in skip_words):
                continue
            card_name = line
            break
    
    print(f"  [OCR] Card name found: '{card_name}'")
    
    # Parse Retreat Cost - German "Rückzug" or English "Retreat"
    retreat_match = re.search(r'(?:Rückzug|Retreat)\s*(\d+)', full_text, re.IGNORECASE)
    retreat = retreat_match.group(1) if retreat_match else ""
    print(f"  [OCR] Retreat found: '{retreat}'")
    
    # Parse attacks - look for patterns like "Name Number" where number is damage
    # German uses numbers in attacks
    attack_matches = re.findall(r'(\w+)\s+(\d+)', full_text)
    attacks = []
    for name, damage in attack_matches:
        if int(damage) > 0 and int(damage) <= 300:  # Reasonable damage range
            attacks.append({'name': name, 'damage': damage})
    print(f"  [OCR] Potential attacks: {attacks[:5]}")
    
    return {
        'name': card_name.strip(),
        'hp': hp,
        'retreat': retreat,
        'attacks': attacks,
        'full_text': full_text,
    }


def fetch_card_from_api(set_id, card_num):
    """
    Fetch card data from tcgdex API
    """
    # Pad card number to 3 digits
    card_id = f"{set_id}-{card_num:03d}"
    url = f"{API_BASE}/{card_id}"
    print(f"  [API] Fetching: {url}")
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"  [API] Found: {data.get('name')} - {data.get('hp')} KP - {data.get('rarity')}")
            return data
        else:
            print(f"  [API] Not found: {resp.status_code}")
    except Exception as e:
        print(f"  [API] Error: {e}")
    
    return None


def search_card_by_name(name):
    """
    Search for card by name in API - ONLY TCG Pocket sets
    TCG Pocket sets: A1, A1a, A2, A2a, A2b, A3, A3a, A3b, A4, A4a, Pikachu, etc.
    Returns: (set_id, card_num, api_data) or (None, None, None)
    """
    # TCG Pocket sets
    tcgp_sets = ['A1', 'A1a', 'A2', 'A2a', 'A2b', 'A3', 'A3a', 'A3b', 'A4', 'A4a', 'Pikachu']
    
    # Search by name
    url = f"{API_BASE}?name={name}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            results = resp.json()
            if results and len(results) > 0:
                # Find first TCG Pocket card
                for card in results:
                    card_id = card.get('id', '')
                    set_id = card_id.split('-')[0] if '-' in card_id else ''
                    
                    # Check if it's a TCG Pocket set
                    if set_id in tcgp_sets:
                        # Fetch full card data to get HP
                        full_card = fetch_card_from_api(set_id, int(card.get('localId', 0)))
                        if full_card and full_card.get('hp'):
                            return set_id, int(card.get('localId', 0)), full_card
    except Exception as e:
        print(f"  [SEARCH] Error: {e}")
    return None, None, None


def process_screenshot(image_path):
    """
    Process a single screenshot:
    1. OCR to find card name
    2. Search API for card by name
    3. Get set/card number
    4. Rename file
    5. Fetch full data
    """
    filename = os.path.basename(image_path)
    print(f"\n{'='*60}")
    print(f"Processing: {filename}")
    print('='*60)
    
    # OCR the image to find card name
    ocr_data = extract_card_data_ocr(image_path)
    ocr_name = ocr_data.get('name', '').strip()
    
    if not ocr_name:
        print(f"[ERROR] Could not extract card name from: {filename}")
        # Move to OCR failed
        os.makedirs(OCR_FAILED_DIR, exist_ok=True)
        failed_path = os.path.join(OCR_FAILED_DIR, filename)
        os.rename(image_path, failed_path)
        print(f"[MOVED] to {OCR_FAILED_DIR}/")
        return None
    
    print(f"[OCR] Found name: {ocr_name}")
    
    # Search API for this card name
    set_id, card_num, api_data = search_card_by_name(ocr_name)
    
    if not api_data:
        print(f"[WARNING] No API match for: {ocr_name}")
        # Move to OCR failed
        os.makedirs(OCR_FAILED_DIR, exist_ok=True)
        failed_path = os.path.join(OCR_FAILED_DIR, filename)
        os.rename(image_path, failed_path)
        print(f"[MOVED] to {OCR_FAILED_DIR}/")
        return None
    
    print(f"[API] Matched: {api_data.get('name')} - Set: {set_id}, Num: {card_num}")
    
    # Rename the file
    card_name = api_data.get('name')
    new_filename = f"{card_name}_{set_id}_{card_num}.png"
    new_path = os.path.join(SCREENSHOT_DIR, new_filename)
    
    # Handle duplicates - if file exists, add suffix
    dup_count = 1
    while os.path.exists(new_path):
        dup_count += 1
        new_filename = f"{card_name}_{set_id}_{card_num}_{dup_count-1}.png"
        new_path = os.path.join(SCREENSHOT_DIR, new_filename)
    
    os.rename(image_path, new_path)
    print(f"[RENAMED] → {new_filename}")
    
    # Merge OCR + API data
    card_data = {
        'filename': new_filename,
        'card_name_ocr': ocr_name,
        'card_name_api': api_data.get('name', ''),
        'hp_ocr': ocr_data.get('hp', ''),
        'hp_api': str(api_data.get('hp', '')),
        'set_id': set_id,
        'set_name_api': api_data.get('set', {}).get('name', ''),
        'card_num': card_num,
        'duplicates': dup_count,
        'energy_type': api_data.get('types', [''])[0],
        
        # Weakness
        'weakness_type': api_data.get('weaknesses', [{}])[0].get('type', ''),
        'weakness_value': api_data.get('weaknesses', [{}])[0].get('value', ''),
        
        'retreat': ocr_data.get('retreat') or str(api_data.get('retreat', '')),
        'rarity': api_data.get('rarity', ''),
        'stage': api_data.get('stage', ''),
        'description': api_data.get('description', ''),
        
        # Abilities
        'abilities': api_data.get('abilities', []),
        
        # Attacks
        'attacks': api_data.get('attacks', []),
        
        'api_data': api_data,
        'ocr_data': ocr_data,
    }
    
    # Print summary
    print(f"\n[SUMMARY]")
    print(f"  Name: {card_data['card_name_api']}")
    print(f"  HP: {card_data['hp_api']}")
    print(f"  Set: {card_data['set_name_api']}")
    print(f"  Rarity: {card_data['rarity']}")
    
    return card_data


def write_csv(cards, output_path):
    """
    Write cards to CSV - matching the existing structure
    """
    fieldnames = [
        'Card Name',
        'HP',
        'Energy Type',
        'Weakness',
        'Resistance',
        'Retreat Cost',
        'Ability Name',
        'Ability Description',
        'Attack 1 Name',
        'Attack 1 Cost',
        'Attack 1 Damage',
        'Attack 1 Description',
        'Attack 2 Name',
        'Attack 2 Cost',
        'Attack 2 Damage',
        'Attack 2 Description',
        'Rarity',
        'Pack'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for card in cards:
            # Extract ability data
            abilities = card.get('abilities', [])
            ability = abilities[0] if abilities else {}
            
            # Extract attack data  
            attacks = card.get('attacks', [])
            attack1 = attacks[0] if len(attacks) > 0 else {}
            attack2 = attacks[1] if len(attacks) > 1 else {}
            
            # Format weakness
            weakness = ""
            if card.get('weakness_type') and card.get('weakness_value'):
                weakness = f"{card['weakness_type']} {card['weakness_value']}"
            
            row = {
                'Card Name': card.get('card_name_ocr') or card.get('card_name_api', ''),
                'HP': card.get('hp_ocr') or card.get('hp_api', ''),
                'Energy Type': card.get('energy_type', ''),
                'Weakness': weakness,
                'Resistance': '',
                'Retreat Cost': card.get('retreat', ''),
                'Ability Name': ability.get('name', ''),
                'Ability Description': ability.get('effect', ''),
                'Attack 1 Name': attack1.get('name', ''),
                'Attack 1 Cost': ', '.join(attack1.get('cost', [])),
                'Attack 1 Damage': str(attack1.get('damage', '')),
                'Attack 1 Description': attack1.get('effect', ''),
                'Attack 2 Name': attack2.get('name', ''),
                'Attack 2 Cost': ', '.join(attack2.get('cost', [])),
                'Attack 2 Damage': str(attack2.get('damage', '')),
                'Attack 2 Description': attack2.get('effect', ''),
                'Rarity': card.get('rarity', ''),
                'Pack': card.get('set_name_api', ''),
            }
            writer.writerow(row)


def process_test_card():
    """
    Test OCR on a single card
    """
    print("\n" + "="*60)
    print("TEST MODE - Processing test_card.png")
    print("="*60 + "\n")
    
    if not os.path.exists(TEST_IMAGE):
        print(f"[ERROR] Test image not found: {TEST_IMAGE}")
        return
    
    # Test OCR + API search on test card
    print("[TEST] Running OCR + API search on test_card.png")
    
    ocr_data = extract_card_data_ocr(TEST_IMAGE)
    full_text = ocr_data.get('full_text', '')
    
    # Print full text to see what's extracted
    print(f"\n[OCR] Full text:\n{full_text}")
    
    # Look for card name - search for any German Pokemon name in text
    import re
    
    # Get all capitalized words
    words = re.findall(r'([A-Z][a-z]+)', full_text)
    
    # Filter common OCR misreads and UI text - MINIMAL skip list
    skip = {'Nr', 'Symbol', 'Pokemon', 'CHECK', 'Will'}
    
    # Search API for each candidate name
    card_name = None
    card_data = None
    
    print(f"\n[OCR] Found words: {words[:15]}")  # First 15 words
    
    for word in words:
        if word in skip:
            continue
        if len(word) >= 3:
            print(f"[API] Searching for: {word}")
            # Search API for this name
            sid, cnum, api_data = search_card_by_name(word)
            print(f"[API] Result: set={sid}, num={cnum}, data={api_data}")
            if api_data:
                # Check if it's a TCG Pocket card (has hp)
                if api_data.get('hp'):
                    card_name = word
                    card_data = (sid, cnum, api_data)
                    print(f"[MATCH] Found: {api_data.get('name')} (HP: {api_data.get('hp')})")
                    break
    
    if card_data:
        set_id, card_num, api_data = card_data
        print(f"\n[API] Found: {api_data.get('name')} - Set: {set_id}, Num: {card_num}")
        print(f"  HP: {api_data.get('hp')}")
        print(f"  Rarity: {api_data.get('rarity')}")
        print(f"  Set: {api_data.get('set', {}).get('name')}")
        print("\n[TEST] SUCCESS!")
    else:
        print("[TEST] No match found")
    
    print("\n" + "="*60)


def main():
    """
    Main entry point
    """
    print("="*60)
    print("Pokemon TCG Pocket Card Extractor")
    print("="*60)
    
    # Check if test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        process_test_card()
        return
    
    # Get all screenshots
    screenshots = sorted(glob.glob(os.path.join(SCREENSHOT_DIR, "*.png")))
    
    print(f"\nFound {len(screenshots)} screenshots in {SCREENSHOT_DIR}")
    
    if not screenshots:
        print("No screenshots found!")
        return
    
    # Process each screenshot
    all_cards = []
    ocr_failed = []
    
    for i, screenshot in enumerate(screenshots):
        print(f"\n[{i+1}/{len(screenshots)}] Processing: {os.path.basename(screenshot)}")
        
        card = process_screenshot(screenshot)
        if card:
            all_cards.append(card)
        else:
            ocr_failed.append(screenshot)
    
    # Write CSV
    write_csv(all_cards, OUTPUT_CSV)
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print(f"Total screenshots: {len(screenshots)}")
    print(f"Successfully processed: {len(all_cards)}")
    print(f"Failed (moved to ocr_failed): {len(ocr_failed)}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
