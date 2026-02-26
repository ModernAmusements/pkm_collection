#!/usr/bin/env python3
"""
Scrape German Pokemon TCG Pocket card data from pokemongohub.net using Playwright.
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright

BASE_URL = "https://pocket.pokemongohub.net/de"

async def get_all_sets():
    """Get all set URLs from the homepage."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        print("Loading homepage...")
        try:
            await page.goto(BASE_URL, timeout=90000)
            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
            
            # Take screenshot for debugging
            await page.screenshot(path="debug_homepage.png")
            print("Saved screenshot to debug_homepage.png")
            
            # Wait for content to load
            await page.wait_for_selector('a[href*="/de/set/"]', timeout=30000)
            
            # Find all set links
            set_links = await page.query_selector_all('a[href*="/de/set/"]')
            sets = []
            for link in set_links:
                href = await link.get_attribute('href')
                if href and href not in sets:
                    sets.append(href)
        except Exception as e:
            print(f"Error loading homepage: {e}")
            # Try alternative: directly construct set URLs from known set IDs
            sets = [
                "/de/set/t3hb77i3xy08no0-unschlagbare-gene",  # A1
                "/de/set/bh6swrnbnb0xqp7-mysterise-insel",   # A1a
                "/de/set/i344270g8xo3wb9-kollision-von-raum-und-zeit",  # A2
                "/de/set/j6yh136n6ar7m1q-licht-des-triumphs",  # A2a
                "/de/set/48r74kv8tun9j02-glnzendes-festival",  # A2b
                "/de/set/797ubb2z58mtxl1-hter-des-firmaments",  # A3
                "/de/set/n112zho988s4v74-extradimensional-crisis",  # A3a
                "/de/set/0g49s62r1wb1p2b-evoli-hain",  # A3b
                "/de/set/h61dsk33evt45mp-weisheit-von-meer-und-himmel",  # A4
                "/de/set/h5n4a0fs0kvgztc-verborgene-quelle",  # A4a
                "/de/set/dzswkhwwfk811kd-deluxepack-ex",  # A4b
                "/de/set/hrvgwu3dwxaboc7-promo-a",  # PROMO-A
                "/de/set/vxunkwyap88g5jr-promo-b",  # PROMO-B
                "/de/set/0guapr9h7we56l3-mega-aufstieg",  # B1
                "/de/set/t8vwgpxthcklr0n-crimson-blaze",  # B1a
            ]
        
        await browser.close()
        return list(set(sets))

async def get_cards_from_set(set_url, progress_callback=None):
    """Get all card URLs from a set page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Loading set: {set_url}")
        try:
            full_url = f"https://pocket.pokemongohub.net{set_url}"
            await page.goto(full_url, timeout=90000)
            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Wait for cards to load
            await page.wait_for_selector('a[href*="/de/card/"]', timeout=30000)
            
            # Find all card links
            card_links = await page.query_selector_all('a[href*="/de/card/"]')
            cards = []
            for link in card_links:
                href = await link.get_attribute('href')
                if href and href not in cards:
                    cards.append(href)
        except Exception as e:
            print(f"Error loading set {set_url}: {e}")
            cards = []
        
        await browser.close()
        return list(set(cards))

async def scrape_card_details(card_url):
    """Scrape detailed information for a single card."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(f"https://pocket.pokemongohub.net{card_url}" if not card_url.startswith('http') else card_url, 
                          timeout=60000)
            await page.wait_for_timeout(2000)
            
            # Get the page content
            content = await page.content()
            
            # Extract data using regex patterns
            data = {'url': card_url}
            
            # Card name (from URL or heading)
            match = re.search(r'/de/card/[^/]+-([^-]+)$', card_url)
            if match:
                data['german_name'] = match.group(1).replace('-', ' ').title()
            
            # Extract HP
            hp_match = re.search(r'(\d+)\s*KP|KP|HP[:\s]*(\d+)', content, re.I)
            if hp_match:
                data['hp'] = hp_match.group(1) or hp_match.group(2)
            
            # Extract weakness with damage
            weak_match = re.search(r'Schwäche.*?eng-(\w+).*?[\"+](\d+)', content, re.I | re.DOTALL)
            if weak_match:
                data['weakness_type'] = weak_match.group(1)
                data['weakness_damage'] = weak_match.group(2)
            
            # Extract retreat cost
            retreat_match = re.search(r'Rückzugskosten.*?eng-(\w+).*?(\d+)', content, re.I | re.DOTALL)
            if retreat_match:
                data['retreat_energy'] = retreat_match.group(1)
                data['retreat_cost'] = retreat_match.group(2)
            
            # Extract card number
            num_match = re.search(r'Karte.*?#\s*(\d+)\s*/\s*(\d+)', content)
            if num_match:
                data['card_number'] = num_match.group(1)
                data['set_total'] = num_match.group(2)
            
            # Extract energy type
            energy_match = re.search(r'Energie-Typ.*?eng-(\w+)', content)
            if energy_match:
                data['energy_type'] = energy_match.group(1)
            
            # Extract stage
            stage_match = re.search(r'Entwicklungsstufe.*?<strong>([^<]+)', content)
            if stage_match:
                data['stage'] = stage_match.group(1)
            
            # Extract rarity
            rarity_match = re.search(r'(\d+)-Diamant|(\w+)\s*Seltenheit|Stern', content)
            if rarity_match:
                if rarity_match.group(1):
                    data['rarity_diamonds'] = rarity_match.group(1)
                elif rarity_match.group(2):
                    data['rarity'] = rarity_match.group(2)
            
            # Extract illustrator
            illust_match = re.search(r'Illustrator[:\s]*\*\*([^*]+)\*\*', content)
            if illust_match:
                data['illustrator'] = illust_match.group(1)
            
            # Extract pack points
            points_match = re.search(r'(\d+)\s*Booster-Punkte', content)
            if points_match:
                data['pack_points'] = points_match.group(1)
            
            # Extract attacks (name, cost, damage, effect)
            attacks = []
            attack_blocks = re.findall(r'###\s*([^#\n]+).*?(\d+)\s*$', content, re.MULTILINE)
            for name, damage in attack_blocks[:3]:
                attacks.append({
                    'name': name.strip(),
                    'damage': damage.strip()
                })
            if attacks:
                data['attacks'] = attacks
            
            # Extract release date
            date_match = re.search(r'Verfügbar seit\s*(\d{2}/\d{2}/\d{4})', content)
            if date_match:
                data['release_date'] = date_match.group(1)
            
            return data
            
        except Exception as e:
            print(f"Error scraping {card_url}: {e}")
            return {'url': card_url, 'error': str(e)}
        
        finally:
            await browser.close()

async def main():
    print("=" * 60)
    print("Pokemon TCG Pocket - German Card Scraper")
    print("=" * 60)
    
    # Step 1: Get all sets
    print("\n[1/3] Fetching all sets...")
    sets = await get_all_sets()
    print(f"Found {len(sets)} sets")
    
    # Step 2: Get all cards from all sets
    print("\n[2/3] Fetching all card URLs...")
    all_cards = []
    for i, set_url in enumerate(sets):
        print(f"  Set {i+1}/{len(sets)}: {set_url.split('/')[-1]}")
        cards = await get_cards_from_set(set_url)
        all_cards.extend(cards)
        print(f"    -> Found {len(cards)} cards")
    
    all_cards = list(set(all_cards))
    print(f"\nTotal cards found: {len(all_cards)}")
    
    # Step 3: Scrape each card
    print("\n[3/3] Scraping card details...")
    scraped_data = []
    
    for i, card_url in enumerate(all_cards):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(all_cards)} cards scraped...")
        
        data = await scrape_card_details(card_url)
        scraped_data.append(data)
        
        # Save incrementally
        if (i + 1) % 50 == 0:
            with open('api/cache/german_cards_scraped.json', 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    
    # Final save
    with open('api/cache/german_cards_scraped.json', 'w', encoding='utf-8') as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 60}")
    print(f"Scraping complete! Saved {len(scraped_data)} cards")
    print(f"Saved to: api/cache/german_cards_scraped.json")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    asyncio.run(main())
