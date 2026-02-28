#!/usr/bin/env python3
"""
Mega Pokemon ex Scraper for Pokemon TCG Pocket.
Scrapes Mega Evolution cards from pokewiki.de.

Target Sets:
- B1: Mega-Aufstieg (Mega Rising)
- B1a: Feuerrote Flammen (Crimson Blaze)
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
    "Finsternis": "Darkness",
}

# Rarity mapping
RARITY_MAP = {
    "nicht so häufige": "1 Diamond",
    "häufige": "2 Diamond",
    "sehr seltene": "3 Diamond",
    "ultimative": "3 Diamond",
    "seltene holografische sammelkarte": "Rare Holo",
    "seltene besondere illustrations-sammelkarte": "Special Illustration Rare",
    "seltene illustrations-sammelkarte": "Illustration Rare",
    "seltene schillernde sammelkarte": "Shiny Rare",
    "seltene geheime sammelkarte": "Ultra Rare",
}

# Sets to scrape
SETS = [
    ("B1", "Mega-Aufstieg", "https://www.pokewiki.de/Mega-Aufstieg_(TCG_Pocket)"),
    ("B1a", "Feuerrote Flammen", "https://www.pokewiki.de/Feuerrote_Flammen_(TCG_Pocket)"),
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
    """Parse a single Mega card detail page."""
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
        "card_type": "",  # Mega ex indicator
    }

    # Get card name from infobox
    name_th = soup.find("th", class_="name")
    if name_th:
        card["german_name"] = get_text_safe(name_th)
        card["german_name"] = re.sub(r'\s+', ' ', card["german_name"])

    # Get illustrator from bild td
    bild_td = soup.find("td", class_="bild")
    if bild_td:
        text = bild_td.get_text(strip=True)
        # Look for "illustriert von" text
        if "illustriert von" in text:
            # Get all links in the bild td and find the one that's not the image
            links = bild_td.find_all("a", href=True)
            for link in links:
                href = str(link.get("href", ""))
                link_text = link.get_text(strip=True)
                # Skip the image link
                if href.startswith("/Datei:") or not link_text:
                    continue
                if link_text:
                    card["illustrator"] = link_text
                    break

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
                    # Method 1: Try to find type from link href
                    type_link = cells[1].find("a", href=True)
                    if type_link:
                        type_href = type_link.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                card["energy_type"] = eng
                                break

                    # Method 2: If no link found, try to find type from image alt
                    if not card["energy_type"]:
                        type_imgs = cells[1].find_all("img", alt=True)
                        for img in type_imgs:
                            alt = img.get("alt", "").lower()
                            for ger, eng in TYPE_MAP.items():
                                if ger.lower() in alt:
                                    card["energy_type"] = eng
                                    break
                            if card["energy_type"]:
                                break

                    # Method 3: Try to find type in plain text
                    if not card["energy_type"]:
                        cell_text = get_text_safe(cells[1]).lower()
                        for ger, eng in TYPE_MAP.items():
                            if ger.lower() in cell_text:
                                card["energy_type"] = eng
                                break

                elif "KP" in label:
                    hp_match = re.search(r'(\d+)', value)
                    if hp_match:
                        card["hp"] = hp_match.group(1)

                elif "Schwäche" in label:
                    weak_type = None

                    # Method 1: Try from link href
                    weak_link = cells[1].find("a", href=True)
                    if weak_link:
                        type_href = weak_link.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                weak_type = eng
                                break

                    # Method 2: Try from image alt
                    if not weak_type:
                        weak_imgs = cells[1].find_all("img", alt=True)
                        for img in weak_imgs:
                            alt = img.get("alt", "").lower()
                            for ger, eng in TYPE_MAP.items():
                                if ger.lower() in alt:
                                    weak_type = eng
                                    break
                            if weak_type:
                                break

                    # Method 3: Try from text
                    if not weak_type:
                        cell_text = get_text_safe(cells[1]).lower()
                        for ger, eng in TYPE_MAP.items():
                            if ger.lower() in cell_text:
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
            alt = rarity_img.get("alt", "").lower()
            for ger_key, eng_val in RARITY_MAP.items():
                if ger_key in alt:
                    card["rarity"] = eng_val
                    break

    # Get abilities - look for Fähigkeiten section
    ability_headers = soup.find_all("h2", string=re.compile("Fähigkeiten|Ability"))
    for ability_header in ability_headers:
        next_elem = ability_header.find_next_sibling()
        while next_elem:
            if next_elem.name == "table":
                ability_rows = next_elem.find_all("tr")
                for row in ability_rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        ability_name_cell = cells[1] if len(cells) > 1 else cells[0]
                        ability_name = get_text_safe(ability_name_cell)

                        ability_effect = ""
                        if len(cells) >= 3:
                            ability_effect = get_text_safe(cells[2])

                        if ability_name and not ability_name.startswith("Angriff"):
                            card["ability"] = ability_name
                            card["ability_effect"] = ability_effect
                            break
                break
            next_elem = next_elem.find_next_sibling()

    # Get attacks and abilities
    attack_headers = soup.find_all("h2", string=re.compile("Angriff|Attacken"))
    for attack_header in attack_headers:
        next_elem = attack_header.find_next_sibling()
        while next_elem:
            if next_elem.name == "table" and "angriff" in str(next_elem.get("class", [])):
                attack_rows = next_elem.find_all("tr")
                for row in attack_rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        # Check if this is an ability (Fähigkeit)
                        is_ability = False
                        first_cell = cells[0]
                        power_link = first_cell.find("a", href=lambda x: x and ("Power" in str(x) or "Fähigkeit" in str(x)))
                        if power_link:
                            is_ability = True

                        if is_ability:
                            ability_name = get_text_safe(cells[1]) if len(cells) > 1 else get_text_safe(cells[0])
                            ability_effect = ""
                            next_row = row.find_next_sibling()
                            if next_row and "beschreibung" in str(next_row.get("class", [])):
                                ability_effect = get_text_safe(next_row.find("td"))

                            if ability_name and not ability_name.startswith("Angriff"):
                                card["ability"] = ability_name
                                card["ability_effect"] = ability_effect
                                continue

                        # Normal attack
                        attack_name_cell = cells[1] if len(cells) > 1 else cells[0]
                        attack_name = get_text_safe(attack_name_cell)
                        for a in attack_name_cell.find_all("a"):
                            a.unwrap()
                        attack_name = attack_name_cell.get_text(strip=True)

                        damage = ""
                        if len(cells) >= 3:
                            damage_text = get_text_safe(cells[-1])
                            damage_match = re.search(r'(\d+)', damage_text)
                            damage = damage_match.group(1) if damage_match else ""

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


def get_mega_card_links_from_set_page(soup: BeautifulSoup, set_name: str) -> list:
    """Extract Mega card links from the set page."""
    links = []

    # Find the setliste table
    tables = soup.find_all("table", class_="setliste")

    for table in tables:
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Second column contains the card name
            name_cell = cells[1]

            # Look for Mega- prefix in links (must be at START of name)
            links_in_cell = name_cell.find_all("a", href=True)
            for link in links_in_cell:
                href = link.get("href", "")
                link_text = link.get_text(strip=True)

                # Check if this is a Mega card - must start with "Mega-"
                # Also check the href for Mega- pattern like /Mega-Pinsir-ex_
                is_mega = False
                if href.startswith("/Mega-"):
                    is_mega = True
                elif link_text.startswith("Mega-"):
                    is_mega = True
                
                if is_mega:
                    # Extract card number from the href
                    match = re.search(r'_(\d+)\)$', href)
                    if match:
                        card_num = int(match.group(1))
                        full_url = urljoin("https://www.pokewiki.de", href)
                        links.append((card_num, full_url, link_text))

    # Sort by card number
    links.sort(key=lambda x: x[0])
    
    # Remove duplicates based on card number
    seen = set()
    unique_links = []
    for link in links:
        if link[0] not in seen:
            seen.add(link[0])
            unique_links.append(link)
    
    return unique_links


def scrape_set(set_id: str, set_name: str, set_url: str) -> list:
    """Scrape all Mega cards from a set."""
    print(f"\n{'='*50}")
    print(f"Scraping Mega cards from: {set_name} ({set_id})")
    print(f"{'='*50}")

    try:
        print(f"Fetching set page: {set_url}")
        soup = get_page(set_url)

        print("Extracting Mega card links...")
        card_links = get_mega_card_links_from_set_page(soup, set_name)

        if not card_links:
            print(f"WARNING: No Mega cards found for {set_name}")
            return []

        print(f"Found {len(card_links)} Mega cards")

        cards = []
        for i, (card_num, url, name) in enumerate(card_links):
            print(f"[{i+1}/{len(card_links)}] {name} (#{card_num})")
            try:
                card_soup = get_page(url)
                card = parse_card_page(card_soup, url, set_id, set_name)
                card["card_number"] = str(card_num)
                cards.append(card)
                print(f"  -> {card.get('german_name')}: {card.get('hp')} HP, {card.get('energy_type')}")
                if card.get("ability"):
                    print(f"  -> Ability: {card.get('ability')}")
                if card.get("attacks"):
                    print(f"  -> Attacks: {len(card['attacks'])}")
            except Exception as e:
                print(f"  ERROR: {e}")

            time.sleep(0.3)

        return cards
    except Exception as e:
        print(f"ERROR scraping {set_name}: {e}")
        return []


def main():
    """Scrape all Mega Pokemon ex cards."""
    all_cards = []

    for set_id, set_name, set_url in SETS:
        cards = scrape_set(set_id, set_name, set_url)
        all_cards.extend(cards)
        time.sleep(1)

    print(f"\n{'='*50}")
    print(f"TOTAL: Scraped {len(all_cards)} Mega Pokemon ex cards")
    print(f"{'='*50}")

    # Save to file
    output_file = "api/cache/mega_pkm_ex.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    print(f"Saved to {output_file}")

    # Print summary
    if all_cards:
        print("\n=== Summary ===")
        sets_count = {}
        for card in all_cards:
            sid = card.get("set_id", "unknown")
            sets_count[sid] = sets_count.get(sid, 0) + 1

        for sid, count in sorted(sets_count.items()):
            print(f"  {sid}: {count} cards")


if __name__ == "__main__":
    main()
