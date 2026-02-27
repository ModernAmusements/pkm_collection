# Data Workflow

This document shows the data flow through the Pokemon TCG Pocket card extraction system.

## Card Extraction Pipeline

```mermaid
flowchart TD
    A[Screenshot Image] --> B[Card Type Detection]
    B --> C{Type?}
    C -->|Pokemon| D[Zone Extraction]
    C -->|Trainer| E[Trainer Processing]
    C -->|Energy| F[Energy Processing]
    
    D --> G[Name Zone OCR]
    D --> H[HP Zone OCR]
    D --> I[Attack Zone OCR]
    D --> J[Weakness/Retreat Zone OCR]
    
    G --> K[Signal Correction]
    H --> K
    I --> K
    J --> K
    
    K --> L[Card Matching Engine]
    
    L --> M{Confidence >= 60%?}
    M -->|Yes| N[collection.db]
    M -->|No| O[failed_to_capture/]
    
    N --> P[Export CSV]
    
    E --> K
    F --> K
```

## Database Sources

```mermaid
flowchart LR
    A[pokewiki.de] -->|Scrape| B[pokewiki_*.json]
    B -->|Combine| C[pokewiki_scraped_all.json]
    C -->|Index| D[cards.db SQLite]
    
    E[Abilities Scraping] -->|Scrape| F[abilities.json]
    F --> C
```

## Card Matching Priority

```mermaid
flowchart TD
    A[OCR Signals] --> B{Exact Name + Set?}
    B -->|Yes| C[95% Confidence]
    B -->|No| D{Name + HP?}
    
    D -->|Yes| E[85% Confidence]
    D -->|No| F{HP + Attack + Set?}
    
    F -->|Yes| G[85% Confidence]
    F -->|No| H{HP + Weakness + Set?}
    
    H -->|Yes| I[80% Confidence]
    H -->|No| J{HP Only?}
    
    J -->|Yes| K[60% Confidence - Last Resort]
    J -->|No| L[No Match]
    
    C --> M[Add to Collection]
    E --> M
    G --> M
    I --> M
    K --> M
    L --> N[failed_to_capture/]
```

## Data Schema

### Input: Screenshot
```
PKM_CARDS/A1/card_001.png
```

### After OCR: Signals
```json
{
  "name": "Darkrai-ex",
  "hp": "130",
  "attacks": ["Finstere Flut"],
  "weakness": "Fire+20",
  "retreat": "2"
}
```

### Database Match: Card Data
```json
{
  "german_name": "Darkrai-ex",
  "set_id": "A2",
  "set_name": "Kollision von Raum und Zeit",
  "hp": "130",
  "energy_type": "Psychic",
  "stage": "Stage 1",
  "attacks": [{"name": "Finstere Flut", "damage": "130"}],
  "weakness": "Fire+20",
  "retreat": "2",
  "ability": "Schattendolch",
  "ability_effect": "...",
  "rarity": "4 Star"
}
```

### Collection Storage
```
collection.db → cards table
├── name: Darkrai-ex
├── set_name: A2
├── hp: 130
├── quantity: 1
└── ... (all card fields)
```

## File Transformations

```mermaid
flowchart LR
    subgraph Input
        A[Screenshot]
    end
    
    subgraph Processing
        B[extract_batch_v2.py]
        C[EasyOCR]
        D[local_lookup.py]
    end
    
    subgraph Cache
        E[pokewiki_scraped_all.json]
        F[abilities.json]
    end
    
    subgraph Output
        G[collection.db]
        H[collection_export.csv]
        I[failed_to_capture/]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    D --> F
    E --> D
    F --> D
    D --> G
    G --> H
    D --> I
```

## Collection Statistics Flow

```mermaid
flowchart TD
    A[collection.db] --> B[database.py]
    B --> C[get_stats]
    C --> D{Total Cards}
    C --> E{By Set}
    C --> F{By Rarity}
    C --> G{Failed Captures}
    
    D --> H[Display Stats]
    E --> H
    F --> H
    G --> H
```

## Scraping Workflow

```mermaid
flowchart TD
    A[pokewiki.de Set Page] --> B[scrape_pokewiki.py]
    B --> C[Extract Card Links]
    C --> D[For Each Card]
    D --> E[Fetch Card Page]
    E --> F[Parse HTML]
    F --> G[Extract Data]
    G --> H[pokewiki_{set}.json]
    
    I[pokewiki.de Card Page] --> J[scrape_abilities.py]
    J --> K[Find Cards with Power]
    K --> L[Extract Ability]
    L --> M[abilities.json]
    
    H --> N[Combine All Sets]
    M --> N
    N --> O[pokewiki_scraped_all.json]
```
