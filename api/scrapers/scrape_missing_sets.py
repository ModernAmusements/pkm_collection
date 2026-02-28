#!/usr/bin/env python3
"""
Scraper for missing sets: A4b (Deluxepack-ex), B1 (Mega-Aufstieg), B1a (Feuerrote Flammen)
Optimized for speed with minimal output
"""

import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

TYPE_MAP = {
    "Pflanze": "Grass", "Feuer": "Fire", "Wasser": "Water", "Elektro": "Electric",
    "Psycho": "Psychic", "Kampf": "Fighting", "Geist": "Ghost", "Drache": "Dragon",
    "Farblos": "Colorless", "Fee": "Fairy", "Metall": "Metal", "Dark": "Darkness",
    "Finsternis": "Darkness",
}

SETS = [
    ("A4b", "Deluxepack-ex", "https://www.pokewiki.de/Deluxepack-ex_(TCG_Pocket)"),
    ("B1", "Mega-Aufstieg", "https://www.pokewiki.de/Mega-Aufstieg_(TCG_Pocket)"),
    ("B1a", "Feuerrote Flammen", "https://www.pokewiki.de/Feuerrote_Flammen_(TCG_Pocket)"),
]


def get_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    return BeautifulSoup(resp.text, "html.parser")


def get_text(elem):
    return elem.get_text(strip=True) if elem else ""


def parse_card_page(soup, url, set_id, set_name):
    card = {
        "url": url,
        "german_name": "",
        "set_id": set_id,
        "set_name": set_name,
        "card_number": "",
        "hp": "",
        "energy_type": "",
        "stage": "",
        "weakness": "",
        "retreat": "",
        "attacks": [],
        "ability": None,
        "rarity": "",
        "illustrator": "",
        "pokedex_number": "",
        "regulation_mark": "",
    }

    name_th = soup.find("th", class_="name")
    if name_th:
        card["german_name"] = re.sub(r'\s+', ' ', get_text(name_th))

    bild_td = soup.find("td", class_="bild")
    if bild_td:
        links = bild_td.find_all("a", href=True)
        for link in links:
            href = str(link.get("href", ""))
            link_text = link.get_text(strip=True)
            if href.startswith("/Datei:") or not link_text:
                continue
            if link_text:
                card["illustrator"] = link_text
                break

    infobox = soup.find("table", class_="karte-infobox")
    if infobox:
        rows = infobox.find_all("tr")
        for row in rows:
            cells = row.find_all("td", class_="eigenschaft")
            if len(cells) >= 2:
                label = get_text(cells[0])
                value = get_text(cells[1])

                if "Typ" in label:
                    type_link = cells[1].find("a", href=True)
                    if type_link:
                        type_href = str(type_link.get("href", ""))
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                card["energy_type"] = eng
                                break
                    if not card["energy_type"]:
                        imgs = cells[1].find_all("img", alt=True)
                        for img in imgs:
                            alt = str(img.get("alt", "")).lower()
                            for ger, eng in TYPE_MAP.items():
                                if ger.lower() in alt:
                                    card["energy_type"] = eng
                                    break
                            if card["energy_type"]:
                                break

                elif "KP" in label:
                    hp_match = re.search(r'(\d+)', value)
                    if hp_match:
                        card["hp"] = hp_match.group(1)

                elif "Schwäche" in label:
                    weak_type = None
                    weak_link = cells[1].find("a", href=True)
                    if weak_link:
                        type_href = str(weak_link.get("href", ""))
                        for ger, eng in TYPE_MAP.items():
                            if ger in type_href:
                                weak_type = eng
                                break
                    if not weak_type:
                        imgs = cells[1].find_all("img", alt=True)
                        for img in imgs:
                            alt = str(img.get("alt", "")).lower()
                            for ger, eng in TYPE_MAP.items():
                                if ger.lower() in alt:
                                    weak_type = eng
                                    break
                            if weak_type:
                                break
                    damage_match = re.search(r'\+(\d+)', value)
                    if damage_match and weak_type:
                        card["weakness"] = f"{weak_type}+{damage_match.group(1)}"

                elif "Rückzug" in label:
                    card["retreat"] = str(len(cells[1].find_all("a", href=True)))

                elif "Entwicklungsstufe" in label:
                    if value in ["Basis-Pokémon", "Basis"]:
                        card["stage"] = "Basic"
                    elif "Phase 1" in value or "Stufe 1" in value:
                        card["stage"] = "Stage 1"
                    elif "Phase 2" in value or "Stufe 2" in value:
                        card["stage"] = "Stage 2"
                    else:
                        card["stage"] = value

    # Get attacks
    attack_headers = soup.find_all("h2", string=re.compile("Angriff|Attacken"))
    for attack_header in attack_headers:
        next_elem = attack_header.find_next_sibling()
        while next_elem:
            if next_elem.name == "table" and "angriff" in str(next_elem.get("class", [])):
                for row in next_elem.find_all("tr"):
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        attack_name_cell = cells[1] if len(cells) > 1 else cells[0]
                        for a in attack_name_cell.find_all("a"):
                            a.unwrap()
                        attack_name = attack_name_cell.get_text(strip=True)
                        
                        damage = ""
                        if len(cells) >= 3:
                            damage_text = get_text(cells[-1])
                            damage_match = re.search(r'(\d+)', damage_text)
                            damage = damage_match.group(1) if damage_match else ""

                        costs = []
                        for e in cells[0].find_all("a", href=True):
                            e_href = str(e.get("href", ""))
                            for ger, eng in TYPE_MAP.items():
                                if ger in e_href:
                                    costs.append(eng)
                                    break

                        if attack_name and not attack_name.startswith("Angriff"):
                            card["attacks"].append({"name": attack_name, "damage": damage, "cost": costs, "effect": ""})
                break
            next_elem = next_elem.find_next_sibling()

    # Get rarity and card number
    if infobox:
        for set_row in infobox.find_all("td", class_="zeile"):
            set_text = get_text(set_row)
            num_match = re.search(r'(\d+)/\d+', set_text)
            if num_match:
                card["card_number"] = num_match.group(1)
            rarity_img = set_row.find("img", alt=True)
            if rarity_img:
                alt = str(rarity_img.get("alt", "")).lower()
                if "seltene holografische" in alt:
                    card["rarity"] = "Rare Holo"
                elif "seltene illustrations" in alt:
                    card["rarity"] = "Illustration Rare"
                elif "seltene besondere" in alt:
                    card["rarity"] = "Special Illustration Rare"
                elif "seltene schillernde" in alt:
                    card["rarity"] = "Shiny Rare"
                elif "nicht so häufige" in alt:
                    card["rarity"] = "1 Diamond"
                elif "häufige" in alt:
                    card["rarity"] = "2 Diamond"

    return card


def scrape_set(set_id, set_name, set_url, skip_mega=False):
    print(f"Scraping {set_name} ({set_id})...", flush=True)
    
    soup = get_page(set_url)
    tables = soup.find_all("table", class_="setliste")
    card_links = []

    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                for link in cells[1].find_all("a", href=True):
                    href = str(link.get("href", ""))
                    if skip_mega and href.startswith("/Mega-"):
                        continue
                    match = re.search(r'_(\d+)\)$', href)
                    if match:
                        card_links.append((int(match.group(1)), urljoin("https://www.pokewiki.de", href)))

    card_links.sort(key=lambda x: x[0])
    print(f"  Found {len(card_links)} cards", flush=True)

    cards = []
    for i, (card_num, url) in enumerate(card_links):
        try:
            card_soup = get_page(url)
            card = parse_card_page(card_soup, url, set_id, set_name)
            card["card_number"] = str(card_num)
            cards.append(card)
        except:
            pass
        
        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(card_links)}]", flush=True)
        
        time.sleep(0.15)

    print(f"  Done: {len(cards)} cards", flush=True)
    return cards


def main():
    all_cards = []
    
    # A4b - Deluxepack-ex
    all_cards.extend(scrape_set("A4b", "Deluxepack-ex", SETS[0][2]))
    time.sleep(1)

    # B1 - Mega-Aufstieg (skip Mega cards)
    all_cards.extend(scrape_set("B1", "Mega-Aufstieg", SETS[1][2], skip_mega=True))
    time.sleep(1)

    # B1a - Feuerrote Flammen (skip Mega cards)
    all_cards.extend(scrape_set("B1a", "Feuerrote Flammen", SETS[2][2], skip_mega=True))

    print(f"\nTotal: {len(all_cards)} new cards", flush=True)

    with open("api/cache/new_cards.json", "w", encoding="utf-8") as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    print("Saved to api/cache/new_cards.json")


if __name__ == "__main__":
    main()
