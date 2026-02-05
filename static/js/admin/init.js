document.addEventListener('DOMContentLoaded', function() {
    // Use window reference to ensure function is accessible
    if (typeof window.loadOverviewWithTimeout === 'function') {
        window.loadOverviewWithTimeout();
    } else if (typeof loadOverviewWithTimeout === 'function') {
        loadOverviewWithTimeout();
    }
    
    // Initialize all tables view mode on page load
    updateAllTablesViewMode();
    
    // Also load cities so they're available for venue dropdown and event filters
    loadCities().then(() => {
        // Repopulate event filters after cities are loaded
        if (window.allEvents) {
            populateEventFilters();
        }
        // All city dropdowns are populated by loadCities() -> populateAllCityDropdowns()
    });
    
    // Setup forms
    setupImageUploadForm();
    setupUrlScraperForm();
    
    // Add form submission handlers
    const addCityForm = document.getElementById('addCityForm');
    if (addCityForm) {
        addCityForm.addEventListener('submit', handleAddCity);
    }
    
    const addVenueForm = document.getElementById('addVenueForm');
    if (addVenueForm) {
        addVenueForm.addEventListener('submit', handleAddVenue);
    }
    
    // Add edit form submission handlers
    const editCityForm = document.getElementById('editCityForm');
    if (editCityForm) {
        editCityForm.addEventListener('submit', handleEditCity);
    }
    
    const editVenueForm = document.getElementById('editVenueForm');
    if (editVenueForm) {
        editVenueForm.addEventListener('submit', handleEditVenue);
    }
    
    const editEventForm = document.getElementById('editEventForm');
    if (editEventForm) {
        editEventForm.addEventListener('submit', handleEditEvent);
    }
    
    // Add search input event listeners for real-time filtering
    const citySearch = document.getElementById('citySearch');
    if (citySearch) {
        citySearch.addEventListener('input', applyCityFilters);
    }
    
    const venueSearch = document.getElementById('venueSearch');
    if (venueSearch) {
        venueSearch.addEventListener('input', applyVenueFilters);
    }
    
    const eventSearch = document.getElementById('eventSearch');
    if (eventSearch) {
        eventSearch.addEventListener('input', applyEventFilters);
    }
    
    // Add filter dropdown event listeners for real-time filtering
    const cityCountryFilter = document.getElementById('cityCountryFilter');
    if (cityCountryFilter) {
        cityCountryFilter.addEventListener('change', applyCityFilters);
    }
    
    const venueTypeFilter = document.getElementById('venueTypeFilter');
    if (venueTypeFilter) {
        venueTypeFilter.addEventListener('change', applyVenueFilters);
    }
    
    const venueCityFilter = document.getElementById('venueCityFilter');
    if (venueCityFilter) {
        venueCityFilter.addEventListener('change', applyVenueFilters);
    }
    
    const venueFeeFilter = document.getElementById('venueFeeFilter');
    if (venueFeeFilter) {
        venueFeeFilter.addEventListener('change', applyVenueFilters);
    }
    
    const venueClosureFilter = document.getElementById('venueClosureFilter');
    if (venueClosureFilter) {
        venueClosureFilter.addEventListener('change', applyVenueFilters);
    }
    
    const venueSortBy = document.getElementById('venueSortBy');
    if (venueSortBy) {
        venueSortBy.addEventListener('change', applyVenueFilters);
    }
    
    const eventTypeFilter = document.getElementById('eventTypeFilter');
    if (eventTypeFilter) {
        eventTypeFilter.addEventListener('change', applyEventFilters);
    }
    
    const eventVenueFilter = document.getElementById('eventVenueFilter');
    if (eventVenueFilter) {
        eventVenueFilter.addEventListener('change', applyEventFilters);
    }
    
    // Add source filter event listeners for real-time filtering
    const sourceSearch = document.getElementById('sourceSearch');
    if (sourceSearch) {
        sourceSearch.addEventListener('input', applySourceFilters);
    }
    
    const sourceTypeFilter = document.getElementById('sourceTypeFilter');
    if (sourceTypeFilter) {
        sourceTypeFilter.addEventListener('change', applySourceFilters);
    }
    
    const sourceCityFilter = document.getElementById('sourceCityFilter');
    if (sourceCityFilter) {
        sourceCityFilter.addEventListener('change', applySourceFilters);
    }
});

// Handle add city form submission
async function handleAddCity(event) {
    event.preventDefault();
    
    const formData = {
        name: document.getElementById('cityName').value.trim(),
        state: document.getElementById('cityState').value.trim(),
        country: document.getElementById('cityCountry').value.trim(),
        timezone: document.getElementById('cityTimezone').value.trim()
    };
    
    // Validate required fields
    if (!formData.name || !formData.country) {
        alert('City name and country are required');
        return;
    }
    
    try {
        
        const response = await fetch('/api/admin/add-city', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('City added successfully!');
            
            // Close modal
            closeModal('addCityModal');
            
            // Reload cities data
            await loadCities();
            
        } else {
            console.error('Error adding city:', result);
            alert('Error adding city: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Error adding city:', error);
        alert('Error adding city: ' + error.message);
    }
}

// Handle add venue form submission
async function handleAddVenue(event) {
    event.preventDefault();
    
    // Collect all form data dynamically
    const formData = {};
    const form = document.getElementById('addVenueForm');
    const formElements = form.querySelectorAll('input, select, textarea');
    
    formElements.forEach(element => {
        if (element.name && element.id) {
            let value = element.value.trim();
            
            // Handle number fields
            if (element.type === 'number' && value) {
                value = parseFloat(value);
            }
            
            // Handle city_id specifically
            if (element.name === 'city_id' && value) {
                value = parseInt(value);
            }
            
            // Only include non-empty values
            if (value !== '' && value !== null && value !== undefined) {
                formData[element.name] = value;
            }
        }
    });
    
    // Validate required fields
    if (!formData.name || !formData.venue_type || !formData.city_id) {
        alert('Venue name, type, and city are required');
        return;
    }
    
    try {
        console.log('Adding venue:', formData);
        
        const response = await fetch('/api/admin/add-venue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Venue added successfully!');
            
            // Close modal
            closeModal('addVenueModal');
            
            // Reload venues data
            await loadVenues();
            
        } else {
            console.error('Error adding venue:', result);
            alert('Error adding venue: ' + (result.error || 'Unknown error'));
        }
        
    } catch (error) {
        console.error('Error adding venue:', error);
        alert('Error adding venue: ' + error.message);
    }
}

// Handle edit form submissions
async function handleEditCity(event) {
    event.preventDefault();
    
    const editData = {
        id: parseInt(document.getElementById('editCityId').value),
        name: document.getElementById('editCityName').value.trim(),
        state: document.getElementById('editCityState').value.trim(),
        country: document.getElementById('editCityCountry').value.trim(),
        timezone: document.getElementById('editCityTimezone').value.trim()
    };
    
    try {
        const response = await fetch('/api/admin/edit-city', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(editData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('City updated successfully!');
            closeModal('editCityModal');
            loadCities();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error updating city: ' + error.message);
    }
}

async function handleEditVenue(event) {
    event.preventDefault();
    
    const editData = {
        id: parseInt(document.getElementById('editVenueId').value),
        name: document.getElementById('editVenueName').value.trim(),
        venue_type: document.getElementById('editVenueType').value.trim(),
        address: document.getElementById('editVenueAddress').value.trim(),
        description: document.getElementById('editVenueDescription').value.trim(),
        opening_hours: document.getElementById('editVenueHours').value.trim(),
        phone_number: document.getElementById('editVenuePhone').value.trim(),
        email: document.getElementById('editVenueEmail').value.trim(),
        website_url: document.getElementById('editVenueWebsite').value.trim(),
        ticketing_url: document.getElementById('editVenueTicketing').value.trim(),
        admission_fee: document.getElementById('editVenueAdmission').value.trim()
    };
    
    try {
        const response = await fetch('/api/admin/edit-venue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(editData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Venue updated successfully!');
            closeModal('editVenueModal');
            loadVenues();
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error updating venue: ' + error.message);
    }
}

async function handleEditEvent(event) {
    event.preventDefault();
    
    const cityId = document.getElementById('editEventCityId').value;
    const venueId = document.getElementById('editEventVenueId').value;
    
    if (!cityId) {
        alert('Please select a city');
        return;
    }
    
    const editData = {
        id: parseInt(document.getElementById('editEventId').value),
        title: document.getElementById('editEventTitle').value.trim(),
        description: document.getElementById('editEventDescription').value.trim(),
        start_date: document.getElementById('editEventStartDate').value,
        end_date: document.getElementById('editEventEndDate').value || null,
        start_time: document.getElementById('editEventStartTime').value || null,
        end_time: document.getElementById('editEventEndTime').value || null,
        event_type: document.getElementById('editEventType').value.trim(),
        city_id: cityId ? parseInt(cityId) : null,
        venue_id: venueId ? parseInt(venueId) : null
    };
    
    // Add exhibition-specific fields if event type is 'exhibition'
    if (editData.event_type === 'exhibition') {
        editData.exhibition_location = document.getElementById('editExhibitionLocation').value.trim();
        editData.curator = document.getElementById('editCurator').value.trim();
        const admissionPrice = document.getElementById('editAdmissionPrice').value;
        editData.admission_price = admissionPrice ? parseFloat(admissionPrice) : null;
        editData.artists = document.getElementById('editArtists').value.trim();
        editData.exhibition_type = document.getElementById('editExhibitionType').value.trim();
        editData.collection_period = document.getElementById('editCollectionPeriod').value.trim();
        const numArtworks = document.getElementById('editNumberOfArtworks').value;
        editData.number_of_artworks = numArtworks ? parseInt(numArtworks) : null;
        editData.opening_reception_date = document.getElementById('editOpeningReceptionDate').value || null;
        editData.opening_reception_time = document.getElementById('editOpeningReceptionTime').value || null;
        editData.is_permanent = document.getElementById('editIsPermanent').checked;
        editData.related_exhibitions = document.getElementById('editRelatedExhibitions').value.trim();
    }
    
    try {
        const response = await fetch('/api/admin/edit-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(editData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('Event updated successfully!');
            closeModal('editEventModal');
            loadEvents();
            // Refresh overview stats
            setTimeout(() => {
                console.log('🔄 Refreshing overview after event creation...');
                if (typeof window.loadOverview === 'function') {
                    window.loadOverview().catch(err => console.error('Error refreshing overview:', err));
                } else if (typeof loadOverview === 'function') {
                    loadOverview().catch(err => console.error('Error refreshing overview:', err));
                }
            }, 500);
        } else {
            alert('Error: ' + result.error);
        }
    } catch (error) {
        alert('Error updating event: ' + error.message);
    }
}

function generateSourceDetailsHTML(source) {
    // Helper function to format timestamps (remove seconds, make reader-friendly)
    const formatTimestamp = (timestamp) => {
        if (!timestamp) return '';
        try {
            // Normalize UTC timestamp (append 'Z' if missing timezone)
            const normalizedTimestamp = normalizeUTCTimestamp(timestamp);
            const date = new Date(normalizedTimestamp);
            const options = { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            };
            return date.toLocaleString(undefined, options);
        } catch (e) {
            return timestamp;
        }
    };
    
    // Helper function to add field only if value exists
    const addField = (label, value, isLink = false, isTimestamp = false) => {
        if (!value || value === 'N/A' || value === '') return '';
        let displayValue = value;
        if (isTimestamp) {
            displayValue = formatTimestamp(value);
        } else if (isLink) {
            displayValue = `<a href="${value}" target="_blank" style="color: #1976d2; word-break: break-all;">${value}</a>`;
        }
        return `<div style="margin-bottom: 6px; font-size: 0.875rem; line-height: 1.4;"><strong>${label}:</strong> ${displayValue}</div>`;
    };
    
    let html = `
        <div class="source-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📱 Basic Information</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 6px; font-size: 0.875rem;"><strong>ID:</strong> ${source.id}</div>
                    ${addField('Name', source.name)}
                    ${addField('Handle', source.handle)}
                    ${addField('Type', source.source_type)}
                    ${addField('Description', source.description)}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🔗 Links & Contact</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('URL', source.url, true)}
                    ${addField('Email', source.email)}
                    ${addField('Phone', source.phone)}
                    ${addField('Contact Person', source.contact_person)}
                </div>
            </div>
        </div>
        
        <div class="source-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🎯 Event Information</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Event Types', source.event_types)}
                    ${addField('Frequency', source.frequency)}
                    ${addField('Language', source.language)}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📊 Status & Stats</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 6px; font-size: 0.875rem;"><strong>Active:</strong> ${source.is_active ? 'Yes' : 'No'}</div>
                    ${addField('Last Scraped', source.last_scraped_at)}
                    ${addField('Events Count', source.events_count)}
                </div>
            </div>
        </div>
        
        <div>
            <h4 style="margin-bottom: 10px; color: #4a5568;">⚙️ System Information</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                ${addField('Created', source.created_at, false, true)}
                ${addField('Updated', source.updated_at, false, true)}
            </div>
        </div>
    `;
    
    return html;
}

async function autoFillFromUrl() {
    const url = document.getElementById('eventUrl').value;
    
    if (!url) {
        alert('Please enter a URL first');
        return;
    }
    
    // Show loading indicator
    const autoFillBtn = document.getElementById('autoFillBtn');
    const originalText = autoFillBtn.textContent;
    autoFillBtn.textContent = '⏳ Extracting...';
    autoFillBtn.disabled = true;
    
    try {
        
        const response = await fetch('/api/admin/extract-event-from-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });
        
        const result = await response.json();
        console.log('Extraction result:', result);
        
        if (response.ok) {
            // Show extracted data preview
            displayExtractedData(result);
        } else {
            alert(`Error: ${result.error || 'Failed to extract data from URL'}`);
        }
    } catch (error) {
        console.error('Error extracting from URL:', error);
        alert('An error occurred while extracting data from the URL: ' + error.message);
    } finally {
        // Restore button
        autoFillBtn.textContent = originalText;
        autoFillBtn.disabled = false;
    }
}

function displayExtractedData(data) {
    
    // Show the preview section
    document.getElementById('urlExtractedPreview').style.display = 'block';
    
    // Add extraction method indicator
    let extractionBadge = '';
    if (data.llm_extracted) {
        const confidenceColor = {
            'high': '#10b981',
            'medium': '#f59e0b',
            'low': '#ef4444'
        }[data.confidence || 'medium'];
        extractionBadge = `<span style="background: ${confidenceColor}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">🤖 AI Extracted (${data.confidence || 'medium'} confidence)</span>`;
    }
    
    // Display summary
    const content = document.getElementById('urlExtractedContent');
    content.innerHTML = `
        <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px 12px;">
            <strong>Title:</strong> <span>${data.title || 'Not found'}</span>
            <strong>Description:</strong> 
            <div>
                <span id="preview-desc" class="description-text collapsed">${data.description || 'Not found'}</span>
                ${data.description && data.description.length > 100 ? `<a href="javascript:void(0)" class="more-link" onclick="toggleAdminDescription('preview-desc', this)">More</a>` : ''}
            </div>
            <strong>Schedule:</strong> <span>${data.schedule_info || 'Not detected'}</span>
            <strong>Start Time:</strong> <span>${data.start_time || 'Not found'}</span>
            <strong>End Time:</strong> <span>${data.end_time || 'Not found'}</span>
            <strong>Location:</strong> <span>${data.location || 'Not found'}</span>
            <strong>Venue:</strong> <span>${data.venue_id ? '✅ Auto-matched' : '❌ Not matched'}</span>
            <strong>City:</strong> <span>${data.city_id ? '✅ Auto-matched' : '❌ Not matched'}</span>
            <strong>Image:</strong> <span>${data.image_url ? '✅ Found' : '❌ Not found'}</span>
            ${data.is_registration_required !== undefined ? `<strong>Registration Required:</strong> <span>${data.is_registration_required ? 'Yes' : 'No'}</span>` : ''}
            ${data.registration_info ? `<strong>Registration Info:</strong> <span>${data.registration_info}</span>` : ''}
            ${data.registration_url ? `<strong>Registration URL:</strong> <span><a href="${data.registration_url}" target="_blank">${data.registration_url.substring(0, 50)}...</a></span>` : ''}
            ${data.price !== undefined ? `<strong>Price:</strong> <span>${data.price === 0 || data.price === '0' || data.price === 'Free' ? 'Free' : '$' + data.price}</span>` : ''}
            ${data.llm_extracted ? `<strong>Extraction:</strong> ${extractionBadge}` : ''}
        </div>
    `;
    
    // Fill editable fields
    document.getElementById('extractedTitle').value = data.title || '';
    document.getElementById('extractedDescription').value = data.description || '';
    document.getElementById('extractedStartTime').value = data.start_time || '';
    document.getElementById('extractedEndTime').value = data.end_time || '';
    document.getElementById('extractedLocation').value = data.location || '';
    document.getElementById('extractedSchedule').value = data.schedule_info || '';
    
    // Store extracted data for later use
    window.extractedEventData = data;
    
    console.log('💾 Stored extracted data:', data);
    
    // Show the Apply button if we have venue or city data
    if (data.venue_id || data.city_id) {
        document.getElementById('applyToFormSection').style.display = 'block';
    }
}

function applyExtractedToForm() {
    const data = window.extractedEventData;
    if (!data) {
        alert('No extracted data available');
        return;
    }
    
    // Apply venue
    if (data.venue_id) {
        const venueSelect = document.getElementById('urlVenueSelect');
        if (venueSelect) {
            venueSelect.value = data.venue_id;
        }
    }
    
    // Apply city
    if (data.city_id) {
        const citySelect = document.getElementById('urlCitySelect');
        if (citySelect) {
            citySelect.value = data.city_id;
            console.log('✅ Applied city ID:', data.city_id);
        }
    }
    
    // Visual confirmation
    alert('✅ Venue and City have been applied to the form!');
}

function openUrlScraperModal() {
    document.getElementById('urlScraperModal').style.display = 'block';
    document.getElementById('scrapedDataDisplay').style.display = 'none';
    document.getElementById('urlExtractedPreview').style.display = 'none';
    document.getElementById('urlScraperForm').reset();
    
    // Attach event listener to Auto-Fill button
    const autoFillBtn = document.getElementById('autoFillBtn');
    if (autoFillBtn) {
        // Remove any existing listeners by cloning the button
        const newAutoFillBtn = autoFillBtn.cloneNode(true);
        autoFillBtn.parentNode.replaceChild(newAutoFillBtn, autoFillBtn);
        // Add the event listener
        newAutoFillBtn.addEventListener('click', autoFillFromUrl);
    }
    
    // Store references for later auto-selection
    window.venueDropdownLoaded = false;
    window.cityDropdownLoaded = false;
    
    // Populate venue dropdown
    fetch('/api/admin/venues')
        .then(response => response.json())
        .then(venues => {
            const select = document.getElementById('urlVenueSelect');
            select.innerHTML = '<option value="">No specific venue (city-wide event)</option>';
            
            // Check if venues is an array
            if (Array.isArray(venues)) {
                venues.forEach(venue => {
                    const option = document.createElement('option');
                    option.value = venue.id;
                    option.textContent = `${venue.name} (${venue.city_name || 'No city'})`;
                    select.appendChild(option);
                });
            } else {
                console.error('Venues response is not an array:', venues);
            }
            
            window.venueDropdownLoaded = true;
            // Try auto-selection if we have extracted data
            if (window.extractedEventData && window.extractedEventData.venue_id) {
                select.value = window.extractedEventData.venue_id;
            }
        })
        .catch(error => console.error('Error loading venues:', error));
    
    // Populate city dropdown using cached cities or fetch if needed
    if (window.allCities) {
        populateUrlCitySelector();
    } else {
        fetch('/api/admin/cities')
            .then(response => response.json())
            .then(cities => {
                window.allCities = cities;
                populateUrlCitySelector();
            })
            .catch(error => console.error('Error loading cities:', error));
    }
}

function openImageUploadModal() {
    console.log('Opening image upload modal...');
    document.getElementById('imageUploadModal').style.display = 'block';
    document.getElementById('extractedDataDisplay').style.display = 'none';
    document.getElementById('imageUploadForm').style.display = 'block';
    document.getElementById('imageUploadForm').reset();
    
    // Hide sticky footer when opening modal
    const stickyFooter = document.getElementById('imageUploadStickyFooter');
    if (stickyFooter) {
        stickyFooter.style.display = 'none';
    }
    
    // Reset padding on scrollable content
    const scrollableContent = document.getElementById('imageUploadScrollableContent');
    if (scrollableContent) {
        scrollableContent.style.paddingBottom = '20px';
    }
    
    // Clear any previous file selection
    const fileInput = document.getElementById('eventImage');
    if (fileInput) {
        fileInput.value = '';
    }
    
    // Reset manual input fields
    document.getElementById('manualEventTitle').value = '';
    document.getElementById('manualEventDescription').value = '';
    document.getElementById('manualStartDate').value = '';
    document.getElementById('manualEndDate').value = '';
    document.getElementById('manualStartTime').value = '';
    document.getElementById('manualEndTime').value = '';
    document.getElementById('manualEventType').value = 'tour';
    document.getElementById('manualStartLocation').value = '';
    document.getElementById('manualEndLocation').value = '';
    document.getElementById('manualPrice').value = '';
    document.getElementById('manualUrl').value = '';
    document.getElementById('manualCityId').value = '';
    document.getElementById('manualEventSource').value = '';
    document.getElementById('manualSourceUrl').value = '';
    // Reset social media fields
    document.getElementById('manualSocialMediaPlatform').value = '';
    document.getElementById('manualSocialMediaHandle').value = '';
    document.getElementById('manualSocialMediaPageName').value = '';
    document.getElementById('manualSocialMediaPostedBy').value = '';
    document.getElementById('manualSocialMediaUrl').value = '';
    
    // Populate city dropdown with a small delay to ensure modal is fully rendered
    setTimeout(() => {
        populateCitySelect('manualCityId');
        
        // Add listener for city change to populate venues
        const citySelect = document.getElementById('manualCityId');
        if (citySelect) {
            citySelect.addEventListener('change', function() {
                const cityId = this.value;
                if (cityId) {
                    populateVenuesForCity(cityId, 'manualVenueId');
                } else {
                    const venueSelect = document.getElementById('manualVenueId');
                    if (venueSelect) {
                        venueSelect.innerHTML = '<option value="">Select Venue (optional)</option>';
                    }
                }
            });
        }
    }, 100);
}

async function populateVenuesForCity(cityId, selectId) {
    const venueSelect = document.getElementById(selectId);
    if (!venueSelect) {
        console.error(`Venue select element not found: ${selectId}`);
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/venues?city_id=${cityId}`);
        const venues = await response.json();
        
        venueSelect.innerHTML = '<option value="">Select Venue (optional)</option>';
        venues.forEach(venue => {
            const option = document.createElement('option');
            option.value = venue.id;
            option.textContent = venue.name;
            venueSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading venues:', error);
        venueSelect.innerHTML = '<option value="">Error loading venues</option>';
    }
}

function openCreateFromVenueModal() {
    document.getElementById('createFromVenueModal').style.display = 'block';
    populateVenueSelect();
}

function populateVenueSelect() {
    const venueSelect = document.getElementById('venueSelect');
    venueSelect.innerHTML = '<option value="">Choose a venue...</option>';
    
    if (window.allVenues) {
        window.allVenues.forEach(venue => {
            const option = document.createElement('option');
            option.value = venue.id;
            option.textContent = `${venue.name} (${venue.city_name || 'Unknown City'})`;
            venueSelect.appendChild(option);
        });
    }
}

// Handle time period selection
document.getElementById('timePeriod')?.addEventListener('change', function() {
    const customFields = document.getElementById('customPeriodFields');
    if (this.value === 'custom') {
        customFields.style.display = 'block';
    } else {
        customFields.style.display = 'none';
    }
});

// Handle URL scraper form submission
function setupUrlScraperForm() {
    const urlScraperForm = document.getElementById('urlScraperForm');
    if (urlScraperForm) {
        urlScraperForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const url = document.getElementById('eventUrl').value;
            const venueId = document.getElementById('urlVenueSelect').value;
            const cityId = document.getElementById('urlCitySelect').value;
            const timePeriod = document.getElementById('timePeriod').value;
            let startDate = null;
            let endDate = null;
            
            if (!cityId) {
                alert('Please select a city');
                return;
            }
            
            if (timePeriod === 'custom') {
                startDate = document.getElementById('customStartDate').value;
                endDate = document.getElementById('customEndDate').value;
                if (!startDate || !endDate) {
                    alert('Please specify custom period dates');
                    return;
                }
            }
            
            // Use edited extracted data if available
            const extractedData = window.extractedEventData || {};
            const editedTitle = document.getElementById('extractedTitle').value;
            const editedDescription = document.getElementById('extractedDescription').value;
            const editedStartTime = document.getElementById('extractedStartTime').value;
            const editedEndTime = document.getElementById('extractedEndTime').value;
            const editedLocation = document.getElementById('extractedLocation').value;
            
            const requestData = {
                url: url,
                venue_id: venueId ? parseInt(venueId) : null,
                city_id: parseInt(cityId),
                time_period: timePeriod,
                start_date: startDate,
                end_date: endDate,
                // Include edited extracted data
                title: editedTitle || extractedData.title,
                description: editedDescription || extractedData.description,
                start_time: editedStartTime || extractedData.start_time,
                end_time: editedEndTime || extractedData.end_time,
                location: editedLocation || extractedData.location,
                image_url: extractedData.image_url,
                schedule_info: extractedData.schedule_info,
                days_of_week: extractedData.days_of_week
            };
            
            try {
                showLoadingState('Scraping URL and creating events...');
                
                const response = await fetch('/api/admin/scrape-event-from-url', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                const result = await response.json();
                hideLoadingState();
                
                if (response.ok) {
                    displayScrapedData(result);
                    await loadEvents(); // Refresh events table
                } else {
                    alert(`Error: ${result.error || 'Failed to scrape URL'}`);
                }
            } catch (error) {
                hideLoadingState();
                console.error('Error scraping URL:', error);
                alert('An error occurred while scraping the URL');
            }
        });
    }
}

function displayScrapedData(result) {
    const display = document.getElementById('scrapedDataDisplay');
    const content = document.getElementById('scrapedDataContent');
    
    let html = `
        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
            <h5 style="color: #10b981; margin-bottom: 10px;">✅ Successfully Created ${result.events_created || 0} Event(s)</h5>
    `;
    
    if (result.events && result.events.length > 0) {
        result.events.forEach((event, index) => {
            html += `
                <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; margin-bottom: 8px;">
                    <strong>Event ${index + 1}:</strong> ${event.title || 'Untitled'}<br>
                    <small>📅 ${event.start_date || 'No date'} ${event.start_time || ''}</small><br>
                    ${event.description ? `
                        <div style="margin-top: 4px;">
                            <small id="event-res-${index}" class="description-text collapsed">📝 ${event.description}</small>
                            ${event.description.length > 100 ? `<a href="javascript:void(0)" class="more-link" onclick="toggleAdminDescription('event-res-${index}', this)">More</a>` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }
    
    if (result.schedule_info) {
        html += `
            <div style="background: #e3f2fd; padding: 10px; border-radius: 6px; margin-top: 10px;">
                <strong>📅 Schedule Detected:</strong><br>
                <small>${result.schedule_info}</small>
            </div>
        `;
    }
    
    html += '</div>';
    content.innerHTML = html;
    display.style.display = 'block';
}

// Populate quick URL city selector
async function populateQuickUrlCitySelector() {
    try {
        const citySelect = document.getElementById('quickUrlCitySelect');
        if (!citySelect) return;
        
        // Use cached cities if available, otherwise fetch
        let cities = window.allCities;
        if (!cities) {
            const response = await fetch('/api/admin/cities');
            cities = await response.json();
            window.allCities = cities;
        }
        
        // Clear existing options except the first one
        citySelect.innerHTML = '<option value="">Select City...</option>';
        
        // Add cities
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.id;
            option.textContent = city.name + (city.state ? `, ${city.state}` : '');
            citySelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error populating quick URL city selector:', error);
    }
}

async function quickCreateEventFromUrl() {
    const urlInput = document.getElementById('quickEventUrl');
    const statusDiv = document.getElementById('quickUrlStatus');
    const url = urlInput.value.trim();
    
    if (!url) {
        statusDiv.innerHTML = '<span style="color: #ef4444;">❌ Please enter a URL</span>';
        return;
    }
    
    // Validate URL format
    try {
        new URL(url);
    } catch (e) {
        statusDiv.innerHTML = '<span style="color: #ef4444;">❌ Invalid URL format</span>';
        return;
    }
    
    statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Extracting event details...</span>';
    
    try {
        // Step 1: Extract event data
        const extractResponse = await fetch('/api/admin/extract-event-from-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        
        const extractedData = await extractResponse.json();
        
        if (!extractResponse.ok) {
            statusDiv.innerHTML = `<span style="color: #ef4444;">❌ Extraction failed: ${extractedData.error || 'Unknown error'}</span>`;
            return;
        }
        
        if (!extractedData.title) {
            statusDiv.innerHTML = '<span style="color: #ef4444;">❌ Could not extract event title. Try the advanced "From URL" option.</span>';
            return;
        }
        
        statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Creating event...</span>';
        
        // Step 2: Auto-detect city and venue
        let cityId = extractedData.city_id;
        let venueId = extractedData.venue_id;
        
        // If no city detected, try to detect from URL
        if (!cityId) {
            const citiesResponse = await fetch('/api/admin/cities');
            const cities = await citiesResponse.json();
            
            // Check for NGA (National Gallery of Art) - DC
            if (url.includes('nga.gov') || url.toLowerCase().includes('national gallery')) {
                const dcCity = cities.find(c => 
                    c.name.toLowerCase().includes('washington') || 
                    c.name.toLowerCase().includes('dc')
                );
                if (dcCity) {
                    cityId = dcCity.id;
                    statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Auto-detected Washington DC...</span>';
                    
                    // Try to find NGA venue
                    if (!venueId) {
                        const venuesResponse = await fetch('/api/admin/venues');
                        const venues = await venuesResponse.json();
                        const ngaVenue = venues.find(v => 
                            v.name.toLowerCase().includes('national gallery') && 
                            (v.city_id == cityId || v.city_name?.toLowerCase().includes('washington'))
                        );
                        if (ngaVenue) {
                            venueId = ngaVenue.id;
                        }
                    }
                }
            }
            // Check for SAAM (Smithsonian American Art Museum) - Washington DC
            else if (url.includes('americanart.si.edu')) {
                const dcCity = cities.find(c => 
                    c.name.toLowerCase().includes('washington') || 
                    c.name.toLowerCase().includes('dc')
                );
                if (dcCity) {
                    cityId = dcCity.id;
                    statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Auto-detected Washington DC...</span>';
                    if (!venueId) {
                        const venuesResponse = await fetch('/api/admin/venues');
                        const venues = await venuesResponse.json();
                        const saamVenue = venues.find(v => 
                            (v.name.toLowerCase().includes('smithsonian american art') || v.name.toLowerCase().includes('american art museum')) &&
                            (v.city_id == cityId || v.city_name?.toLowerCase().includes('washington'))
                        );
                        if (saamVenue) venueId = saamVenue.id;
                    }
                }
            }
            // Check for OCMA (Orange County Museum of Art) - Irvine
            else if (url.includes('ocma.art') || url.toLowerCase().includes('orange county museum')) {
                const irvineCity = cities.find(c => 
                    c.name.toLowerCase().includes('irvine') || 
                    c.name.toLowerCase().includes('orange county')
                );
                if (irvineCity) {
                    cityId = irvineCity.id;
                    statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Auto-detected Irvine...</span>';
                    
                    // Try to find OCMA venue
                    if (!venueId) {
                        const venuesResponse = await fetch('/api/admin/venues');
                        const venues = await venuesResponse.json();
                        const ocmaVenue = venues.find(v => 
                            (v.name.toLowerCase().includes('ocma') || v.name.toLowerCase().includes('orange county museum')) && 
                            (v.city_id == cityId || v.city_name?.toLowerCase().includes('irvine'))
                        );
                        if (ocmaVenue) {
                            venueId = ocmaVenue.id;
                        }
                    }
                }
            }
        }
        
        // If still no city, check if user selected one from dropdown
        if (!cityId) {
            const citySelect = document.getElementById('quickUrlCitySelect');
            if (citySelect && citySelect.value) {
                cityId = parseInt(citySelect.value);
                statusDiv.innerHTML = '<span style="color: #3b82f6;">⏳ Using selected city...</span>';
            } else {
                statusDiv.innerHTML = '<span style="color: #ef4444;">❌ Please select a city from the dropdown above, or use the advanced "From URL" option.</span>';
                return;
            }
        }
        
        // Step 3: Determine date and time from extracted data or URL
        let startDate = extractedData.start_date;
        let startTime = extractedData.start_time;
        let endTime = extractedData.end_time;
        
        // Try to extract date and time from URL as fallback (e.g., evd=202601311530 = YYYYMMDDHHMM)
        const evdMatch = url.match(/evd=(\d{12})/); // 12 digits: YYYYMMDDHHMM
        if (evdMatch) {
            const timestamp = evdMatch[1];
            // Extract date (first 8 digits) - use if not already extracted
            if (!startDate) {
                const year = timestamp.substring(0, 4);
                const month = timestamp.substring(4, 6);
                const day = timestamp.substring(6, 8);
                startDate = `${year}-${month}-${day}`;
            }
            
            // Extract time (last 4 digits: HHMM) - use if not already extracted from page
            if (!startTime) {
                const hour = timestamp.substring(8, 10);
                const minute = timestamp.substring(10, 12);
                startTime = `${hour}:${minute}:00`;
            }
            
            // If no end time extracted, calculate default (add 90 minutes for typical event)
            if (!endTime && startTime) {
                // Parse start time to calculate end time
                const timeMatch = startTime.match(/(\d{2}):(\d{2})/);
                if (timeMatch) {
                    const startHour = parseInt(timeMatch[1]);
                    const startMin = parseInt(timeMatch[2]);
                    const totalMinutes = startHour * 60 + startMin + 90; // Add 90 minutes
                    const endHour = Math.floor(totalMinutes / 60) % 24;
                    const endMin = totalMinutes % 60;
                    endTime = `${String(endHour).padStart(2, '0')}:${String(endMin).padStart(2, '0')}:00`;
                }
            }
        } else if (!startDate) {
            // Try to extract just date (8 digits)
            const dateMatch = url.match(/evd=(\d{8})/);
            if (dateMatch) {
                const dateStr = dateMatch[1]; // YYYYMMDD
                startDate = `${dateStr.substring(0,4)}-${dateStr.substring(4,6)}-${dateStr.substring(6,8)}`;
            } else {
                // Use today
                const today = new Date();
                startDate = today.toISOString().split('T')[0];
            }
        }
        
        // If we have start time but no end time, add default duration (90 minutes)
        if (startTime && !endTime) {
            const timeMatch = startTime.match(/(\d{2}):(\d{2})/);
            if (timeMatch) {
                const startHour = parseInt(timeMatch[1]);
                const startMin = parseInt(timeMatch[2]);
                const totalMinutes = startHour * 60 + startMin + 90; // Add 90 minutes
                const endHour = Math.floor(totalMinutes / 60) % 24;
                const endMin = totalMinutes % 60;
                endTime = `${String(endHour).padStart(2, '0')}:${String(endMin).padStart(2, '0')}:00`;
            }
        }
        
        // Step 4: Prepare location (meeting point)
        // The location should be the specific meeting point (e.g., "West Building Main Floor, Gallery 40")
        // The venue is set separately (e.g., "National Gallery of Art")
        let meetingLocation = extractedData.location || extractedData.start_location || '';
        
        // For NGA events, try to extract location from description if not found
        if (!meetingLocation && url.includes('nga.gov')) {
            // Look for patterns like "West Building", "Gallery 40", etc. in description
            const desc = extractedData.description || '';
            const locationPatterns = [
                /(West Building[^.]*)/i,
                /(East Building[^.]*)/i,
                /(Gallery\s+\d+[^.]*)/i,
                /(Main Floor[^.]*)/i,
                /(West Building Main Floor, Gallery \d+)/i
            ];
            
            for (const pattern of locationPatterns) {
                const match = desc.match(pattern);
                if (match) {
                    meetingLocation = match[1].trim();
                    break;
                }
            }
            
            // Also check title for location hints
            if (!meetingLocation && extractedData.title) {
                const titleMatch = extractedData.title.match(/(West Building|East Building|Gallery \d+)/i);
                if (titleMatch) {
                    meetingLocation = titleMatch[1];
                }
            }
        }
        
        // Step 5: Create the event
        // Use 'custom' time_period if we have a specific date, otherwise use 'today'
        const timePeriod = startDate ? 'custom' : 'today';
        
        const createData = {
            url: url,
            venue_id: venueId || null,
            city_id: parseInt(cityId),
            time_period: timePeriod,
            start_date: startDate || null, // Use extracted date if available
            end_date: startDate || null,   // Use extracted date if available
            title: extractedData.title,
            description: extractedData.description || '',
            start_time: startTime || extractedData.start_time || null,
            end_time: endTime || extractedData.end_time || null,
            location: meetingLocation, // This becomes start_location in the event
            image_url: extractedData.image_url || null,
            schedule_info: extractedData.schedule_info || null,
            // Include registration and price fields from extracted data
            // Convert price to number if it's "Free" or 0
            price: (extractedData.price !== undefined && extractedData.price !== null) 
                ? (extractedData.price === 'Free' || extractedData.price === 0 || extractedData.price === '0' ? 0.0 : extractedData.price)
                : null,
            admission_price: (extractedData.admission_price !== undefined && extractedData.admission_price !== null)
                ? (extractedData.admission_price === 'Free' || extractedData.admission_price === 0 || extractedData.admission_price === '0' ? 0.0 : extractedData.admission_price)
                : null,
            is_registration_required: extractedData.is_registration_required || false,
            registration_url: extractedData.registration_url || null,
            registration_info: extractedData.registration_info || null
        };
        
        const createResponse = await fetch('/api/admin/scrape-event-from-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(createData)
        });
        
        const createResult = await createResponse.json();
        
        if (createResponse.ok) {
            const eventCount = createResult.events_created || 0;
            statusDiv.innerHTML = `<span style="color: #10b981;">✅ Successfully created ${eventCount} event(s)!</span>`;
            urlInput.value = ''; // Clear input
            
            // Refresh events table
            await loadEvents();
            
            // Clear status after 5 seconds
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        } else {
            statusDiv.innerHTML = `<span style="color: #ef4444;">❌ Failed to create event: ${createResult.error || 'Unknown error'}</span>`;
        }
        
    } catch (error) {
        console.error('Quick create error:', error);
        statusDiv.innerHTML = `<span style="color: #ef4444;">❌ Error: ${error.message}</span>`;
    }
}

// Handle image upload form submission
function setupImageUploadForm() {
    const imageUploadForm = document.getElementById('imageUploadForm');
    if (imageUploadForm) {
        imageUploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Form submission started');
            
            const formData = new FormData();
            const imageFile = document.getElementById('eventImage').files[0];
            
            if (!imageFile) {
                alert('Please select an image file');
                return;
            }
            
            formData.append('image', imageFile);
            
            // Add OCR engine selection
            const ocrEngine = document.getElementById('ocrEngine').value;
            formData.append('ocr_engine', ocrEngine);
            
            try {
                const response = await fetch('/api/admin/upload-event-image', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    if (result.extracted_data) {
                        displayExtractedData(result.extracted_data);
                    } else {
                        console.error('No extracted_data in result:', result);
                    }
                } else {
                    console.error('Upload failed:', result);
                    alert('Error processing image: ' + result.error);
                }
            } catch (error) {
                console.error('Upload error:', error);
                alert('Error uploading image: ' + error.message);
            }
        });
    } else {
        console.error('imageUploadForm not found');
    }
}

function displayExtractedData(data) {
    const displayDiv = document.getElementById('extractedDataDisplay');
    const contentDiv = document.getElementById('extractedDataContent');
    
    if (!displayDiv || !contentDiv) {
        console.error('Required elements not found:', { displayDiv, contentDiv });
        return;
    }
    
    // Store extracted data for later use (including venue_id)
    window.extractedEventData = data;
    // First, populate the form fields with extracted data
    populateManualFields(data);
    
    let html = '<div class="extracted-data-grid">';
    
    if (data.title) html += `<div><strong>Title:</strong> ${data.title}</div>`;
    if (data.description) html += `<div><strong>Description:</strong> ${data.description}</div>`;
    if (data.start_date) html += `<div><strong>Start Date:</strong> ${data.start_date}</div>`;
    if (data.end_date) html += `<div><strong>End Date:</strong> ${data.end_date}</div>`;
    if (data.start_time) html += `<div><strong>Start Time:</strong> ${data.start_time}</div>`;
    if (data.end_time) html += `<div><strong>End Time:</strong> ${data.end_time}</div>`;
    if (data.location) html += `<div><strong>Location:</strong> ${data.location}</div>`;
    if (data.start_location) html += `<div><strong>Start Location:</strong> ${data.start_location}</div>`;
    if (data.end_location) html += `<div><strong>End Location:</strong> ${data.end_location}</div>`;
    if (data.event_type) html += `<div><strong>Event Type:</strong> ${data.event_type}</div>`;
    if (data.price) html += `<div><strong>Price:</strong> $${data.price}</div>`;
    if (data.organizer) html += `<div><strong>Organizer:</strong> ${data.organizer}</div>`;
    // Deduplicate URLs - show each unique URL once
    const normalizeUrl = (u) => (u || '').trim().replace(/\/$/, '');
    const seen = new Set();
    const uniqueUrls = [];
    [[data.url, 'URL'], [data.registration_url, 'Registration URL'], [data.social_media_url, 'Social Media URL'], [data.source_url, 'Source URL']].forEach(([url, label]) => {
        const key = normalizeUrl(url);
        if (url && key && !seen.has(key)) { seen.add(key); uniqueUrls.push({url, label}); }
    });
    uniqueUrls.forEach(({url, label}) => {
        html += `<div><strong>${uniqueUrls.length > 1 ? label : 'URL'}:</strong> <a href="${url}" target="_blank">${url}</a></div>`;
    });
    if (data.is_online !== undefined) html += `<div><strong>Online/Virtual:</strong> ${data.is_online ? 'Yes' : 'No'}</div>`;
    if (data.is_registration_required !== undefined) html += `<div><strong>Registration Required:</strong> ${data.is_registration_required ? 'Yes' : 'No'}</div>`;
    if (data.registration_info) html += `<div><strong>Registration Info:</strong> ${data.registration_info}</div>`;
    if (data.city) html += `<div><strong>City:</strong> ${data.city}</div>`;
    if (data.state) html += `<div><strong>State:</strong> ${data.state}</div>`;
    // Social media fields (non-URL)
    if (data.social_media_platform) html += `<div><strong>Social Media Platform:</strong> ${data.social_media_platform}</div>`;
    if (data.social_media_handle) html += `<div><strong>Social Media Handle:</strong> @${data.social_media_handle}</div>`;
    if (data.social_media_page_name) html += `<div><strong>Page/Group Name:</strong> ${data.social_media_page_name}</div>`;
    if (data.social_media_posted_by) html += `<div><strong>Posted By:</strong> ${data.social_media_posted_by}</div>`;
    if (data.country) html += `<div><strong>Country:</strong> ${data.country}</div>`;
    if (data.city_id) html += `<div><strong>City ID:</strong> ${data.city_id}</div>`;
    if (data.source) html += `<div><strong>Source:</strong> ${data.source}</div>`;
    if (data.instagram_handle) html += `<div><strong>Instagram Handle:</strong> @${data.instagram_handle}</div>`;
    
    html += `<div><strong>Confidence:</strong> ${Math.round(data.confidence * 100)}%</div>`;
    html += '</div>';
    
    contentDiv.innerHTML = html;
    displayDiv.style.display = 'block';
    
    // Show the sticky footer with Create Event button
    const stickyFooter = document.getElementById('imageUploadStickyFooter');
    if (stickyFooter) {
        stickyFooter.style.display = 'block';
        
        // On mobile, ensure footer is fixed at bottom
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            stickyFooter.style.position = 'fixed';
            stickyFooter.style.bottom = '0';
            stickyFooter.style.left = '0';
            stickyFooter.style.right = '0';
            stickyFooter.style.width = '100%';
            stickyFooter.style.zIndex = '1000';
        }
    }
    
    // Hide the upload form to make room for extracted data
    const uploadForm = document.getElementById('imageUploadForm');
    if (uploadForm) {
        uploadForm.style.display = 'none';
    }
    
    // Add padding to scrollable content to prevent content from being hidden behind footer
    const scrollableContent = document.getElementById('imageUploadScrollableContent');
    if (scrollableContent && stickyFooter) {
        const isMobile = window.innerWidth <= 768;
        scrollableContent.style.paddingBottom = isMobile ? '100px' : '80px'; // More space on mobile
    }
    
    // Scroll to top of extracted data section
    setTimeout(() => {
        displayDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
    
    // Populate manual input fields with extracted data (second time for safety)
    populateManualFields(data);
    
    // Store extracted data for event creation
    window.extractedEventData = data;
}

async function populateCitySelect(selectId, targetCity = null, targetState = null) {
    const select = document.getElementById(selectId);
    if (!select) {
        console.error(`Element with id '${selectId}' not found`);
        return;
    }
    
    try {
        const response = await fetch('/api/admin/cities');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const cities = await response.json();
        
        // Clear existing options
        select.innerHTML = '<option value="">Select City</option>';
        
        // Add cities to dropdown
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city.id;
            option.textContent = `${city.name}, ${city.state}`;
            select.appendChild(option);
            
            // Auto-select if this matches the target city
            if (targetCity && targetState && 
                city.name.toLowerCase() === targetCity.toLowerCase() && 
                city.state === targetState) {
                option.selected = true;
                console.log(`Auto-selected city: ${city.name}, ${city.state}`);
            }
        });
        
    } catch (error) {
        console.error('Error loading cities:', error);
        select.innerHTML = '<option value="">Error loading cities</option>';
    }
}

function populateManualFields(data) {
    // Populate manual input fields with extracted data
    console.log('=== POPULATING FORM WITH EXTRACTED DATA ===');
    console.log('Extracted data:', data);
    
    if (!data) {
        console.error('No data provided to populateManualFields');
        return;
    }
    
    const fields = [
        'manualEventTitle', 'manualEventDescription', 'manualStartDate', 'manualEndDate',
        'manualStartTime', 'manualEndTime', 'manualEventType', 'manualStartLocation', 'manualEndLocation',
        'manualPrice', 'manualUrl', 'manualEventSource', 'manualSourceUrl',
        'manualSocialMediaPlatform', 'manualSocialMediaHandle', 'manualSocialMediaPageName',
        'manualSocialMediaPostedBy', 'manualSocialMediaUrl'
    ];
    
    // Helper function to safely set field value
    function setFieldValue(fieldId, value) {
        const element = document.getElementById(fieldId);
        if (element) {
            element.value = value || '';
        } else {
            console.warn(`Field not found: ${fieldId}`);
        }
    }
    
    // Populate all fields safely
    setFieldValue('manualEventTitle', data.title);
    setFieldValue('manualEventDescription', data.description);
    setFieldValue('manualStartDate', data.start_date);
    setFieldValue('manualEndDate', data.end_date);
    setFieldValue('manualStartTime', data.start_time);
    setFieldValue('manualEndTime', data.end_time);
    
    // Smart event type mapping to available dropdown options
    if (data.event_type) {
        const eventTypeField = document.getElementById('manualEventType');
        if (eventTypeField) {
            const smartMatch = findBestMatch(data.event_type, eventTypeField, 'event type');
            if (smartMatch !== -1) {
                eventTypeField.selectedIndex = smartMatch;
            } else {
                setFieldValue('manualEventType', 'tour'); // Default fallback
            }
        }
    } else {
        setFieldValue('manualEventType', 'tour'); // Default
    }
    
    setFieldValue('manualStartLocation', data.start_location);
    setFieldValue('manualEndLocation', data.end_location);
    setFieldValue('manualPrice', data.price);
    // Handle Instagram URL - convert handle to full URL
    if (data.instagram_handle) {
        setFieldValue('manualUrl', `https://instagram.com/${data.instagram_handle}`);
    } else if (data.url) {
        setFieldValue('manualUrl', data.url);
    }
    
    // Populate source fields
    if (data.source) {
        setFieldValue('manualEventSource', data.source);
    }
    if (data.source_url) {
        setFieldValue('manualSourceUrl', data.source_url);
    }
    
    // Social media fields
    if (data.social_media_platform) {
        setFieldValue('manualSocialMediaPlatform', data.social_media_platform);
    }
    if (data.social_media_handle) {
        setFieldValue('manualSocialMediaHandle', data.social_media_handle);
    }
    if (data.social_media_page_name) {
        setFieldValue('manualSocialMediaPageName', data.social_media_page_name);
    }
    if (data.social_media_posted_by) {
        setFieldValue('manualSocialMediaPostedBy', data.social_media_posted_by);
    }
    if (data.social_media_url) {
        setFieldValue('manualSocialMediaUrl', data.social_media_url);
    }
    
    // Set default date to today if no date extracted
    if (!data.start_date) {
        const today = new Date().toISOString().split('T')[0];
        setFieldValue('manualStartDate', today);
    }
    
    // Auto-select city if extracted (ensure dropdown is populated first)
    const selectCityAfterPopulation = async (cityId, cityName) => {
        const citySelect = document.getElementById('manualCityId');
        if (!citySelect) {
            console.error('City select element not found');
            return;
        }
        
        // Ensure dropdown is populated
        const ensureDropdownPopulated = async () => {
            const options = citySelect.options;
            if (options.length <= 1) {
                await populateCitySelect('manualCityId');
                // Wait a bit for DOM to update
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        };
        
        await ensureDropdownPopulated();
        
        const options = citySelect.options;
        console.log(`🔍 Attempting to select city ID ${cityId} (type: ${typeof cityId}), dropdown has ${options.length} options`);
        
        // Log all available city IDs for debugging
        const availableIds = [];
        for (let i = 0; i < options.length; i++) {
            if (options[i].value) {
                availableIds.push(`${options[i].value} (${options[i].text})`);
            }
        }
        console.log(`🔍 Available city IDs in dropdown:`, availableIds);
        
        // Try to find and select the city by ID (compare as both string and number)
        let found = false;
        const cityIdStr = String(cityId);
        const cityIdNum = Number(cityId);
        
        for (let i = 0; i < options.length; i++) {
            const optionValue = options[i].value;
            // Try both string and number comparison
            if (optionValue == cityId || optionValue == cityIdStr || optionValue == cityIdNum) {
                citySelect.selectedIndex = i;
                citySelect.dispatchEvent(new Event('change'));
                found = true;
                break;
            }
        }
        
        if (!found) {
            // Fall back to city name matching if available
            if (cityName) {
                const smartMatch = findBestMatch(cityName, citySelect, 'city');
                if (smartMatch !== -1) {
                    citySelect.selectedIndex = smartMatch;
                    citySelect.dispatchEvent(new Event('change'));
                } else {
                    // Try direct text match
                    for (let i = 0; i < options.length; i++) {
                        if (options[i].text.toLowerCase().includes(cityName.toLowerCase())) {
                            citySelect.selectedIndex = i;
                            citySelect.dispatchEvent(new Event('change'));
                            break;
                        }
                    }
                }
            }
        }
    };
    
    // Helper function to select venue after city is ready
    const selectVenueAfterCity = async (venueId, cityId) => {
        const venueSelect = document.getElementById('manualVenueId');
        if (!venueSelect) {
            console.error('Venue select element not found');
            return;
        }
        
        // Wait for city to be selected and venues to be populated
        const waitForVenues = async (retryCount = 0) => {
            if (retryCount > 15) {
                return;
            }
            
            // Populate venues if we have a city_id
            const citySelect = document.getElementById('manualCityId');
            const currentCityId = citySelect ? citySelect.value : null;
            
            // Use provided cityId or current selection
            const targetCityId = cityId || currentCityId;
            
            if (targetCityId) {
                await populateVenuesForCity(targetCityId, 'manualVenueId');
                await new Promise(resolve => setTimeout(resolve, 150));
            }
            
            const options = venueSelect.options;
            
            if (options.length <= 1) {
                setTimeout(() => waitForVenues(retryCount + 1), 200);
                return;
            }
            
            // Try to select the venue
            const venueIdStr = String(venueId);
            const venueIdNum = Number(venueId);
            for (let i = 0; i < options.length; i++) {
                if (options[i].value == venueId || options[i].value == venueIdStr || options[i].value == venueIdNum) {
                    venueSelect.selectedIndex = i;
                    venueSelect.dispatchEvent(new Event('change'));
                    return;
                }
            }
        };
        
        await waitForVenues();
    };
    
    // Auto-select city first (required for venue selection)
    if (data.city_id) {
        selectCityAfterPopulation(data.city_id, data.city).then(() => {
            // After city is selected, select venue if provided
            if (data.venue_id) {
                selectVenueAfterCity(data.venue_id, data.city_id);
            }
        }).catch(err => {
            console.error('Error selecting city:', err);
            // Even if city selection fails, try to select venue with the city_id we have
            if (data.venue_id && data.city_id) {
                selectVenueAfterCity(data.venue_id, data.city_id);
            }
        });
    } else if (data.city) {
        // Smart city matching with retry logic
        const citySelect = document.getElementById('manualCityId');
        if (citySelect) {
            // Function to attempt city selection
            const attemptCitySelection = (retryCount = 0) => {
                const options = citySelect.options;
                
                if (options.length <= 1) { // Only has "Select City" option
                    if (retryCount < 5) {
                        setTimeout(() => attemptCitySelection(retryCount + 1), 200);
                        return;
                    }
                    return;
                }
                
                // Try smart matching
                const smartMatch = findBestMatch(data.city, citySelect, 'city');
                if (smartMatch !== -1) {
                    citySelect.selectedIndex = smartMatch;
                }
            };
            
            // Start the city selection process
            attemptCitySelection();
        }
    }
    
    // Additional city selection logic
    if (data.city && data.state) {
        populateCitySelect('manualCityId', data.city, data.state);
    }
}

async function createEventFromExtractedData() {
    // Get data from manual input fields
    const title = document.getElementById('manualEventTitle').value.trim();
    const startDate = document.getElementById('manualStartDate').value;
    
    if (!title) {
        alert('Event title is required');
        return;
    }
    
    if (!startDate) {
        alert('Start date is required');
        return;
    }
    
    // Handle end date - if no end date provided, assume same as start date
    let endDate = document.getElementById('manualEndDate').value || startDate;
    
    // Handle end time - if start time provided but no end time, assume 1 hour duration
    let startTime = document.getElementById('manualStartTime').value || null;
    let endTime = document.getElementById('manualEndTime').value || null;
    
    if (startTime && !endTime) {
        // Calculate end time (1 hour after start time)
        const startTimeObj = new Date(`2000-01-01T${startTime}`);
        const endTimeObj = new Date(startTimeObj.getTime() + 60 * 60 * 1000); // Add 1 hour
        endTime = endTimeObj.toTimeString().slice(0, 5); // Format as HH:MM
    }
    
    const data = {
        title: title,
        description: document.getElementById('manualEventDescription').value.trim(),
        start_date: startDate,
        end_date: endDate,
        start_time: startTime,
        end_time: endTime,
        event_type: document.getElementById('manualEventType').value,
        start_location: document.getElementById('manualStartLocation').value.trim(),
        end_location: document.getElementById('manualEndLocation').value.trim(),
        price: document.getElementById('manualPrice').value ? parseFloat(document.getElementById('manualPrice').value) : null,
        url: document.getElementById('manualUrl').value.trim() || null,
        city_id: document.getElementById('manualCityId').value || null,
        venue_id: document.getElementById('manualVenueId').value || null,
        source: document.getElementById('manualEventSource').value || null,
        source_url: document.getElementById('manualSourceUrl').value.trim() || null,
        // Social media fields
        social_media_platform: document.getElementById('manualSocialMediaPlatform').value || null,
        social_media_handle: document.getElementById('manualSocialMediaHandle').value || null,
        social_media_page_name: document.getElementById('manualSocialMediaPageName').value || null,
        social_media_posted_by: document.getElementById('manualSocialMediaPostedBy').value || null,
        social_media_url: document.getElementById('manualSocialMediaUrl').value || null,
        // Online/virtual status (from extracted data or defaults)
        is_online: window.extractedEventData?.is_online || false,
        // Registration fields (from extracted data or defaults)
        is_registration_required: window.extractedEventData?.is_registration_required || false,
        registration_url: window.extractedEventData?.registration_url || null,
        create_calendar_event: false
    };
    
    try {
        const response = await fetch('/api/admin/create-event-from-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Event created successfully! Event ID: ${result.event_id}`);
            if (result.calendar_event_id) {
                alert('Google Calendar event also created!');
            }
            closeModal('imageUploadModal');
            loadEvents();
            // Refresh overview stats
            setTimeout(() => {
                console.log('🔄 Refreshing overview after event creation...');
                if (typeof window.loadOverview === 'function') {
                    window.loadOverview().catch(err => console.error('Error refreshing overview:', err));
                } else if (typeof loadOverview === 'function') {
                    loadOverview().catch(err => console.error('Error refreshing overview:', err));
                }
            }, 500);
        } else {
            alert('Error creating event: ' + result.error);
        }
    } catch (error) {
        alert('Error creating event: ' + error.message);
    }
}

// Handle create from venue form submission
document.getElementById('createFromVenueForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Handle end date - if no end date provided, assume same as start date
    const startDate = document.getElementById('startDateFromVenue').value;
    let endDate = document.getElementById('endDateFromVenue').value || startDate;
    
    // Handle end time - if start time provided but no end time, assume 1 hour duration
    let startTime = document.getElementById('startTimeFromVenue').value || null;
    let endTime = document.getElementById('endTimeFromVenue').value || null;
    
    if (startTime && !endTime) {
        // Calculate end time (1 hour after start time)
        const startTimeObj = new Date(`2000-01-01T${startTime}`);
        const endTimeObj = new Date(startTimeObj.getTime() + 60 * 60 * 1000); // Add 1 hour
        endTime = endTimeObj.toTimeString().slice(0, 5); // Format as HH:MM
    }
    
    const formData = {
        venue_id: document.getElementById('venueSelect').value,
        title: document.getElementById('eventTitleFromVenue').value,
        description: document.getElementById('eventDescriptionFromVenue').value,
        start_date: startDate,
        end_date: endDate,
        start_time: startTime,
        end_time: endTime,
        event_type: document.getElementById('eventTypeFromVenue').value,
        url: document.getElementById('eventUrlFromVenue').value || null,
        source: document.getElementById('eventSourceFromVenue').value || null,
        source_url: document.getElementById('sourceUrlFromVenue').value.trim() || null,
        create_calendar_event: document.getElementById('createCalendarEventFromVenue').checked
    };
    
    try {
        const response = await fetch('/api/admin/create-event-from-venue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Event created successfully! Event ID: ${result.event_id}`);
            if (result.calendar_event_id) {
                alert('Google Calendar event also created!');
            }
            closeModal('createFromVenueModal');
            loadEvents();
            // Refresh overview stats
            setTimeout(() => {
                console.log('🔄 Refreshing overview after event creation...');
                if (typeof window.loadOverview === 'function') {
                    window.loadOverview().catch(err => console.error('Error refreshing overview:', err));
                } else if (typeof loadOverview === 'function') {
                    loadOverview().catch(err => console.error('Error refreshing overview:', err));
                }
            }, 500);
        } else {
            alert('Error creating event: ' + result.error);
        }
    } catch (error) {
        alert('Error creating event: ' + error.message);
    }
});

// Event Scraping Functions
async function startSmithsonianScraping() {
    updateScrapingStatus('🏛️ Starting Smithsonian scraping...', 'info');
    
    try {
        const response = await fetch('/api/admin/scrape-smithsonian', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateScrapingStatus(`✅ Smithsonian scraping completed! Found ${result.events_found} events, saved ${result.events_saved}`, 'success');
            // Reload events table
            await loadEvents();
        } else {
            updateScrapingStatus(`❌ Smithsonian scraping failed: ${result.error}`, 'error');
        }
    } catch (error) {
        updateScrapingStatus(`❌ Smithsonian scraping error: ${error.message}`, 'error');
    }
}

async function startMuseumScraping() {
    showScrapingProgressModal('Museums');
    
    try {
        const response = await fetch('/api/admin/scrape-museums', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateScrapingProgress({
                percentage: 100,
                message: `✅ Scraping completed! Scraped ${result.museums_scraped} museums, saved ${result.events_saved} events`,
                events_saved: result.events_saved
            });
            await loadEvents();
            setTimeout(() => closeScrapingProgressModal(), 3000);
        } else {
            updateScrapingProgress({
                percentage: 0,
                message: `❌ Scraping failed: ${result.error}`,
                error: true
            });
        }
    } catch (error) {
        updateScrapingProgress({
            percentage: 0,
            message: `❌ Scraping error: ${error.message}`,
            error: true
        });
    }
}

async function startHirshhornScraping() {
    showScrapingProgressModal('Hirshhorn Museum');
    
    try {
        const response = await fetch('/api/admin/scrape-hirshhorn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Hirshhorn scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startAllVenuesScraping() {
    showScrapingProgressModal('All Venues');
    
    try {
        const response = await fetch('/api/admin/scrape-all-venues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateScrapingProgress({
                percentage: 100,
                message: `✅ Scraping completed! Scraped ${result.venues_scraped} venues, saved ${result.events_saved} events`,
                events_saved: result.events_saved
            });
            await loadEvents();
            setTimeout(() => closeScrapingProgressModal(), 3000);
        } else {
            updateScrapingProgress({
                percentage: 0,
                message: `❌ Scraping failed: ${result.error}`,
                error: true
            });
        }
    } catch (error) {
        updateScrapingProgress({
            percentage: 0,
            message: `❌ Scraping error: ${error.message}`,
            error: true
        });
    }
}

async function startWebstersScraping() {
    showScrapingProgressModal('Webster\'s Bookstore Cafe');
    
    try {
        const response = await fetch('/api/admin/scrape-websters', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Webster\'s scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startVipassanaScraping() {
    showScrapingProgressModal('Vipassana Virtual Events');
    
    try {
        const response = await fetch('/api/admin/scrape-vipassana', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Vipassana scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startDCEmbassyEventbriteScraping() {
    showScrapingProgressModal('DC Embassy Events (Eventbrite)');
    
    try {
        const response = await fetch('/api/admin/scrape-dc-embassy-eventbrite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})  // Send empty JSON object explicitly
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const responseText = await response.text();
                if (responseText) {
                    try {
                        const errorData = JSON.parse(responseText);
                        errorMessage = errorData.error || errorMessage;
                    } catch (e) {
                        // Not JSON, use text as error message
                        if (responseText.length < 500) {
                            errorMessage = responseText;
                        }
                    }
                }
            } catch (e) {
                // Ignore parsing errors
                console.error('Error parsing error response:', e);
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        // Parse JSON response
        let result;
        try {
            const responseText = await response.text();
            if (!responseText || responseText.trim() === '') {
                throw new Error('Empty response from server');
            }
            result = JSON.parse(responseText);
        } catch (parseError) {
            console.error('JSON parse error:', parseError);
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        if (result.success) {
            updateScrapingStatus(`✅ DC Embassy Eventbrite scraping completed! Found ${result.events_found} events, saved ${result.events_saved}`, 'success');
            // Reload events table
            await loadEvents();
            setTimeout(() => {
                closeScrapingProgressModal();
            }, 3000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('DC Embassy Eventbrite scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && (error.message.includes('JSON') || error.message.includes('parse'))) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed. Check server logs for details.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startNGAScraping() {
    showScrapingProgressModal('National Gallery of Art');
    
    try {
        // NGA scrape takes 2-5 min - use 6 min timeout to avoid "Failed to fetch"
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 360000);
        const response = await fetch('/api/admin/scrape-nga', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('NGA scraping error:', error);
        let msg = error.message || 'Unknown error';
        const isTimeout = error.name === 'AbortError' || msg.includes('Failed to fetch') || msg.includes('NetworkError');
        if (msg.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else if (isTimeout) {
            updateScrapingStatus(`❌ Connection failed or timed out (NGA takes 2–5 min). Run from terminal: python scripts/nga_comprehensive_scraper.py`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${msg}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startSAAMScraping() {
    showScrapingProgressModal('Smithsonian American Art Museum');
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 360000);
        const response = await fetch('/api/admin/scrape-saam', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('SAAM scraping error:', error);
        let msg = error.message || 'Unknown error';
        const isTimeout = error.name === 'AbortError' || msg.includes('Failed to fetch') || msg.includes('NetworkError');
        if (msg.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else if (isTimeout) {
            updateScrapingStatus(`❌ Connection failed or timed out. Run from terminal: python -c "from scripts.saam_scraper import scrape_all_saam_events, create_events_in_database; e=scrape_all_saam_events(); create_events_in_database(e) if e else None"`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${msg}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startNPGScraping() {
    showScrapingProgressModal('National Portrait Gallery');
    
    try {
        const response = await fetch('/api/admin/scrape-npg', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('NPG scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startAsianArtScraping() {
    showScrapingProgressModal('Smithsonian National Museum of Asian Art');
    
    try {
        const response = await fetch('/api/admin/scrape-asian-art', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Asian Art scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startCultureDCScraping() {
    showScrapingProgressModal('Culture DC');
    
    try {
        const response = await fetch('/api/admin/scrape-culture-dc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {}
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            setTimeout(() => {
                closeScrapingProgressModal();
                if (typeof loadEvents === 'function') loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Culture DC scraping error:', error);
        updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        closeScrapingProgressModal();
    }
}

async function startWharfDCScraping() {
    showScrapingProgressModal('Wharf DC');
    
    try {
        const response = await fetch('/api/admin/scrape-wharf-dc', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {}
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            setTimeout(() => {
                closeScrapingProgressModal();
                if (typeof loadEvents === 'function') loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Wharf DC scraping error:', error);
        updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        closeScrapingProgressModal();
    }
}

async function startSunsCinemaScraping() {
    showScrapingProgressModal('Suns Cinema');
    
    try {
        const response = await fetch('/api/admin/scrape-suns-cinema', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {}
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            setTimeout(() => {
                closeScrapingProgressModal();
                if (typeof loadEvents === 'function') loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Suns Cinema scraping error:', error);
        updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        closeScrapingProgressModal();
    }
}

async function startAfricanArtScraping() {
    showScrapingProgressModal('Smithsonian National Museum of African Art');
    
    try {
        const response = await fetch('/api/admin/scrape-african-art', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('African Art scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function startFindingAweScraping() {
    showScrapingProgressModal('Finding Awe (NGA)');
    
    try {
        const response = await fetch('/api/admin/scrape-finding-awe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        // Check if response is OK before parsing JSON
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
            } catch (e) {
                // If response is not JSON, try to get text
                try {
                    const errorText = await response.text();
                    if (errorText && errorText.length < 200) {
                        errorMessage = errorText;
                    }
                } catch (e2) {
                    // Ignore parsing errors
                }
            }
            updateScrapingStatus(`❌ Error: ${errorMessage}`, 'error');
            closeScrapingProgressModal();
            return;
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Progress modal will be updated via polling
            // Auto-close after a delay
            setTimeout(() => {
                closeScrapingProgressModal();
                loadEvents();
            }, 2000);
        } else {
            updateScrapingStatus(`❌ Error: ${result.error || 'Unknown error'}`, 'error');
            closeScrapingProgressModal();
        }
    } catch (error) {
        console.error('Finding Awe scraping error:', error);
        // Check if error is JSON parsing error
        if (error.message && error.message.includes('JSON')) {
            updateScrapingStatus(`❌ Error: Server returned invalid response. The scraper may have crashed.`, 'error');
        } else {
            updateScrapingStatus(`❌ Error: ${error.message}`, 'error');
        }
        closeScrapingProgressModal();
    }
}

async function discoverNewVenues() {
    updateScrapingStatus('🔍 Discovering new venues...', 'info');
    
    try {
        const response = await fetch('/api/admin/discover-new-venues', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateScrapingStatus(`✅ Venue discovery completed! Found ${result.events_found} events from new venues`, 'success');
            // Reload events table
            await loadEvents();
        } else {
            updateScrapingStatus(`❌ Venue discovery failed: ${result.error}`, 'error');
        }
    } catch (error) {
        updateScrapingStatus(`❌ Venue discovery error: ${error.message}`, 'error');
    }
}

function updateScrapingStatus(message, type = 'info') {
    const statusDiv = document.getElementById('scrapingStatus');
    if (!statusDiv) return;
    
    const timestamp = new Date().toLocaleTimeString();
    const statusMessage = `[${timestamp}] ${message}`;
    
    // Clear previous status after 10 seconds for success/info messages
    if (type === 'success' || type === 'info') {
        statusDiv.innerHTML = statusMessage;
        setTimeout(() => {
            statusDiv.innerHTML = '';
        }, 10000);
    } else {
        // Keep error messages visible longer
        statusDiv.innerHTML = statusMessage;
        statusDiv.style.color = type === 'error' ? '#dc3545' : '#007bff';
    }
}

// Progress modal functions
let progressPollInterval = null;
// Track last events_saved count to detect new events
let lastEventsSavedCount = 0;
let lastTableRefreshTime = 0;
const TABLE_REFRESH_INTERVAL = 5000; // Refresh table every 5 seconds during scraping

function showScrapingProgressModal(sourceName = 'Scraping') {
    // Reset tracking variables when starting new scraping
    lastEventsSavedCount = 0;
    lastTableRefreshTime = 0;
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('scrapingProgressModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'scrapingProgressModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; font-size: 1.5rem; color: #1f2937;">🔄 ${sourceName} Progress</h2>
                    <button onclick="closeScrapingProgressModal()" style="background: none; border: none; font-size: 28px; cursor: pointer; color: #6b7280; padding: 0; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: background 0.2s;" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='none'">&times;</button>
                </div>
                <div id="progressBarContainer" style="margin-bottom: 20px;">
                    <div style="background: #e5e7eb; border-radius: 10px; height: 30px; overflow: hidden; position: relative;">
                        <div id="progressBar" style="background: linear-gradient(90deg, #3b82f6, #8b5cf6); height: 100%; width: 0%; transition: width 0.3s ease; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 14px;"></div>
                    </div>
                </div>
                <div id="progressMessage" style="margin-bottom: 20px; padding: 15px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #3b82f6; font-size: 0.9375rem; line-height: 1.5; color: #1e40af;">
                    Starting...
                </div>
                <div style="margin-bottom: 20px;">
                    <h3 style="margin-bottom: 12px; color: #4a5568; font-size: 1.125rem; font-weight: 600;">📊 Statistics</h3>
                    <div class="stats-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 12px;">
                        <div style="padding: 16px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Events Found</div>
                            <div id="eventsFound" style="font-size: 28px; font-weight: bold; color: #3b82f6; line-height: 1.2;">0</div>
                        </div>
                        <div style="padding: 16px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Events Saved</div>
                            <div id="eventsSaved" style="font-size: 28px; font-weight: bold; color: #10b981; line-height: 1.2;">0</div>
                        </div>
                    </div>
                    <div id="additionalStats" class="stats-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                        <div id="venuesProcessedContainer" style="padding: 12px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e5e7eb; display: none;">
                            <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Venues Processed</div>
                            <div id="venuesProcessed" style="font-size: 20px; font-weight: bold; color: #8b5cf6; line-height: 1.2;">0/0</div>
                        </div>
                        <div id="sourcesProcessedContainer" style="padding: 12px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e5e7eb; display: none;">
                            <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Sources Processed</div>
                            <div id="sourcesProcessed" style="font-size: 20px; font-weight: bold; color: #f59e0b; line-height: 1.2;">0/0</div>
                        </div>
                    </div>
                    <div id="currentVenueContainer" style="margin-top: 12px; padding: 12px; background: #eff6ff; border-radius: 8px; border-left: 4px solid #3b82f6; display: none;">
                        <div style="font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Currently Processing</div>
                        <div id="currentVenue" style="font-size: 14px; font-weight: 600; color: #1e40af; line-height: 1.4;"></div>
                    </div>
                </div>
                <div>
                    <h3 style="margin-bottom: 12px; color: #4a5568; font-size: 1.125rem; font-weight: 600;">📝 Recent Events</h3>
                    <div id="recentEvents" style="max-height: 200px; overflow-y: auto; background: #f8f9fa; border-radius: 8px; padding: 12px; -webkit-overflow-scrolling: touch;">
                        <div style="color: #6b7280; text-align: center; padding: 20px; font-size: 0.9375rem;">No events extracted yet...</div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    } else {
        // Modal exists - update the title if source name changed
        const titleElement = modal.querySelector('h2');
        if (titleElement) {
            titleElement.textContent = `🔄 ${sourceName} Progress`;
        }
        // Reset progress display when starting new scraping
        const progressBar = document.getElementById('progressBar');
        const progressMessage = document.getElementById('progressMessage');
        const eventsFound = document.getElementById('eventsFound');
        const eventsSaved = document.getElementById('eventsSaved');
        const recentEvents = document.getElementById('recentEvents');
        
        if (progressBar) {
            progressBar.style.width = '0%';
            progressBar.textContent = '';
        }
        if (progressMessage) {
            progressMessage.textContent = 'Starting...';
            progressMessage.style.borderLeftColor = '#3b82f6';
            progressMessage.style.background = '#f0f9ff';
        }
        if (eventsFound) {
            eventsFound.textContent = '0';
        }
        if (eventsSaved) {
            eventsSaved.textContent = '0';
        }
        if (recentEvents) {
            recentEvents.innerHTML = '<div style="color: #6b7280; text-align: center; padding: 20px; font-size: 0.9375rem;">No events extracted yet...</div>';
        }
        // Hide additional stats containers
        const venuesContainer = document.getElementById('venuesProcessedContainer');
        const sourcesContainer = document.getElementById('sourcesProcessedContainer');
        const currentVenueContainer = document.getElementById('currentVenueContainer');
        if (venuesContainer) venuesContainer.style.display = 'none';
        if (sourcesContainer) sourcesContainer.style.display = 'none';
        if (currentVenueContainer) currentVenueContainer.style.display = 'none';
    }
    
    modal.style.display = 'block';
    
    // Start polling for progress
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
    }
    progressPollInterval = setInterval(pollScrapingProgress, 1000); // Poll every second
}

function closeScrapingProgressModal() {
    const modal = document.getElementById('scrapingProgressModal');
    if (modal) {
        modal.style.display = 'none';
    }
    // Stop polling when modal is closed
    if (progressPollInterval) {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
    }
    // Reset tracking variables
    lastEventsSavedCount = 0;
    lastTableRefreshTime = 0;
}

async function pollScrapingProgress() {
    // Check if modal is still open before polling
    const modal = document.getElementById('scrapingProgressModal');
    if (!modal || modal.style.display === 'none') {
        // Modal is closed, stop polling
        if (progressPollInterval) {
            clearInterval(progressPollInterval);
            progressPollInterval = null;
        }
        lastEventsSavedCount = 0;
        return;
    }
    
    try {
        // Use AbortController for timeout (more compatible)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch('/api/scrape-progress', {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const progress = await response.json();
        
        if (progress.error) {
            console.error('Error fetching progress:', progress.error);
            return;
        }
        
        updateScrapingProgress(progress);
        
        // Refresh events table if events are being saved
        const currentEventsSaved = progress.events_saved || 0;
        const currentTime = Date.now();
        
        // Refresh table if:
        // 1. New events have been saved since last check, OR
        // 2. It's been more than TABLE_REFRESH_INTERVAL since last refresh (periodic update)
        if (currentEventsSaved > lastEventsSavedCount || 
            (currentTime - lastTableRefreshTime > TABLE_REFRESH_INTERVAL && currentEventsSaved > 0)) {
            // Only refresh if we're actively saving events (percentage > 50 means we're past scraping phase)
            if (progress.percentage >= 50 && progress.percentage < 100) {
                loadEvents();
                lastTableRefreshTime = currentTime;
            }
            lastEventsSavedCount = currentEventsSaved;
        }
        
        // Stop polling if scraping is complete
        if (progress.percentage >= 100 || (progress.message && progress.message.toLowerCase().includes('complete'))) {
            if (progressPollInterval) {
                clearInterval(progressPollInterval);
                progressPollInterval = null;
            }
            // Refresh table one final time when complete
            loadEvents();
            lastEventsSavedCount = 0;
            // Auto-close modal after 3 seconds
            setTimeout(() => {
                closeScrapingProgressModal();
            }, 3000);
        }
    } catch (error) {
        // Only log if it's not an abort/timeout error
        if (error.name !== 'AbortError' && error.name !== 'TimeoutError') {
            console.error('Error polling progress:', error);
        }
        // Don't stop polling on network errors - they might be temporary
    }
}

function updateScrapingProgress(progress) {
    const progressBar = document.getElementById('progressBar');
    const progressMessage = document.getElementById('progressMessage');
    const eventsFound = document.getElementById('eventsFound');
    const eventsSaved = document.getElementById('eventsSaved');
    const recentEvents = document.getElementById('recentEvents');
    
    if (!progressBar) return;
    
    // Clamp percentage between 0 and 100
    const percentage = Math.min(100, Math.max(0, progress.percentage || progress.progress || 0));
    progressBar.style.width = percentage + '%';
    progressBar.textContent = percentage >= 5 ? percentage + '%' : ''; // Only show text if bar is wide enough
    
    // Build a more detailed message
    let message = progress.message || 'Processing...';
    if (progress.current_step) {
        message = `Step ${progress.current_step}/${progress.total_steps || 3}: ${message}`;
    }
    if (progress.current_venue) {
        message += `<br><small style="opacity: 0.8;">📍 ${progress.current_venue}</small>`;
    }
    
    const isError = progress.error || false;
    progressMessage.innerHTML = message;
    progressMessage.style.borderLeftColor = isError ? '#ef4444' : '#3b82f6';
    progressMessage.style.background = isError ? '#fef2f2' : '#f0f9ff';
    
    if (eventsFound) {
        eventsFound.textContent = progress.events_found || 0;
    }
    if (eventsSaved) {
        eventsSaved.textContent = progress.events_saved || 0;
    }
    
    // Show/hide venues processed
    if (progress.venues_processed !== undefined && progress.total_venues !== undefined) {
        const container = document.getElementById('venuesProcessedContainer');
        const venuesInfo = document.getElementById('venuesProcessed');
        if (container && venuesInfo) {
            container.style.display = 'block';
            venuesInfo.textContent = `${progress.venues_processed}/${progress.total_venues}`;
        }
    }
    
    // Show/hide sources processed
    if (progress.sources_processed !== undefined && progress.total_sources !== undefined) {
        const container = document.getElementById('sourcesProcessedContainer');
        const sourcesInfo = document.getElementById('sourcesProcessed');
        if (container && sourcesInfo) {
            container.style.display = 'block';
            sourcesInfo.textContent = `${progress.sources_processed}/${progress.total_sources}`;
        }
    }
    
    // Show/hide current venue
    const currentVenueContainer = document.getElementById('currentVenueContainer');
    const currentVenueEl = document.getElementById('currentVenue');
    if (currentVenueContainer && currentVenueEl) {
        if (progress.current_venue) {
            currentVenueContainer.style.display = 'block';
            currentVenueEl.textContent = progress.current_venue;
        } else {
            currentVenueContainer.style.display = 'none';
        }
    }
    
    // Update recent events with more detail
    if (recentEvents && progress.recent_events && progress.recent_events.length > 0) {
        recentEvents.innerHTML = progress.recent_events.slice(0, 10).map(event => {
            const timeStr = event.start_time ? ` at ${event.start_time}` : '';
            const locationStr = event.start_location ? ` • ${event.start_location}` : '';
            return `
            <div style="padding: 10px; margin-bottom: 6px; background: white; border-radius: 6px; border-left: 4px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="font-weight: bold; color: #1f2937; margin-bottom: 4px;">${event.title || 'Untitled Event'}</div>
                <div style="font-size: 12px; color: #6b7280; display: flex; gap: 8px; flex-wrap: wrap;">
                    <span style="background: #e0e7ff; color: #4338ca; padding: 2px 6px; border-radius: 4px; font-weight: 500;">${event.event_type || 'event'}</span>
                    <span>${event.start_date || 'No date'}${timeStr}</span>
                    ${locationStr ? `<span>${locationStr.replace(' • ', '')}</span>` : ''}
                </div>
            </div>
        `;
        }).join('');
    } else if (recentEvents && (!progress.recent_events || progress.recent_events.length === 0)) {
        recentEvents.innerHTML = '<div style="color: #6b7280; text-align: center; padding: 20px;">No events extracted yet...</div>';
    }
}

