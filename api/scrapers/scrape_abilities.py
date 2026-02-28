import json
from bs4 import BeautifulSoup
import requests
import re
import urllib.parse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

SETS = [
    ("A1", "Unschlagbare Gene", "https://www.pokewiki.de/Unschlagbare_Gene_(TCG_Pocket)"),
    ("A2", "Kollision von Raum und Zeit", "https://www.pokewiki.de/Kollision_von_Raum_und_Zeit_(TCG_Pocket)"),
    ("A3", "Licht des Triumphs", "https://www.pokewiki.de/Licht_des_Triumphs_(TCG_Pocket)"),
    ("A3a", "Dimensionale Krise", "https://www.pokewiki.de/Dimensionale_Krise_(TCG_Pocket)"),
    ("A3b", "Evoli-Hain", "https://www.pokewiki.de/Evoli-Hain_(TCG_Pocket)"),
    ("A2b", "Weisheit von Meer und Himmel", "https://www.pokewiki.de/Weisheit_von_Meer_und_Himmel_(TCG_Pocket)"),
    ("A4a", "Verborgene Quelle", "https://www.pokewiki.de/Verborgene_Quelle_(TCG_Pocket)"),
    ("A1a", "Mysteriöse Insel", "https://www.pokewiki.de/Mysteri%C3%B6se_Insel_(TCG_Pocket)"),
    ("A2a", "Hüter des Firmaments", "https://www.pokewiki.de/H%C3%BCter_des_Firmaments_(TCG_Pocket)"),
    ("A2b", "Glänzendes Festival", "https://www.pokewiki.de/Gl%C3%A4nzendes_Festival_(TCG_Pocket)"),
    ("B2a", "Wundervolles Paldea", "https://www.pokewiki.de/Wundervolles_Paldea_(TCG_Pocket)"),
    ("B2", "Traumhafte Parade", "https://www.pokewiki.de/Traumhafte_Parade_(TCG_Pocket)"),
    ("PROMO-A", "PROMO-A", "https://www.pokewiki.de/PROMO-A_(TCG_Pocket)"),
    ("PROMO-B", "PROMO-B", "https://www.pokewiki.de/PROMO-B_(TCG_Pocket)"),
]

def get_card_links(soup, base_url="https://www.pokewiki.de"):
    links = []
    tables = soup.find_all('table', class_='setliste')
    
    for table in tables:
        all_links = table.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            
            # Match pattern: /CardName_SetName_NNN
            if re.search(r'_\d+\)$', href):
                match = re.search(r'/([^_(]+)', href)
                if match:
                    card_name = match.group(1)
                    full_url = base_url + href
                    links.append((card_name, full_url))
    
    return links

def extract_ability(html):
    if 'Pokémon-Power' not in html:
        return None, None
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='karte-angriffe')
    if not table:
        return None, None
    
    rows = table.find_all('tr')
    for row in rows:
        if 'Pokémon-Power' in str(row):
            cells = row.find_all('td')
            ability = None
            
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if cell_text and len(cell_text) > 2:
                    if cell_text.isdigit():
                        continue
                    ability = cell_text
                    break
            
            effect = None
            next_row = row.find_next_sibling()
            if next_row and 'beschreibung' in str(next_row.get('class', [])):
                desc_cell = next_row.find('td')
                if desc_cell:
                    effect = desc_cell.get_text(strip=True)
            
            if ability:
                return ability, effect
    
    return None, None

# Load existing
try:
    existing = json.load(open("api/cache/abilities.json"))
except:
    existing = []

seen = {(a['card_name'], a['set_id']) for a in existing}
all_abilities = list(existing)

for set_id, set_name, set_url in SETS:
    print(f"\n{set_id}...", end=" ", flush=True)
    
    try:
        resp = requests.get(set_url, headers=HEADERS)
        if resp.status_code != 200:
            continue
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        card_links = get_card_links(soup)
        
        for card_name, card_url in card_links:
            try:
                card_resp = requests.get(card_url, headers=HEADERS)
                
                if card_resp.status_code == 200:
                    ability, effect = extract_ability(card_resp.text)
                    if ability:
                        try:
                            card_name = urllib.parse.unquote(card_name)
                        except:
                            pass
                        
                        key = (card_name, set_id)
                        if key not in seen:
                            seen.add(key)
                            print(f"{card_name}", end=" ", flush=True)
                            all_abilities.append({
                                "card_name": card_name,
                                "set_id": set_id,
                                "set_name": set_name,
                                "ability": ability,
                                "ability_effect": effect
                            })
            except:
                pass
    except:
        pass

print(f"\n\nTotal: {len(all_abilities)} abilities")

with open("api/cache/abilities.json", "w", encoding="utf-8") as f:
    json.dump(all_abilities, f, ensure_ascii=False, indent=2)
