// Simple test function
async function loadOverview() {
    try {
        const statsGrid = document.getElementById('statsGrid');
        
        if (!statsGrid) {
            console.error('statsGrid element not found!');
            return;
        }
        
        const response = await fetch('/api/admin/stats');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const stats = await response.json();
        
        // Ensure all values are numbers, default to 0 if undefined
        const citiesCount = stats.cities !== undefined ? stats.cities : 0;
        const venuesCount = stats.venues !== undefined ? stats.venues : 0;
        const sourcesCount = stats.sources !== undefined ? stats.sources : 0;
        const eventsCount = stats.events !== undefined ? stats.events : 0;
        
        statsGrid.innerHTML = 
            '<div class="stat-card" onclick="showSection(\'cities\')" style="cursor: pointer;">' +
                '<h3>' + citiesCount + '</h3>' +
                '<p>Cities</p>' +
            '</div>' +
            '<div class="stat-card" onclick="showSection(\'venues\')" style="cursor: pointer;">' +
                '<h3>' + venuesCount + '</h3>' +
                '<p>Venues</p>' +
            '</div>' +
            '<div class="stat-card" onclick="showSection(\'sources\')" style="cursor: pointer;">' +
                '<h3>' + sourcesCount + '</h3>' +
                '<p>Sources</p>' +
            '</div>' +
            '<div class="stat-card" onclick="showSection(\'events\')" style="cursor: pointer;">' +
                '<h3>' + eventsCount + '</h3>' +
                '<p>Events</p>' +
            '</div>';
        
    } catch (error) {
        console.error('Error loading statistics:', error);
        if (statsGrid) {
            statsGrid.innerHTML = 
                '<div class="stat-card">' +
                    '<h3>Error</h3>' +
                    '<p>Failed to load statistics: ' + (error.message || 'Unknown error') + '</p>' +
                '</div>';
        }
    }
}

// Add timeout to prevent infinite loading
function loadOverviewWithTimeout() {
    const statsGrid = document.getElementById('statsGrid');
    if (statsGrid) {
        // Set a timeout to show error if loading takes too long
        const timeout = setTimeout(() => {
            if (statsGrid.innerHTML.includes('Loading statistics')) {
                statsGrid.innerHTML = 
                    '<div class="stat-card">' +
                        '<h3>Timeout</h3>' +
                        '<p>Statistics are taking too long to load. Please check the server.</p>' +
                    '</div>';
            }
        }, 10000); // 10 second timeout
        
        loadOverview().finally(() => {
            clearTimeout(timeout);
        });
    }
}

// Navigation functions
function showSection(sectionId) {
    // Show section immediately (synchronous) for instant UI feedback
    const sections = document.querySelectorAll('.data-section');
    sections.forEach(section => {
        section.classList.remove('active');
        section.style.display = 'none';
        section.style.visibility = 'hidden';
    });
    
    // Show selected section immediately
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
        targetSection.style.display = 'block';
        targetSection.style.visibility = 'visible';
        targetSection.style.opacity = '1';
        targetSection.style.position = 'relative';
        targetSection.style.zIndex = '1';
        targetSection.style.minHeight = '500px';
        
    } else {
        console.error('Section not found:', sectionId);
        return;
    }
    
    // Update navigation buttons
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Set active on the clicked button
    const activeButton = document.getElementById(`nav-${sectionId}`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Fallback: find by onclick attribute
    const activeTab = document.querySelector(`[onclick="showSection('${sectionId}')"]`);
    if (activeTab) {
        activeTab.classList.add('active');
    }
    
    // Load data asynchronously without blocking UI - use setTimeout to ensure UI updates first
    setTimeout(() => {
        loadSectionData(sectionId);
        // Re-render table if data is already loaded (for sources, cities, venues, events)
        // Use a small delay to ensure section is fully visible
        setTimeout(() => {
            if (sectionId === 'sources' && window.allSources) {
                renderSourcesTable();
            } else if (sectionId === 'cities' && window.allCities) {
                renderCitiesTable();
            } else if (sectionId === 'venues' && window.allVenues) {
                renderVenuesTable();
            } else if (sectionId === 'events' && window.allEvents) {
                renderEventsTable();
            }
        }, 50);
    }, 0);
}

// Smart matching function for dropdown options
function findBestMatch(extractedValue, dropdownElement, fieldType) {
    if (!extractedValue || !dropdownElement) return -1;
    
    const options = dropdownElement.options;
    const searchTerm = extractedValue.toLowerCase().trim();
    
    
    // Define semantic mappings for common variations
    const semanticMappings = {
        'event type': {
            'meetup': ['photowalk', 'tour', 'workshop'],
            'gathering': ['meetup', 'party', 'reception'],
            'talk': ['talk', 'lecture', 'presentation', 'seminar'],
            'talks': ['talk', 'lecture', 'presentation', 'seminar'],
            'show': ['performance', 'concert', 'exhibition'],
            'class': ['workshop', 'seminar', 'lecture'],
            'demo': ['presentation', 'workshop', 'lecture'],
            'social': ['party', 'reception', 'meetup'],
            'networking': ['meeting', 'reception', 'party']
        },
        'city': {
            'washington': ['washington, district of columbia', 'washington dc', 'washington, dc', 'dc'],
            'washington dc': ['washington, district of columbia', 'washington, dc', 'dc'],
            'dc': ['washington, district of columbia', 'washington, dc', 'washington dc'],
            'new york': ['new york, new york', 'nyc', 'new york city'],
            'nyc': ['new york, new york', 'new york city', 'new york'],
            'los angeles': ['los angeles, california', 'la'],
            'la': ['los angeles, california', 'los angeles'],
            'san francisco': ['san francisco, california', 'sf'],
            'sf': ['san francisco, california', 'san francisco']
        }
    };
    
    // 1. Exact match (compare against option text, not value)
    for (let i = 0; i < options.length; i++) {
        if (options[i].text.toLowerCase() === searchTerm) {
            return i;
        }
    }
    
    // 2. Semantic mapping match
    if (semanticMappings[fieldType] && semanticMappings[fieldType][searchTerm]) {
        const candidates = semanticMappings[fieldType][searchTerm];
        for (const candidate of candidates) {
            for (let i = 0; i < options.length; i++) {
                if (options[i].text.toLowerCase() === candidate) {
                    return i;
                }
            }
        }
    }
    
    // 3. Partial match (contains) - compare against option text
    for (let i = 0; i < options.length; i++) {
        if (options[i].text.toLowerCase().includes(searchTerm) || 
            searchTerm.includes(options[i].text.toLowerCase())) {
            return i;
        }
    }
    
    // 4. Fuzzy match (similar words) - compare against option text
    for (let i = 0; i < options.length; i++) {
        if (calculateSimilarity(searchTerm, options[i].text.toLowerCase()) > 0.6) {
            console.log(`✅ Fuzzy match: ${options[i].text} (similarity: ${calculateSimilarity(searchTerm, options[i].text.toLowerCase())})`);
            return i;
        }
    }
    
    return -1;
}

// Simple similarity calculation (Levenshtein distance based)
function calculateSimilarity(str1, str2) {
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;
    
    if (longer.length === 0) return 1.0;
    
    const distance = levenshteinDistance(longer, shorter);
    return (longer.length - distance) / longer.length;
}

function levenshteinDistance(str1, str2) {
    const matrix = [];
    for (let i = 0; i <= str2.length; i++) {
        matrix[i] = [i];
    }
    for (let j = 0; j <= str1.length; j++) {
        matrix[0][j] = j;
    }
    for (let i = 1; i <= str2.length; i++) {
        for (let j = 1; j <= str1.length; j++) {
            if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                matrix[i][j] = matrix[i - 1][j - 1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i - 1][j - 1] + 1,
                    matrix[i][j - 1] + 1,
                    matrix[i - 1][j] + 1
                );
            }
        }
    }
    return matrix[str2.length][str1.length];
}

// Load data for sections
function loadSectionData(sectionName) {
    // For events, if data is already loaded, just render the table
    if (sectionName === 'events' && window.allEvents && window.allEvents.length > 0) {
        renderEventsTable();
        return;
    }
    
    switch(sectionName) {
        case 'overview':
            loadOverviewWithTimeout();
            break;
        case 'cities':
            if (!window.allCities || window.allCities.length === 0) {
                loadCities();
            } else {
                renderCitiesTable();
            }
            break;
        case 'venues':
            if (!window.allVenues || window.allVenues.length === 0) {
                loadVenues();
            } else {
                renderVenuesTable();
            }
            break;
        case 'events':
            loadEvents();
            break;
        case 'sources':
            if (!window.allSources || window.allSources.length === 0) {
                loadSources();
            } else {
                renderSourcesTable();
            }
            break;
    }
}
