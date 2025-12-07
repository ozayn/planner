// Load cities data
async function loadCities() {
    try {
        const response = await fetch('/api/admin/cities');
        const cities = await response.json();
        
        if (cities.error) throw new Error(cities.error);
        
        // Sort by most recently updated first (descending)
        cities.sort((a, b) => {
            const aDate = new Date(a.updated_at || a.created_at || 0);
            const bDate = new Date(b.updated_at || b.created_at || 0);
            return bDate - aDate; // Descending order (most recent first)
        });
        
        // Store cities globally for filtering
        window.allCities = cities;
        window.filteredCities = [...cities];
        
        // Render the cities table
        renderCitiesTable();
        populateCityFilters();
        
        // Populate all city dropdowns
        populateAllCityDropdowns();
        
    } catch (error) {
        console.error('Error loading cities:', error);
        const citiesTable = document.getElementById('citiesTable');
        if (citiesTable) {
            citiesTable.innerHTML = '<tr><td colspan="11" class="no-results">❌ Failed to load cities: ' + error.message + '</td></tr>';
        }
    }
}

// Helper function to populate all city dropdowns across the admin interface
function populateAllCityDropdowns() {
    if (!window.allCities) {
        console.warn('Cities not loaded yet, skipping dropdown population');
        return;
    }
    
    // Populate quick URL city selector
    populateQuickUrlCitySelector();
    
    // Populate URL scraper city selector (if modal is open or on demand)
    populateUrlCitySelector();
}

// Populate the URL scraper modal city dropdown
function populateUrlCitySelector() {
    if (!window.allCities) return;
    
    const select = document.getElementById('urlCitySelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Choose a city...</option>';
    window.allCities.forEach(city => {
        const option = document.createElement('option');
        option.value = city.id;
        option.textContent = `${city.name}${city.state ? ', ' + city.state : ''}, ${city.country || ''}`;
        select.appendChild(option);
    });
    
    // Try auto-selection if we have extracted data
    if (window.extractedEventData && window.extractedEventData.city_id) {
        select.value = window.extractedEventData.city_id;
    }
}

// Render cities table dynamically
function renderCitiesTable() {
    const data = window.filteredCities || window.allCities || [];
    // Ensure the section is visible before rendering
    const citiesSection = document.getElementById('cities');
    if (!citiesSection) {
        console.warn('Cities section not found, skipping render');
        return;
    }
    
    // Check if section is visible - use class check instead of getComputedStyle (faster, no reflow)
    if (!citiesSection.classList.contains('active')) {
        return;
    }
    
    // Defer heavy table rendering to next frame to keep UI responsive
    requestAnimationFrame(() => {
        // Ensure the table container is visible before rendering
        const tableContainer = citiesSection.querySelector('.table-container');
        if (tableContainer) {
            tableContainer.style.display = 'block';
            tableContainer.style.visibility = 'visible';
            tableContainer.style.minHeight = '400px';
            tableContainer.style.height = 'auto';
        }
        renderDynamicTable('citiesTable', data, 'cities');
        updateAllTablesViewMode();
    });
}

// Populate city filters
function populateCityFilters() {
    const countryFilter = document.getElementById('cityCountryFilter');
    if (!countryFilter || !window.allCities) return;
    
    const countries = [...new Set(window.allCities.map(city => city.country).filter(Boolean))].sort();
    
    countryFilter.innerHTML = '<option value="">All Countries</option>';
    countries.forEach(country => {
        countryFilter.innerHTML += '<option value="' + country + '">' + country + '</option>';
    });
}

// City filter functions
function applyCityFilters() {
    if (!window.allCities) return;
    
    const searchTerm = document.getElementById('citySearch').value.toLowerCase();
    const countryFilter = document.getElementById('cityCountryFilter').value;
    const venueFilter = document.getElementById('cityVenueFilter').value;
    
    window.filteredCities = window.allCities.filter(city => {
        const matchesSearch = !searchTerm || 
            city.name.toLowerCase().includes(searchTerm) ||
            (city.state && city.state.toLowerCase().includes(searchTerm)) ||
            city.country.toLowerCase().includes(searchTerm);
        
        const matchesCountry = !countryFilter || city.country === countryFilter;
        
        const matchesVenue = !venueFilter || (() => {
            const count = city.venue_count || 0;
            switch (venueFilter) {
                case '0': return count === 0;
                case '1-4': return count >= 1 && count <= 4;
                case '5+': return count >= 5;
                default: return true;
            }
        })();
        
        return matchesSearch && matchesCountry && matchesVenue;
    });
    
    // Sort by most recently updated first (descending) - default sort order
    window.filteredCities.sort((a, b) => {
        const aDate = new Date(a.updated_at || a.created_at || 0);
        const bDate = new Date(b.updated_at || b.created_at || 0);
        return bDate - aDate; // Descending order (most recent first)
    });
    
    renderCitiesTable();
}

function clearCityFilters() {
    document.getElementById('citySearch').value = '';
    document.getElementById('cityCountryFilter').value = '';
    document.getElementById('cityVenueFilter').value = '';
    
    if (window.allCities) {
        window.filteredCities = [...window.allCities];
        renderCitiesTable();
    }
}

function openAddCityModal() {
    document.getElementById('addCityModal').style.display = 'block';
    // Clear form
    document.getElementById('addCityForm').reset();
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    
    // Reset image upload modal state when closing
    if (modalId === 'imageUploadModal') {
        const stickyFooter = document.getElementById('imageUploadStickyFooter');
        if (stickyFooter) {
            stickyFooter.style.display = 'none';
        }
        const scrollableContent = document.getElementById('imageUploadScrollableContent');
        if (scrollableContent) {
            scrollableContent.style.paddingBottom = '20px';
        }
        const uploadForm = document.getElementById('imageUploadForm');
        if (uploadForm) {
            uploadForm.style.display = 'block';
        }
    }
}

function editCity(id) {
    // Find the city data
    const city = window.allCities.find(c => c.id == id);
    if (!city) {
        alert('City not found');
        return;
    }
    
    // Populate the edit form
    document.getElementById('editCityId').value = city.id;
    document.getElementById('editCityName').value = city.name;
    document.getElementById('editCityState').value = city.state || '';
    document.getElementById('editCityCountry').value = city.country;
    document.getElementById('editCityTimezone').value = city.timezone || '';
    
    // Show the modal
    document.getElementById('editCityModal').style.display = 'block';
}

function deleteCity(id) {
    if (confirm('Are you sure you want to delete this city? This will also delete all associated venues and events.')) {
        handleDeleteCity(id);
    }
}

// Handle delete city API call
async function handleDeleteCity(cityId) {
    try {
        
        const response = await fetch('/api/admin/cities/' + cityId, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('City deleted successfully!');
            
            // Reload cities data
            await loadCities();
            
        } else {
            console.error('Error deleting city:', result);
            alert('Error deleting city: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Error deleting city:', error);
        alert('Error deleting city: ' + error.message);
    }
}

