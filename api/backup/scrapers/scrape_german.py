#!/usr/bin/env python3
"""
Scrape German Pokemon TCG Pocket card data from pokemongohub.net
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time

BASE_URL = "https://pocket.pokemongohub.net/de"

CATEGORIES = [
    "item-cards",
    "supporter-cards", 
    "pokemon-tool-cards",
]

def get_card_links(category_url):
    """Get all card links from a category page."""
    response = requests.get(category_url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/de/card/' in href:
            full_url = f"https://pocket.pokemongohub.net{href}"
            if full_url not in links:
                links.append(full_url)
    
    return links

def get_card_details(card_url):
    """Get detailed info for a single card."""
    try:
        response = requests.get(card_url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get card name from page title or heading
        name = None
        
        # Try to find the name in heading
        heading = soup.find('h1') or soup.find('h2')
        if heading:
            name = heading.get_text().strip()
        
        # Try meta title
        if not name:
            title = soup.find('title')
            if title:
                name = title.get_text().split('|')[0].strip()
        
        # Get set from breadcrumb or set info
        set_name = None
        card_number = None
        
        # Look for set info
        set_elem = soup.find(string=re.compile(r'Set:'))
        if set_elem:
            set_match = re.search(r'([A-Z][0-9a-z]+)', set_elem)
            if set_match:
                set_name = set_match.group(1)
        
        # Look for card number
        num_elem = soup.find(string=re.compile(r'#\d+'))
        if num_elem:
            num_match = re.search(r'#(\d+)', num_elem)
            if num_match:
                card_number = num_match.group(1)
        
        return {
            'name': name,
            'set': set_name,
            'number': card_number,
            'url': card_url
        }
        
    except Exception as e:
        print(f"Error fetching {card_url}: {e}")
        return None

def scrape_all_cards():
    """Scrape all cards from all trainer categories."""
    all_cards = []
    
    for category in CATEGORIES:
        url = f"{BASE_URL}/{category}"
        print(f"\n=== Scraping {category} ===")
        
        links = get_card_links(url)
        print(f"Found {len(links)} cards")
        
        for i, link in enumerate(links):
            print(f"  [{i+1}/{len(links)}] {link}")
            card = get_card_details(link)
            if card and card.get('name'):
                all_cards.append(card)
                print(f"    -> {card['name']}")
            time.sleep(0.2)  # Rate limit
    
    return all_cards

def generate_mappings(cards):
    """Generate German->English mappings from scraped cards."""
    # Manual mappings for known translations
    # This would need to be expanded with English database matching
    
    mappings = {}
    for card in cards:
        german_name = card.get('name', '').lower()
        if german_name:
            # Store for later matching
            mappings[german_name] = card
    
    return mappings

if __name__ == "__main__":
    cards = scrape_all_cards()
    
    print(f"\n=== Total cards scraped: {len(cards)} ===")
    
    # Save raw data
    with open('api/cache/german_cards_scraped.json', 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)
    
    print("Saved to api/cache/german_cards_scraped.json")
    
    # Print unique names
    names = sorted(set(c.get('name', '') for c in cards if c.get('name')))
    print(f"\nUnique German card names ({len(names)}):")
    for name in names[:50]:
        print(f"  {name}")
