#!/usr/bin/env python3
"""
PokéWiki Scraper for Pokemon TCG Pocket cards.
Scrapes card data from pokewiki.de
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SET_ID = "B2"
SET_NAME = "Traumhafte Parade"
SET_URL = "https://www.pokewiki.de/Traumhafte_Parade_(TCG_Pocket)"

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
}

# Rarity mapping
RARITY_MAP = {
    "nicht so häufige": "1 Diamond",
    "häufige": "2 Diamond", 
    "sehr seltene": "3 Diamond",
    "ultimative": "3 Diamond",
}


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


def parse_card_page(soup: BeautifulSoup, url: str) -> dict:
    """Parse a single card detail page."""
    card = {
        "url": url,
        "german_name": "",
        "set_id": SET_ID,
        "set_name": SET_NAME,
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
        # Remove any extra text
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
                
                # Parse based on label
                if "Typ" in label:
                    # Get type from link
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
                    # Find type from link and get +damage
                    weak_type = None
                    weak_link = cells[1].find("a", href=True)
                    if weak_link:
                        type_href = weak_link.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                weak_type = eng
                                break
                    # Get damage number
                    damage_match = re.search(r'\+(\d+)', value)
                    if damage_match and weak_type:
                        card["weakness"] = f"{weak_type}+{damage_match.group(1)}"
                
                elif "Resistenz" in label:
                    card["resistance"] = value if value and value != "—" else ""
                
                elif "Rückzugskosten" in label:
                    # Count energy icons
                    energy_count = len(cells[1].find_all("a", href=lambda x: x and "Farblos" in str(x)))
                    if energy_count > 0:
                        card["retreat"] = str(energy_count)
                
                elif "Entwicklungsstufe" in label:
                    card["stage"] = value
                    # Determine evolution_from based on stage
                    if value == "Basis":
                        card["stage"] = "Basic"
                    elif value == "Phase 1":
                        card["stage"] = "Stage 1"
                    elif value == "Phase 2":
                        card["stage"] = "Stage 2"
                
                elif "Regelzeichen" in label:
                    card["regulation_mark"] = value
    
    # Get card number and rarity from set row
    set_rows = infobox.find_all("td", class_="zeile")
    for set_row in set_rows:
        set_text = get_text_safe(set_row)
        # Extract card number like "009/155"
        num_match = re.search(r'(\d+)/\d+', set_text)
        if num_match:
            card["card_number"] = num_match.group(1)
        # Extract rarity from image alt text
        rarity_img = set_row.find("img", alt=True)
        if rarity_img:
            alt = rarity_img.get("alt", "")
            for ger_key, eng_val in RARITY_MAP.items():
                if ger_key in alt.lower():
                    card["rarity"] = eng_val
                    break
    
    # Get attacks
    attack_table = soup.find("table", class_="karte-angriffe")
    if attack_table:
        attack_rows = attack_table.find_all("tr", class_="attack-zeile")
        for row in attack_rows:
            # Get attack name and damage
            cells = row.find_all("td")
            if len(cells) >= 3:
                # Attack name is in middle cell
                attack_name_link = cells[1].find("a")
                if attack_name_link:
                    attack_name = attack_name_link.get_text(strip=True)
                    # Get damage
                    damage_text = get_text_safe(cells[2])
                    damage_match = re.search(r'(\d+)', damage_text)
                    damage = damage_match.group(1) if damage_match else ""
                    
                    # Get cost (energy icons in first cell)
                    energy_cells = cells[0].find_all("a", href=True)
                    costs = []
                    for e in energy_cells:
                        e_href = e.get("href", "")
                        for ger, eng in TYPE_MAP.items():
                            if ger in e_href:
                                costs.append(eng)
                                break
                    
                    card["attacks"].append({
                        "name": attack_name,
                        "damage": damage,
                        "cost": costs,
                        "effect": ""
                    })
    
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


def get_card_links_from_set_page(soup: BeautifulSoup) -> list:
    """Extract all card detail page links from the set page."""
    links = []
    
    # Find all links that look like card pages
    all_links = soup.find_all("a", href=re.compile(r"/[A-Za-zÄÖÜäöüß_-]+\(Traumhafte_Parade_\d+\)"))
    
    seen = set()
    for link in all_links:
        href = link.get("href", "")
        if href and href not in seen:
            seen.add(href)
            full_url = urljoin("https://www.pokewiki.de", href)
            # Extract card number
            match = re.search(r"Traumhafte_Parade_(\d+)", href)
            if match:
                card_num = match.group(1)
                links.append((int(card_num), full_url))
    
    # Sort by card number
    links.sort(key=lambda x: x[0])
    return links


def scrape_set(set_url: str = SET_URL) -> list:
    """Scrape all cards from a set."""
    print(f"Fetching set page: {set_url}")
    soup = get_page(set_url)
    
    print("Extracting card links...")
    card_links = get_card_links_from_set_page(soup)
    print(f"Found {len(card_links)} cards")
    
    cards = []
    for i, (card_num, url) in enumerate(card_links):
        print(f"[{i+1}/{len(card_links)}] Scraping card {card_num}: {url}")
        try:
            card_soup = get_page(url)
            card = parse_card_page(card_soup, url)
            card["card_number"] = str(card_num)
            cards.append(card)
            print(f"  -> {card.get('german_name')}: {card.get('hp')} HP, {card.get('energy_type')}, {card.get('stage')}")
            if card.get("attacks"):
                print(f"  -> Attacks: {len(card['attacks'])}")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        time.sleep(0.3)  # Be polite
    
    return cards


def save_cards(cards: list, output_file: str = "api/cache/pokewiki_b2.json"):
    """Save scraped cards to JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(cards)} cards to {output_file}")


def merge_with_existing(new_cards: list):
    """Merge new cards with existing german_cards_complete.json"""
    existing_file = "api/cache/german_cards_complete.json"
    
    # Load existing
    with open(existing_file, "r", encoding="utf-8") as f:
        existing = json.load(f)
    
    print(f"Existing cards: {len(existing)}")
    
    # Add new cards (filter out duplicates by url)
    existing_urls = {c.get("url") for c in existing}
    added = 0
    for card in new_cards:
        if card.get("url") not in existing_urls:
            existing.append(card)
            added += 1
    
    print(f"Added {added} new cards")
    
    # Save merged
    with open(existing_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"Total now: {len(existing)} cards")


if __name__ == "__main__":
    # Scrape the full set
    cards = scrape_set()
    
    # Save raw
    save_cards(cards)
    
    # Merge with existing
    merge_with_existing(cards)
    
    print("Done!")
