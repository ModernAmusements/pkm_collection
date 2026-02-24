# Pokémon TCG Pocket Card Inventory

Extract your complete card collection from Pokémon TCG Pocket using OCR + API.

## How It Works

1. **Preprocess** - Crop screenshot → Zone extraction → Greyscale → Scale
2. **Detect** - Pokemon vs Trainer card (Zone 1 keywords)
3. **OCR** - Extract text from specific zones:
   - **Pokemon**: Zone 1 (Name+HP) + Zone 5 (Attacks)
   - **Trainer**: Zone 1 (Type) + Zone 2 (Name) + Zone 4 (Effect)
4. **API Fallback** - Only if OCR fails or lacks data
5. **Save** - Move to captured + append to CSV

## Extraction Flow

```
┌─────────────────────┐
│ 1. PREPROCESS      │  Crop sides 8.5%, crop height 555px
│ Image (472x1018)   │  → Output: 392x555
└──────────┬──────────┘
            ▼
┌─────────────────────┐
│ 2. DETECT TYPE      │  OCR Zone 1, look for keywords
│ Pokemon/Trainer     │  HP/KP = Pokemon, TRAINER/ARTIKEL = Trainer
└──────────┬──────────┘
            ▼
┌─────────────────────┐
│ 3. OCR ZONES       │  Pokemon: Zone 1 + Zone 5
│ Extract specific   │  Trainer: Zone 1 + Zone 2 + Zone 4
│ zones for each     │  Scale 3x, Grayscale, OCR (German)
└──────────┬──────────┘
            ▼
┌─────────────────────┐
│ 4. API FALLBACK    │  Only if OCR fails or lacks data
│ (Last Resort)      │  Search by name first, then card number
└──────────┬──────────┘
            ▼
┌─────────────────────┐
│ 5. SAVE            │  Move to captured/
│ Success/Failed     │  Append to CSV
└─────────────────────┘
```

## Zone Definitions

### Pokemon Cards (7 zones)
| Zone | Pixels | Content |
|------|--------|---------|
| 1 | 0-55 | Pokemon name + HP + Energy |
| 2 | 55-65 | Evolution stage |
| 3 | 65-263 | Artwork |
| 4 | 263-282 | Card number |
| 5 | 282-475 | Attacks & Abilities |
| 6 | 475-494 | Weakness + Retreat |
| 7 | 494-555 | Info text |

### Trainer Cards (5 zones)
| Zone | Pixels | Content |
|------|--------|---------|
| 1 | 0-41 | Card type (Item/Stadium) |
| 2 | 41-81 | Card name |
| 3 | 81-289 | Artwork |
| 4 | 289-480 | Effect |
| 5 | 480-554 | Special rule |

## Image Preprocessing

- Crop sides: 8.5% from each side
- Crop height: 555px from top (14% from top)
- Scale: 3x for OCR

## Folder Structure

```
screenshots/
├── to_process/          # Screenshots to process (input)
├── captured/           # Successfully identified cards (output)
└── failed_to_capture/  # Cards that couldn't be identified (output)
```

## Setup

### Install Dependencies

```bash
pip install pillow pytesseract requests
brew install tesseract
```

### Capture Screenshots

1. Open Pokémon TCG Pocket on your phone
2. Go to your card collection
3. Screen record or take screenshots of each card
4. Transfer images to your Mac
5. Put images in `screenshots/to_process/`

## Usage

```bash
# Show status
python3 extract_batch.py status

# Process next 25 cards
python3 extract_batch.py run

# Process specific number
python3 extract_batch.py run 50

# Reset progress
python3 extract_batch.py reset
```

## Output CSV Format

| Column | Description |
|--------|-------------|
| Card Name | German card name |
| HP | Hit points (KP) |
| Energy Type | Card energy (Feuer, Wasser, Psycho, etc.) |
| Weakness | Weakness type and value |
| Retreat Cost | Retreat cost |
| Category | Pokemon/Trainer |
| Ability Name | German ability name |
| Ability Description | Ability effect |
| Attack 1 Name | First attack name |
| Attack 1 Cost | Energy cost |
| Attack 1 Damage | Damage |
| Attack 1 Description | Attack effect |
| Attack 2 Name | Second attack name |
| Attack 2 Cost | Energy cost |
| Attack 2 Damage | Damage |
| Attack 2 Description | Attack effect |
| Rarity | Rareza (Ein Diamant, Zwei Diamant, etc.) |
| Pack | German set name |

## Card Data Source

Card data fetched from [TCGdex API](https://tcgdex.dev/) in German.

## Tips

- Process in batches of 25 to avoid API rate limits
- Script saves progress automatically - safe to stop anytime
- Failed cards go to `failed_to_capture/` - can retry later
