// Load venues data
async function loadVenues() {
    try {
        // Load cities first if not already loaded (needed for city filter)
        if (!window.allCities || window.allCities.length === 0) {
            try {
                const citiesResponse = await fetch('/api/admin/cities');
                const cities = await citiesResponse.json();
                if (!cities.error) {
                    window.allCities = cities;
                }
            } catch (citiesError) {
                console.warn('Could not load cities for filter:', citiesError);
            }
        }
        
        const response = await fetch('/api/admin/venues');
        const venues = await response.json();
        
        if (venues.error) throw new Error(venues.error);
        
        // Backend already sorts by updated_at.desc(), but ensure frontend sorting is consistent
        // Sort by most recently updated first (descending), with ID as tiebreaker
        venues.sort((a, b) => {
            const aDate = new Date(a.updated_at || a.created_at || 0);
            const bDate = new Date(b.updated_at || b.created_at || 0);
            const dateDiff = bDate - aDate; // Descending order (most recent first)
            if (dateDiff !== 0) return dateDiff;
            // Tiebreaker: use ID descending for venues updated at the same time
            return (b.id || 0) - (a.id || 0);
        });
        
        // Store venues globally for filtering
        window.allVenues = venues;
        window.filteredVenues = [...venues];
        
        // Render the venues table
        renderVenuesTable();
        populateVenueFilters();
        
        // Update select all checkbox state after rendering
        setTimeout(() => {
            updateSelectAllVenuesForMainPageCheckbox();
        }, 100);
        
        // Update select all checkbox state after rendering
        setTimeout(() => {
            updateSelectAllVenuesForMainPageCheckbox();
        }, 100);
        
    } catch (error) {
        console.error('Error loading venues:', error);
        const venuesTable = document.getElementById('venuesTable');
        if (venuesTable) {
            venuesTable.innerHTML = '<tr><td colspan="20" class="no-results">❌ Failed to load venues: ' + error.message + '</td></tr>';
        }
    }
}

// Sorting functionality for dynamic tables
function sortTable(tableId, field) {
    // Determine which data array to sort based on table ID
    let dataArray;
    let filteredArray;
    
    switch(tableId) {
        case 'citiesTable':
            dataArray = window.allCities;
            filteredArray = window.filteredCities;
            break;
        case 'venuesTable':
            dataArray = window.allVenues;
            filteredArray = window.filteredVenues;
            break;
        case 'eventsTable':
            dataArray = window.allEvents;
            filteredArray = window.filteredEvents;
            break;
        case 'sourcesTable':
            dataArray = window.allSources;
            filteredArray = window.filteredSources;
            break;
        default:
            console.error('Unknown table ID for sorting:', tableId);
            return;
    }
    
    // Use allData if filtered is not available
    if (!filteredArray) {
        filteredArray = dataArray;
    }
    
    if (!dataArray || !filteredArray) {
        console.error('Data arrays not available for sorting');
        return;
    }
    
    // Toggle sort direction (store in data attribute)
    const table = document.querySelector(`#${tableId}`).closest('table');
    const currentSort = table.dataset.currentSort;
    const currentField = table.dataset.currentField;
    
    let ascending = true;
    if (currentField === field && currentSort === 'asc') {
        ascending = false;
    }
    
    // Update table data attributes
    table.dataset.currentField = field;
    table.dataset.currentSort = ascending ? 'asc' : 'desc';
    
    // Create a copy to sort (don't mutate the original)
    const sortedArray = [...filteredArray].sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];
        
        // Handle null/undefined values
        if (aVal === null || aVal === undefined) aVal = '';
        if (bVal === null || bVal === undefined) bVal = '';
        
        // Handle different data types
        if (typeof aVal === 'string' && typeof bVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }
        
        // Handle dates (ISO format)
        if (field.includes('_at') || field.includes('_date')) {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }
        
        // Compare values
        if (aVal < bVal) return ascending ? -1 : 1;
        if (aVal > bVal) return ascending ? 1 : -1;
        return 0;
    });
    
    // Update the window variable for the filtered array
    switch(tableId) {
        case 'citiesTable':
            window.filteredCities = sortedArray;
            break;
        case 'venuesTable':
            window.filteredVenues = sortedArray;
            break;
        case 'eventsTable':
            window.filteredEvents = sortedArray;
            break;
        case 'sourcesTable':
            window.filteredSources = sortedArray;
            break;
    }
    
    // Re-render the table
    const tableType = tableId.replace('Table', '');
    renderDynamicTable(tableId, sortedArray, tableType);
    
    // Update header arrows to show sort direction
    updateSortArrows(table, field, ascending);
}

function updateSortArrows(table, field, ascending) {
    // Remove all arrows first
    const headers = table.querySelectorAll('th');
    headers.forEach(header => {
        const text = header.textContent.replace(' ↕', '').replace(' ↑', '').replace(' ↓', '');
        header.textContent = text + ' ↕';
    });
    
    // Add arrow to current field
    const currentHeader = Array.from(headers).find(header => 
        header.textContent.includes(field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()))
    );
    if (currentHeader) {
        const text = currentHeader.textContent.replace(' ↕', '').replace(' ↑', '').replace(' ↓', '');
        currentHeader.textContent = text + (ascending ? ' ↑' : ' ↓');
    }
}

function getEventTypeBadgeClass(eventType) {
    // Return appropriate badge class based on event type
    const type = eventType.toLowerCase();
    
    if (type.includes('photowalk') || type.includes('photo_walk')) {
        return 'badge-photowalk';
    } else if (type.includes('exhibition') || type.includes('gallery')) {
        return 'badge-exhibition';
    } else if (type.includes('tour')) {
        return 'badge-tour';
    } else if (type.includes('festival') || type.includes('event')) {
        return 'badge-festival';
    } else if (type.includes('workshop') || type.includes('class')) {
        return 'badge-workshop';
    } else if (type.includes('talk') || type.includes('lecture') || type.includes('reading')) {
        return 'badge-talk';
    } else if (type.includes('music') || type.includes('concert') || type.includes('performance')) {
        return 'badge-music';
    } else if (type.includes('cultural') || type.includes('culture')) {
        return 'badge-cultural';
    } else if (type.includes('film') || type.includes('cinema')) {
        return 'badge-film';
    } else if (type.includes('art') || type.includes('creative')) {
        return 'badge-art';
    } else if (type.includes('language') || type.includes('french')) {
        return 'badge-language';
    } else {
        return 'badge-default';
    }
}

// Dynamic table rendering system

// Render venues table using dynamic system
function renderVenuesTable() {
    const data = window.filteredVenues || window.allVenues || [];
    // Ensure the section is visible before rendering
    const venuesSection = document.getElementById('venues');
    if (!venuesSection) {
        console.warn('Venues section not found, skipping render');
        return;
    }
    
    // Check if section is visible - use class check instead of getComputedStyle (faster, no reflow)
    if (!venuesSection.classList.contains('active')) {
        return;
    }
    
    // Defer heavy table rendering to next frame to keep UI responsive
    requestAnimationFrame(() => {
        // Ensure the table container is visible before rendering
        const tableContainer = venuesSection.querySelector('.table-container');
        if (tableContainer) {
            tableContainer.style.display = 'block';
            tableContainer.style.visibility = 'visible';
            tableContainer.style.minHeight = '400px';
            tableContainer.style.height = 'auto';
        }
        renderDynamicTable('venuesTable', data, 'venues');
        updateAllTablesViewMode();
    });
}

// Populate venue filters
function populateVenueFilters() {
    const typeFilter = document.getElementById('venueTypeFilter');
    const cityFilter = document.getElementById('venueCityFilter');
    
    if (!typeFilter || !cityFilter || !window.allVenues) return;
    
    const types = [...new Set(window.allVenues.map(venue => venue.venue_type).filter(Boolean))].sort();
    
    // Populate city filter from all cities (not just cities with venues)
    // This ensures cities like State College and Irvine appear even if they have no venues yet
    // Format city names to match the API format: "City, State, Country" or "City, Country"
    let cityOptions = [];
    if (window.allCities && window.allCities.length > 0) {
        // Use all cities from the cities data, format to match API response
        cityOptions = window.allCities.map(city => {
            let displayName = city.name;
            if (city.state) {
                displayName += `, ${city.state}, ${city.country}`;
            } else {
                displayName += `, ${city.country}`;
            }
            return {
                id: city.id,
                name: displayName,
                cityName: city.name // Store just the city name for matching
            };
        }).sort((a, b) => a.name.localeCompare(b.name));
    } else {
        // Fallback to cities from venues if cities haven't loaded yet
        const cityNames = [...new Set(window.allVenues.map(venue => venue.city_name).filter(Boolean))].sort();
        cityOptions = cityNames.map(name => ({
            id: null,
            name: name,
            cityName: name.split(',')[0].trim() // Extract just city name
        }));
    }
    
    typeFilter.innerHTML = '<option value="">All Types</option>';
    types.forEach(type => {
        typeFilter.innerHTML += '<option value="' + type + '">' + type + '</option>';
    });
    
    cityFilter.innerHTML = '<option value="">All Cities</option>';
    cityOptions.forEach(city => {
        cityFilter.innerHTML += '<option value="' + city.name + '">' + city.name + '</option>';
    });
}

// Venue filter functions
function applyVenueFilters() {
    if (!window.allVenues) return;
    
    const searchTerm = document.getElementById('venueSearch').value.toLowerCase();
    const typeFilter = document.getElementById('venueTypeFilter').value;
    const cityFilter = document.getElementById('venueCityFilter').value;
    const feeFilter = document.getElementById('venueFeeFilter').value;
    const closureFilter = document.getElementById('venueClosureFilter').value;
    const sortBy = document.getElementById('venueSortBy').value;
    
    window.filteredVenues = window.allVenues.filter(venue => {
        const matchesSearch = !searchTerm || 
            venue.name.toLowerCase().includes(searchTerm) ||
            (venue.venue_type && venue.venue_type.toLowerCase().includes(searchTerm)) ||
            (venue.address && venue.address.toLowerCase().includes(searchTerm)) ||
            (venue.description && venue.description.toLowerCase().includes(searchTerm));
        
        const matchesType = !typeFilter || venue.venue_type === typeFilter;
        // Match city by exact city_name (which includes state/country in format from API)
        const matchesCity = !cityFilter || (venue.city_name && venue.city_name === cityFilter);
        
        // Fee filter logic
        let matchesFee = true;
        if (feeFilter === 'free') {
            matchesFee = !venue.admission_fee || 
                        venue.admission_fee.toLowerCase().includes('free') ||
                        venue.admission_fee.toLowerCase().includes('no charge') ||
                        venue.admission_fee.toLowerCase().includes('complimentary') ||
                        !venue.admission_fee || venue.admission_fee === '';
        } else if (feeFilter === 'paid') {
            matchesFee = venue.admission_fee && 
                       !venue.admission_fee.toLowerCase().includes('free') &&
                       !venue.admission_fee.toLowerCase().includes('no charge') &&
                       !venue.admission_fee.toLowerCase().includes('complimentary') &&
                       venue.admission_fee !== '';
        }
        
        // Closure status filter logic
        let matchesClosure = true;
        if (closureFilter) {
            try {
                const additionalInfo = venue.additional_info ? JSON.parse(venue.additional_info) : {};
                const venueClosureStatus = additionalInfo.closure_status || 'unknown';
                matchesClosure = venueClosureStatus === closureFilter;
            } catch (e) {
                matchesClosure = closureFilter === 'unknown';
            }
        }
        
        return matchesSearch && matchesType && matchesCity && matchesFee && matchesClosure;
    });
    
    // Apply sorting - default to most recently updated first if no sort specified
    window.filteredVenues.sort((a, b) => {
        if (sortBy) {
            switch(sortBy) {
                case 'name':
                    return (a.name || '').localeCompare(b.name || '');
                case 'name_desc':
                    return (b.name || '').localeCompare(a.name || '');
                case 'updated_at_desc':
                    return new Date(normalizeUTCTimestamp(b.updated_at || '') || 0) - new Date(normalizeUTCTimestamp(a.updated_at || '') || 0);
                case 'updated_at':
                    return new Date(normalizeUTCTimestamp(a.updated_at || '') || 0) - new Date(normalizeUTCTimestamp(b.updated_at || '') || 0);
                case 'created_at_desc':
                    return new Date(normalizeUTCTimestamp(b.created_at || '') || 0) - new Date(normalizeUTCTimestamp(a.created_at || '') || 0);
                case 'created_at':
                    return new Date(normalizeUTCTimestamp(a.created_at || '') || 0) - new Date(normalizeUTCTimestamp(b.created_at || '') || 0);
                case 'venue_type':
                    return (a.venue_type || '').localeCompare(b.venue_type || '');
                case 'city_name':
                    return (a.city_name || '').localeCompare(b.city_name || '');
                default:
                    // Default to most recently updated first, with ID as tiebreaker
                    const aDate = new Date(a.updated_at || a.created_at || 0);
                    const bDate = new Date(b.updated_at || b.created_at || 0);
                    const dateDiff = bDate - aDate;
                    if (dateDiff !== 0) return dateDiff;
                    return (b.id || 0) - (a.id || 0);
            }
        } else {
            // Default to most recently updated first, with ID as tiebreaker
            const aDate = new Date(a.updated_at || a.created_at || 0);
            const bDate = new Date(b.updated_at || b.created_at || 0);
            const dateDiff = bDate - aDate;
            if (dateDiff !== 0) return dateDiff;
            return (b.id || 0) - (a.id || 0);
        }
    });
    
    renderVenuesTable();
}

function clearVenueFilters() {
    document.getElementById('venueSearch').value = '';
    document.getElementById('venueTypeFilter').value = '';
    document.getElementById('venueCityFilter').value = '';
    document.getElementById('venueFeeFilter').value = '';
    document.getElementById('venueClosureFilter').value = '';
    document.getElementById('venueSortBy').value = '';
    
    if (window.allVenues) {
        window.filteredVenues = [...window.allVenues];
        renderVenuesTable();
    }
}

function openAddVenueModal() {
    // Generate dynamic form fields
    generateDynamicVenueForm();
    
    // Populate city dropdown
    populateVenueCityDropdown();
    
    // Populate venue type dropdown
    populateVenueTypeDropdown();
    
    // Clear form
    document.getElementById('addVenueForm').reset();
    
    // Show modal
    document.getElementById('addVenueModal').style.display = 'block';
}

function generateDynamicVenueForm() {
    const container = document.getElementById('dynamicVenueFormFields');
    if (!container) return;
    
    // Define all venue fields with their properties
    const venueFields = [
        {
            id: 'venueName',
            name: 'name',
            label: 'Venue Name',
            type: 'text',
            required: true,
            placeholder: 'Enter venue name',
            special: 'smart_search' // Special handling for smart search button
        },
        {
            id: 'venueType',
            name: 'venue_type',
            label: 'Venue Type',
            type: 'select',
            required: true,
            options: [
                { value: '', text: 'Select Type' }
                // Dynamic venue types will be loaded from backend
            ],
            special: 'venue_type_dropdown' // Special handling for dynamic venue types
        },
        {
            id: 'venueCity',
            name: 'city_id',
            label: 'City',
            type: 'select',
            required: true,
            options: [{ value: '', text: 'Select City' }],
            special: 'city_dropdown' // Special handling for city population
        },
        {
            id: 'venueAddress',
            name: 'address',
            label: 'Address',
            type: 'text',
            placeholder: 'Full street address'
        },
        {
            id: 'venueLatitude',
            name: 'latitude',
            label: 'Latitude',
            type: 'number',
            step: '0.000001',
            placeholder: 'e.g., 38.9072'
        },
        {
            id: 'venueLongitude',
            name: 'longitude',
            label: 'Longitude',
            type: 'number',
            step: '0.000001',
            placeholder: 'e.g., -77.0369'
        },
        {
            id: 'venueImageUrl',
            name: 'image_url',
            label: 'Image URL',
            type: 'url',
            placeholder: 'https://example.com/image.jpg'
        },
        {
            id: 'venueDescription',
            name: 'description',
            label: 'Description',
            type: 'textarea',
            rows: 3,
            placeholder: 'Brief description of the venue...'
        },
        {
            id: 'venueOpeningHours',
            name: 'opening_hours',
            label: 'Opening Hours',
            type: 'text',
            placeholder: 'e.g., Mon-Fri: 9AM-5PM, Sat-Sun: 10AM-6PM'
        },
        {
            id: 'venueHolidayHours',
            name: 'holiday_hours',
            label: 'Holiday Hours',
            type: 'text',
            placeholder: 'e.g., Closed on Thanksgiving and Christmas'
        },
        {
            id: 'venuePhone',
            name: 'phone_number',
            label: 'Phone Number',
            type: 'tel',
            placeholder: 'e.g., (202) 555-0123'
        },
        {
            id: 'venueEmail',
            name: 'email',
            label: 'Email',
            type: 'email',
            placeholder: 'info@venue.com'
        },
        {
            id: 'venueWebsite',
            name: 'website_url',
            label: 'Website URL',
            type: 'url',
            placeholder: 'https://www.venue.com'
        },
        {
            id: 'venueTicketing',
            name: 'ticketing_url',
            label: 'Ticketing URL',
            type: 'url',
            placeholder: 'https://www.eventbrite.com/... or https://www.ticketmaster.com/...',
            special: 'eventbrite_search'
        },
        {
            id: 'venueAdmission',
            name: 'admission_fee',
            label: 'Admission Fee',
            type: 'text',
            placeholder: 'e.g., Free, $20, $15-25'
        },
        {
            id: 'venueTourInfo',
            name: 'tour_info',
            label: 'Tour Information',
            type: 'textarea',
            rows: 2,
            placeholder: 'Information about tours, guided visits, etc.'
        },
        {
            id: 'venueInstagram',
            name: 'instagram_url',
            label: 'Instagram',
            type: 'text',
            placeholder: '@venuehandle'
        },
        {
            id: 'venueFacebook',
            name: 'facebook_url',
            label: 'Facebook',
            type: 'url',
            placeholder: 'https://facebook.com/venue'
        },
        {
            id: 'venueTwitter',
            name: 'twitter_url',
            label: 'Twitter',
            type: 'text',
            placeholder: '@venuehandle'
        },
        {
            id: 'venueYoutube',
            name: 'youtube_url',
            label: 'YouTube',
            type: 'url',
            placeholder: 'https://youtube.com/c/venue'
        },
        {
            id: 'venueTiktok',
            name: 'tiktok_url',
            label: 'TikTok',
            type: 'text',
            placeholder: '@venuehandle'
        },
        {
            id: 'venueAdditionalInfo',
            name: 'additional_info',
            label: 'Additional Information',
            type: 'textarea',
            rows: 3,
            placeholder: 'Additional details (JSON format)'
        }
    ];
    
    let formHTML = '';
    
    venueFields.forEach(field => {
        formHTML += '<div class="form-group">';
        formHTML += `<label for="${field.id}">${field.label}${field.required ? ' *' : ''}</label>`;
        
        if (field.special === 'smart_search') {
            formHTML += '<div style="display: flex; gap: 10px;">';
            formHTML += `<input type="${field.type}" id="${field.id}" name="${field.name}" ${field.required ? 'required' : ''} placeholder="${field.placeholder || ''}" style="flex: 1;">`;
            formHTML += '<button type="button" id="smartSearchBtn" onclick="smartSearchVenue()" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">🔍 Smart Search</button>';
            formHTML += '</div>';
        } else if (field.special === 'eventbrite_search') {
            formHTML += '<div style="display: flex; gap: 8px; align-items: center;">';
            formHTML += `<input type="${field.type}" id="${field.id}" name="${field.name}" ${field.required ? 'required' : ''} placeholder="${field.placeholder || ''}" style="flex: 1;">`;
            formHTML += '<button type="button" onclick="searchEventbriteOrganizerForAdd()" class="btn btn-secondary" style="white-space: nowrap; padding: 8px 12px;">🔍 Search Eventbrite</button>';
            formHTML += '</div>';
            formHTML += '<div id="addEventbriteSearchResults" style="margin-top: 8px; display: none;"></div>';
        } else if (field.type === 'select') {
            formHTML += `<select id="${field.id}" name="${field.name}" ${field.required ? 'required' : ''}>`;
            field.options.forEach(option => {
                formHTML += `<option value="${option.value}">${option.text}</option>`;
            });
            formHTML += '</select>';
        } else if (field.type === 'textarea') {
            formHTML += `<textarea id="${field.id}" name="${field.name}" rows="${field.rows || 3}" placeholder="${field.placeholder || ''}"></textarea>`;
        } else {
            formHTML += `<input type="${field.type}" id="${field.id}" name="${field.name}" ${field.required ? 'required' : ''} placeholder="${field.placeholder || ''}" ${field.step ? `step="${field.step}"` : ''}>`;
        }
        
        formHTML += '</div>';
    });
    
    container.innerHTML = formHTML;
}

function populateVenueCityDropdown() {
    const citySelect = document.getElementById('venueCity');
    if (!citySelect) return;
    
    // If cities aren't loaded yet, try to load them first
    if (!window.allCities) {
        loadCities().then(() => {
            populateVenueCityDropdown(); // Try again after loading
        }).catch(error => {
            console.error('Failed to load cities:', error);
            citySelect.innerHTML = '<option value="">Loading cities...</option>';
        });
        return;
    }
    
    citySelect.innerHTML = '<option value="">Select City</option>';
    window.allCities.forEach(city => {
        // Always include state/province if available, then country
        let displayName = city.name;
        if (city.state) {
            displayName += `, ${city.state}`;
        }
        displayName += `, ${city.country}`;
        citySelect.innerHTML += `<option value="${city.id}">${displayName}</option>`;
    });
    
}

async function populateVenueTypeDropdown() {
    const typeSelect = document.getElementById('venueType');
    if (!typeSelect) return;
    
    try {
        const response = await fetch('/api/venue-types');
        const data = await response.json();
        
        if (data.venue_types) {
            typeSelect.innerHTML = '<option value="">Select Type</option>';
            data.venue_types.forEach(type => {
                typeSelect.innerHTML += `<option value="${type.value}">${type.text}</option>`;
            });
        } else {
            console.error('No venue types returned from API');
        }
    } catch (error) {
        console.error('Error loading venue types:', error);
        // Fallback to basic types
        typeSelect.innerHTML = `
            <option value="">Select Type</option>
            <option value="museum">Museum</option>
            <option value="gallery">Gallery</option>
            <option value="theater">Theater</option>
            <option value="cafe">Cafe</option>
            <option value="restaurant">Restaurant</option>
            <option value="bookstore">Bookstore</option>
            <option value="other">Other</option>
        `;
    }
}

async function smartSearchVenue() {
    const venueName = document.getElementById('venueName').value.trim();
    const cityId = document.getElementById('venueCity').value;
    
    if (!venueName) {
        alert('Please enter a venue name first');
        return;
    }
    
    if (!cityId) {
        alert('Please select a city first');
        return;
    }
    
    // Find city name from selected city ID
    const selectedCity = window.allCities.find(city => city.id == cityId);
    if (!selectedCity) {
        alert('Selected city not found');
        return;
    }
    
    const smartSearchBtn = document.getElementById('smartSearchBtn');
    const originalText = smartSearchBtn.textContent;
    smartSearchBtn.textContent = '🔍 Searching...';
    smartSearchBtn.disabled = true;
    
    try {
        
        const response = await fetch('/api/admin/smart-search-venue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                venue_name: venueName,
                city_name: selectedCity.name,
                city_id: parseInt(cityId)
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            console.log('Smart search successful:', result);
            
            // Populate form with AI-discovered details
            populateFormWithVenueDetails(result.venue_details);
            
            alert('Venue details found and populated! Review and adjust as needed.');
            
        } else {
            console.error('Smart search failed:', result);
            alert('Smart search failed: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Error during smart search:', error);
        alert('Error during smart search: ' + error.message);
    } finally {
        smartSearchBtn.textContent = originalText;
        smartSearchBtn.disabled = false;
    }
}

function populateFormWithVenueDetails(venueDetails) {
    // Populate all form fields dynamically based on venue details
    const fieldMappings = {
        'name': 'venueName',
        'venue_type': 'venueType',
        'address': 'venueAddress',
        'latitude': 'venueLatitude',
        'longitude': 'venueLongitude',
        'image_url': 'venueImageUrl',
        'description': 'venueDescription',
        'opening_hours': 'venueOpeningHours',
        'holiday_hours': 'venueHolidayHours',
        'phone_number': 'venuePhone',
        'email': 'venueEmail',
        'website_url': 'venueWebsite',
        'admission_fee': 'venueAdmission',
        'tour_info': 'venueTourInfo',
        'instagram_url': 'venueInstagram',
        'facebook_url': 'venueFacebook',
        'twitter_url': 'venueTwitter',
        'youtube_url': 'venueYoutube',
        'tiktok_url': 'venueTiktok',
        'additional_info': 'venueAdditionalInfo'
    };
    
    // Populate each field if the data exists
    Object.entries(fieldMappings).forEach(([dataKey, fieldId]) => {
        const element = document.getElementById(fieldId);
        if (element && venueDetails[dataKey]) {
            if (element.tagName === 'TEXTAREA' && typeof venueDetails[dataKey] === 'object') {
                // Handle JSON objects for additional_info
                element.value = JSON.stringify(venueDetails[dataKey], null, 2);
            } else {
                element.value = venueDetails[dataKey];
            }
        }
    });
}

async function manageJsonCopy() {
    const action = confirm('JSON Management\n\n' +
        'Click OK to create a fresh venues.json from predefined_venues.json\n' +
        'Click Cancel to apply venues.json changes back to original\n\n' +
        'This allows safe editing without affecting the original file.');
    
    try {
        let endpoint, message;
        
        if (action) {
            // Create venues.json
            endpoint = '/api/admin/create-json-copy';
            message = 'Creating fresh venues.json...';
        } else {
            // Apply venues.json to original
            endpoint = '/api/admin/apply-json-copy';
            message = 'Applying venues.json changes to original file...';
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message || message);
        } else {
            alert('Error: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Error managing JSON copy:', error);
        alert('Error managing JSON copy: ' + error.message);
    }
}

async function exportVenuesFromDatabase() {
    const confirmed = confirm('Export Venues from Database\n\n' +
        'This will download all venues from the database as a JSON file.\n' +
        'Useful for production environments or creating backups.\n\n' +
        'Continue?');
    
    if (!confirmed) return;
    
    try {
        console.log('Starting venues export...');
        
        const response = await fetch('/api/admin/export-venues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            // Get the filename from the response headers
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition ? 
                contentDisposition.split('filename=')[1].replace(/"/g, '') : 
                'venues_exported.json';
            
            // Create blob and download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ Export successful! File downloaded.');
        } else {
            const result = await response.json();
            alert('❌ Export failed: ' + result.error);
        }
        
    } catch (error) {
        console.error('Export error:', error);
        alert('❌ Export error: ' + error.message);
    }
}

async function exportCitiesFromDatabase() {
    const confirmed = confirm('Export Cities from Database\n\n' +
        'This will download all cities from the database as a JSON file.\n' +
        'Matches the cities.json format for easy replacement.\n\n' +
        'Continue?');
    
    if (!confirmed) return;
    
    try {
        
        const response = await fetch('/api/admin/export-cities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            // Get the filename from the response headers
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition ? 
                contentDisposition.split('filename=')[1].replace(/"/g, '') : 
                'cities_exported.json';
            
            // Create blob and download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ Export successful! File downloaded.');
        } else {
            const result = await response.json();
            alert('❌ Export failed: ' + result.error);
        }
        
    } catch (error) {
        console.error('Export error:', error);
        alert('❌ Export error: ' + error.message);
    }
}

async function exportSourcesFromDatabase() {
    const confirmed = confirm('Export Sources from Database\n\n' +
        'This will download all sources from the database as a JSON file.\n' +
        'Matches the sources.json format for easy replacement.\n\n' +
        'Continue?');
    
    if (!confirmed) return;
    
    try {
        console.log('Starting sources export...');
        
        const response = await fetch('/api/admin/export-sources', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            // Get the filename from the response headers
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition ? 
                contentDisposition.split('filename=')[1].replace(/"/g, '') : 
                'sources_exported.json';
            
            // Create blob and download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            alert('✅ Export successful! File downloaded.');
        } else {
            const result = await response.json();
            alert('❌ Export failed: ' + result.error);
        }
        
    } catch (error) {
        console.error('Export error:', error);
        alert('❌ Export error: ' + error.message);
    }
}

function editVenue(id) {
    // Find the venue data
    const venue = window.allVenues.find(v => v.id == id);
    if (!venue) {
        alert('Venue not found');
        return;
    }
    
    // Populate the edit form with current venue data
    document.getElementById('editVenueId').value = venue.id;
    document.getElementById('editVenueName').value = venue.name || '';
    document.getElementById('editVenueType').value = venue.venue_type || '';
    document.getElementById('editVenueAddress').value = venue.address || '';
    document.getElementById('editVenueDescription').value = venue.description || '';
    document.getElementById('editVenueHours').value = venue.opening_hours || '';
    document.getElementById('editVenuePhone').value = venue.phone_number || '';
    document.getElementById('editVenueEmail').value = venue.email || '';
    document.getElementById('editVenueWebsite').value = venue.website_url || '';
    document.getElementById('editVenueTicketing').value = venue.ticketing_url || '';
    document.getElementById('editVenueAdmission').value = venue.admission_fee || '';
    
    // Clear Eventbrite search results
    const resultsDiv = document.getElementById('eventbriteSearchResults');
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
        resultsDiv.innerHTML = '';
    }
    
    // Show the modal
    document.getElementById('editVenueModal').style.display = 'block';
}

function deleteVenue(id) {
    if (confirm('Are you sure you want to delete this venue? This will also delete all associated events.')) {
        fetch(`/api/delete-venue/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Venue deleted successfully!');
                loadVenues(); // Reload data
            } else {
                alert('Error: ' + result.error);
            }
        })
        .catch(error => {
            alert('Error deleting venue: ' + error.message);
        });
    }
}

async function searchEventbriteOrganizer() {
    /**Search Eventbrite for organizer pages matching the venue name or extract from URL*/
    const venueNameInput = document.getElementById('editVenueName');
    const ticketingInput = document.getElementById('editVenueTicketing');
    const resultsDiv = document.getElementById('eventbriteSearchResults');
    
    if (!venueNameInput || !ticketingInput || !resultsDiv) {
        console.error('Required elements not found for Eventbrite search');
        return;
    }
    
    const venueName = venueNameInput.value.trim();
    const currentUrl = ticketingInput.value.trim();
    
    // If there's already a URL in the field, try to extract organizer ID from it
    if (currentUrl && 'eventbrite.com' in currentUrl) {
        // Show loading
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">🔍 Extracting organizer ID from URL...</div>';
        
        try {
            const response = await fetch('/api/admin/search-eventbrite-organizer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    organizer_url: currentUrl,
                    venue_name: venueName
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.organizers && data.organizers.length > 0) {
                const org = data.organizers[0];
                resultsDiv.innerHTML = `
                    <div style="padding: 10px; background: #d1fae5; border-radius: 4px; color: #065f46;">
                        ✅ Found organizer: ${org.name}
                        ${org.verified ? '' : '<br><small>⚠️ Could not verify via API, but URL format looks correct</small>'}
                    </div>
                `;
                return;
            }
        } catch (error) {
            console.error('Error extracting organizer:', error);
        }
    }
    
    if (!venueName) {
        alert('Please enter a venue name first, or paste an Eventbrite organizer URL in the Ticketing URL field');
        return;
    }
    
    // Get city name if available
    const citySelect = document.getElementById('editVenueCity');
    let cityName = '';
    if (citySelect && citySelect.value) {
        const selectedOption = citySelect.options[citySelect.selectedIndex];
        cityName = selectedOption.text.split(',')[0]; // Get just the city name
    }
    
    // Show loading state
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">🔍 Searching Eventbrite...</div>';
    
    try {
        const response = await fetch('/api/admin/search-eventbrite-organizer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                venue_name: venueName,
                city_name: cityName
            })
        });
        
        const data = await response.json();
        
        // Eventbrite API no longer supports public search
        if (data.error === 'Eventbrite public search not available' || !data.success) {
            const searchUrl = data.search_url || `https://www.eventbrite.com/d/${cityName ? cityName.toLowerCase().replace(' ', '-') : 'dc--washington'}/${venueName.replace(/\s+/g, '-').toLowerCase()}/`;
            
            resultsDiv.innerHTML = `
                <div style="padding: 12px; background: #fef3c7; border-radius: 6px; border: 1px solid #fbbf24; color: #92400e;">
                    <div style="font-weight: 600; margin-bottom: 8px;">ℹ️ Manual Search Required</div>
                    <div style="font-size: 0.875rem; margin-bottom: 12px;">
                        Eventbrite API no longer provides public search. To find the organizer page:
                    </div>
                    <ol style="font-size: 0.875rem; margin: 0 0 12px 20px; padding: 0;">
                        <li>Search Eventbrite for "${venueName}" events</li>
                        <li>Click on any event from that venue</li>
                        <li>Click the organizer name to go to their page</li>
                        <li>Copy the organizer page URL</li>
                        <li>Paste it in the Ticketing URL field above</li>
                    </ol>
                    <div style="margin-top: 12px;">
                        <a href="${searchUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #3b82f6; color: white; text-decoration: none; border-radius: 4px; font-size: 0.875rem;">
                            🔍 Open Eventbrite Search
                        </a>
                    </div>
                    <div style="margin-top: 8px; font-size: 0.75rem; color: #78716c;">
                        Or paste an Eventbrite organizer URL directly in the field above and click "Search Eventbrite" again to verify it.
                    </div>
                </div>
            `;
            return;
        }
        
        if (!data.organizers || data.organizers.length === 0) {
            resultsDiv.innerHTML = `
                <div style="padding: 10px; background: #fef3c7; border-radius: 4px; color: #92400e;">
                    ℹ️ No Eventbrite organizers found for "${venueName}". 
                    <br>You can manually enter the Eventbrite organizer page URL.
                </div>
            `;
            return;
        }
        
        // Display results (if we ever get any from a future API)
        let resultsHTML = `
            <div style="margin-top: 8px; padding: 12px; background: #f9fafb; border-radius: 6px; border: 1px solid #e5e7eb;">
                <div style="font-weight: 600; margin-bottom: 8px; color: #374151;">
                    Found ${data.organizers.length} organizer${data.organizers.length > 1 ? 's' : ''}:
                </div>
        `;
        
        data.organizers.forEach((organizer, index) => {
            const eventCount = organizer.event_count || 0;
            const sampleEvents = organizer.sample_events || [];
            
            resultsHTML += `
                <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer;" 
                     onclick="selectEventbriteOrganizer('${organizer.url.replace(/'/g, "\\'")}', '${organizer.name.replace(/'/g, "\\'")}')"
                     onmouseover="this.style.background='#f3f4f6'" 
                     onmouseout="this.style.background='white'">
                    <div style="font-weight: 500; color: #1f2937; margin-bottom: 4px;">
                        ${organizer.name}
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 6px;">
                        ${eventCount} event${eventCount !== 1 ? 's' : ''} found
                    </div>
                    ${sampleEvents.length > 0 ? `
                        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 4px;">
                            Sample: ${sampleEvents[0].name}
                        </div>
                    ` : ''}
                    <div style="font-size: 0.75rem; color: #3b82f6; margin-top: 4px;">
                        Click to use this organizer
                    </div>
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        resultsDiv.innerHTML = resultsHTML;
        
    } catch (error) {
        console.error('Error searching Eventbrite:', error);
        resultsDiv.innerHTML = `
            <div style="padding: 10px; background: #fee2e2; border-radius: 4px; color: #991b1b;">
                ❌ Error: ${error.message}
            </div>
        `;
    }
}

// Functions to manage venue selection for main page filtering
// Make it globally accessible so tables.js can use it
window.getMainPageSelectedVenues = function() {
    const saved = localStorage.getItem('mainPageSelectedVenues');
    if (saved) {
        try {
            const ids = JSON.parse(saved);
            return new Set(ids);
        } catch (e) {
            return new Set();
        }
    }
    return new Set();
};

function getMainPageSelectedVenues() {
    return window.getMainPageSelectedVenues();
}

function saveMainPageSelectedVenues(venueIds) {
    localStorage.setItem('mainPageSelectedVenues', JSON.stringify(Array.from(venueIds)));
}

function toggleVenueForMainPage(venueId, isChecked) {
    const selectedVenues = getMainPageSelectedVenues();
    if (isChecked) {
        selectedVenues.add(venueId);
    } else {
        selectedVenues.delete(venueId);
    }
    saveMainPageSelectedVenues(selectedVenues);
    
    // Update select all checkbox state
    updateSelectAllVenuesForMainPageCheckbox();
}

function toggleSelectAllVenuesForMainPage(checkbox) {
    if (!window.allVenues) return;
    
    const selectedVenues = new Set();
    if (checkbox.checked) {
        // Select all visible venues
        window.allVenues.forEach(venue => selectedVenues.add(venue.id));
    }
    // If unchecked, selectedVenues stays empty
    
    saveMainPageSelectedVenues(selectedVenues);
    
    // Update all checkboxes
    const venueCheckboxes = document.querySelectorAll('.venue-main-page-checkbox');
    venueCheckboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
}

function updateSelectAllVenuesForMainPageCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAllVenuesForMainPage');
    if (!selectAllCheckbox || !window.allVenues) return;
    
    const selectedVenues = getMainPageSelectedVenues();
    const allSelected = window.allVenues.length > 0 && 
                       window.allVenues.every(venue => selectedVenues.has(venue.id));
    selectAllCheckbox.checked = allSelected;
}

function selectEventbriteOrganizer(url, name) {
    /**Select an Eventbrite organizer and populate the ticketing URL field (for edit modal)*/
    const ticketingInput = document.getElementById('editVenueTicketing');
    const resultsDiv = document.getElementById('eventbriteSearchResults');
    
    if (ticketingInput) {
        ticketingInput.value = url;
        // Show confirmation
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div style="padding: 10px; background: #d1fae5; border-radius: 4px; color: #065f46;">
                    ✅ Selected: ${name}
                </div>
            `;
            // Hide after 2 seconds
            setTimeout(() => {
                if (resultsDiv) {
                    resultsDiv.style.display = 'none';
                }
            }, 2000);
        }
    }
}

function selectEventbriteOrganizerForAdd(url, name) {
    /**Select an Eventbrite organizer and populate the ticketing URL field (for add modal)*/
    const ticketingInput = document.getElementById('venueTicketing');
    const resultsDiv = document.getElementById('addEventbriteSearchResults');
    
    if (ticketingInput) {
        ticketingInput.value = url;
        // Show confirmation
        if (resultsDiv) {
            resultsDiv.innerHTML = `
                <div style="padding: 10px; background: #d1fae5; border-radius: 4px; color: #065f46;">
                    ✅ Selected: ${name}
                </div>
            `;
            // Hide after 2 seconds
            setTimeout(() => {
                if (resultsDiv) {
                    resultsDiv.style.display = 'none';
                }
            }, 2000);
        }
    }
}

async function searchEventbriteOrganizerForAdd() {
    /**Search Eventbrite for organizer pages (for add venue modal) or extract from URL*/
    const venueNameInput = document.getElementById('venueName');
    const ticketingInput = document.getElementById('venueTicketing');
    const resultsDiv = document.getElementById('addEventbriteSearchResults');
    
    if (!venueNameInput || !ticketingInput || !resultsDiv) {
        console.error('Required elements not found for Eventbrite search');
        return;
    }
    
    const venueName = venueNameInput.value.trim();
    const currentUrl = ticketingInput.value.trim();
    
    // If there's already a URL in the field, try to extract organizer ID from it
    if (currentUrl && 'eventbrite.com' in currentUrl) {
        resultsDiv.style.display = 'block';
        resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">🔍 Extracting organizer ID from URL...</div>';
        
        try {
            const response = await fetch('/api/admin/search-eventbrite-organizer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    organizer_url: currentUrl,
                    venue_name: venueName
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.organizers && data.organizers.length > 0) {
                const org = data.organizers[0];
                resultsDiv.innerHTML = `
                    <div style="padding: 10px; background: #d1fae5; border-radius: 4px; color: #065f46;">
                        ✅ Found organizer: ${org.name}
                        ${org.verified ? '' : '<br><small>⚠️ Could not verify via API, but URL format looks correct</small>'}
                    </div>
                `;
                return;
            }
        } catch (error) {
            console.error('Error extracting organizer:', error);
        }
    }
    
    if (!venueName) {
        alert('Please enter a venue name first, or paste an Eventbrite organizer URL in the Ticketing URL field');
        return;
    }
    
    // Get city name if available
    const citySelect = document.getElementById('venueCity');
    let cityName = '';
    if (citySelect && citySelect.value) {
        const selectedOption = citySelect.options[citySelect.selectedIndex];
        cityName = selectedOption.text.split(',')[0];
    }
    
    // Show loading state
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div style="padding: 10px; text-align: center; color: #666;">🔍 Searching Eventbrite...</div>';
    
    try {
        const response = await fetch('/api/admin/search-eventbrite-organizer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                venue_name: venueName,
                city_name: cityName
            })
        });
        
        const data = await response.json();
        
        // Eventbrite API no longer supports public search
        if (data.error === 'Eventbrite public search not available' || !data.success) {
            const searchUrl = data.search_url || `https://www.eventbrite.com/d/${cityName ? cityName.toLowerCase().replace(' ', '-') : 'dc--washington'}/${venueName.replace(/\s+/g, '-').toLowerCase()}/`;
            
            resultsDiv.innerHTML = `
                <div style="padding: 12px; background: #fef3c7; border-radius: 6px; border: 1px solid #fbbf24; color: #92400e;">
                    <div style="font-weight: 600; margin-bottom: 8px;">ℹ️ Manual Search Required</div>
                    <div style="font-size: 0.875rem; margin-bottom: 12px;">
                        Eventbrite API no longer provides public search. To find the organizer page:
                    </div>
                    <ol style="font-size: 0.875rem; margin: 0 0 12px 20px; padding: 0;">
                        <li>Search Eventbrite for "${venueName}" events</li>
                        <li>Click on any event from that venue</li>
                        <li>Click the organizer name to go to their page</li>
                        <li>Copy the organizer page URL</li>
                        <li>Paste it in the Ticketing URL field above</li>
                    </ol>
                    <div style="margin-top: 12px;">
                        <a href="${searchUrl}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #3b82f6; color: white; text-decoration: none; border-radius: 4px; font-size: 0.875rem;">
                            🔍 Open Eventbrite Search
                        </a>
                    </div>
                    <div style="margin-top: 8px; font-size: 0.75rem; color: #78716c;">
                        Or paste an Eventbrite organizer URL directly in the field above and click "Search Eventbrite" again to verify it.
                    </div>
                </div>
            `;
            return;
        }
        
        if (!data.organizers || data.organizers.length === 0) {
            resultsDiv.innerHTML = `
                <div style="padding: 10px; background: #fef3c7; border-radius: 4px; color: #92400e;">
                    ℹ️ No Eventbrite organizers found for "${venueName}". 
                    <br>You can manually enter the Eventbrite organizer page URL.
                </div>
            `;
            return;
        }
        
        // Display results (if we ever get any)
        let resultsHTML = `
            <div style="margin-top: 8px; padding: 12px; background: #f9fafb; border-radius: 6px; border: 1px solid #e5e7eb;">
                <div style="font-weight: 600; margin-bottom: 8px; color: #374151;">
                    Found ${data.organizers.length} organizer${data.organizers.length > 1 ? 's' : ''}:
                </div>
        `;
        
        data.organizers.forEach((organizer, index) => {
            const eventCount = organizer.event_count || 0;
            const sampleEvents = organizer.sample_events || [];
            
            resultsHTML += `
                <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer;" 
                     onclick="selectEventbriteOrganizerForAdd('${organizer.url.replace(/'/g, "\\'")}', '${organizer.name.replace(/'/g, "\\'")}')"
                     onmouseover="this.style.background='#f3f4f6'" 
                     onmouseout="this.style.background='white'">
                    <div style="font-weight: 500; color: #1f2937; margin-bottom: 4px;">
                        ${organizer.name}
                    </div>
                    <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 6px;">
                        ${eventCount} event${eventCount !== 1 ? 's' : ''} found
                    </div>
                    ${sampleEvents.length > 0 ? `
                        <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 4px;">
                            Sample: ${sampleEvents[0].name}
                        </div>
                    ` : ''}
                    <div style="font-size: 0.75rem; color: #3b82f6; margin-top: 4px;">
                        Click to use this organizer
                    </div>
                </div>
            `;
        });
        
        resultsHTML += '</div>';
        resultsDiv.innerHTML = resultsHTML;
        
    } catch (error) {
        console.error('Error searching Eventbrite:', error);
        resultsDiv.innerHTML = `
            <div style="padding: 10px; background: #fee2e2; border-radius: 4px; color: #991b1b;">
                ❌ Error: ${error.message}
            </div>
        `;
    }
}

// Functions to manage venue selection for main page filtering
// Make it globally accessible so tables.js can use it
window.getMainPageSelectedVenues = function() {
    const saved = localStorage.getItem('mainPageSelectedVenues');
    if (saved) {
        try {
            const ids = JSON.parse(saved);
            return new Set(ids);
        } catch (e) {
            return new Set();
        }
    }
    return new Set();
};

function getMainPageSelectedVenues() {
    return window.getMainPageSelectedVenues();
}

function saveMainPageSelectedVenues(venueIds) {
    localStorage.setItem('mainPageSelectedVenues', JSON.stringify(Array.from(venueIds)));
}

function toggleVenueForMainPage(venueId, isChecked) {
    const selectedVenues = getMainPageSelectedVenues();
    if (isChecked) {
        selectedVenues.add(venueId);
    } else {
        selectedVenues.delete(venueId);
    }
    saveMainPageSelectedVenues(selectedVenues);
    
    // Update select all checkbox state
    updateSelectAllVenuesForMainPageCheckbox();
}

function toggleSelectAllVenuesForMainPage(checkbox) {
    if (!window.allVenues) return;
    
    const selectedVenues = new Set();
    if (checkbox.checked) {
        // Select all visible venues
        window.allVenues.forEach(venue => selectedVenues.add(venue.id));
    }
    // If unchecked, selectedVenues stays empty
    
    saveMainPageSelectedVenues(selectedVenues);
    
    // Update all checkboxes
    const venueCheckboxes = document.querySelectorAll('.venue-main-page-checkbox');
    venueCheckboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
}

function updateSelectAllVenuesForMainPageCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAllVenuesForMainPage');
    if (!selectAllCheckbox || !window.allVenues) return;
    
    const selectedVenues = getMainPageSelectedVenues();
    const allSelected = window.allVenues.length > 0 && 
                       window.allVenues.every(venue => selectedVenues.has(venue.id));
    selectAllCheckbox.checked = allSelected;
}
