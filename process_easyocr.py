#!/usr/bin/env python3
import os
import csv
import glob
import requests
import re
from PIL import Image
import easyocr
from rapidfuzz import fuzz
import numpy as np

UNCAPTURED_DIR = "screenshots/impossible_to_capture"
CAPTURED_DIR = "screenshots/captured"
OUTPUT_CSV = "my_cards_full.csv"

GERMAN_TO_ENGLISH = {
    'Panekon': 'Panekon', 'Sandan': 'Sandshrew', 'Sandamer': 'Sandslash',
    'Enton': 'Psyduck', 'Entoron': 'Golduck', 'Karpador': 'Magikarp',
    'Garados': 'Gyarados', 'Flegmon': 'Slowpoke', 'Lahmus': 'Slowbro',
    'Magnetilo': 'Magnemite', 'Porenta': 'Farfetchd', 'Dodu': 'Doduo',
    'Dodri': 'Dodrio', 'Jurob': 'Seel', 'Jugong': 'Dewgong',
    'Sleima': 'Grimer', 'Sleimok': 'Muk', 'Muschas': 'Shellder',
    'Austos': 'Cloyster', 'Nebulak': 'Gastly', 'Alpollo': 'Haunter',
    'Traumato': 'Drowzee', 'Owei': 'Exeggcute', 'Kokowei': 'Exeggutor',
    'Tragosso': 'Cubone', 'Knogga': 'Marowak', 'Kicklee': 'Hitmonlee',
    'Nockchan': 'Hitmonchan', 'Schlurp': 'Lickitung', 'Smogon': 'Koffing',
    'Smogmog': 'Weezing', 'Rihorn': 'Rhyhorn', 'Rizeros': 'Rhydon',
    'Chaneira': 'Chansey', 'Kangama': 'Kangaskhan', 'Seeper': 'Horsea',
    'Seemon': 'Seadra', 'Goldini': 'Goldeen', 'Golking': 'Seaking',
    'Sterndu': 'Staryu', 'Starmie': 'Starmie', 'Pantimos': 'Mr. Mime',
    'Sichlor': 'Scyther', 'Rossana': 'Jynx', 'Elektek': 'Electabuzz',
    'Aquana': 'Vaporeon', 'Blitza': 'Jolteon', 'Flamara': 'Flareon',
    'Amonitas': 'Omanyte', 'Amoroso': 'Omastar', 'Relaxo': 'Snorlax',
    'Arktos': 'Articuno', 'Zapdos': 'Zapdos', 'Lavados': 'Moltres',
    'Dragonir': 'Dragonair', 'Dragoran': 'Dragonite', 'Mewtu': 'Mewtwo',
    'Bisasam': 'Bulbasaur', 'Bisaknosp': 'Ivysaur', 'Bisaflor': 'Venusaur',
    'Glumanda': 'Charmander', 'Glutexo': 'Charmeleon', 'Glurak': 'Charizard',
    'Schiggy': 'Squirtle', 'Schillok': 'Wartortle', 'Turtok': 'Blastoise',
    'Raupy': 'Caterpie', 'Safcon': 'Metapod', 'Smettbo': 'Butterfree',
    'Hornliu': 'Weedle', 'Kokuna': 'Kakuna', 'Bibor': 'Beedrill',
    'Taubsi': 'Pidgey', 'Tauboga': 'Pidgeotto', 'Tauboss': 'Pidgeot',
    'Rattfratz': 'Rattata', 'Rattikarl': 'Raticate', 'Habitak': 'Spearow',
    'Ibitak': 'Fearow', 'Rettan': 'Ekans', 'Arbok': 'Arbok',
    'Pikachu': 'Pikachu', 'Raichu': 'Raichu', 'Sandan': 'Sandshrew',
    'Sandamer': 'Sandslash', 'Nidoran': 'Nidoran', 'Nidorina': 'Nidorina',
    'Nidoqueen': 'Nidoqueen', 'Nidorino': 'Nidorino', 'Nidoking': 'Nidoking',
    'Piepi': 'Pichu', 'Piepi': 'Clefairy', 'Pixi': 'Clefable',
    'Vulpix': 'Vulpix', 'Vulnona': 'Ninetales', 'Pummeluff': 'Jigglypuff',
    'Knuddeluff': 'Wigglytuff', 'Zubat': 'Zubat', 'Golbat': 'Golbat',
    'Myrapla': 'Oddish', 'Duflor': 'Gloom', 'Giflor': 'Vileplume',
    'Paras': 'Paras', 'Parasek': 'Parasect', 'Bluzuk': 'Venonat',
    'Omot': 'Venomoth', 'Digda': 'Diglett', 'Digdri': 'Dugtrio',
    'Mauzi': 'Meowth', 'Snobilikat': 'Persian', 'Enton': 'Psyduck',
    'Entoron': 'Golduck', 'Menki': 'Mankey', 'Rasaff': 'Primeape',
    'Fukano': 'Growlithe', 'Arkani': 'Arcanine', 'Quapsel': 'Poliwag',
    'Quaputzi': 'Poliwhirl', 'Quappo': 'Poliwrath', 'Abra': 'Abra',
    'Kadabra': 'Kadabra', 'Simsala': 'Alakazam', 'Machollo': 'Machop',
    'Maschock': 'Machoke', 'Machomei': 'Machamp', 'Knofensa': 'Bellsprout',
    'Ultrigaria': 'Weepinbell', 'Sarzenia': 'Victreebel', 'Tentacha': 'Tentacool',
    'Tentoxa': 'Tentacruel', 'Kleinstein': 'Geodude', 'Georok': 'Graveler',
    'Geowaz': 'Golem', 'Ponita': 'Ponyta', 'Gallopa': 'Rapidash',
    'Flegmon': 'Slowpoke', 'Lahmus': 'Slowbro', 'Magnetilo': 'Magnemite',
    'Magneton': 'Magneton', 'Porenta': 'Farfetchd', 'Dodu': 'Doduo',
    'Dodri': 'Dodrio', 'Jurob': 'Seel', 'Jugong': 'Dewgong',
    'Sleima': 'Grimer', 'Sleimok': 'Muk', 'Muschas': 'Shellder',
    'Austos': 'Cloyster', 'Nebulak': 'Gastly', 'Alpollo': 'Haunter',
    'Gengar': 'Gengar', 'Onix': 'Onix', 'Traumato': 'Drowzee',
    'Hypno': 'Hypno', 'Krabby': 'Krabby', 'Kingler': 'Kingler',
    'Voltobal': 'Voltorb', 'Lektrobal': 'Electrode', 'Owei': 'Exeggcute',
    'Kokowei': 'Exeggutor', 'Tragosso': 'Cubone', 'Knogga': 'Marowak',
    'Kicklee': 'Hitmonlee', 'Nockchan': 'Hitmonchan', 'Schlurp': 'Lickitung',
    'Smogon': 'Koffing', 'Smogmog': 'Weezing', 'Rihorn': 'Rhyhorn',
    'Rizeros': 'Rhydon', 'Chaneira': 'Chansey', 'Tangela': 'Tangela',
    'Kangama': 'Kangaskhan', 'Seeper': 'Horsea', 'Seemon': 'Seadra',
    'Goldini': 'Goldeen', 'Golking': 'Seaking', 'Sterndu': 'Staryu',
    'Starmie': 'Starmie', 'Pantimos': 'Mr. Mime', 'Sichlor': 'Scyther',
    'Rossana': 'Jynx', 'Elektek': 'Electabuzz', 'Magmar': 'Magmar',
    'Pinsir': 'Pinsir', 'Tauros': 'Tauros', 'Karpador': 'Magikarp',
    'Garados': 'Gyarados', 'Lapras': 'Lapras', 'Ditto': 'Ditto',
    'Evoli': 'Eevee', 'Aquana': 'Vaporeon', 'Blitza': 'Jolteon',
    'Flamara': 'Flareon', 'Porygon': 'Porygon', 'Amonitas': 'Omanyte',
    'Amoroso': 'Omastar', 'Kabuto': 'Kabuto', 'Kabutops': 'Kabutops',
    'Aerodactyl': 'Aerodactyl', 'Relaxo': 'Snorlax', 'Arktos': 'Articuno',
    'Zapdos': 'Zapdos', 'Lavados': 'Moltres', 'Dratini': 'Dratini',
    'Dragonir': 'Dragonair', 'Dragoran': 'Dragonite', 'Mewtu': 'Mewtwo',
    'Mew': 'Mew',
    'Iglybuf': 'Igglybuff', 'Feurigel': 'Chikorita', 'Lavin': 'Bayleef',
    'Meganie': 'Meganium', 'Fennekin': 'Fennekin', 'Froferno': 'Braixen',
    'Psiana': 'Delphox', 'Nebulak': 'Gastly', 'Darkrai': 'Darkrai',
    'Shaymin': 'Shaymin', 'Arceus': 'Arceus', 'Victini': 'Victini',
    'Serperior': 'Serperior', 'Emboar': 'Emboar', 'Samurott': 'Samurott',
    'Pikachu': 'Pikachu', 'Raichu': 'Raichu', 'Machop': 'Machop',
    'Machoke': 'Machoke', 'Machamp': 'Machamp', 'Gastly': 'Gastly',
    'Haunter': 'Haunter', 'Gengar': 'Gengar', 'Onix': 'Onix',
    'Voltorb': 'Voltorb', 'Electrode': 'Electrode', 'Rattata': 'Rattata',
    'Raticate': 'Raticate', 'Spearow': 'Spearow', 'Fearow': 'Fearow',
    'Zubat': 'Zubat', 'Golbat': 'Golbat', 'Oddish': 'Oddish',
    'Gloom': 'Gloom', 'Vileplume': 'Vileplume', 'Paras': 'Paras',
    'Parasect': 'Parasect', 'Venonat': 'Venonat', 'Venomoth': 'Venomoth',
    'Psyduck': 'Psyduck', 'Golduck': 'Golduck', 'Mankey': 'Mankey',
    'Primeape': 'Primeape', 'Growlithe': 'Growlithe', 'Arcanine': 'Arcanine',
    'Poliwag': 'Poliwag', 'Poliwhirl': 'Poliwhirl', 'Poliwrath': 'Poliwrath',
    'Abra': 'Abra', 'Kadabra': 'Kadabra', 'Alakazam': 'Alakazam',
    'Bellsprout': 'Bellsprout', 'Weepinbell': 'Weepinbell', 'Victreebel': 'Victreebel',
    'Tentacool': 'Tentacool', 'Tentacruel': 'Tentacruel', 'Geodude': 'Geodude',
    'Graveler': 'Graveler', 'Golem': 'Golem', 'Ponyta': 'Ponyta',
    'Rapidash': 'Rapidash', 'Slowpoke': 'Slowpoke', 'Slowbro': 'Slowbro',
    'Magnemite': 'Magnemite', 'Magneton': 'Magneton', 'Farfetchd': 'Farfetchd',
    'Doduo': 'Doduo', 'Dodrio': 'Dodrio', 'Seel': 'Seel',
    'Dewgong': 'Dewgong', 'Grimer': 'Grimer', 'Muk': 'Muk',
    'Shellder': 'Shellder', 'Cloyster': 'Cloyster', 'Gastly': 'Gastly',
    'Haunter': 'Haunter', 'Gengar': 'Gengar', 'Onix': 'Onix',
    'Drowzee': 'Drowzee', 'Hypno': 'Hypno', 'Krabby': 'Krabby',
    'Kingler': 'Kingler', 'Voltorb': 'Voltorb', 'Electrode': 'Electrode',
    'Exeggcute': 'Exeggcute', 'Exeggutor': 'Exeggutor', 'Cubone': 'Cubone',
    'Marowak': 'Marowak', 'Hitmonlee': 'Hitmonlee', 'Hitmonchan': 'Hitmonchan',
    'Lickitung': 'Lickitung', 'Koffing': 'Koffing', 'Weezing': 'Weezing',
    'Rhyhorn': 'Rhyhorn', 'Rhydon': 'Rhydon', 'Chansey': 'Chansey',
    'Tangela': 'Tangela', 'Kangaskhan': 'Kangaskhan', 'Horsea': 'Horsea',
    'Seadra': 'Seadra', 'Goldeen': 'Goldeen', 'Seaking': 'Seaking',
    'Staryu': 'Staryu', 'Starmie': 'Starmie', 'MrMime': 'Mr. Mime',
    'Scyther': 'Scyther', 'Jynx': 'Jynx', 'Electabuzz': 'Electabuzz',
    'Magmar': 'Magmar', 'Pinsir': 'Pinsir', 'Tauros': 'Tauros',
    'Magikarp': 'Magikarp', 'Gyarados': 'Gyarados', 'Lapras': 'Lapras',
    'Ditto': 'Ditto', 'Eevee': 'Eevee', 'Vaporeon': 'Vaporeon',
    'Jolteon': 'Jolteon', 'Flareon': 'Flareon', 'Porygon': 'Porygon',
    'Omanyte': 'Omanyte', 'Omastar': 'Omastar', 'Kabuto': 'Kabuto',
    'Kabutops': 'Kabutops', 'Aerodactyl': 'Aerodactyl', 'Snorlax': 'Snorlax',
    'Articuno': 'Articuno', 'Zapdos': 'Zapdos', 'Moltres': 'Moltres',
    'Dratini': 'Dratini', 'Dragonair': 'Dragonair', 'Dragonite': 'Dragonite',
    'Mewtwo': 'Mewtwo', 'Mew': 'Mew',
    'Ledyba': 'Ledyba', 'Ledian': 'Ledian', 'Spinarak': 'Spinarak',
    'Ariados': 'Ariados', 'Crobat': 'Crobat', 'Chinchou': 'Chinchou',
    'Lanturn': 'Lanturn', 'Pichu': 'Pichu', 'Cleffa': 'Cleffa',
    'Clefairy': 'Clefairy', 'Clefable': 'Clefable', 'Igglybuff': 'Igglybuff',
    'Jigglypuff': 'Jigglypuff', 'Sunkern': 'Sunkern', 'Sunflora': 'Sunflora',
    'Yanma': 'Yanma', 'Wooper': 'Wooper', 'Quagsire': 'Quagsire',
    'Espeon': 'Espeon', 'Umbreon': 'Umbreon', 'Murkrow': 'Murkrow',
    'Slowking': 'Slowking', 'Misdreavus': 'Misdreavus', 'Unown': 'Unown',
    'Wobbuffet': 'Wobbuffet', 'Girafarig': 'Girafarig', 'Pineco': 'Pineco',
    'Forretress': 'Forretress', 'Dunsparce': 'Dunsparce', 'Gligar': 'Gligar',
    'Steelix': 'Steelix', 'Scizor': 'Scizor', 'Shuckle': 'Shuckle',
    'Heracross': 'Heracross', 'Sneasel': 'Sneasel', 'Teddiursa': 'Teddiursa',
    'Ursaring': 'Ursaring', 'Slugma': 'Slugma', 'Magcargo': 'Magcargo',
    'Swinub': 'Swinub', 'Piloswine': 'Piloswine', 'Corsola': 'Corsola',
    'Remoraid': 'Remoraid', 'Octillery': 'Octillery', 'Delibird': 'Delibird',
    'Mantine': 'Mantine', 'Skarmory': 'Skarmory', 'Houndour': 'Houndour',
    'Houndoom': 'Houndoom', 'Kingdra': 'Kingdra', 'Phanpy': 'Phanpy',
    'Donphan': 'Donphan', 'Porygon2': 'Porygon2', 'Stantler': 'Stantler',
    'Smeargle': 'Smeargle', 'Tyrogue': 'Tyrogue', 'Hitmontop': 'Hitmontop',
    'Smoochum': 'Smoochum', 'Elekid': 'Elekid', 'Magby': 'Magby',
    'Miltank': 'Miltank', 'Blissey': 'Blissey', 'Raikou': 'Raikou',
    'Entei': 'Entei', 'Suicune': 'Suicune', 'Larvitar': 'Larvitar',
    'Pupitar': 'Pupitar', 'Tyranitar': 'Tyranitar', 'Lugia': 'Lugia',
    'HoOh': 'Ho-Oh', 'Ho-Oh': 'Ho-Oh', 'Celebi': 'Celebi',
    'Treecko': 'Treecko', 'Grovyle': 'Grovyle', 'Sceptile': 'Sceptile',
    'Torchic': 'Torchic', 'Combusken': 'Combusken', 'Blaziken': 'Blaziken',
    'Mudkip': 'Mudkip', 'Marshtomp': 'Marshtomp', 'Swampert': 'Swampert',
    'Poochyena': 'Poochyena', 'Mightyena': 'Mightyena', 'Zigzagoon': 'Zigzagoon',
    'Linoone': 'Linoone', 'Wurmple': 'Wurmple', 'Silcoon': 'Silcoon',
    'Beautifly': 'Beautifly', 'Cascoon': 'Cascoon', 'Dustox': 'Dustox',
    'Lotad': 'Lotad', 'Lombre': 'Lombre', 'Ludicolo': 'Ludicolo',
    'Seedot': 'Seedot', 'Nuzleaf': 'Nuzleaf', 'Shiftry': 'Shiftry',
    'Taillow': 'Taillow', 'Swellow': 'Swellow', 'Wingull': 'Wingull',
    'Pelipper': 'Pelipper', 'Ralts': 'Ralts', 'Kirlia': 'Kirlia',
    'Gardevoir': 'Gardevoir', 'Surskit': 'Surskit', 'Masquerain': 'Masquerain',
    'Shroomish': 'Shroomish', 'Breloom': 'Breloom', 'Slakoth': 'Slakoth',
    'Vigoroth': 'Vigoroth', 'Slaking': 'Slaking', 'Nincada': 'Nincada',
    'Ninjask': 'Ninjask', 'Shedinja': 'Shedinja', 'Whismur': 'Whismur',
    'Loudred': 'Loudred', 'Exploud': 'Exploud', 'Makuhita': 'Makuhita',
    'Hariyama': 'Hariyama', 'Azurill': 'Azurill', 'Nosepass': 'Nosepass',
    'Skitty': 'Skitty', 'Delcatty': 'Delcatty', 'Sableye': 'Sableye',
    'Mawile': 'Mawile', 'Aron': 'Aron', 'Lairon': 'Lairon',
    'Aggron': 'Aggron', 'Meditite': 'Meditite', 'Medicham': 'Medicham',
    'Electrike': 'Electrike', 'Manectric': 'Manectric', 'Plusle': 'Plusle',
    'Minun': 'Minun', 'Volbeat': 'Volbeat', 'Illumise': 'Illumise',
    'Roselia': 'Roselia', 'Gulpin': 'Gulpin', 'Swalot': 'Swalot',
    'Carvanha': 'Carvanha', 'Sharpedo': 'Sharpedo', 'Wailmer': 'Wailmer',
    'Wailord': 'Wailord', 'Numel': 'Numel', 'Camerupt': 'Camerupt',
    'Torkoal': 'Torkoal', 'Spoink': 'Spoink', 'Grumpig': 'Grumpig',
    'Spinda': 'Spinda', 'Trapinch': 'Trapinch', 'Vibrava': 'Vibrava',
    'Flygon': 'Flygon', 'Cacnea': 'Cacnea', 'Cacturne': 'Cacturne',
    'Swablu': 'Swablu', 'Altaria': 'Altaria', 'Zangoose': 'Zangoose',
    'Seviper': 'Seviper', 'Lunatone': 'Lunatone', 'Solrock': 'Solrock',
    'Barboach': 'Barboach', 'Whiscash': 'Whiscash', 'Corphish': 'Corphish',
    'Crawdaunt': 'Crawdaunt', 'Baltoy': 'Baltoy', 'Claydol': 'Claydol',
    'Lileep': 'Lileep', 'Cradily': 'Cradily', 'Anorith': 'Anorith',
    'Armaldo': 'Armaldo', 'Feebas': 'Feebas', 'Milotic': 'Milotic',
    'Castform': 'Castform', 'Kecleon': 'Kecleon', 'Shuppet': 'Shuppet',
    'Banette': 'Banette', 'Duskull': 'Duskull', 'Dusclops': 'Dusclops',
    'Tropius': 'Tropius', 'Chimecho': 'Chimecho', 'Absol': 'Absol',
    'Wynaut': 'Wynaut', 'Snorunt': 'Snorunt', 'Glalie': 'Glalie',
    'Spheal': 'Spheal', 'Sealeo': 'Sealeo', 'Walrein': 'Walrein',
    'Clamperl': 'Clamperl', 'Huntail': 'Huntail', 'Gorebyss': 'Gorebyss',
    'Relicanth': 'Relicanth', 'Luvdisc': 'Luvdisc', 'Bagon': 'Bagon',
    'Shelgon': 'Shelgon', 'Salamence': 'Salamence', 'Beldum': 'Beldum',
    'Metang': 'Metang', 'Metagross': 'Metagross', 'Regirock': 'Regirock',
    'Regice': 'Regice', 'Registeel': 'Registeel', 'Latias': 'Latias',
    'Latios': 'Latios', 'Kyogre': 'Kyogre', 'Groudon': 'Groudon',
    'Rayquaza': 'Rayquaza', 'Jirachi': 'Jirachi', 'Deoxys': 'Deoxys',
    'Turtwig': 'Turtwig', 'Grotle': 'Grotle', 'Torterra': 'Torterra',
    'Chimchar': 'Chimchar', 'Monferno': 'Monferno', 'Infernape': 'Infernape',
    'Piplup': 'Piplup', 'Prinplup': 'Prinplup', 'Empoleon': 'Empoleon',
    'Starly': 'Starly', 'Staravia': 'Staravia', 'Staraptor': 'Staraptor',
    'Bidoof': 'Bidoof', 'Bibarel': 'Bibarel', 'Kricketot': 'Kricketot',
    'Kricketune': 'Kricketune', 'Shinx': 'Shinx', 'Luxio': 'Luxio',
    'Luxray': 'Luxray', 'Budew': 'Budew', 'Roserade': 'Roserade',
    'Cranidos': 'Cranidos', 'Rampardos': 'Rampardos', 'Shieldon': 'Shieldon',
    'Bastiodon': 'Bastiodon', 'Burmy': 'Burmy', 'Wormadam': 'Wormadam',
    'Mothim': 'Mothim', 'Combee': 'Combee', 'Vespiquen': 'Vespiquen',
    'Pachirisu': 'Pachirisu', 'Buizel': 'Buizel', 'Floatzel': 'Floatzel',
    'Cherubi': 'Cherubi', 'Cherrim': 'Cherrim', 'Shellos': 'Shellos',
    'Gastrodon': 'Gastrodon', 'Ambipom': 'Ambipom', 'Drifloon': 'Drifloon',
    'Drifblim': 'Drifblim', 'Buneary': 'Buneary', 'Lopunny': 'Lopunny',
    'Mismagius': 'Mismagius', 'Honchkrow': 'Honchkrow', 'Glameow': 'Glameow',
    'Purugly': 'Purugly', 'Chingling': 'Chingling', 'Stunky': 'Stunky',
    'Skuntank': 'Skuntank', 'Bronzor': 'Bronzor', 'Bronzong': 'Bronzong',
    'Bonsly': 'Bonsly', 'MimeJr': 'Mime Jr.', 'MimeJr': 'Mime Jr.',
    'Happiny': 'Happiny', 'Chatot': 'Chatot', 'Spiritomb': 'Spiritomb',
    'Gible': 'Gible', 'Gabite': 'Gabite', 'Garchomp': 'Garchomp',
    'Munchlax': 'Munchlax', 'Riolu': 'Riolu', 'Lucario': 'Lucario',
    'Hippopotas': 'Hippopotas', 'Hippowdon': 'Hippowdon', 'Skorupi': 'Skorupi',
    'Drapion': 'Drapion', 'Croagunk': 'Croagunk', 'Toxicroak': 'Toxicroak',
    'Carnivine': 'Carnivine', 'Finneon': 'Finneon', 'Lumineon': 'Lumineon',
    'Mantyke': 'Mantyke', 'Snover': 'Snover', 'Abomasnow': 'Abomasnow',
    'Weavile': 'Weavile', 'Lickilicky': 'Lickilicky', 'Rhyperior': 'Rhyperior',
    'Tangrowth': 'Tangrowth', 'Electivire': 'Electivire', 'Magmortar': 'Magmortar',
    'Togekiss': 'Togekiss', 'Yanmega': 'Yanmega', 'Leafeon': 'Leafeon',
    'Glaceon': 'Glaceon', 'Gliscor': 'Gliscor', 'Mamoswine': 'Mamoswine',
    'PorygonZ': 'Porygon-Z', 'PorygonZ': 'Porygon-Z', 'Gallade': 'Gallade',
    'Probopass': 'Probopass', 'Dusknoir': 'Dusknoir', 'Froslass': 'Froslass',
    'Rotom': 'Rotom', 'Uxie': 'Uxie', 'Mesprit': 'Mesprit',
    'Azelf': 'Azelf', 'Dialga': 'Dialga', 'Palkia': 'Palkia',
    'Heatran': 'Heatran', 'Regigigas': 'Regigigas', 'Giratina': 'Giratina',
    'Cresselia': 'Cresselia', 'Phione': 'Phione', 'Manaphy': 'Manaphy',
    'Darkrai': 'Darkrai', 'Shaymin': 'Shaymin', 'Arceus': 'Arceus',
    'Victini': 'Victini', 'Snivy': 'Snivy', 'Servine': 'Servine',
    'Serperior': 'Serperior', 'Tepig': 'Tepig', 'Pignite': 'Pignite',
    'Emboar': 'Emboar', 'Oshawott': 'Oshawott', 'Dewott': 'Dewott',
    'Samurott': 'Samurott', 'Patrat': 'Patrat', 'Watchog': 'Watchog',
    'Lillipup': 'Lillipup', 'Herdier': 'Herdier', 'Stoutland': 'Stoutland',
    'Purrloin': 'Purrloin', 'Liepard': 'Liepard', 'Pansage': 'Pansage',
    'Simisage': 'Simisage', 'Pansear': 'Pansear', 'Simisear': 'Simisear',
    'Panpour': 'Panpour', 'Simipour': 'Simipour', 'Munna': 'Munna',
    'Musharna': 'Musharna', 'Pidove': 'Pidove', 'Tranquill': 'Tranquill',
    'Unfezant': 'Unfezant', 'Blitzle': 'Blitzle', 'Zebstrika': 'Zebstrika',
    'Roggenrola': 'Roggenrola', 'Boldore': 'Boldore', 'Gigalith': 'Gigalith',
    'Woobat': 'Woobat', 'Swoobat': 'Swoobat', 'Drilbur': 'Drilbur',
    'Excadrill': 'Excadrill', 'Audino': 'Audino', 'Timburr': 'Timburr',
    'Gurdurr': 'Gurdurr', 'Conkeldurr': 'Conkeldurr', 'Tympole': 'Tympole',
    'Palpitoad': 'Palpitoad', 'Seismitoad': 'Seismitoad', 'Throh': 'Throh',
    'Sawk': 'Sawk', 'Sewaddle': 'Sewaddle', 'Swadloon': 'Swadloon',
    'Leavanny': 'Leavanny', 'Venipede': 'Venipede', 'Whirlipede': 'Whirlipede',
    'Scolipede': 'Scolipede', 'Cottonee': 'Cottonee', 'Whimsicott': 'Whimsicott',
    'Petilil': 'Petilil', 'Lilligant': 'Lilligant', 'Basculin': 'Basculin',
    'Sandile': 'Sandile', 'Krokorok': 'Krokorok', 'Krookodile': 'Krookodile',
    'Darumaka': 'Darumaka', 'Darmanitan': 'Darmanitan', 'Maractus': 'Maractus',
    'Dwebble': 'Dwebble', 'Crustle': 'Crustle', 'Scraggy': 'Scraggy',
    'Scrafty': 'Scrafty', 'Sigilyph': 'Sigilyph', 'Yamask': 'Yamask',
    'Cofagrigus': 'Cofagrigus', 'Tirtouga': 'Tirtouga', 'Carracosta': 'Carracosta',
    'Archen': 'Archen', 'Archeops': 'Archeops', 'Trubbish': 'Trubbish',
    'Garbodor': 'Garbodor', 'Zorua': 'Zorua', 'Zoroark': 'Zoroark',
    'Minccino': 'Minccino', 'Cinccino': 'Cinccino', 'Gothita': 'Gothita',
    'Gothorita': 'Gothorita', 'Gothitelle': 'Gothitelle', 'Solosis': 'Solosis',
    'Duosion': 'Duosion', 'Reuniclus': 'Reuniclus', 'Ducklett': 'Ducklett',
    'Swanna': 'Swanna', 'Vanillite': 'Vanillite', 'Vanillish': 'Vanillish',
    'Vanilluxe': 'Vanilluxe', 'Deerling': 'Deerling', 'Sawsbuck': 'Sawsbuck',
    'Emolga': 'Emolga', 'Karrablast': 'Karrablast', 'Escavalier': 'Escavalier',
    'Foongus': 'Foongus', 'Amoonguss': 'Amoonguss', 'Frillish': 'Frillish',
    'Jellicent': 'Jellicent', 'Alomomola': 'Alomomola', 'Joltik': 'Joltik',
    'Galvantula': 'Galvantula', 'Ferroseed': 'Ferroseed', 'Ferrothorn': 'Ferrothorn',
    'Klink': 'Klink', 'Klang': 'Klang', 'Klinklang': 'Klinklang',
    'Tynamo': 'Tynamo', 'Eelektrik': 'Eelektrik', 'Eelektross': 'Eelektross',
    'Elgyem': 'Elgyem', 'Beheeyem': 'Beheeyem', 'Litwick': 'Litwick',
    'Lampent': 'Lampent', 'Chandelure': 'Chandelure', 'Axew': 'Axew',
    'Fraxure': 'Fraxure', 'Haxorus': 'Haxorus', 'Cubchoo': 'Cubchoo',
    'Beartic': 'Beartic', 'Cryogonal': 'Cryogonal', 'Shelmet': 'Shelmet',
    'Accelgor': 'Accelgor', 'Stunfisk': 'Stunfisk', 'Mienfoo': 'Mienfoo',
    'Mienshao': 'Mienshao', 'Druddigon': 'Druddigon', 'Golett': 'Golett',
    'Golurk': 'Golurk', 'Pawniard': 'Pawniard', 'Bisharp': 'Bisharp',
    'Bouffalant': 'Bouffalant', 'Rufflet': 'Rufflet', 'Braviary': 'Braviary',
    'Vullaby': 'Vullaby', 'Mandibuzz': 'Mandibuzz', 'Heatmor': 'Heatmor',
    'Durant': 'Durant', 'Deino': 'Deino', 'Zweilous': 'Zweilous',
    'Hydreigon': 'Hydreigon', 'Larvesta': 'Larvesta', 'Volcarona': 'Volcarona',
    'Cobalion': 'Cobalion', 'Terrakion': 'Terrakion', 'Virizion': 'Virizion',
    'Tornadus': 'Tornadus', 'Thundurus': 'Thundurus', 'Reshiram': 'Reshiram',
    'Zekrom': 'Zekrom', 'Landorus': 'Landorus', 'Kyurem': 'Kyurem',
    'Keldeo': 'Keldeo', 'Meloetta': 'Meloetta', 'Genesect': 'Genesect',
    'Chespin': 'Chespin', 'Quilladin': 'Quilladin', 'Chesnaught': 'Chesnaught',
    'Fennekin': 'Fennekin', 'Braixen': 'Braixen', 'Delphox': 'Delphox',
    'Froakie': 'Froakie', 'Frogadier': 'Frogadier', 'Greninja': 'Greninja',
    'Bunnelby': 'Bunnelby', 'Diggersby': 'Diggersby', 'Fletchling': 'Fletchling',
    'Fletchinder': 'Fletchinder', 'Talonflame': 'Talonflame', 'Scatterbug': 'Scatterbug',
    'Spewpa': 'Spewpa', 'Vivillon': 'Vivillon', 'Litleo': 'Litleo',
    'Pyroar': 'Pyroar', 'Flabebe': 'Flabébé', 'Floette': 'Floette',
    'Florges': 'Florges', 'Skiddo': 'Skiddo', 'Gogoat': 'Gogoat',
    'Pancham': 'Pancham', 'Pangoro': 'Pangoro', 'Furfrou': 'Furfrou',
    'Espurr': 'Espurr', 'Meowstic': 'Meowstic', 'Honedge': 'Honedge',
    'Doublade': 'Doublade', 'Aegislash': 'Aegislash', 'Spritzee': 'Spritzee',
    'Aromatisse': 'Aromatisse', 'Swirlix': 'Swirlix', 'Slurpuff': 'Slurpuff',
    'Inkay': 'Inkay', 'Malamar': 'Malamar', 'Binacle': 'Binacle',
    'Barbaracle': 'Barbaracle', 'Skrelp': 'Skrelp', 'Dragalge': 'Dragalge',
    'Clauncher': 'Clauncher', 'Clawitzer': 'Clawitzer', 'Helioptile': 'Helioptile',
    'Heliolisk': 'Heliolisk', 'Tyrunt': 'Tyrunt', 'Tyrantrum': 'Tyrantrum',
    'Amaura': 'Amaura', 'Aurorus': 'Aurorus', 'Sylveon': 'Sylveon',
    'Hawlucha': 'Hawlucha', 'Dedenne': 'Dedenne', 'Carbink': 'Carbink',
    'Goomy': 'Goomy', 'Sliggoo': 'Sliggoo', 'Goodra': 'Goodra',
    'Klefki': 'Klefki', 'Phantump': 'Phantump', 'Trevenant': 'Trevenant',
    'Pumpkaboo': 'Pumpkaboo', 'Gourgeist': 'Gourgeist', 'Bergmite': 'Bergmite',
    'Avalugg': 'Avalugg', 'Noibat': 'Noibat', 'Noivern': 'Noivern',
    'Xerneas': 'Xerneas', 'Yveltal': 'Yveltal', 'Zygarde': 'Zygarde',
    'Diancie': 'Diancie', 'Hoopa': 'Hoopa', 'Volcanion': 'Volcanion',
    'Rowlet': 'Rowlet', 'Dartrix': 'Dartrix', 'Decidueye': 'Decidueye',
    'Litten': 'Litten', 'Torracat': 'Torracat', 'Incineroar': 'Incineroar',
    'Popplio': 'Popplio', 'Brionne': 'Brionne', 'Primarina': 'Primarina',
    'Pikipek': 'Pikipek', 'Yungoos': 'Yungoos', 'Gumshoos': 'Gumshoos',
    'Grubbin': 'Grubbin', 'Charjabug': 'Charjabug', 'Vikavolt': 'Vikavolt',
    'Crabrawler': 'Crabrawler', 'Crabominable': 'Crabominable', 'Oricorio': 'Oricorio',
    'Cutiefly': 'Cutiefly', 'Ribombee': 'Ribombee', 'Rockruff': 'Rockruff',
    'Lycanroc': 'Lycanroc', 'Wishiwashi': 'Wishiwashi', 'Mareanie': 'Mareanie',
    'Toxapex': 'Toxapex', 'Mudbray': 'Mudbray', 'Mudsdale': 'Mudsdale',
    'Dewpider': 'Dewpider', 'Araquanid': 'Araquanid', 'Fomantis': 'Fomantis',
    'Lurantis': 'Lurantis', 'Morelull': 'Morelull', 'Shiinotic': 'Shiinotic',
    'Salandit': 'Salandit', 'Salazzle': 'Salazzle', 'Stufful': 'Stufful',
    'Bewear': 'Bewear', 'Bounsweet': 'Bounsweet', 'Steenee': 'Steenee',
    'Tsareena': 'Tsareena', 'Comfey': 'Comfey', 'Oranguru': 'Oranguru',
    'Passimian': 'Passimian', 'Wimpod': 'Wimpod', 'Golisopod': 'Golisopod',
    'Sandygast': 'Sandygast', 'Palossand': 'Palossand', 'Pyukumuku': 'Pyukumuku',
    'TypeNull': 'Type: Null', 'TypeNull': 'Type: Null', 'Silvally': 'Silvally',
    'Minior': 'Minior', 'Komala': 'Komala', 'Turtonator': 'Turtonator',
    'Togedemaru': 'Togedemaru', 'Mimikyu': 'Mimikyu', 'Bruxish': 'Bruxish',
    'Drampa': 'Drampa', 'Dhelmise': 'Dhelmise', 'JangmoO': 'Jangmo-o',
    'JangmoO': 'Jangmo-o', 'TapuKoko': 'Tapu Koko', 'TapuLele': 'Tapu Lele',
    'TapuBulu': 'Tapu Bulu', 'TapuFini': 'Tapu Fini', 'Cosmog': 'Cosmog',
    'Nebby': 'Nebby', 'Nihilego': 'Nihilego', 'Buzzwole': 'Buzzwole',
    'Pheromosa': 'Pheromosa', 'Xurkitree': 'Xurkitree', 'Celesteela': 'Celesteela',
    'Kartana': 'Kartana', 'Guzzlord': 'Guzzlord', 'Necrozma': 'Necrozma',
    'Magearna': 'Magearna', 'Marshadow': 'Marshadow', 'Poipole': 'Poipole',
    'Stakataka': 'Stakataka', 'Blacephalon': 'Blacephalon', 'Zeraora': 'Zeraora',
    'Meltan': 'Meltan', 'Melmetal': 'Melmetal', 'Grookey': 'Grookey',
    'Thwackey': 'Thwackey', 'Rillaboom': 'Rillaboom', 'Scorbunny': 'Scorbunny',
    'Raboot': 'Raboot', 'Cinderace': 'Cinderace', 'Sobble': 'Sobble',
    'Drizzile': 'Drizzile', 'Inteleon': 'Inteleon', 'Skwovet': 'Skwovet',
    'Greedent': 'Greedent', 'Rookidee': 'Rookidee', 'Corvisquire': 'Corvisquire',
    'Corviknight': 'Corviknight', 'Blipbug': 'Blipbug', 'Dottler': 'Dottler',
    'Orbeetle': 'Orbeetle', 'Nickit': 'Nickit', 'Thievul': 'Thievul',
    'Gossifleur': 'Gossifleur', 'Eldegoss': 'Eldegoss', 'Wooloo': 'Wooloo',
    'Dubwool': 'Dubwool', 'Chewtle': 'Chewtle', 'Drednaw': 'Drednaw',
    'Yamper': 'Yamper', 'Boltund': 'Boltund', 'Rolycoly': 'Rolycoly',
    'Carkol': 'Carkol', 'Coalossal': 'Coalossal', 'Appletun': 'Appletun',
    'Silicobra': 'Silicobra', 'Sandaconda': 'Sandaconda', 'Cramorant': 'Cramorant',
    'Toxel': 'Toxel', 'Toxtricity': 'Toxtricity', 'Sizzlipede': 'Sizzlipede',
    'Centiskorch': 'Centiskorch', 'Clobbopus': 'Clobbopus', 'Grapploct': 'Grapploct',
    'Sinistea': 'Sinistea', 'Polteageist': 'Polteageist', 'Hatenna': 'Hatenna',
    'Hattrem': 'Hattrem', 'Hatterene': 'Hatterene', 'Impidimp': 'Impidimp',
    'Morgrem': 'Morgrem', 'Grimmsnarl': 'Grimmsnarl', 'Obstagoon': 'Obstagoon',
    'Perrserker': 'Perrserker', 'Cursola': 'Cursola', 'Sirfetchd': 'Sirfetchd',
    'MrRime': 'Mr. Rime', 'Runerigus': 'Runerigus', 'Milcery': 'Milcery',
    'Alcremie': 'Alcremie', 'Falinks': 'Falinks', 'Pincurchin': 'Pincurchin',
    'Snom': 'Snom', 'Frosmoth': 'Frosmoth', 'Stonjourner': 'Stonjourner',
    'Eiscue': 'Eiscue', 'Indeedee': 'Indeedee', 'Morpeko': 'Morpeko',
    'Cufant': 'Cufant', 'Copperajah': 'Copperajah', 'Dracozolt': 'Dracozolt',
    'Arctovish': 'Arctovish', 'Duraludon': 'Duraludon', 'Dreepy': 'Dreepy',
    'Drakloak': 'Drakloak', 'Dragapult': 'Dragapult', 'Zacian': 'Zacian',
    'Zamazenta': 'Zamazenta', 'Eternatus': 'Eternatus', 'Calyrex': 'Calyrex',
}

print("Loading EasyOCR...")
reader = easyocr.Reader(['en', 'de'], gpu=False)
print("EasyOCR loaded!")

def load_db():
    resp = requests.get('https://raw.githubusercontent.com/flibustier/pokemon-tcg-pocket-database/main/dist/cards.no-image.min.json', timeout=60)
    cards = resp.json()
    for card in cards:
        card['search_names'] = [card['name'].lower()]
    return cards

def extract_features(path):
    try:
        img = Image.open(path)
        img_array = np.array(img)
        
        results = reader.readtext(img_array)
        
        all_text = ' '.join([text for _, text, _ in results])
        
        features = {
            'hp': None, 'name': None, 'is_trainer': False,
            'attacks': [], 'retreat': None, 'weakness': None,
            'energy_type': None
        }
        
        is_trainer = 'Trainer' in all_text or 'Karte' in all_text
        features['is_trainer'] = is_trainer
        
        if not is_trainer:
            hp_match = re.search(r'(?:KP|HP|@)\s*(\d{2,3})|(\d{2,3})\s*(?:KP|HP)', all_text, re.IGNORECASE)
            if not hp_match:
                all_nums = re.findall(r'\b(\d{2,3})\b', all_text)
                for n in all_nums:
                    if 30 <= int(n) <= 350:
                        hp = int(n)
                        features['hp'] = hp
                        break
            
            retreat_match = re.search(r'(?:Rückzug|Retreat)\s*(\d)', all_text, re.IGNORECASE)
            if retreat_match:
                features['retreat'] = int(retreat_match.group(1))
        
        name_candidates = []
        for bbox, text, conf in results:
            text_clean = text.strip()
            if conf < 0.3:
                continue
            words = re.findall(r'([A-Z][a-züäöß]{2,})', text_clean)
            for w in words:
                if len(w) >= 3 and w not in ['Pokemon', 'Items', 'Will', 'Nicht', 'Dieses', 'Wenn', 'Basis', 'Attack', 'Gewicht', 'Schaden', 'Gegner', 'Energy', 'Retreat', 'Weakness', 'Resistance', 'Karte', 'Karten', 'Illustr', 'Erhalten', 'Fünf', 'Punkt', 'Größe', 'Schwäche', 'Rückzug', 'Boxhieb', 'Nest', 'Gemeinsam', 'Reflektor', 'Nr', 'Verprügler', 'Verwirrend', 'Holzgeweih', 'Jungglut', 'Mega', 'Zungenpeitsche', 'Feuersturm', 'Schadenspunkte', 'Letzte', 'Kosturso', 'Colossand', 'Klonkett', 'Pam', 'Nagen', 'Feenbrise', 'Parfinesse', 'Härtner', 'Pikser', 'Krabbox']:
                    if conf > 0.5:
                        name_candidates.append((w, conf))
        
        if name_candidates:
            name_candidates.sort(key=lambda x: -x[1])
            features['name'] = name_candidates[0][0]
        
        return features
    except Exception as e:
        print(f"Error: {e}")
        return None

def find_card(features, cards):
    if not features:
        return None, 0
    
    best, best_score = None, 0
    
    ocr_name = features.get('name', '')
    
    for card in cards:
        score = 0
        card_name = card.get('name', '')
        
        if ocr_name and card_name:
            name_score = fuzz.ratio(ocr_name.lower(), card_name.lower())
            
            if ocr_name in GERMAN_TO_ENGLISH:
                english_name = GERMAN_TO_ENGLISH[ocr_name]
                german_score = fuzz.ratio(ocr_name.lower(), english_name.lower())
                name_score = max(name_score, german_score)
            
            if name_score >= 40:
                score += name_score
        
        if score > best_score and score >= 35:
            best_score = score
            best = card
    
    return best, best_score

def process_one(path, cards_db, existing):
    features = extract_features(path)
    if not features:
        return None
    
    print(f"  OCR: name={features.get('name')}, hp={features.get('hp')}")
    
    card, score = find_card(features, cards_db)
    
    if card and card['name'] not in existing:
        print(f"  MATCH: {card['name']} (score: {score})")
        
        card_set = card["set"]
        card_num = card["number"]
        url = f"https://api.tcgdex.net/v2/en/cards/{card_set}-{card_num:03d}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                details = resp.json()
                atks = details.get('attacks', [])
                a1 = atks[0] if len(atks) > 0 else {}
                a2 = atks[1] if len(atks) > 1 else {}
                w = details.get('weaknesses', [])
                
                card_data = {
                    'Card Name': details.get('name', card['name']),
                    'HP': str(details.get('hp', card.get('health', ''))),
                    'Energy Type': details.get('types', [''])[0] if details.get('types') else card.get('element', '').capitalize(),
                    'Weakness': f"{w[0].get('type', '')} {w[0].get('value', '')}" if w else '',
                    'Resistance': '',
                    'Retreat Cost': str(details.get('retreat', card.get('retreatCost', ''))),
                    'Ability Name': '',
                    'Ability Description': details.get('description', '')[:200],
                    'Attack 1 Name': a1.get('name', ''),
                    'Attack 1 Cost': ','.join(a1.get('cost', [])) if a1.get('cost') else '',
                    'Attack 1 Damage': str(a1.get('damage', '')),
                    'Attack 1 Description': a1.get('effect', '')[:100] if a1.get('effect') else '',
                    'Attack 2 Name': a2.get('name', ''),
                    'Attack 2 Cost': ','.join(a2.get('cost', [])) if a2.get('cost') else '',
                    'Attack 2 Damage': str(a2.get('damage', '')),
                    'Attack 2 Description': a2.get('effect', '')[:100] if a2.get('effect') else '',
                    'Rarity': details.get('rarity', card.get('rarity', '')),
                    'Pack': card.get('packs', [''])[0] if card.get('packs') else ''
                }
                
                safe_name = re.sub(r'[^\w\-]', '_', card['name'])
                new_name = f"{safe_name}_{card['set']}_{card['number']:03d}.png"
                os.rename(path, os.path.join(CAPTURED_DIR, new_name))
                
                return card_data
        except Exception as e:
            print(f"  Error fetching details: {e}")
    
    return None

def main():
    cards_db = load_db()
    print(f"Loaded {len(cards_db)} cards from DB")
    
    existing = set()
    existing_data = []
    with open(OUTPUT_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.add(row['Card Name'].strip())
            existing_data.append(row)
    print(f'Existing: {len(existing)} cards')
    
    screenshots = sorted(glob.glob(f'{UNCAPTURED_DIR}/*.png'))
    print(f'Processing {len(screenshots)} screenshots...')
    
    new_cards = []
    matched = 0
    
    for i, s in enumerate(screenshots):
        if i % 20 == 0:
            print(f'\n--- {i}/{len(screenshots)} - Found: {matched} ---')
        
        result = process_one(s, cards_db, existing)
        
        if result:
            existing.add(result['Card Name'])
            new_cards.append(result)
            matched += 1
    
    print(f'\n=== Found {len(new_cards)} new cards ===')
    
    all_cards = existing_data + new_cards
    
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_cards[0].keys())
        writer.writeheader()
        writer.writerows(all_cards)
    
    print(f'✅ Total: {len(all_cards)} unique cards')

if __name__ == "__main__":
    main()
