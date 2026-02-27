import json
from bs4 import BeautifulSoup
import requests
import re
import urllib.parse

SETS = [
    ("A3", "Licht des Triumphs", "https://www.pokewiki.de/Licht_des_Triumphs_(TCG_Pocket)"),
    ("A1", "Unschlagbare Gene", "https://www.pokewiki.de/Unschlagbare_Gene_(TCG_Pocket)"),
    ("A2", "Kollision von Raum und Zeit", "https://www.pokewiki.de/Kollision_von_Raum_und_Zeit_(TCG_Pocket)"),
    ("A3a", "Dimensionale Krise", "https://www.pokewiki.de/Dimensionale_Krise_(TCG_Pocket)"),
    ("A3b", "Evoli-Hain", "https://www.pokewiki.de/Evoli-Hain_(TCG_Pocket)"),
    ("A2b", "Weisheit von Meer und Himmel", "https://www.pokewiki.de/Weisheit_von_Meer_und_Himmel_(TCG_Pocket)"),
    ("A4a", "Verborgene Quelle", "https://www.pokewiki.de/Verborgene_Quelle_(TCG_Pocket)"),
    ("B1", "Wundervolles Paldea", "https://www.pokewiki.de/Wundervolles_Paldea_(TCG_Pocket)"),
    ("B2", "Traumhafte Parade", "https://www.pokewiki.de/Traumhafte_Parade_(TCG_Pocket)"),
    ("PROMO-A", "PROMO-A", "https://www.pokewiki.de/PROMO-A_(TCG_Pocket)"),
]

def get_card_links(soup, base_url="https://www.pokewiki.de"):
    links = []
    tables = soup.find_all('table', class_='setliste')
    
    for table in tables:
        all_links = table.find_all('a', href=True)
        for link in all_links:
            href = str(link.get('href', ''))
            
            # Pattern 1: /CardName_SetName_NNN
            match1 = re.search(r'/([^_]+)_[^_]+_(\d+)$', href)
            if match1:
                card_name = match1.group(1)
                full_url = base_url + href
                if (card_name, full_url) not in [(c[0], c[1]) for c in links]:
                    links.append((card_name, full_url))
                continue
            
            # Pattern 2: /CardName_(TCG_Pocket) - Trainer cards
            match2 = re.search(r'/([^_(]+)_\(TCG_Pocket\)$', href)
            if match2:
                card_name = match2.group(1)
                full_url = base_url + href
                if (card_name, full_url) not in [(c[0], c[1]) for c in links]:
                    links.append((card_name, full_url))
    
    return links

def extract_trainer_effect(html):
    if 'karte-trainer' not in html:
        return None, None
    
    soup = BeautifulSoup(html, 'html.parser')
    trainer_table = soup.find('table', class_='karte-trainer')
    if not trainer_table:
        return None, None
    
    rows = trainer_table.find_all('tr')
    effects = []
    for row in rows:
        cells = row.find_all('td')
        if cells:
            text = cells[0].get_text(strip=True)
            if text and len(text) > 10:
                effects.append(text)
    
    if len(effects) > 1:
        effect = " | ".join(effects[1:])
    else:
        effect = effects[0] if effects else None
    
    return "Trainer", effect

all_trainers = []
seen = set()

for set_id, set_name, set_url in SETS:
    print(f"{set_id}...", end=" ", flush=True)
    
    try:
        resp = requests.get(set_url, timeout=15)
        if resp.status_code != 200:
            continue
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        card_links = get_card_links(soup)
        
        for card_name, card_url in card_links:
            try:
                card_resp = requests.get(card_url, timeout=8)
                
                if card_resp.status_code == 200:
                    trainer_type, effect = extract_trainer_effect(card_resp.text)
                    if trainer_type and effect:
                        try:
                            card_name = urllib.parse.unquote(card_name)
                        except:
                            pass
                        
                        key = (card_name, set_id)
                        if key not in seen:
                            seen.add(key)
                            print(f"{card_name}", end=" ", flush=True)
                            all_trainers.append({
                                "german_name": card_name,
                                "set_id": set_id,
                                "set_name": set_name,
                                "url": card_url,
                                "card_type": "Trainer",
                                "ability": effect,
                                "hp": "",
                                "stage": "",
                                "attacks": [],
                                "weakness": "",
                                "retreat": "",
                                "rarity": "",
                                "illustrator": "",
                            })
            except:
                pass
    except:
        pass

print(f"\n\nTotal: {len(all_trainers)} trainer cards")

with open("api/cache/trainers.json", "w", encoding="utf-8") as f:
    json.dump(all_trainers, f, ensure_ascii=False, indent=2)

print("Saved to api/cache/trainers.json")
