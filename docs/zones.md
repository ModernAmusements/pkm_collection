# Pokemon TCG Pocket - Zone Extraction Documentation

## Overview

The extraction process divides card screenshots into **zones** for OCR processing. Each zone contains specific card information that helps identify and extract complete card data.

---

## Image Preprocessing

Before zone extraction, screenshots are preprocessed:

```
Original Image
     │
     ▼
┌─────────────────────────────────────┐
│ 1. Detect orientation (rotate if    │
│    width > height)                  │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 2. Crop sides: 8.5% from each side  │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 3. Crop height: 555px from top      │
│    (14% from top of original)       │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│ 4. Scale: 4x for better OCR         │
└─────────────────────────────────────┘
     │
     ▼
  Preprocessed Image (555px height)
```

---

## Pokemon Card Zones

The Pokemon card is divided into **7 zones** from top to bottom:

```mermaid
block-beta
    columns 1
    
    block:row1:1
        columns 1
        z1["Zone 1: 0-55px<br/>Name + HP + Energy"]
    end
    
    block:row2:1
        columns 1
        z2["Zone 2: 55-65px<br/>Evolution Stage"]
    end
    
    block:row3:1
        columns 1
        z3["Zone 3: 65-263px<br/>Artwork (Image)"]
    end
    
    block:row4:1
        columns 1
        z4["Zone 4: 263-282px<br/>Card Number"]
    end
    
    block:row5:1
        columns 1
        z5["Zone 5: 282-475px<br/>Attacks & Abilities"]
    end
    
    block:row6:1
        columns 1
        z6["Zone 6: 475-494px<br/>Weakness + Retreat"]
    end
    
    block:row7:1
        columns 1
        z7["Zone 7: 494-555px<br/>Info (not used)"]
    end

    row1 --> row2 --> row3 --> row4 --> row5 --> row6 --> row7
```

### Pokemon Zone Details

| Zone | Pixels | Height | Content | OCR Purpose |
|------|--------|--------|---------|------------|
| **Zone 1** | 0-55 | 55px | Name + HP + Energy | **Extract for OCR** - Primary identification |
| **Zone 2** | 55-65 | 10px | Evolution stage | Ignored |
| **Zone 3** | 65-263 | 198px | Artwork | Ignored |
| **Zone 4** | 263-282 | 19px | Card number | **API fallback only** - TCG Pocket set numbers don't match general API |
| **Zone 5** | 282-475 | 193px | Attacks + Abilities | **Extract for OCR** - Full text extraction |
| **Zone 6** | 475-494 | 19px | Weakness + Retreat | Ignored |
| **Zone 7** | 494-555 | 61px | Info (not used) | Ignored |

---

## Trainer Card Zones

Trainer cards have a **different layout** with 5 zones:

```mermaid
block-beta
    columns 1
    
    block:row1:1
        columns 1
        z1["Zone 1: 0-41px<br/>Type (Item/Stadium)"]
    end
    
    block:row2:1
        columns 1
        z2["Zone 2: 41-81px<br/>Name"]
    end
    
    block:row3:1
        columns 1
        z3["Zone 3: 81-289px<br/>Artwork"]
    end
    
    block:row4:1
        columns 1
        z4["Zone 4: 289-480px<br/>Effect Description"]
    end
    
    block:row5:1
        columns 1
        z5["Zone 5: 480-554px<br/>Extra (not used)"]
    end

    row1 --> row2 --> row3 --> row4 --> row5
```

### Trainer Zone Details

| Zone | Pixels | Height | Content | OCR Purpose |
|------|--------|--------|---------|------------|
| **Zone 1** | 0-41 | 41px | Type (Item, Stadium, Unterstützung) | Card type detection |
| **Zone 2** | 41-81 | 40px | Name | **Extract for OCR** - Primary identification |
| **Zone 3** | 81-289 | 208px | Artwork | Ignored |
| **Zone 4** | 289-480 | 191px | Effect description | **Extract for OCR** - Full text extraction |
| **Zone 5** | 480-554 | 74px | Extra | Ignored |

---

## Card Type Detection Flow

```mermaid
flowchart TD
    A[Start: Preprocessed Image] --> B[Try Pokemon Zone 1<br/>0-55px]
    
    B --> C{Keywords found?}
    C -->|TRAINER/ARTIKEL/STADION| D[Trainer Card]
    C -->|HP/KP found| E[Pokemon Card]
    C -->|Nothing| F[Try Trainer Zone 1<br/>0-41px]
    
    F --> G{Keywords found?}
    G -->|Yes| D
    G -->|No| E
    
    D --> H[Use TRAINER zones]
    E --> I[Use POKEMON zones]
    
    H --> J[Extract Zones 1-4]
    I --> J
```

---

## Extraction Process Flow

```mermaid
flowchart TD
    A[Screenshot Image] --> B[Preprocess Image<br/>Crop & Scale]
    
    B --> C[Detect Card Type<br/>Pokemon vs Trainer]
    
    C --> D{Type?}
    D -->|Pokemon| E[Extract Pokemon Zones 1,5]
    D -->|Trainer| F[Extract Trainer Zones 1,2,4]
    
    E --> G[OCR Each Zone]
    F --> G
    
    G --> H{Text Found?}
    H -->|Yes| I[Search API by Name<br/>from Zone 1 or 2]
    H -->|No| J[Try Alternative Zones]
    
    I --> K{Match Found?}
    K -->|Yes| L[Get Full Card Data<br/>HP, Attacks, Abilities, etc.]
    K -->|No| M[Try Zone 4 Card Number<br/>for Trainer only]
    
    M --> N{Number Found?}
    N -->|Yes| O[Search API by Number<br/>All TCG Pocket Sets]
    N -->|No| P[Mark as Failed]
    
    O --> L
    L --> Q[Save to CSV]
    Q --> R[Move to captured/]
    
    J --> S[Try Zone 4/5 if available]
    S --> I
    
    P --> T[Move to failed/]
```

---

## OCR Configuration

### Zone Preprocessing Pipeline
1. **Crop**: Extract specific zone from preprocessed card image
2. **Greyscale**: Convert to grayscale for better OCR
3. **Scale**: 3-4x scale factor for better text recognition
4. **Contrast**: Minimal contrast enhancement (1.0x)

### Languages
1. **German (deu)** - Primary (matches game language)
2. **English (eng)** - Fallback

### Energy Type Colors (for manual detection)

| German | English | RGB Range |
|--------|---------|-----------|
| Feuer | Fire | (200-255, 50-100, 50-100) |
| Wasser | Water | (50-100, 100-150, 200-255) |
| Elektro | Lightning | (200-255, 200-255, 50-100) |
| Pflanze | Grass | (50-100, 200-255, 50-100) |
| Kampf | Fighting | (200-255, 150-200, 50-100) |
| Psycho | Psychic | (150-200, 50-100, 200-255) |
| Unlicht | Darkness | (50-100, 50-100, 100-150) |
| Metall | Metal | (150-200, 150-200, 150-200) |
| Fee | Fairy | (200-255, 150-200, 200-255) |
| Drache | Dragon | (150-200, 100-150, 50-100) |
| Farblos | Colorless | (200-255, 200-255, 200-255) |

---

## TCG Pocket Sets (Priority Order)

The API searches these sets in priority order when matching card numbers:

| Set Code | Priority | Set Name |
|----------|----------|----------|
| A1 | 10 | Unschlagbare Gene |
| A1a | 10 | Entwicklungen in Paldea |
| A2 | 9 | Kollision von Raum und Zeit |
| A2a | 9 | Strahlende Sternenpracht |
| A2b | 8 | Neue Helden |
| A3 | 8 | Hüter des Firmaments |
| A3a | 7 | Mysterien der Vergangenheit |
| A3b | 7 | Fantastische Abenteuer |
| A4 | 6 | Silberne Sturmwinde |
| A4a | 6 | Stille Wogen |
| Pikachu | 9 | Pikachu |
| ... | ... | ... |

---

## Output CSV Format

| Column | Description | Source |
|--------|-------------|--------|
| Card Name | Pokemon/Trainer name | API |
| HP | Hit points | API |
| Energy Type | Pokemon energy type | API |
| Weakness | Weakness type + value | API |
| Resistance | Resistance type + value | API |
| Retreat Cost | Retreat cost (0-5) | API |
| Category | Pokemon/Trainer | API |
| Ability Name | Ability name | API |
| Ability Description | Ability effect | API |
| Attack 1 Name | First attack name | Zone 5 (OCR) + API |
| Attack 1 Cost | Energy cost | API |
| Attack 1 Damage | Damage value | API |
| Attack 1 Description | Attack effect | Zone 5 (OCR) + API |
| Attack 2 Name | Second attack name | Zone 5 (OCR) + API |
| Attack 2 Cost | Energy cost | API |
| Attack 2 Damage | Damage value | API |
| Attack 2 Description | Attack effect | Zone 5 (OCR) + API |
| Rarity | Rarity (◊, ◊◊, etc.) | API |
| Pack | Set/Pack name | API |

---

## Summary

### Workflow
1. **Preprocess**: Crop screenshot → Zone extraction → Greyscale → Sharpen → Scale
2. **Detect Card Type**: Check Zone 1 for "HP/KP" (Pokemon) or "TRAINER/ARTIKEL" (Trainer)
3. **OCR Extraction**: Extract specific zones for each card type
4. **API Fallback**: Only use API if OCR fails or doesn't provide enough data

### Zones to Extract
- **Pokemon**: Zone 1 (Name+HP) and Zone 5 (Attacks)
- **Trainer**: Zone 1 (Type), Zone 2 (Name), Zone 4 (Effect)

### Critical Zones
- **Pokemon**: Zone 1 and Zone 5 for OCR, Zone 4 as API fallback (limited)
- **Trainer**: Zone 2 and Zone 4 for OCR, Zone 4 as API fallback

### API Usage
- **Last resort only** - OCR is primary method
- Zone 4 card numbers don't match general Pokemon TCG API
- Only TCG Pocket sets (A1, A1a, A2, etc.) work reliably
