#!/usr/bin/env python3
"""
Incremental German Card Scraper - Only scrape missing cards.

Compares existing data against official set counts. Uses:
1. pokemongohub.net for German data (preferred)
2. Limitless English data as fallback (when German source is blocked)

Updates both JSON cache and database.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

BASE_URL = 'https://pocket.pokemongohub.net'

# Official card counts per set (update when new sets release)
OFFICIAL_SETS = {
    'A1': 286,
    'A1a': 86,
    'A2': 207,
    'A2a': 96,
    'A2b': 111,
    'A3': 239,
    'A3a': 103,
    'A3b': 107,
    'A4': 241,
    'A4a': 105,
    'A4b': 379,
    'B1': 331,
    'B1a': 103,
    'PROMO-A': 108,
    'PROMO-B': 11,
}

SETS = [
    ("A1", "t3hb77i3xy08no0-unschlagbare-gene", "Unschlagbare Gene"),
    ("A1a", "bh6swrnbnb0xqp7-mysterise-insel", "Mysteriöse Insel"),
    ("A2", "i344270g8xo3wb9-kollision-von-raum-und-zeit", "Kollision von Raum und Zeit"),
    ("A2a", "j6yh136n6ar7m1q-licht-des-triumphs", "Licht des Triumphs"),
    ("A2b", "48r74kv8tun9j02-glnzendes-festival", "Glänzendes Festival"),
    ("A3", "797ubb2z58mtxl1-hter-des-firmaments", "Hüter des Firmaments"),
    ("A3a", "n112zho988s4v74-extradimensional-crisis", "Extradimensional Crisis"),
    ("A3b", "0g49s62r1wb1p2b-evoli-hain", "Evoli-Hain"),
    ("A4", "h61dsk33evt45mp-weisheit-von-meer-und-himmel", "Weisheit von Meer und Himmel"),
    ("A4a", "h5n4a0fs0kvgztc-verborgene-quelle", "Verborgene Quelle"),
    ("A4b", "dzswkhwwfk811kd-deluxepack-ex", "Deluxepack-ex"),
    ("PROMO-A", "hrvgwu3dwxaboc7-promo-a", "PROMO-A"),
    ("PROMO-B", "vxunkwyap88g5jr-promo-b", "PROMO-B"),
    ("B1", "0guapr9h7we56l3-mega-aufstieg", "Mega-Aufstieg"),
    ("B1a", "jzb6gjz5xmiw7pu-crimson-blaze", "Crimson Blaze"),
]

CACHE_FILE = 'api/cache/german_cards_complete.json'
LIMITLESS_FILE = 'api/cache/limitless_cards.json'
ENG_TO_GER_FILE = 'api/cache/eng_to_ger_names.json'


def clean_german_name(name: str) -> str:
    """Clean German card name - REMOVE any trailing backslashes.
    
    RULE: We only MAP/translate names - never append anything.
    The backslash was an artifact from the scraper that must be removed.
    """
    if not name:
        return ''
    # Remove trailing backslash or other artifacts
    return name.rstrip('\\').strip()


def load_limitless_cards(set_id: Optional[str] = None) -> list:
    """Load English cards from Limitless cache.
    
    Args:
        set_id: Optional set ID to filter by (e.g., 'B1a')
    
    Returns:
        List of cards with translated German names + extra fields
    """
    if not os.path.exists(LIMITLESS_FILE):
        return []
    
    with open(LIMITLESS_FILE, 'r', encoding='utf-8') as f:
        limitless = json.load(f)
    
    # Load English to German mapping
    eng_to_ger = {}
    if os.path.exists(ENG_TO_GER_FILE):
        with open(ENG_TO_GER_FILE, 'r', encoding='utf-8') as f:
            eng_to_ger = json.load(f)
    
    # Filter by set if specified
    if set_id:
        limitless = [c for c in limitless if c.get('set_id', '').lower() == set_id.lower()]
    
    # Convert English cards to German format
    german_cards = []
    for card in limitless:
        eng_name = card.get('name', '')
        
        # Translate to German
        ger_name = eng_to_ger.get(eng_name, eng_name)
        
        # Get evolution_from from English
        evolution_from = card.get('evolution_from', '')
        if evolution_from:
            evolution_from = eng_to_ger.get(evolution_from, evolution_from)
        
        # Build attacks with proper energy costs
        attacks = []
        for att in card.get('attacks', []):
            att_name = att.get('name', '')
            att_damage = str(att.get('damage', ''))
            att_cost = att.get('cost', [])
            
            # Map energy costs to German
            energy_map = {
                'Fire': 'Fire', 'Water': 'Water', 'Grass': 'Grass',
                'Lightning': 'Lightning', 'Psychic': 'Psychic',
                'Fighting': 'Fighting', 'Darkness': 'Darkness',
                'Metal': 'Metal', 'Fairy': 'Fairy', 'Dragon': 'Dragon',
                'Colorless': 'Colorless', 'Flying': 'Flying'
            }
            ger_cost = [energy_map.get(c, c) for c in att_cost]
            
            attacks.append({
                'name': att_name,
                'damage': att_damage,
                'cost': ger_cost,
                'effect': att.get('effect', '')
            })
        
        # Build German card data
        ger_card = {
            'url': f'/de/card/{card.get("set_id", "").lower()}-{eng_name.lower().replace(" ", "-")}',
            'german_name': clean_german_name(ger_name),
            'set_id': card.get('set_id', '').upper(),
            'card_number': str(card.get('card_number', '')),
            'set_total': '',
            'hp': str(card.get('hp', '')),
            'energy_type': card.get('energy_type', ''),
            'stage': card.get('stage', ''),
            'evolution_from': evolution_from,
            'rarity': card.get('rarity', ''),
            'weakness': card.get('weakness', ''),
            'retreat': str(card.get('retreat', '')) if card.get('retreat') else '',
            'illustrator': card.get('illustrator', ''),
            'pack_points': '',
            'release_date': '',
            'attacks': attacks,
        }
        german_cards.append(ger_card)
    
    return german_cards


def load_existing_cards(clean: bool = True):
    """Load existing cards from cache.
    
    Args:
        clean: If True, remove trailing backslashes from German names
    """
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        
        if clean:
            for card in cards:
                if card.get('german_name'):
                    card['german_name'] = clean_german_name(card['german_name'])
                # Normalize set_id to uppercase
                if card.get('set_id'):
                    card['set_id'] = card['set_id'].upper()
        
        return cards
    return []


def count_by_set(cards):
    """Count cards per set from existing data."""
    counts = {}
    for card in cards:
        sid = card.get('set_id', '').upper()  # Use uppercase for consistency
        counts[sid] = counts.get(sid, 0) + 1
    return counts


def analyze_missing(cards):
    """Analyze which sets are missing cards."""
    existing = count_by_set(cards)
    
    print("\n" + "=" * 60)
    print("SET ANALYSIS")
    print("=" * 60)
    print(f"{'SET':<10} {'OUR':>6} {'OFFICIAL':>10} {'STATUS':>15}")
    print("-" * 60)
    
    missing_sets = []
    complete_sets = []
    
    for set_id, official_count in sorted(OFFICIAL_SETS.items()):
        our_count = existing.get(set_id, 0)
        diff = our_count - official_count
        
        if diff == 0:
            status = "✅ COMPLETE"
            complete_sets.append(set_id)
        elif diff > 0:
            status = f"⚠️ +{diff} EXTRA"
            complete_sets.append(set_id)
        else:
            status = f"❌ MISSING {-diff}"
            missing_sets.append(set_id)
        
        print(f"{set_id:<10} {our_count:>6} {official_count:>10} {status:>15}")
    
    print("-" * 60)
    complete = len(complete_sets)
    missing = len(missing_sets)
    print(f"Complete: {complete} sets | Missing: {missing} sets")
    
    return missing_sets


def get_session():
    """Create a session with proper headers."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
    })
    return session


def get_card_urls(session, set_slug):
    """Get all card URLs from a set page. Try both /de/set/ and /de/booster/ paths."""
    # Try /de/set/ first
    url = f"{BASE_URL}/de/set/{set_slug}"
    response = session.get(url, timeout=30)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'/de/card/'))
        
        if links:
            card_urls = list(set([link.get('href') for link in links]))
            return card_urls
    
    # Try /de/booster/ as fallback
    url = f"{BASE_URL}/de/booster/{set_slug}"
    response = session.get(url, timeout=30)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'/de/card/'))
        
        if links:
            card_urls = list(set([link.get('href') for link in links]))
            return card_urls
    
    return []


def parse_card(session, card_url, set_id):
    """Parse a single card page."""
    url = BASE_URL + card_url if card_url.startswith('/') else card_url
    response = session.get(url, timeout=30)
    
    if response.status_code != 200:
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    
    data = {
        'url': card_url,
        'german_name': '',
        'set_id': set_id,
        'card_number': '',
        'set_total': '',
        'hp': '',
        'energy_type': '',
        'stage': '',
        'evolution_from': '',
        'rarity': '',
        'weakness': '',
        'retreat': '',
        'illustrator': '',
        'pack_points': '',
        'release_date': '',
        'attacks': [],
        'ability': {},
    }
    
    # Extract from URL
    match = re.search(r'/de/card/[^/]+-([^-]+)$', card_url)
    if match:
        data['german_name'] = clean_german_name(match.group(1).replace('-', ' ').title())
    
    # HP
    hp_match = re.search(r'(\d+)\s*KP', text)
    if hp_match:
        data['hp'] = hp_match.group(1)
    
    # Card number
    num_match = re.search(r'#\s*(\d+)\s*/\s*(\d+)', text)
    if num_match:
        data['card_number'] = num_match.group(1)
        data['set_total'] = num_match.group(2)
    
    # Energy type
    energy_match = re.search(r'Energie-Typ.*?(\w+)-Karte', text)
    if energy_match:
        data['energy_type'] = energy_match.group(1).capitalize()
    
    # Stage
    stage_match = re.search(r'Entwicklungsstufe.*?<strong>([^<]+)', text, re.DOTALL)
    if stage_match:
        data['stage'] = stage_match.group(1).strip()
    
    # Energy type - map German to English
    german_energy_map = {
        'kampf': 'Fighting', 'feuer': 'Fire', 'wasser': 'Water', 'pflanze': 'Grass',
        'elektro': 'Lightning', 'psycho': 'Psychic', 'drache': 'Dragon',
        'fee': 'Fairy', 'eis': 'Ice', 'dunkel': 'Darkness', 'stahl': 'Metal',
        'flug': 'Flying', 'geist': 'Ghost', 'boden': 'Ground', 'gestein': 'Rock',
        'käfer': 'Bug', 'unlicht': 'Dark', 'fee': 'Fairy'
    }
    text_lower = text.lower()
    for ger, eng in german_energy_map.items():
        if ger in text_lower:
            data['energy_type'] = eng
            break
    
    # Rarity
    rarity_match = re.search(r'(\d+)-Diamant', text)
    if rarity_match:
        data['rarity'] = f"{rarity_match.group(1)} Diamond"
    
    # Weakness with damage
    weak_section = soup.find(string=re.compile(r'Schwäche'))
    if weak_section:
        parent = weak_section.find_parent()
        if parent:
            parent_text = parent.get_text()
            weak_match = re.search(r'(\w+)\s*\+\s*(\d+)', parent_text)
            if weak_match:
                data['weakness'] = f"{weak_match.group(1)}+{weak_match.group(2)}"
    
    # Retreat cost
    retreat_section = soup.find(string=re.compile(r'Rückzug'))
    if retreat_section:
        parent = retreat_section.find_parent()
        if parent:
            parent_text = parent.get_text()
            retreat_match = re.search(r'(\d+)', parent_text)
            if retreat_match:
                data['retreat'] = retreat_match.group(1)
    
    # Illustrator
    illust_match = re.search(r'Illu(?:strator)?\.?\s*([^•\n]+)', text)
    if illust_match:
        data['illustrator'] = illust_match.group(1).strip()[:50]
    
    # Attacks - NEW PARSER using HTML structure
    # Structure: <li class="p-4 border-2..."> with energy costs, name, damage, effect
    energy_map = {
        'psychic': 'Psychic', 'fire': 'Fire', 'water': 'Water', 'grass': 'Grass',
        'lightning': 'Lightning', 'fighting': 'Fighting', 'darkness': 'Darkness',
        'metal': 'Metal', 'dragon': 'Dragon', 'fairy': 'Fairy', 
        'colorless': 'Colorless', 'steel': 'Steel', 'ghost': 'Ghost', 'ice': 'Ice'
    }
    
    # Find all attack list items (li with class p-4 border-2)
    attack_lis = soup.find_all('li', class_='p-4')
    
    for li in attack_lis:
        # Check if this li contains an h3 (attack name)
        h3 = li.find('h3')
        if not h3:
            continue
        
        attack_name = h3.get_text(strip=True)
        if not attack_name:
            continue
        
        # Get energy costs from img alt attributes
        costs = []
        imgs = li.find_all('img', alt=True)
        for img in imgs:
            alt = img.get('alt', '')
            if alt and isinstance(alt, str):
                energy = alt.lower()
                if energy in energy_map:
                    costs.append(energy_map[energy])
        
        # Get damage from spans with numbers
        damage = ''
        spans = li.find_all('span')
        for span in spans:
            span_text = span.get_text(strip=True)
            if span_text.isdigit():
                damage = span_text
                break
        
        # Get effect from p with class text-sm pt-1
        effect = ''
        effect_p = li.find('p', class_='text-sm')
        if effect_p:
            effect = effect_p.get_text(strip=True)[:200]
        
        data['attacks'].append({
            'name': attack_name,
            'damage': damage,
            'cost': costs,
            'effect': effect
        })
    
    # Extract set_id from URL - NOTE: Card URLs don't contain set slug, 
    # so set_id must be passed in. This is a placeholder for backward compat.
    # The set_id should be set by the caller.
    
    return data


def add_to_database(card_data):
    """Add a card to the database."""
    try:
        database.add_card({
            'name': card_data.get('german_name', ''),
            'category': 'Pokemon' if card_data.get('hp') else 'Trainer',
            'set': card_data.get('set_id', ''),
            'card_number': card_data.get('card_number', ''),
            'hp': card_data.get('hp', ''),
            'stage': card_data.get('stage', ''),
            'energy_type': card_data.get('energy_type', ''),
            'evolution_from': '',
            'attacks': card_data.get('attacks', []),
            'weakness': card_data.get('weakness', ''),
            'retreat_cost': card_data.get('retreat', ''),
            'rarity': card_data.get('rarity', ''),
            'illustrator': card_data.get('illustrator', ''),
        }, quantity=0)
        return True
    except Exception as e:
        print(f"    DB Error: {e}")
        return False


def main():
    print("=" * 60)
    print("INCREMENTAL GERMAN CARD SCRAPER")
    print("Re-scraping ALL sets for complete attack data")
    print("=" * 60)
    
    # Load existing data
    print("\n[1/4] Loading existing data...")
    existing_cards = load_existing_cards()
    print(f"  Loaded {len(existing_cards)} cards from cache")
    
    # Analyze what's missing
    missing_sets = analyze_missing(existing_cards)
    
    # ALWAYS scrape all sets to get complete attack data
    # This ensures 100% completeness for attack cost/damage/effect
    print(f"\n[2/4] Re-scraping ALL sets for complete attack data...")
    all_set_ids = list(OFFICIAL_SETS.keys())
    print(f"  Sets to scrape: {', '.join(all_set_ids)}")
    
    # Setup session
    session = get_session()
    print("\n[3/4] Scraping missing cards...")
    session.get(BASE_URL + "/de", timeout=30)
    print("  Session ready")
    
    new_cards = []
    set_slug_map = {s[0]: s[1] for s in SETS}
    
    for set_id in all_set_ids:
        set_slug = set_slug_map.get(set_id, '')
        official_count = OFFICIAL_SETS.get(set_id, 0)
        
        print(f"\n  Scraping {set_id} ({official_count} cards)...")
        
        # Get card URLs for this set
        card_urls = get_card_urls(session, set_slug)
        
        if not card_urls:
            print(f"    ⚠️ German source blocked, skipping set...")
            continue
        
        print(f"    Found {len(card_urls)} URLs")
        
        # Parse each card
        for i, card_url in enumerate(card_urls):
            if (i + 1) % 20 == 0:
                print(f"    Progress: {i+1}/{len(card_urls)}")
            
            data = parse_card(session, card_url, set_id)
            if data:
                new_cards.append(data)
            
            time.sleep(0.2)  # Rate limiting
        
        print(f"    Scraped {len([c for c in new_cards if c.get('set_id') == set_id])} cards from {set_id}")
    
    # Merge with existing
    print("\n[4/4] Merging and saving...")
    
    # Create lookup of existing cards (by set_id + card_number)
    # Prefer NEW data if available (has better attack info)
    existing_lookup = {}
    for card in existing_cards:
        key = (card.get('set_id', '').upper(), str(card.get('card_number', '')))
        existing_lookup[key] = card
    
    # Add/update with new cards (new cards have better attack data)
    for card in new_cards:
        key = (card.get('set_id', '').upper(), str(card.get('card_number', '')))
        existing_lookup[key] = card  # New data overwrites old
    
    merged = list(existing_lookup.values())
    
    # Save to JSON
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved {len(merged)} cards to {CACHE_FILE}")
    print(f"  New cards added: {len(new_cards)}")
    
    # Update database
    print("\n[5/5] Updating database...")
    db_count = 0
    for card in new_cards:
        if add_to_database(card):
            db_count += 1
    
    print(f"  Added {db_count} cards to database")
    
    print("\n" + "=" * 60)
    print("COMPLETE!")
    print(f"  Total cards: {len(merged)}")
    print(f"  New cards scraped: {len(new_cards)}")
    print(f"  Cards in DB: {db_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
