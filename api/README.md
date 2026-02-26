# API - Card Database

## Scraped Cards

Currently scraped from Limitless: **240 cards** (3 sets)

### Scraped Sets
| Set ID | Name | Cards |
|--------|------|-------|
| a1 | Genetic Apex | 80 |
| a1a | Mythical Island | 80 |
| a2a | Triumphant Light | 80 |

### Remaining Sets to Scrape
| Set ID | Name |
|--------|------|
| a1 | Genetic Apex (more) |
| a2 | Space-Time Smackdown |
| a2b | Shining Revelry |
| a3 | Celestial Guardians |
| a3a | Extradimensional Crisis |
| a3b | Eevee Grove |
| a4 | Wisdom of Sea and Sky |
| a4a | Secluded Springs |
| a4b | Deluxe Pack: ex |
| b1 | Mega Rising |
| b1a | Crimson Blaze |
| b2 | Fantastical Parade |
| promo | Promo |

---

## Commands

### Resume Scraping
```bash
python3 api/scrape_all.py --resume
```

### Check Current Status
```bash
python3 -c "import json; c=json.load(open('api/cache/limitless_cards.json')); print(f'Scraped: {len(c)} cards')"
```

---

## Card Type Detection

The extraction now detects:

### Pokemon Variants
- **Regular**: Standard Pokemon cards
- **ex**: Pokemon ex (modern lowercase)
- **Tera**: Tera Pokemon ex
- **Full Art**: Full Art variants
- **Illustration Rare**: IR/SIR cards
- **Gold**: Gold rare cards

### Trainer Subtypes
- **Item**: (ARTIKEL)
- **Supporter**: (UNTERSTÜTZUNG)
- **Stadium**: (STADION)

---

## Data Fields

Each scraped card contains:
- `id` - Card ID (e.g., "a2a-38")
- `set_id` - Set ID (e.g., "a2a")
- `set_name` - Set name
- `card_number` - Card number in set
- `name` - Card name
- `hp` - HP (Pokemon only)
- `energy_type` - Energy type
- `stage` - Stage (Basic/Stage 1/Stage 2)
- `evolution_from` - Evolves from
- `weakness` - Weakness type (+damage)
- `retreat` - Retreat cost
- `attacks` - List of attacks
- `illustrator` - Artist
- `rarity` - Rarity symbols

---

## Usage in V2 Extraction

V2 uses this data for 100% confidence matching:
1. OCR extracts card name
2. Lookup in limitless_cards.json
3. If match found → use ALL scraped data
4. If no match → fallback to chase-manning JSON

**Current coverage**: ~240 cards (needs more sets for full coverage)
