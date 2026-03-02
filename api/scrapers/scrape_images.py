#!/usr/bin/env python3
"""
Scraper to fetch missing card images from pokewiki.de
"""

import json
import time
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote, urljoin
import sys

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

def get_page(url: str) -> BeautifulSoup:
    """Fetch a page and return BeautifulSoup object."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def extract_image_from_designs_section(soup: BeautifulSoup, german_name: str, set_id: str, card_number: str, set_name: str) -> list:
    """Extract image URLs from the 'Verschiedene Designs' section."""
    images = []
    
    # Get set name in German from our data or URL
    set_name_map = {
        "A1": "Unschlagbare Gene",
        "A1a": "Mysteriöse Insel",
        "A2": "Kollision von Raum und Zeit",
        "A2a": "Hüter des Firmaments",
        "A2b": "Weisheit von Meer und Himmel",
        "A3": "Licht des Triumphs",
        "A3a": "Dimensionale Krise",
        "A3b": "Evoli-Hain",
        "A4": "Weisheit von Meer und Himmel",
        "A4a": "Verborgene Quelle",
        "A4b": "Deluxepack-ex",
        "B1": "Mega-Aufstieg",
        "B1a": "Feuerrote Flammen",
        "B2": "Traumhafte Parade",
        "B2a": "Wundervolles Paldea",
        "PROMO-A": "PROMO-A",
        "PROMO-B": "PROMO-B",
    }
    
    target_set = set_name_map.get(set_id, set_name)
    
    designs = soup.find_all("div", class_="design")
    for design in designs:
        # Check if this design matches our target set
        set_div = design.find("div", class_="set")
        if not set_div:
            continue
        
        set_text = set_div.get_text()
        
        # Check if this design matches our target set (partial match)
        if target_set not in set_text:
            continue
        
        img_div = design.find("div", class_="img")
        if not img_div:
            continue
            
        img_tag = img_div.find("img")
        if not img_tag:
            continue
            
        src = img_tag.get("src", "")
        if not src:
            continue
            
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://www.pokewiki.de" + src
            
        # Remove thumbnail path to get full image
        if "/thumb/" in src:
            src = src.replace("/thumb/", "/").split("/px-")[0]
            
        if src not in images:
            images.append(src)
    
    return images


def extract_image_from_infobox(soup: BeautifulSoup) -> str:
    """Extract main image from card infobox."""
    bild_td = soup.find("td", class_="bild")
    if not bild_td:
        return None
        
    img_tag = bild_td.find("img")
    if not img_tag:
        return None
        
    src = img_tag.get("src", "")
    if not src:
        return None
        
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        src = "https://www.pokewiki.de" + src
        
    # Get full-size image (not thumbnail)
    if "/thumb/" in src:
        # Format: /images/thumb/c/cd/Bisasam_%28set_001%29.png/200px-Bisasam_%28set_001%29.png
        # Want: /images/c/cd/Bisasam_%28set_001%29.png
        src = src.replace("/thumb/", "/")
        if "/200px-" in src:
            src = src.split("/200px-")[0]
        
    return src


def get_card_image_urls(url: str, german_name: str, set_id: str, card_number: str, set_name: str) -> list:
    """Get image URL for a card."""
    soup = get_page(url)
    if not soup:
        return []
    
    images = []
    
    infobox_img = extract_image_from_infobox(soup)
    if infobox_img:
        images.append(infobox_img)
    
    return images


def get_set_name_from_url(url: str) -> str:
    """Extract set name from URL like https://www.pokewiki.de/Bisasam_(Unschlagbare_Gene_001)"""
    match = re.search(r'_([A-Za-z_]+)_\d+', url)
    if match:
        return match.group(1).replace("_", " ")
    return ""


def main():
    print("Loading card data...", file=sys.stderr)
    
    with open("api/cache/pokewiki_scraped_all.json", "r", encoding="utf-8") as f:
        card_data = json.load(f)
    
    with open("api/cache/card_images.json", "r", encoding="utf-8") as f:
        existing_images = json.load(f)
    
    existing_urls = set(c.get("card_url", "") for c in existing_images)
    
    missing_cards = [c for c in card_data if c.get("url") not in existing_urls]
    print(f"Found {len(missing_cards)} cards missing images", file=sys.stderr)
    
    new_images = []
    total = len(missing_cards)
    
    for i, card in enumerate(missing_cards):
        if i % 10 == 0:
            print(f"Progress: {i}/{total}", file=sys.stderr)
        
        url = card.get("url", "")
        german_name = card.get("german_name", "")
        set_id = card.get("set_id", "")
        card_number = card.get("card_number", "")
        set_name = card.get("set_name", "")
        
        if not url:
            continue
        
        time.sleep(0.3)
        
        images = get_card_image_urls(url, german_name, set_id, card_number, set_name)
        
        if images:
            for img_url in images:
                new_images.append({
                    "german_name": german_name,
                    "set_id": set_id,
                    "set_name": set_name,
                    "card_number": card_number,
                    "card_url": url,
                    "image_url": img_url
                })
            print(f"  Found {len(images)} image(s) for {german_name} ({set_id}) #{card_number}", file=sys.stderr)
        else:
            print(f"  No images found for {german_name} ({set_id}) #{card_number}", file=sys.stderr)
        
        if i > 0 and i % 50 == 0:
            print(f"Saving intermediate results ({len(new_images)} new images)...", file=sys.stderr)
            with open("api/cache/card_images_new.json", "w", encoding="utf-8") as f:
                json.dump(new_images, f, ensure_ascii=False, indent=2)
    
    print(f"Total new images found: {len(new_images)}", file=sys.stderr)
    
    if new_images:
        print("Saving new images...", file=sys.stderr)
        with open("api/cache/card_images_new.json", "w", encoding="utf-8") as f:
            json.dump(new_images, f, ensure_ascii=False, indent=2)
        print("Saved to api/cache/card_images_new.json", file=sys.stderr)


if __name__ == "__main__":
    main()
