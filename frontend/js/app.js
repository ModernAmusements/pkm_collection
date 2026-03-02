// State
let allCards = [];
let cardImages = [];
let collection = { version: '1.0', lastUpdated: '', cards: [] };
let currentView = 'all';
let currentFilters = { search: '', set: '', energy: '', type: '', stage: '', rarity: '' };

// DOM Elements
const cardGrid = document.getElementById('cardGrid');
const statsBar = document.getElementById('statsBar');
const searchInput = document.getElementById('searchInput');
const themeToggle = document.getElementById('themeToggle');
const modal = document.getElementById('cardModal');
const exportBtn = document.getElementById('exportBtn');
const importBtn = document.getElementById('importBtn');
const importFile = document.getElementById('importFile');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    initFilters();
    renderCards();
    updateStats();
    initEventListeners();
});

// Load Data
async function loadData() {
    try {
        // Load cards
        const cardsResponse = await fetch('data/cards.json');
        allCards = await cardsResponse.json();
        
        // Try to load images if available
        try {
            const imagesResponse = await fetch('data/images.json');
            cardImages = await imagesResponse.json();
        } catch (e) {
            console.log('No images.json found, using URL generation');
            cardImages = [];
        }
        
        // Load collection from localStorage
        const saved = localStorage.getItem('pokemonCollection');
        if (saved) {
            collection = JSON.parse(saved);
        }
        
        console.log(`Loaded ${allCards.length} cards`);
    } catch (error) {
        console.error('Error loading data:', error);
        cardGrid.innerHTML = `<div class="empty-state"><h3>Fehler beim Laden der Daten</h3><p>Bitte überprüfen Sie die Konsole</p></div>`;
    }
}

// Initialize Filters
function initFilters() {
    const sets = [...new Set(allCards.map(c => c.set_id))].sort();
    const energies = [...new Set(allCards.map(c => c.energy_type).filter(Boolean))].sort();
    const types = [...new Set(allCards.map(c => c.card_type).filter(Boolean))].sort();
    const stages = [...new Set(allCards.map(c => c.stage).filter(Boolean))].sort();
    const rarities = [...new Set(allCards.map(c => c.rarity).filter(Boolean))].sort();
    
    populateSelect('filterSet', sets);
    populateSelect('filterEnergy', energies);
    populateSelect('filterType', types);
    populateSelect('filterStage', stages);
    populateSelect('filterRarity', rarities);
}

function populateSelect(id, options) {
    const select = document.getElementById(id);
    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });
}

// Get Image URL
function getCardImageUrl(card) {
    // Try to find in cardImages array first
    if (cardImages.length > 0) {
        const match = cardImages.find(img => 
            img.german_name === card.german_name && 
            img.set_id === card.set_id &&
            img.card_number === card.card_number
        );
        if (match && match.image_url) {
            return match.image_url;
        }
        
        // Fallback: match by name + set_id only (for Trainer cards)
        const fallback = cardImages.find(img => 
            img.german_name === card.german_name && 
            img.set_id === card.set_id
        );
        if (fallback && fallback.image_url) {
            return fallback.image_url;
        }
    }
    
    // Generate URL from the data we have
    // Format: https://www.pokewiki.de/images/X/X/CardName_(SetName_SetNum).png
    const setNameClean = card.set_name ? card.set_name.replace(/ /g, '_') : card.set_id;
    const cardNum = card.card_number || '001';
    const setNum = card.set_id;
    
    return `https://www.pokewiki.de/images/${setNameClean.substring(0,1).toUpperCase()}/${encodeURIComponent(card.german_name)}_(${setNameClean}_${cardNum}).png`;
}

// Render Cards
function renderCards() {
    let cards = currentView === 'collection' ? getOwnedCards() : allCards;
    
    // Apply filters
    cards = filterCards(cards);
    
    if (cards.length === 0) {
        const message = currentView === 'collection' 
            ? 'Keine Karten in Ihrer Sammlung'
            : 'Keine Karten gefunden';
        const hint = currentView === 'collection'
            ? 'Fügen Sie Karten aus "Alle Karten" hinzu'
            : 'Versuchen Sie andere Filter';
            
        cardGrid.innerHTML = `
            <div class="empty-state">
                <h3>${message}</h3>
                <p>${hint}</p>
            </div>
        `;
        return;
    }
    
    cardGrid.innerHTML = cards.map(card => {
        const owned = getOwnedQuantity(card);
        const imageUrl = getCardImageUrl(card);
        
        return `
            <div class="card" data-card='${JSON.stringify(card).replace(/'/g, "&#39;").replace(/"/g, '&quot;')}'>
                ${owned > 0 ? `<span class="card-owned">${owned}</span>` : ''}
                <img class="card-image" src="${imageUrl}" alt="${card.german_name}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 133%22><rect fill=%22%23eee%22 width=%22100%22 height=%22133%22/><text x=%2250%22 y=%2260%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2210%22>Kein Bild</text></svg>'">
                <div class="card-name">${card.german_name}</div>
                <div class="card-info">
                    <span class="card-hp">${card.hp ? card.hp + ' KP' : '-'}</span>
                    <span class="card-set">${card.set_id} #${card.card_number || '?'}</span>
                </div>
                ${currentView === 'all' ? `
                    <button class="card-add" data-name="${card.german_name}" data-set="${card.set_id}" data-num="${card.card_number || ''}">+</button>
                ` : ''}
            </div>
        `;
    }).join('');
    
    // Add click handlers
    document.querySelectorAll('.card').forEach(cardEl => {
        cardEl.addEventListener('click', (e) => {
            if (e.target.classList.contains('card-add')) {
                e.stopPropagation();
                addToCollection(e.target.dataset);
            } else {
                const cardData = JSON.parse(cardEl.dataset.card.replace(/&#39;/g, "'").replace(/&quot;/g, '"'));
                openModal(cardData);
            }
        });
    });
}

// Filter Cards
function filterCards(cards) {
    return cards.filter(card => {
        const search = currentFilters.search.toLowerCase();
        if (search && !card.german_name.toLowerCase().includes(search)) return false;
        if (currentFilters.set && card.set_id !== currentFilters.set) return false;
        if (currentFilters.energy && card.energy_type !== currentFilters.energy) return false;
        if (currentFilters.type && card.card_type !== currentFilters.type) return false;
        if (currentFilters.stage && card.stage !== currentFilters.stage) return false;
        if (currentFilters.rarity && card.rarity !== currentFilters.rarity) return false;
        return true;
    });
}

// Collection Functions
function getOwnedCards() {
    return allCards.filter(card => {
        return collection.cards.some(c => 
            c.german_name === card.german_name && 
            c.set_id === card.set_id &&
            c.card_number === card.card_number
        );
    });
}

function getOwnedQuantity(card) {
    const owned = collection.cards.find(c => 
        c.german_name === card.german_name && 
        c.set_id === card.set_id &&
        c.card_number === card.card_number
    );
    return owned ? owned.quantity : 0;
}

function addToCollection(cardData) {
    const { name, set, num } = cardData;
    const cardNumber = num || '';
    
    const existing = collection.cards.find(c => 
        c.german_name === name && 
        c.set_id === set &&
        c.card_number === cardNumber
    );
    
    if (existing) {
        existing.quantity++;
    } else {
        collection.cards.push({
            german_name: name,
            set_id: set,
            card_number: cardNumber,
            quantity: 1,
            addedAt: new Date().toISOString()
        });
    }
    
    collection.lastUpdated = new Date().toISOString();
    localStorage.setItem('pokemonCollection', JSON.stringify(collection));
    renderCards();
    updateStats();
}

// Update Stats
function updateStats() {
    const totalOwned = collection.cards.reduce((sum, c) => sum + c.quantity, 0);
    const uniqueOwned = collection.cards.length;
    const totalAvailable = allCards.length;
    const percentage = ((uniqueOwned / totalAvailable) * 100).toFixed(2);
    
    // By set
    const bySet = {};
    collection.cards.forEach(c => {
        bySet[c.set_id] = (bySet[c.set_id] || 0) + c.quantity;
    });
    
    const setStats = Object.entries(bySet)
        .map(([set, count]) => `${set}: ${count}`)
        .join(' | ');
    
    statsBar.innerHTML = `
        <span>📊 ${uniqueOwned} / ${totalAvailable} Karten (${percentage}%)</span>
        <span>📦 Gesamte Exemplare: ${totalOwned}</span>
        ${setStats ? `<span>${setStats}</span>` : ''}
    `;
}

// Modal Functions
function openModal(card) {
    document.getElementById('modalImage').src = getCardImageUrl(card);
    document.getElementById('modalImage').onerror = function() {
        this.src = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 133%22><rect fill=%22%23eee%22 width=%22100%22 height=%22133%22/><text x=%2250%22 y=%2260%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2210%22>Kein Bild</text></svg>';
    };
    
    document.getElementById('modalName').textContent = card.german_name;
    document.getElementById('modalHp').textContent = card.hp ? card.hp + ' KP' : '';
    document.getElementById('modalSet').textContent = `${card.set_name} (${card.set_id} #${card.card_number || '?'})`;
    document.getElementById('modalStage').textContent = card.stage || '';
    
    const evolutionEl = document.getElementById('modalEvolution');
    if (card.evolution_from) {
        evolutionEl.textContent = `Entwickelt sich aus: ${card.evolution_from}`;
        evolutionEl.style.display = 'inline';
    } else {
        evolutionEl.style.display = 'none';
    }
    
    // Energy type
    const energyEl = document.getElementById('modalEnergy');
    energyEl.textContent = card.energy_type || '';
    energyEl.title = card.energy_type || '';
    energyEl.className = `type-badge energy-${(card.energy_type || '').toLowerCase()}`;
    
    // Ability
    const abilitySection = document.getElementById('modalAbilitySection');
    if (card.ability) {
        abilitySection.style.display = 'block';
        document.getElementById('modalAbility').textContent = card.ability;
        document.getElementById('modalAbilityEffect').textContent = card.ability_effect || '';
    } else {
        abilitySection.style.display = 'none';
    }
    
    // Attacks
    const attacksSection = document.getElementById('modalAttacksSection');
    const attacksContainer = document.getElementById('modalAttacks');
    if (card.attacks && card.attacks.length > 0) {
        attacksSection.style.display = 'block';
        attacksContainer.innerHTML = card.attacks.map(attack => `
            <div class="attack-item">
                <div class="attack-name">${attack.name}</div>
                <div class="attack-cost">
                    ${(attack.cost || []).map(c => `<span class="type-badge energy-${c.toLowerCase()}" title="${c}">${c}</span>`).join('')}
                </div>
                <div class="attack-damage">${attack.damage || '-'}</div>
                ${attack.effect ? `<div class="attack-effect">${attack.effect}</div>` : ''}
            </div>
        `).join('');
    } else {
        attacksSection.style.display = 'none';
    }
    
    // Weakness - convert "Fire+20" to energy icon
    const weaknessEl = document.getElementById('modalWeakness');
    if (card.weakness && card.weakness !== '-') {
        const weaknessMatch = card.weakness.match(/^(\w+)\+(\d+)$/);
        if (weaknessMatch) {
            const energyType = weaknessMatch[1];
            weaknessEl.innerHTML = `<span class="type-badge energy-${energyType.toLowerCase()}" title="${energyType}"></span> +${weaknessMatch[2]}`;
        } else {
            weaknessEl.textContent = card.weakness;
        }
    } else {
        weaknessEl.textContent = '-';
    }
    
    // Retreat - convert number to energy icons (Colorless)
    const retreatEl = document.getElementById('modalRetreat');
    const retreatNum = parseInt(card.retreat) || 0;
    if (retreatNum > 0) {
        retreatEl.innerHTML = Array(retreatNum).fill('<span class="type-badge energy-colorless" title="Colorless"></span>').join('');
    } else {
        retreatEl.textContent = '0';
    }
    
    document.getElementById('modalResistance').textContent = card.resistance || '-';
    
    // Meta info
    const rarityEl = document.getElementById('modalRarity');
    if (card.rarity) {
        rarityEl.textContent = `Seltenheit: ${card.rarity}`;
        rarityEl.style.display = 'inline';
    } else {
        rarityEl.style.display = 'none';
    }
    
    const illustratorEl = document.getElementById('modalIllustrator');
    if (card.illustrator) {
        illustratorEl.textContent = `Illustrator: ${card.illustrator}`;
        illustratorEl.style.display = 'inline';
    } else {
        illustratorEl.style.display = 'none';
    }
    
    const pokedexEl = document.getElementById('modalPokedex');
    if (card.pokedex_number) {
        pokedexEl.textContent = `#${card.pokedex_number}`;
        pokedexEl.style.display = 'inline';
    } else {
        pokedexEl.style.display = 'none';
    }
    
    const regulationEl = document.getElementById('modalRegulation');
    if (card.regulation_mark) {
        regulationEl.textContent = `Regulation: ${card.regulation_mark}`;
        regulationEl.style.display = 'inline';
    }
    
    modal.classList.add('open');
}

// Event Listeners
function initEventListeners() {
    // Theme toggle
    themeToggle.addEventListener('click', () => {
        const themes = ['light', 'dim', 'dark'];
        const current = document.body.getAttribute('data-theme');
        const next = themes[(themes.indexOf(current) + 1) % themes.length];
        document.body.setAttribute('data-theme', next);
        
        const icons = { light: '🌙', dim: '🌆', dark: '☀️' };
        themeToggle.querySelector('.theme-icon').textContent = icons[next];
    });
    
    // Tab navigation
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            
            // Clear filters when switching views
            resetFilters();
            
            renderCards();
            updateStats();
        });
    });
    
    // Search
    searchInput.addEventListener('input', (e) => {
        currentFilters.search = e.target.value;
        renderCards();
    });
    
    // Filters
    const filterIds = ['filterSet', 'filterEnergy', 'filterType', 'filterStage', 'filterRarity'];
    filterIds.forEach(id => {
        document.getElementById(id).addEventListener('change', (e) => {
            const keyMap = {
                'filterSet': 'set',
                'filterEnergy': 'energy',
                'filterType': 'type',
                'filterStage': 'stage',
                'filterRarity': 'rarity'
            };
            currentFilters[keyMap[id]] = e.target.value;
            renderCards();
        });
    });
    
    // Modal close
    modal.querySelector('.modal-close').addEventListener('click', () => {
        modal.classList.remove('open');
    });
    modal.querySelector('.modal-overlay').addEventListener('click', () => {
        modal.classList.remove('open');
    });
    
    // Close on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('open')) {
            modal.classList.remove('open');
        }
    });
    
    // Export
    exportBtn.addEventListener('click', () => {
        const blob = new Blob([JSON.stringify(collection, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'collection.json';
        a.click();
        URL.revokeObjectURL(url);
    });
    
    // Import
    importBtn.addEventListener('click', () => importFile.click());
    importFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                try {
                    const imported = JSON.parse(event.target.result);
                    if (imported.cards && Array.isArray(imported.cards)) {
                        collection = imported;
                        localStorage.setItem('pokemonCollection', JSON.stringify(collection));
                        renderCards();
                        updateStats();
                        alert('Sammlung erfolgreich importiert!');
                    } else {
                        alert('Ungültiges Format');
                    }
                } catch (err) {
                    alert('Fehler beim Importieren: ' + err.message);
                }
            };
            reader.readAsText(file);
        }
        // Reset input
        importFile.value = '';
    });
}

function resetFilters() {
    currentFilters = { search: '', set: '', energy: '', type: '', stage: '', rarity: '' };
    searchInput.value = '';
    ['filterSet', 'filterEnergy', 'filterType', 'filterStage', 'filterRarity'].forEach(id => {
        document.getElementById(id).value = '';
    });
}
