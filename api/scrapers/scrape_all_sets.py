#!/usr/bin/env python3
"""
PokéWiki Scraper for all Pokemon TCG Pocket sets.
Scrapes card data from pokewiki.de
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# Set name to ID mapping
SET_MAPPING = {
    "Genetische Apex": "A1",
    "Traumhafte Parade": "B2",
    "PROMO-A": "PROMO-A",
    "PROMO-B": "PROMO-B",
    "Unschlagbare Gene": "A1",
    "Mysteriöse Insel": "A2",
    "Kollision von Raum und Zeit": "A3",
    "Licht des Triumphs": "A4",
    "Glänzendes Festival": "A1a",
    "Hüter des Firmaments": "A2a",
    "Dimensionale Krise": "A3a",
    "Evoli-Hain": "A4a",
    "Weisheit von Meer und Himmel": "A2b",
    "Verborgene Quelle": "A3b",
    "Deluxepack-ex": "A1a",
    "Mega-Aufstieg": "A2a",
    "Feuerrote Flammen": "A3a",
    "Wundervolles Paldea": "B1",
}

# Type mapping from German to English
TYPE_MAP = {
    "Pflanze": "Grass",
    "Feuer": "Fire",
    "Wasser": "Water",
    "Elektro": "Electric",
    "Psycho": "Psychic",
    "Kampf": "Fighting",
    "Geist": "Ghost",
    "Drache": "Dragon",
    "Farblos": "Colorless",
    "Fee": "Fairy",
    "Metall": "Metal",
    "Dark": "Darkness",
}

# Rarity mapping
RARITY_MAP = {
    "nicht so häufige": "1 Diamond",
    "häufige": "2 Diamond", 
    "sehr seltene": "3 Diamond",
    "ultimative": "3 Diamond",
}

SETS = [
    ("PROMO-A_(TCG_Pocket)", "https://www.pokewiki.de/PROMO-A_(TCG_Pocket)", "PROMO-A"),
    ("Unschlagbare_Gene_(TCG_Pocket)", "https://www.pokewiki.de/Unschlagbare_Gene_(TCG_Pocket)", "A1"),
    ("Mysteriöse_Insel_(TCG_Pocket)", "https://www.pokewiki.de/Mysteri%C3%B6se_Insel_(TCG_Pocket)", "A1a"),
    ("Kollision_von_Raum_und_Zeit_(TCG_Pocket)", "https://www.pokewiki.de/Kollision_von_Raum_und_Zeit_(TCG_Pocket)", "A2"),
    ("Licht_des_Triumphs_(TCG_Pocket)", "https://www.pokewiki.de/Licht_des_Triumphs_(TCG_Pocket)", "A3"),
    ("Glänzendes_Festival_(TCG_Pocket)", "https://www.pokewiki.de/Gl%C3%A4nzendes_Festival_(TCG_Pocket)", "A4"),
    ("Hüter_des_Firmaments_(TCG_Pocket)", "https://www.pokewiki.de/H%C3%BCter_des_Firmaments_(TCG_Pocket)", "A2a"),
    ("Dimensionale_Krise_(TCG_Pocket)", "https://www.pokewiki.de/Dimensionale_Krise_(TCG_Pocket)", "A3a"),
    ("Evoli-Hain_(TCG_Pocket)", "https://www.pokewiki.de/Evoli-Hain_(TCG_Pocket)", "A4a"),
    ("Weisheit_von_Meer_und_Himmel_(TCG_Pocket)", "https://www.pokewiki.de/Weisheit_von_Meer_und_Himmel_(TCG_Pocket)", "A2b"),
    ("Verborgene_Quelle_(TCG_Pocket)", "https://www.pokewiki.de/Verborgene_Quelle_(TCG_Pocket)", "A3b"),
    ("Deluxepack-ex_(TCG_Pocket)", "https://www.pokewiki.de/Deluxepack-ex_(TCG_Pocket)", "A1a"),
    ("PROMO-B_(TCG_Pocket)", "https://www.pokewiki.de/PROMO-B_(TCG_Pocket)", "PROMO-B"),
    ("Mega-Aufstieg_(TCG_Pocket)", "https://www.pokewiki.de/Mega-Aufstieg_(TCG_Pocket)", "A2a"),
    ("Feuerrote_Flammen_(TCG_Pocket)", "https://www.pokewiki.de/Feuerrote_Flammen_(TCG_Pocket)", "A3a"),
    ("Wundervolles_Paldea_(TCG_Pocket)", "https://www.pokewiki.de/Wundervolles_Paldea_(TCG_Pocket)", "B1"),
]


def get_page(url: str) -> BeautifulSoup:
    """Fetch a page and return BeautifulSoup object."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_text_safe(elem) -> str:
    """Get text from element safely."""
    if elem:
        return elem.get_text(strip=True)
    return ""


def parse_card_page(soup: BeautifulSoup, url: str, set_id: str, set_name: str) -> dict:
    """Parse a single card detail page."""
    card = {
        "url": url,
        "german_name": "",
        "set_id": set_id,
        "set_name": set_name,
        "card_number": "",
        "hp": "",
        "energy_type": "",
        "stage": "",
        "evolution_from": "",
        "weakness": "",
        "retreat": "",
        "attacks": [],
        "ability": None,
        "ability_effect": None,
        "rarity": "",
        "illustrator": "",
        "pokedex_number": "",
        "regulation_mark": "",
    }
    
    # Get card name from infobox
    name_th = soup.find("th", class_="name")
    if name_th:
        card["german_name"] = get_text_safe(name_th)
        card["german_name"] = re.sub(r'\s+', ' ', card["german_name"])
    
    # Get illustrator from bild td
    bild_td = soup.find("td", class_="bild")
    if bild_td:
        illust_link = bild_td.find("a", href=True)
        if illust_link:
            card["illustrator"] = illust_link.get_text(strip=True)
    
    # Find all property rows in the infobox
    infobox = soup.find("table", class_="karte-infobox")
    if infobox:
        rows = infobox.find_all("tr")
        for row in rows:
            cells = row.find_all("td", class_="eigenschaft")
            if len(cells) >= 2:
                label = get_text_safe(cells[0])
                value = get_text_safe(cells[1])
                
                if "Typ" in label:
                    type_link = cells[1].find("a", href=True)
                    if type_link:
                        type_href = type_link.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                card["energy_type"] = eng
                                break
                
                elif "KP" in label:
                    hp_match = re.search(r'(\d+)', value)
                    if hp_match:
                        card["hp"] = hp_match.group(1)
                
                elif "Schwäche" in label:
                    weak_type = None
                    weak_link = cells[1].find("a", href=True)
                    if weak_link:
                        type_href = weak_link.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                weak_type = eng
                                break
                    damage_match = re.search(r'\+(\d+)', value)
                    if damage_match and weak_type:
                        card["weakness"] = f"{weak_type}+{damage_match.group(1)}"
                
                elif "Resistenz" in label:
                    card["resistance"] = value if value and value != "—" else ""
                
                elif "Rückzugskosten" in label:
                    energy_count = len(cells[1].find_all("a", href=lambda x: x and "Farblos" in str(x)))
                    if energy_count > 0:
                        card["retreat"] = str(energy_count)
                
                elif "Entwicklungsstufe" in label:
                    card["stage"] = value
                    if value == "Basis-Pokémon" or value == "Basis":
                        card["stage"] = "Basic"
                    elif value == "Phase 1" or "Stufe 1" in value:
                        card["stage"] = "Stage 1"
                    elif value == "Phase 2" or "Stufe 2" in value:
                        card["stage"] = "Stage 2"
                
                elif "Regelzeichen" in label:
                    card["regulation_mark"] = value
    
    # Get card number and rarity from set row
    set_rows = infobox.find_all("td", class_="zeile") if infobox else []
    for set_row in set_rows:
        set_text = get_text_safe(set_row)
        num_match = re.search(r'(\d+)/\d+', set_text)
        if num_match:
            card["card_number"] = num_match.group(1)
        rarity_img = set_row.find("img", alt=True)
        if rarity_img:
            alt = rarity_img.get("alt", "")
            for ger_key, eng_val in RARITY_MAP.items():
                if ger_key in alt.lower():
                    card["rarity"] = eng_val
                    break
    
    # Get abilities - look for Fähigkeiten section before attacks
    ability_headers = soup.find_all("h2", string=re.compile("Fähigkeiten|Ability"))
    for ability_header in ability_headers:
        next_elem = ability_header.find_next_sibling()
        while next_elem:
            if next_elem.name == "table":
                # Look for ability rows
                ability_rows = next_elem.find_all("tr")
                for row in ability_rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        # Get ability name from cell
                        ability_name_cell = cells[1] if len(cells) > 1 else cells[0]
                        ability_name = get_text_safe(ability_name_cell)
                        
                        # Get ability effect from description cell
                        ability_effect = ""
                        if len(cells) >= 3:
                            ability_effect = get_text_safe(cells[2])
                        
                        if ability_name and not ability_name.startswith("Angriff"):
                            card["ability"] = ability_name
                            card["ability_effect"] = ability_effect
                            break
                break
            next_elem = next_elem.find_next_sibling()
    
    # Get attacks and abilities - look for attack table
    attack_headers = soup.find_all("h2", string=re.compile("Angriff|Attacken"))
    for attack_header in attack_headers:
        # Find next sibling table
        next_elem = attack_header.find_next_sibling()
        while next_elem:
            if next_elem.name == "table" and "angriff" in str(next_elem.get("class", [])):
                attack_rows = next_elem.find_all("tr")
                for row in attack_rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        # Check if this is an ability (Fähigkeit) - has Fähigkeit/Power icon in first cell
                        is_ability = False
                        first_cell = cells[0]
                        # Look for Pokémon-Power or Fähigkeit link
                        power_link = first_cell.find("a", href=lambda x: x and ("Power" in str(x) or "Fähigkeit" in str(x)))
                        if power_link:
                            is_ability = True
                        
                        if is_ability:
                            # This is an ability - name is in second cell (or first if only 2 cells)
                            ability_name = get_text_safe(cells[1]) if len(cells) > 1 else get_text_safe(cells[0])
                            # Get effect from next row
                            ability_effect = ""
                            next_row = row.find_next_sibling()
                            if next_row and "beschreibung" in str(next_row.get("class", [])):
                                ability_effect = get_text_safe(next_row.find("td"))
                            
                            if ability_name and not ability_name.startswith("Angriff"):
                                card["ability"] = ability_name
                                card["ability_effect"] = ability_effect
                                continue  # Skip adding to attacks
                        
                        # Normal attack - get attack name from cell
                        attack_name_cell = cells[1] if len(cells) > 1 else cells[0]
                        attack_name = get_text_safe(attack_name_cell)
                        # Clean attack name (remove links)
                        for a in attack_name_cell.find_all("a"):
                            a.unwrap()
                        attack_name = attack_name_cell.get_text(strip=True)
                        
                        # Get damage from last cell
                        damage = ""
                        if len(cells) >= 3:
                            damage_text = get_text_safe(cells[-1])
                            damage_match = re.search(r'(\d+)', damage_text)
                            damage = damage_match.group(1) if damage_match else ""
                        
                        # Get energy cost from first cell
                        costs = []
                        energy_links = cells[0].find_all("a", href=True) if len(cells) > 0 else []
                        for e in energy_links:
                            e_href = e.get("href", "") or ""
                            for ger, eng in TYPE_MAP.items():
                                if ger in e_href:
                                    costs.append(eng)
                                    break
                        
                        if attack_name and not attack_name.startswith("Angriff"):
                            card["attacks"].append({
                                "name": attack_name,
                                "damage": damage,
                                "cost": costs,
                                "effect": ""
                            })
                break
            next_elem = next_elem.find_next_sibling()
    
    # Get Pokédex number
    pokedex_table = soup.find("table", class_="karte-pokedex")
    if pokedex_table:
        rows = pokedex_table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 1:
                first_cell = get_text_safe(cells[0])
                if re.match(r'^\d+$', first_cell):
                    card["pokedex_number"] = first_cell
    
    return card


def get_card_links_from_set_page(soup: BeautifulSoup, set_name: str) -> list:
    """Extract all card detail page links from the set page."""
    links = []
    
    # Get all links
    all_links = soup.find_all("a", href=True)
    
    seen = set()
    for link in all_links:
        href = str(link.get("href", ""))
        
        # Skip special pages
        if "Spezial:" in href or "Liste_" in href or "Diskussion:" in href or "index.php" in href:
            continue
            
        # Match pattern: /CardName_SetName_NNN
        # Examples: /Hornliu_(Gl%C3%A4nzendes_Festival_001), /Duflor_(Weisheit_von_Meer_und_Himmel_002)
        match = re.search(r'_(\d+)\)$', href)
        
        if match:
            card_num = int(match.group(1))
            full_url = urljoin("https://www.pokewiki.de", href)
            if (card_num, full_url) not in seen:
                seen.add((card_num, full_url))
                links.append((card_num, full_url))
    
    # Sort by card number
    links.sort(key=lambda x: int(x[0]) if x[0] else 0)
    return links


def scrape_set(set_name: str, set_url: str, set_id: str) -> list:
    """Scrape all cards from a set."""
    print(f"\n{'='*50}")
    print(f"Scraping: {set_name} ({set_id})")
    print(f"{'='*50}")
    
    try:
        print(f"Fetching set page: {set_url}")
        soup = get_page(set_url)
        
        print("Extracting card links...")
        card_links = get_card_links_from_set_page(soup, set_name.replace("_(TCG_Pocket)", "").replace(" ", "_"))
        
        if not card_links:
            print(f"WARNING: No card links found for {set_name}")
            return []
        
        print(f"Found {len(card_links)} cards")
        
        cards = []
        for i, (card_num, url) in enumerate(card_links):
            print(f"[{i+1}/{len(card_links)}] Card {card_num}")
            try:
                card_soup = get_page(url)
                card = parse_card_page(card_soup, url, set_id, set_name)
                card["card_number"] = str(card_num)
                cards.append(card)
                print(f"  -> {card.get('german_name')}: {card.get('hp')} HP")
            except Exception as e:
                print(f"  ERROR: {e}")
            
            time.sleep(0.2)
        
        return cards
    except Exception as e:
        print(f"ERROR scraping {set_name}: {e}")
        return []


def main():
    """Scrape all sets."""
    all_cards = []
    
    for set_key, url, set_id in SETS:
        # Clean set name for URL pattern
        set_name_clean = set_key.replace("_(TCG_Pocket)", "").replace("_", " ")
        
        cards = scrape_set(set_name_clean, url, set_id)
        all_cards.extend(cards)
        
        time.sleep(1)  # Delay between sets
    
    print(f"\n{'='*50}")
    print(f"TOTAL: Scraped {len(all_cards)} cards")
    print(f"{'='*50}")
    
    # Save to file
    output_file = "csv/reference/pokewiki_all_sets.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
