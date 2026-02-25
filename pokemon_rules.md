# Pokemon TCG Pocket - Card Structure

## Why Minimal OCR + API?

Traditional OCR struggles with:
- Holographic cards (sparkle patterns)
- Small fonts in badges
- German/English mixed text
- Color energy symbols

**Solution**: Extract only the name (most reliable), then get complete data from API.

---

## Pokemon Card Structure

### 1. Top Bar (Zone 1)
- Name (top left)
- HP (top right)
- Stage indicator (Basic / Stage 1 / Stage 2 / ex)
- Evolution info

**V2**: Extracts ONLY the name for API matching

---

### 2. Artwork Box
- Large central illustration
- Silver border (SV era)
- Full-art variants

**V2**: Ignored

---

### 3. Type + Ability
- Energy type symbol near name
- Ability section (if applicable)

**V2**: From API

---

### 4. Attacks Section
- Energy cost icons
- Attack name
- Damage number
- Effect description

**V2**: From API

---

### 5. Bottom Info Bar
- Weakness (type + damage)
- Resistance
- Retreat cost
- Regulation mark
- Set number + rarity
- Illustrator credit

**V2**: From API

---

## Trainer Card Structure

1. Top label: Trainer + subtype (Item / Supporter / Stadium)
2. Full artwork
3. Effect text box
4. Set info bottom left

**V2**: Extracts ONLY name for matching

---

## API Data Fields

When a card is matched by name, V2 saves ALL of these from the API:

| Field | Source |
|-------|--------|
| name | OCR |
| hp | API |
| stage | API |
| energy_type | API |
| evolution_from | API |
| attacks | API |
| weakness | API |
| retreat_cost | API |
| illustrator | API |
| rarity | API |
| set_name | API |
| card_number | API |

This gives **100% confidence** because:
- Name is OCR'd (verified)
- All other fields come from complete API data
