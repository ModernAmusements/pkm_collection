# Pokemon TCG Pocket - Knowledge Base

## Data Sources

### German Cards (2,777 cards)
- Source: pokemongohub.net (German)
- Sets: A1, A1a, A2, A2a, A2b, A3, A3a, A3b, A4, A4a, A4b, PROMO-A, PROMO-B, B1
- Fields: german_name, hp, card_number, set_id, energy_type, stage, rarity, weakness, retreat, illustrator, attacks
- Status: **Complete** - primary source

### English Cards (Deprecated - Removed)
- Limitless data removed - German DB is now the primary source

## OCR Pipeline (V2)

### Steps
1. **Preprocess**: Crop to card region, convert to greyscale (L mode)
2. **Enhance**: Contrast 1.3x, Sharpness 1.2x
3. **Zone Extract**: Extract name zone using ZoneExtractor
4. **OCR**: Tesseract with PSM modes 6, then 3
5. **HP Correction**: Fix common OCR errors:
   - `502` → `50`, `802` → `80` (trailing zeros)
   - `52` → `50`, `58` → `50` (wrong digit)

### Debug Zones
- `screenshots/debug/` - Zone images
- `screenshots/debug/zones_enhanced/` - Enhanced zones for comparison

## Lookup System (local_lookup.py)

### Priority Order
1. **Exact name match** - 90%+ confidence
2. **Fuzzy name + HP** - 90% confidence
3. **HP-only** - 50% confidence (no set required)
All data comes from German card database:
- Uses German name from OCR
- Uses German weakness with +damage (e.g., "Fighting+20")
- Uses German retreat (e.g., "2")
- Uses German attacks (German names)

## Card Types

### Pokemon Cards
1. **Regular Pokemon** - Standard card with HP, attacks
2. **ex Pokemon** - Has "ex" in name, stronger, 2 prize cards when knocked out
3. **Full Art Pokemon** - Text overlaid on artwork, white/silver border around name area
4. **Illustration Rare** - Full card artwork, no traditional layout
5. **Gold Rare** - Gold border, special cards

### Trainer Cards
1. **Item** - Single use, green label
2. **Supporter** - Once per turn, red label
3. **Stadium** - Green label, only one active at a time

## Image Zones

### Pokemon Card (970x1381 after crop)
| Zone | % Range | Content |
|------|---------|---------|
| 1 | 0-10% | Name + HP + Energy Type |
| 2 | 10-12% | Evolution info |
| 3 | 12-47% | Artwork |
| 4 | 47-51% | Card number + Rarity |
| 5 | 51-84% | Attacks + Abilities |
| 6 | 84-100% | Weakness + Resistance + Retreat |

### Trainer Card (970x1381 after crop)
| Zone | % Range | Content |
|------|---------|---------|
| 1 | 0-6% | Type label (Item/Stadium/Supporter) |
| 2 | 6-15% | Card Name |
| 3 | 15-43% | Artwork |
| 4 | 43-87% | Effect text |
| 5 | 87-100% | Set info |

## Full Art Detection
- Full Art cards have text overlaid directly on artwork
- Name area has white/silver border around it
- Zone 1 OCR is very difficult due to text over colorful background
- May need larger OCR zone or special handling

## German Card Names
German Pokemon names are completely different, not just translated:
- Bisasam → Bulbasaur
- Bidifas → Bibarel
- Glumanda → Charmander
- etc.

German Trainer cards:
- Trainingsbereich → Training Area
- Kampfplatz → Battle Arena
- Riesensonde → ??? (Item card)

## OCR Challenges
1. **"xe" → "ex"**: OCR misreads "xe" in HP text as "ex"
2. **Full Art**: Text over artwork makes OCR very difficult
3. **German special characters**: ü, ö, ä, ß may be misread
4. **Multi-word names**: Trainer cards often have multiple words

## Current Workflow

### V2 Extraction Process
1. **Preprocess**: Crop screenshot → 970x1381

2. **Detect Card Type**: Check Zone 1 for keywords
   - "HP/KP" → Pokemon
   - "TRAINER/ITEM/SUPPORTER/STADIUM" → Trainer

3. **Minimal OCR**: Extract ONLY name from Zone
   - Pokemon: Zone 1 (0-10%)
   - Trainer: Zone 2 (6-15%)
   - Try both original and grayscale+contrast enhanced

4. **API Match**: Find card in local database (tries German first, then English)

5. **Save**: Store complete card data from API

### Lookup Priority
1. German cards (german_cards_complete.json) - primary source

### German Database Logic
```
1. OCR extracts German name (e.g., "Enekoro")
2. Look up in German cards → find HP, weakness+damage, retreat, attacks, illustrator
3. Save to collection.db
```

## API Data Sources

### German Cards (Primary)
- Source: pokemongohub.net
- Contains: Full card data
- Count: 2520 cards
- Contains: 2777 cards

## Files
- `api/cache/limitless_cards.json` - English scraped data (2111 cards)
- `api/cache/cards.json` - English cards (2777 cards)
- `api/cache/german_cards_complete.json` - German cards (4834 cards)
- `api/cache/german_cards.csv` - German CSV export
- `api/cache/eng_to_ger_names.json` - English to German name mapping
- `api/cache/set_mapping.json` - English to German set names
- `api/cache/cards_database.db` - SQLite database (tables: scraped_cards, german_cards)
- `collection.db` - User's captured cards (main collection)

## Database Schemas

### collection.db (cards table)
```sql
cards (
    id, name, category, quantity,
    set_name, card_number, hp, stage,
    energy_type, evolution_from, ability,
    attacks, weakness, resistance,
    retreat_cost, rarity, illustrator
)
```

### cards_database.db
- `scraped_cards` - English Limitless cards (2111)
- `german_cards` - German cards (4834)

## Current Data State

### German Cards (4834 cards)
| Set | Count |
|-----|-------|
| A1 | 572 |
| A1a | 172 |
| A2 | 414 |
| A2a | 190 |
| A2b | 220 |
| A3 | 478 |
| A3a | 206 |
| A3b | 214 |
| A4 | 482 |
| A4a | 210 |
| A4b | 758 |
| PROMO-A | 234 |
| PROMO-B | 22 |
| B1 | 662 |

Fields populated:
- hp, card_number, set_id: 4834 ✓
- weakness: 4528 (includes +damage from German)
- attacks: 4412 (from German scraping)
- retreat: 3316
- illustrator: 3612
- energy_type: ~4100
- rarity: ~3400

## Common OCR Fixes
```
xe → (remove - false ex detection)
GX → ex
EAS → ex
Icognito → Incognito
Riesige → (German card name)
Rupel → (German card name)
```
