#!/usr/bin/env python3
"""
Local database lookup for Pokemon TCG Pocket cards.
Priority: Scraped Limitless data > chase-manning JSON
"""

import re
import json
from pathlib import Path
from typing import Optional
from .download import load_cards, load_expansions
from .models import CardData, MatchResult


# Cache for limitless cards
_LIMITLESS_CARDS = None


def load_limitless_cards() -> list:
    """Load cards from scraped Limitless data."""
    global _LIMITLESS_CARDS
    if _LIMITLESS_CARDS is not None:
        return _LIMITLESS_CARDS
    
    cache_file = Path("api/cache/limitless_cards.json")
    if cache_file.exists():
        with open(cache_file, 'r') as f:
            _LIMITLESS_CARDS = json.load(f)
            return _LIMITLESS_CARDS
    return []


# Pokedex number mapping (built from card names - simplified)
# In reality, this would need a proper mapping
POKEMON_POKEDEX = {
    'bulbasaur': 1, 'ivysaur': 2, 'venusaur': 3,
    'charmander': 4, 'charmeleon': 5, 'charizard': 6,
    'squirtle': 7, 'wartortle': 8, 'blastoise': 9,
    'caterpie': 10, 'metapod': 11, 'butterfree': 12,
    'weedle': 13, 'kakuna': 14, 'beedrill': 15,
    'pidgey': 16, 'pidgeotto': 17, 'pidgeot': 18,
    'rattata': 19, 'raticate': 20, 'spearow': 21,
    'fearow': 22, 'ekans': 23, 'arbok': 24,
    'pikachu': 25, 'raichu': 26, 'sandshrew': 27,
    'sandslash': 28, 'nidoran': 29, 'nidorina': 30,
    'nidoqueen': 31, 'nidorino': 32, 'nidoking': 33,
    'clefairy': 35, 'clefable': 36, 'vulpix': 37,
    'ninetales': 38, 'jigglypuff': 39, 'wigglytuff': 40,
    'zubat': 41, 'golbat': 42, 'oddish': 43,
    'gloom': 44, 'vileplume': 45, 'paras': 46,
    'parasect': 47, 'venonat': 48, 'venomoth': 49,
    'diglett': 50, 'dugtrio': 51, 'meowth': 52,
    'persian': 53, 'psyduck': 54, 'golduck': 55,
    'mankey': 56, 'primeape': 57, 'growlithe': 58,
    'arcanine': 59, 'poliwag': 60, 'poliwhirl': 61,
    'poliwrath': 62, 'abra': 63, 'kadabra': 64,
    'alakazam': 65, 'machop': 66, 'machoke': 67,
    'machamp': 68, 'bellsprout': 69, 'weepinbell': 70,
    'victreebel': 71, 'tentacool': 72, 'tentacruel': 73,
    'geodude': 74, 'graveler': 75, 'golem': 76,
    'ponyta': 77, 'rapidash': 78, 'slowpoke': 79,
    'slowbro': 80, 'magnemite': 81, 'magneton': 82,
    'farfetchd': 83, 'drowzee': 84, 'krabby': 85,
    'kingler': 86, 'voltorb': 87, 'electrode': 88,
    'exeggcute': 89, 'exeggutor': 90, 'cubone': 91,
    'marowak': 92, 'hitmonlee': 106, 'hitmonchan': 107,
    'lickitung': 108, 'koffing': 109, 'weezing': 110,
    'rhyhorn': 111, 'rhydon': 112, 'chansey': 113,
    'tangela': 114, 'kangaskhan': 115, 'horsea': 116,
    'seadra': 117, 'goldeen': 118, 'seaking': 119,
    'staryu': 120, 'starmie': 121, 'mr mime': 122,
    'scyther': 123, 'jynx': 124, 'electabuzz': 125,
    'magmar': 126, 'pinsir': 127, 'tauros': 128,
    'magikarp': 129, 'gyarados': 130, 'lapras': 131,
    'ditto': 132, 'eevee': 133, 'vaporeon': 134,
    'jolteon': 135, 'flareon': 136, 'porygon': 137,
    'omanyte': 138, 'omastar': 139, 'kabuto': 140,
    'kabutops': 141, 'aerodactyl': 142, 'snorlax': 143,
    'articuno': 144, 'zapdos': 145, 'moltres': 146,
    'dratini': 147, 'dragonair': 148, 'dragonite': 149,
    'mewtwo': 150, 'mew': 151,
    # Gen 2
    'chikorita': 152, 'bayleef': 153, 'meganium': 154,
    'cyndaquil': 155, 'quilava': 156, 'typhlosion': 157,
    'totodile': 158, 'croconaw': 159, 'feraligatr': 160,
    'sentret': 161, 'furret': 162, 'hoothoot': 163,
    'noctowl': 164, 'ledyba': 165, 'ledian': 166,
    'spinarak': 167, 'ariados': 168, 'crobat': 169,
    'pichu': 172, 'cleffa': 173, 'igglybuff': 174,
    'togepi': 175, 'togetic': 176, 'natu': 177,
    'xatu': 178, 'mareep': 179, 'flaaffy': 180,
    'ampharos': 181, 'bellossom': 182, 'marill': 187,
    'azumarill': 188, 'politoed': 189, 'jumpluff': 190,
    'aipom': 191, 'sunkern': 192, 'sunflora': 193,
    'yanma': 194, 'wooper': 194, 'quagsire': 195,
    'espeon': 196, 'umbreon': 197, 'murkrow': 198,
    'slowking': 199, 'misdreavus': 200, 'wobbuffet': 202,
    'girafarig': 203, 'pineco': 204, 'forretress': 205,
    'dunsparce': 206, 'gligar': 207, 'steelix': 208,
    'qwilfish': 209, 'scizor': 212, 'shuckle': 213,
    'heracross': 214, 'sneasel': 215, 'tediursa': 216,
    'ursaring': 217, 'slugma': 218, 'magcargo': 219,
    'swinub': 220, 'piloswine': 221, 'corsola': 222,
    'remoraid': 223, 'octillery': 224, 'delibird': 225,
    'mantine': 226, 'skarmory': 227, 'houndour': 228,
    'houndoom': 229, 'kingdra': 230, 'phanpy': 231,
    'donphan': 232, 'porygon2': 233, 'stantler': 234,
    'smeargle': 235, 'tyrogue': 236, 'hitmontop': 237,
    'smoochum': 238, 'elekid': 239, 'magby': 240,
    'miltank': 241, 'blissey': 242, 'raikou': 243,
    'entei': 244, 'suicune': 245, 'larvitar': 246,
    'pupitar': 247, 'tyranitar': 248, 'lugia': 249,
    'ho-oh': 250, 'celebi': 251,
    # Gen 3
    'treecko': 252, 'grovyle': 253, 'sceptile': 254,
    'torchic': 255, 'combusken': 256, 'blaziken': 257,
    'mudkip': 258, 'marshtomp': 259, 'swampert': 260,
    'poochyena': 261, 'mightyena': 262, 'zigzagoon': 263,
    'linoone': 264, 'wurmple': 265, 'silcoon': 266,
    'beautifly': 267, 'cascoon': 268, 'dustox': 269,
    'lotad': 270, 'lombre': 271, 'ludicolo': 272,
    'seedot': 273, 'nuzleaf': 274, 'shiftry': 275,
    'taillow': 276, 'swellow': 277, 'wingull': 278,
    'pelipper': 279, 'ralts': 280, 'kirlia': 281,
    'gardevoir': 282, 'surskit': 283, 'masquerain': 284,
    'shroomish': 285, 'breloom': 286, 'slakoth': 287,
    'vigoroth': 288, 'slaking': 289, 'nincada': 290,
    'ninjask': 291, 'shedinja': 292, 'whismur': 293,
    'loudred': 294, 'exploud': 295, 'makuhita': 296,
    'hariyama': 297, 'azurill': 298, 'nosepass': 299,
    'skitty': 300, 'delcatty': 301, 'sableye': 302,
    'mawile': 303, 'aron': 304, 'lairon': 305,
    'aggron': 306, 'meditite': 307, 'medicham': 308,
    'electrike': 309, 'manectric': 310, 'plusle': 311,
    'minun': 312, 'volbeat': 313, 'illumise': 314,
    'roselia': 315, 'gulpin': 316, 'swalot': 317,
    'carvanha': 318, 'sharpedo': 319, 'wailmer': 320,
    'wailord': 321, 'numel': 322, 'camerupt': 323,
    'torkoal': 324, 'spoink': 325, 'grumpig': 326,
    'spinda': 327, 'trapinch': 328, 'vibrava': 329,
    'flygon': 330, 'cacnea': 331, 'cacturne': 332,
    'swablu': 333, 'altaria': 334, 'zangoose': 335,
    'seviper': 336, 'lunatone': 337, 'solrock': 338,
    'barboach': 339, 'whiscash': 340, 'corphish': 341,
    'crawdaunt': 342, 'baltoy': 343, 'claydol': 344,
    'lileep': 345, 'cradily': 346, 'anorith': 347,
    'armaldo': 348, 'feebas': 349, 'milotic': 350,
    'castform': 351, 'kecleon': 352, 'shuppet': 353,
    'banette': 354, 'duskull': 355, 'dusclops': 356,
    'tropius': 357, 'chimecho': 358, 'absol': 359,
    'wynaut': 360, 'snorunt': 361, 'glalie': 362,
    'spheal': 363, 'sealeo': 364, 'walrein': 365,
    'clamperl': 366, 'huntail': 367, 'gorebyss': 368,
    'relicanth': 369, 'luvdisc': 370, 'bagon': 371,
    'shelgon': 372, 'salamence': 373, 'beldum': 374,
    'metang': 375, 'metagross': 376, 'regirock': 377,
    'regice': 378, 'registeel': 379, 'latias': 380,
    'latios': 381, 'kyogre': 382, 'groudon': 383,
    'rayquaza': 384, 'jirachi': 385, 'deoxys': 386,
    # Add more as needed - this is a simplified mapping
}


def get_pokedex_number(name: str) -> Optional[int]:
    """Get Pokedex number from Pokemon name."""
    name_lower = name.lower().strip()
    return POKEMON_POKEDEX.get(name_lower)


def normalize_name(name: str) -> str:
    """Normalize card name for comparison."""
    # Remove special characters, lowercase
    name = re.sub(r'[^a-z0-9]', '', name.lower())
    return name


def find_card_by_pokedex(cards: list, pokedex: int, hp: str = None) -> list:
    """Find cards by Pokedex number."""
    results = []
    
    for card in cards:
        card_pokedex = get_pokedex_number(card.get('name', ''))
        if card_pokedex == pokedex:
            if hp:
                try:
                    card_hp = int(card.get('health', 0))
                    if card_hp == int(hp):
                        results.append(card)
                except (ValueError, TypeError):
                    results.append(card)
            else:
                results.append(card)
    
    return results


def find_card_by_name(cards: list, name: str, hp: str = None, 
                      energy: str = None) -> list:
    """Find cards by name with optional filters."""
    results = []
    name_norm = normalize_name(name)
    
    for card in cards:
        card_name_norm = normalize_name(card.get('name', ''))
        
        if name_norm in card_name_norm or card_name_norm in name_norm:
            # Apply filters
            if hp:
                try:
                    card_hp = int(card.get('health', 0))
                    if card_hp != int(hp):
                        continue
                except (ValueError, TypeError):
                    pass
            
            if energy:
                card_energy = card.get('type', '').lower()
                if card_energy != energy.lower():
                    continue
            
            results.append(card)
    
    return results


def card_to_carddata(card: dict, source: str = 'local') -> CardData:
    """Convert API card dict to CardData model."""
    # Extract set info from id (e.g., "a2a-038" -> set="a2a", num="038")
    card_id = card.get('id', '')
    parts = card_id.rsplit('-', 1)
    set_id = parts[0] if parts else ''
    card_number = parts[1] if len(parts) > 1 else ''
    
    # Get Pokedex number
    pokedex = get_pokedex_number(card.get('name', ''))
    
    # Get set name from expansions
    set_name = ''
    expansions = load_expansions()
    for exp in expansions:
        if exp.get('id') == set_id:
            set_name = exp.get('name', '')
            break
    
    return CardData(
        id=card_id,
        name=card.get('name', ''),
        hp=int(card.get('health', 0)) if card.get('health') else None,
        energy_type=card.get('type', ''),
        stage='',  # Not in chase-manning data
        evolution_from='',  # Not in chase-manning data
        card_number=card_number,
        set_id=set_id,
        set_name=set_name,
        rarity=card.get('rarity', ''),
        attacks=[],  # Not in chase-manning data
        illustrator=card.get('artist', ''),
        api_source=source,
        pokedex_number=pokedex,
    )


def limitless_to_carddata(card: dict) -> CardData:
    """Convert Limitless scraped card to CardData model."""
    return CardData(
        id=card.get('id', ''),
        name=card.get('name', ''),
        hp=card.get('hp'),
        energy_type=card.get('energy_type', ''),
        stage=card.get('stage', ''),
        evolution_from=card.get('evolution_from', ''),
        card_number=card.get('card_number', ''),
        set_id=card.get('set_id', ''),
        set_name=card.get('set_name', ''),
        rarity=card.get('rarity', ''),
        attacks=card.get('attacks', []),
        weakness=card.get('weakness', ''),
        retreat=card.get('retreat', 0),
        illustrator=card.get('illustrator', ''),
        api_source='limitless',
    )


def find_limitless_card(cards: list, name: str, hp: str = None) -> list:
    """Find cards in Limitless data by name."""
    results = []
    name_lower = name.lower()
    
    for card in cards:
        card_name_lower = card.get('name', '').lower()
        
        # Exact or partial match
        if name_lower in card_name_lower or card_name_lower in name_lower:
            if hp:
                card_hp = card.get('hp')
                if card_hp and str(card_hp) != hp:
                    continue
            results.append(card)
    
    return results


def lookup_card(name: str, hp: str = None, energy: str = None,
                pokedex: str = None) -> MatchResult:
    """
    Lookup card from local database.
    
    Priority:
    1. Limitless scraped data (has full info: attacks, weakness, retreat, stage)
    2. Chase-manning JSON fallback
    
    Matching:
    - Name match = exact
    - Name + HP match = exact
    """
    # FIRST: Try Limitless scraped data (has MORE fields)
    limitless_cards = load_limitless_cards()
    
    if limitless_cards:
        results = find_limitless_card(limitless_cards, name, hp)
        
        if len(results) == 1:
            return MatchResult(
                success=True,
                card=limitless_to_carddata(results[0]),
                match_type='exact',
                confidence=1.0
            )
        
        # Try with HP filter
        if hp and len(results) > 1:
            for r in results:
                if r.get('hp') and str(r['hp']) == hp:
                    return MatchResult(
                        success=True,
                        card=limitless_to_carddata(r),
                        match_type='exact',
                        confidence=1.0
                    )
        
        # Multiple matches - return first
        if results:
            return MatchResult(
                success=True,
                card=limitless_to_carddata(results[0]),
                match_type='fuzzy',
                confidence=0.9
            )
    
    # FALLBACK: Try chase-manning JSON
    cards = load_cards()
    
    if not cards:
        return MatchResult(
            success=False,
            match_type='none',
            errors=['No card data loaded']
        )
    
    results = []
    
    # Try name + HP
    if name:
        results = find_card_by_name(cards, name, hp, energy)
        
        if len(results) == 1:
            return MatchResult(
                success=True,
                card=card_to_carddata(results[0], 'chase-manning'),
                match_type='fuzzy',
                confidence=0.7
            )
        
        # Try just HP filter
        if hp and len(results) > 1:
            for r in results:
                if str(r.get('health')) == hp:
                    return MatchResult(
                        success=True,
                        card=card_to_carddata(r, 'chase-manning'),
                        match_type='fuzzy',
                        confidence=0.6
                    )
    
    # Closest match
    if results:
        return MatchResult(
            success=True,
            card=card_to_carddata(results[0], 'chase-manning'),
            match_type='closest',
            confidence=0.4
        )
    
    # No match
    return MatchResult(
        success=False,
        match_type='none',
        errors=[f'No match found for: {name} (HP: {hp}, Energy: {energy})']
    )
    
    results = []
    
    # Try Pokedex + HP
    if pokedex:
        try:
            pokedex_num = int(pokedex)
            results = find_card_by_pokedex(cards, pokedex_num, hp)
            
            if len(results) == 1:
                return MatchResult(
                    success=True,
                    card=card_to_carddata(results[0]),
                    match_type='exact',
                    confidence=1.0
                )
            
            # Filter by HP if multiple
            if hp and len(results) > 1:
                for r in results:
                    if str(r.get('health')) == hp:
                        return MatchResult(
                            success=True,
                            card=card_to_carddata(r),
                            match_type='exact',
                            confidence=0.9
                        )
            
            # Multiple matches - try energy filter
            if energy and len(results) > 1:
                for r in results:
                    if r.get('type', '').lower() == energy.lower():
                        return MatchResult(
                            success=True,
                            card=card_to_carddata(r),
                            match_type='exact',
                            confidence=0.85
                        )
                        
        except ValueError:
            pass
    
    # Try name + HP + Energy
    if name:
        results = find_card_by_name(cards, name, hp, energy)
        
        if len(results) == 1:
            return MatchResult(
                success=True,
                card=card_to_carddata(results[0]),
                match_type='fuzzy',
                confidence=0.8
            )
        
        # Try just HP filter
        if hp and len(results) > 1:
            for r in results:
                if str(r.get('health')) == hp:
                    return MatchResult(
                        success=True,
                        card=card_to_carddata(r),
                        match_type='fuzzy',
                        confidence=0.7
                    )
    
    # Closest match
    if results:
        # Return first result with lower confidence
        return MatchResult(
            success=True,
            card=card_to_carddata(results[0]),
            match_type='closest',
            confidence=0.5
        )
    
    # No match
    return MatchResult(
        success=False,
        match_type='none',
        errors=[f'No match found for: {name} (HP: {hp}, Energy: {energy})']
    )


if __name__ == "__main__":
    # Test lookup
    print("Testing local lookup...")
    
    # Test Donphan
    result = lookup_card('Donphan', hp='120', energy='Fighting', pokedex='232')
    print(f"Donphan: {result.success}, type: {result.match_type}, conf: {result.confidence}")
    if result.card:
        print(f"  Found: {result.card.name} ({result.card.hp} HP, {result.card.energy_type})")
        print(f"  Set: {result.card.set_id}, Artist: {result.card.illustrator}")
