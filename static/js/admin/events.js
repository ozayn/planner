// Helper function to detect generic/recurring tour titles
function isGenericTourTitle(title) {
    if (!title) return false;
    const genericPatterns = [
        /^docent[- ]led walk[- ]in tour$/i,
        /^walk[- ]in tour$/i,
        /^docent[- ]led tour$/i,
        /^guided tour$/i,
        /^public tour$/i,
        /^drop[- ]in tour$/i,
        /^self[- ]guided tour$/i
    ];
    return genericPatterns.some(pattern => pattern.test(title.trim()));
}

// Track whether to show recurring tours (default: hidden to save space)
let showRecurringToursAdmin = false;

// Load recurring tours visibility preference from localStorage
function loadRecurringToursPreference() {
    const savedState = localStorage.getItem('showRecurringToursAdmin');
    showRecurringToursAdmin = (savedState === 'true');
}

// Toggle recurring tours visibility in admin
function toggleRecurringToursVisibilityAdmin() {
    showRecurringToursAdmin = !showRecurringToursAdmin;
    if (showRecurringToursAdmin) {
        localStorage.setItem('showRecurringToursAdmin', 'true');
    } else {
        localStorage.removeItem('showRecurringToursAdmin'); // Remove to allow default false
    }
    
    // Update button text
    const toggleBtn = document.getElementById('recurringToursToggleBtn');
    if (toggleBtn) {
        toggleBtn.textContent = showRecurringToursAdmin ? '▼ Hide' : '▶ Show';
    }
    
    applyEventFilters(); // Re-apply filters to update display
}

// Load events data
async function loadEvents() {
    try {
        // Load recurring tours preference
        loadRecurringToursPreference();
        
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
        
        const response = await fetch('/api/admin/events');
        const events = await response.json();
        
        if (events.error) throw new Error(events.error);
        
        // Sort by most recently updated first (descending)
        events.sort((a, b) => {
            const aDate = new Date(a.updated_at || a.created_at || 0);
            const bDate = new Date(b.updated_at || b.created_at || 0);
            return bDate - aDate; // Descending order (most recent first)
        });
        
        // Store events globally for filtering
        window.allEvents = events;
        
        // Apply filters (which will hide recurring tours by default)
        applyEventFilters();
        
        // Update recurring tours toggle button
        const toggleBtn = document.getElementById('recurringToursToggleBtn');
        if (toggleBtn) {
            toggleBtn.textContent = showRecurringToursAdmin ? '▼ Hide' : '▶ Show';
        }
        
        // Render the events table
        renderEventsTable();
        populateEventFilters();
        
    } catch (error) {
        console.error('Error loading events:', error);
        const eventsTable = document.getElementById('eventsTable');
        if (eventsTable) {
            eventsTable.innerHTML = '<tr><td colspan="12" class="no-results">❌ Failed to load events: ' + error.message + '</td></tr>';
        }
    }
}

function renderEventsTable() {
    const data = window.filteredEvents || window.allEvents || [];
    // Ensure the section is visible before rendering
    const eventsSection = document.getElementById('events');
    if (!eventsSection) {
        console.warn('Events section not found, skipping render');
        return;
    }
    
    // Check if section is visible - use class check instead of getComputedStyle (faster, no reflow)
    if (!eventsSection.classList.contains('active')) {
        return;
    }
    
    // Defer heavy table rendering to next frame to keep UI responsive
    requestAnimationFrame(() => {
        // Ensure the table container is visible before rendering
        const tableContainer = eventsSection.querySelector('.table-container');
        if (tableContainer) {
            tableContainer.style.display = 'block';
            tableContainer.style.visibility = 'visible';
            tableContainer.style.minHeight = '400px';
            tableContainer.style.height = 'auto';
        }
        renderDynamicTable('eventsTable', data, 'events');
        // Update bulk export button state after rendering
        updateBulkExportButton();
        // Reset select all checkbox
        const selectAllCheckbox = document.getElementById('selectAllEvents');
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
        }
        // Update view mode (table vs cards) based on screen size
        updateAllTablesViewMode();
    });
    // Update bulk export button state after rendering
    updateBulkExportButton();
    // Reset select all checkbox
    const selectAllCheckbox = document.getElementById('selectAllEvents');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = false;
    }
}

function toggleExhibitionFields() {
    const eventType = document.getElementById('editEventType').value;
    const exhibitionFields = document.getElementById('editExhibitionFields');
    if (eventType === 'exhibition') {
        exhibitionFields.style.display = 'block';
    } else {
        exhibitionFields.style.display = 'none';
    }
}

async function editEvent(id) {
    // Find the event data
    const event = window.allEvents.find(e => e.id == id);
    if (!event) {
        alert('Event not found');
        return;
    }
    
    // Populate the edit form with current event data
    document.getElementById('editEventId').value = event.id;
    document.getElementById('editEventTitle').value = event.title || '';
    document.getElementById('editEventDescription').value = event.description || '';
    document.getElementById('editEventStartDate').value = event.start_date || '';
    document.getElementById('editEventEndDate').value = event.end_date || '';
    document.getElementById('editEventStartTime').value = event.start_time || '';
    document.getElementById('editEventEndTime').value = event.end_time || '';
    document.getElementById('editEventType').value = event.event_type || '';
    
    // Populate city and venue dropdowns
    const citySelect = document.getElementById('editEventCityId');
    const venueSelect = document.getElementById('editEventVenueId');
    
    // Populate city dropdown
    if (citySelect) {
        await populateCitySelect('editEventCityId');
        // Select the current city
        if (event.city_id) {
            citySelect.value = event.city_id;
            // Populate venues for the selected city
            await populateEditEventVenues();
            // Select the current venue
            if (event.venue_id && venueSelect) {
                venueSelect.value = event.venue_id;
            }
        }
    }
    
    // Show/hide exhibition fields based on event type
    const exhibitionFields = document.getElementById('editExhibitionFields');
    if (event.event_type === 'exhibition') {
        exhibitionFields.style.display = 'block';
        // Populate exhibition-specific fields
        document.getElementById('editExhibitionLocation').value = event.exhibition_location || '';
        document.getElementById('editCurator').value = event.curator || '';
        document.getElementById('editAdmissionPrice').value = event.admission_price || '';
        document.getElementById('editArtists').value = event.artists || '';
        document.getElementById('editExhibitionType').value = event.exhibition_type || '';
        document.getElementById('editCollectionPeriod').value = event.collection_period || '';
        document.getElementById('editNumberOfArtworks').value = event.number_of_artworks || '';
        document.getElementById('editOpeningReceptionDate').value = event.opening_reception_date || '';
        document.getElementById('editOpeningReceptionTime').value = event.opening_reception_time || '';
        document.getElementById('editIsPermanent').checked = event.is_permanent || false;
        document.getElementById('editRelatedExhibitions').value = event.related_exhibitions || '';
    } else {
        exhibitionFields.style.display = 'none';
    }
    
    // Show the modal
    document.getElementById('editEventModal').style.display = 'block';
}

// Populate venues dropdown for edit event form based on selected city
async function populateEditEventVenues() {
    const citySelect = document.getElementById('editEventCityId');
    const venueSelect = document.getElementById('editEventVenueId');
    
    if (!citySelect || !venueSelect) {
        return;
    }
    
    const cityId = citySelect.value;
    
    // Clear venue dropdown
    venueSelect.innerHTML = '<option value="">Select Venue (optional)</option>';
    
    if (!cityId) {
        return;
    }
    
    try {
        // Fetch all venues and filter by city_id on client side
        // (API doesn't support city_id filter, so we filter client-side)
        const response = await fetch('/api/admin/venues');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const allVenues = await response.json();
        
        // Filter venues by city_id
        const venues = allVenues.filter(venue => venue.city_id == cityId);
        
        // Add venues to dropdown
        venues.forEach(venue => {
            const option = document.createElement('option');
            option.value = venue.id;
            option.textContent = venue.name;
            venueSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading venues:', error);
    }
}

async function addEventToCalendar(eventId) {
    try {
        // Find the event data
        const event = window.allEvents.find(e => e.id == eventId);
        if (!event) {
            alert('Event not found');
            return;
        }
        
        // Use unified module to get calendar location
        const calendarLocation = CalendarExport.getCalendarLocation(event);
        
        // Prepare calendar event data
        const calendarData = {
            title: event.title,
            description: event.description || '',
            start_date: event.start_date,
            end_date: event.end_date || event.start_date,
            start_time: event.start_time,
            end_time: event.end_time,
            location: calendarLocation,
            event_type: event.event_type,
            city_id: event.city_id,  // Include city_id for timezone lookup
            // Enhanced fields for better calendar integration
            start_location: event.start_location,
            end_location: event.end_location,
            venue_address: event.venue_address,
            venue_name: event.venue_name,
            city_name: event.city_name,
            social_media_platform: event.social_media_platform,
            social_media_handle: event.social_media_handle,
            social_media_page_name: event.social_media_page_name,
            social_media_posted_by: event.social_media_posted_by,
            social_media_url: event.social_media_url,
            url: event.url,
            source: event.source,
            source_url: event.source_url,
            organizer: event.organizer,
            price: event.price,
            // Legacy Instagram fields for backward compatibility
            instagram_handle: event.instagram_handle
        };
        
        // Call the calendar API
        const response = await fetch('/api/calendar/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(calendarData)
        });
        
        if (response.ok) {
            const result = await response.json();
            
            // Show options dialog for calendar integration
            const options = [
                '📥 Download .ics File (Recommended)',
                '📅 Open in Calendar App',
                '❌ Cancel'
            ];
            
            const choice = prompt(`Choose how to add "${event.title}" to your calendar:\n\n1. ${options[0]}\n2. ${options[1]}\n3. ${options[2]}\n\nEnter 1, 2, or 3:`, '1');
            
            if (choice === '1') {
                // Download iCal file (recommended - works correctly)
                const icalContent = result.ical_content;
                const blob = new Blob([icalContent], { type: 'text/calendar' });
                const url = window.URL.createObjectURL(blob);
                
                const link = document.createElement('a');
                link.href = url;
                link.download = `${event.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.ics`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(url);
                
                alert('✅ Event downloaded as .ics file! Open it to add to your calendar.');
            } else if (choice === '2') {
                // Open calendar app (may have timezone issues)
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                
                if (isMobile) {
                    const mobileCalendarUrl = generateMobileCalendarUrl(calendarData);
                    if (mobileCalendarUrl) {
                        window.location.href = mobileCalendarUrl;
                        alert('✅ Opening in your calendar app...');
                    } else {
                        const calendarUrl = generateCalendarUrl(calendarData);
                        window.open(calendarUrl, '_blank');
                        alert('✅ Event opened in Google Calendar!');
                    }
                } else {
                    const calendarUrl = generateCalendarUrl(calendarData);
                    if (calendarUrl) {
                        window.open(calendarUrl, '_blank');
                        alert('✅ Event opened in Google Calendar!');
                    } else {
                        alert('❌ Could not generate calendar URL');
                    }
                }
            }
            // If choice is '3' or anything else, do nothing (cancelled)
        } else {
            const error = await response.json();
            alert('❌ Failed to add event to calendar: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error adding event to calendar:', error);
        alert('❌ Error adding event to calendar: ' + error.message);
    }
}

// Generate mobile calendar URL (using unified module)
function generateMobileCalendarUrl(eventData) {
    // Use unified module to parse dates and generate URL
    const { startDate, endDate, isAllDay } = CalendarExport.parseEventDates(eventData);
    const calendarUrl = CalendarExport.generateGoogleCalendarUrl(eventData, startDate, endDate, isAllDay);
    
    // Detect iOS vs Android
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    
    if (isIOS) {
        return calendarUrl.replace('https://', 'webcal://');
    } else if (isAndroid) {
        return calendarUrl;
    }
    
    return null; // Not mobile or unsupported
}

// Generate calendar URL (using unified module)
function generateCalendarUrl(eventData) {
    const { startDate, endDate, isAllDay } = CalendarExport.parseEventDates(eventData);
    return CalendarExport.generateGoogleCalendarUrl(eventData, startDate, endDate, isAllDay);
}

// Calendar export functions now use the unified CalendarExport module
// Helper functions are available via CalendarExport.* if needed

// Multi-select and bulk export functions
function toggleSelectAllEvents(checkbox) {
    const eventCheckboxes = document.querySelectorAll('.event-checkbox');
    eventCheckboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
    updateBulkExportButton();
}

async function deleteSelectedEvents() {
    const selectedCheckboxes = document.querySelectorAll('.event-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        alert('Please select at least one event to delete.');
        return;
    }
    
    const selectedIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
    const events = window.allEvents.filter(e => selectedIds.includes(e.id));
    
    if (events.length === 0) {
        alert('No events found for selected IDs.');
        return;
    }
    
    // Show confirmation dialog
    const eventTitles = events.map(e => `  • ${e.title}`).join('\n');
    const confirmed = confirm(
        `Are you sure you want to delete ${events.length} event(s)?\n\n` +
        `${eventTitles}\n\n` +
        `This action cannot be undone.`
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        // Delete each event
        let deletedCount = 0;
        let failedCount = 0;
        
        for (const eventId of selectedIds) {
            try {
                const response = await fetch(`/api/delete-event/${eventId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (response.ok) {
                    deletedCount++;
                } else {
                    const result = await response.json();
                    console.error(`Failed to delete event ${eventId}:`, result.error);
                    failedCount++;
                }
            } catch (error) {
                console.error(`Error deleting event ${eventId}:`, error);
                failedCount++;
            }
        }
        
        // Show result
        if (failedCount === 0) {
            alert(`✅ Successfully deleted ${deletedCount} event(s)!`);
        } else {
            alert(`⚠️ Deleted ${deletedCount} event(s), but ${failedCount} failed. Check console for details.`);
        }
        
        // Reload events
        loadEvents();
        
    } catch (error) {
        console.error('Error deleting events:', error);
        alert('❌ Error deleting events: ' + error.message);
    }
}

function updateBulkExportButton() {
    const selectedCount = document.querySelectorAll('.event-checkbox:checked').length;
    const bulkExportBtn = document.getElementById('bulkExportBtn');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');
    
    if (bulkExportBtn) {
        bulkExportBtn.disabled = selectedCount === 0;
        if (selectedCount > 0) {
            bulkExportBtn.textContent = `📅 Export ${selectedCount} Selected to Calendar`;
        } else {
            bulkExportBtn.textContent = '📅 Export Selected to Calendar';
        }
    }
    
    if (bulkDeleteBtn) {
        bulkDeleteBtn.disabled = selectedCount === 0;
        if (selectedCount > 0) {
            bulkDeleteBtn.textContent = `🗑️ Delete ${selectedCount} Selected`;
        } else {
            bulkDeleteBtn.textContent = '🗑️ Delete Selected';
        }
    }
}

async function exportSelectedEventsToCalendar() {
    const selectedCheckboxes = document.querySelectorAll('.event-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        alert('Please select at least one event to export.');
        return;
    }
    
    const selectedIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));
    const events = window.allEvents.filter(e => selectedIds.includes(e.id));
    
    if (events.length === 0) {
        alert('No events found for selected IDs.');
        return;
    }
    
    // For single event, use the existing single event export
    if (events.length === 1) {
        addEventToCalendar(events[0].id);
        return;
    }
    
    // For multiple events, generate ICS file and open Google Calendar import page
    const icsContent = generateICSForEvents(events);
    
    // Download the ICS file
    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `events_${new Date().toISOString().split('T')[0]}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    // Open Google Calendar import page
    setTimeout(() => {
        window.open('https://calendar.google.com/calendar/u/0/r/settings/export', '_blank');
        alert(`✅ Downloaded ${events.length} events as .ics file!\n\nNext steps:\n1. Go to Google Calendar (opened in new tab)\n2. Click "Import" in the left sidebar\n3. Select the downloaded .ics file\n4. Choose which calendar to import to\n5. Click "Import"`);
    }, 500);
}

// Generate ICS for multiple events (using unified module)
function generateICSForEvents(events) {
    return CalendarExport.generateICS(events, 'Planner Events');
}

// Generate ICS for single event (using unified module)
// Generate ICS for single event (using unified module)
function generateICSEvent(event) {
    return CalendarExport.generateICSEvent(event);
}

function generateCalendarUrlForEvent(event) {
    // Prepare event data in the format expected by generateCalendarUrl
    const eventData = {
        title: event.title || '',
        description: event.description || '',
        start_date: event.start_date || '',
        end_date: event.end_date || event.start_date || '',
        start_time: event.start_time || '',
        end_time: event.end_time || '',
        start_location: event.start_location || '',
        venue_name: event.venue_name || '',
        venue_address: event.venue_address || '',
        city_name: event.city_name || '',
        url: event.url || '',
        event_type: event.event_type || '',
        city_timezone: event.city_timezone || 'America/New_York'
    };
    
    return generateCalendarUrl(eventData);
}

function deleteEvent(id) {
    if (confirm('Are you sure you want to delete this event?')) {
        fetch(`/api/delete-event/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Event deleted successfully!');
                loadEvents(); // Reload data
            } else {
                alert('Error: ' + result.error);
            }
        })
        .catch(error => {
            alert('Error deleting event: ' + error.message);
        });
    }
}

// Event filter functions
function applyEventFilters() {
    if (!window.allEvents) return;
    
    const searchTerm = document.getElementById('eventSearch').value.toLowerCase();
    const typeFilter = document.getElementById('eventTypeFilter').value;
    const cityFilter = document.getElementById('eventCityFilter').value;
    const venueFilter = document.getElementById('eventVenueFilter').value;
    
    window.filteredEvents = window.allEvents.filter(event => {
        // Filter out recurring tours if not shown
        if (!showRecurringToursAdmin && event.event_type === 'tour' && isGenericTourTitle(event.title)) {
            return false;
        }
        
        const matchesSearch = !searchTerm || 
            event.title.toLowerCase().includes(searchTerm) ||
            (event.event_type && event.event_type.toLowerCase().includes(searchTerm)) ||
            (event.description && event.description.toLowerCase().includes(searchTerm));
        
        const matchesType = !typeFilter || event.event_type === typeFilter;
        const matchesCity = !cityFilter || 
            (event.city_id && String(event.city_id) === cityFilter) ||
            (event.city_name && event.city_name.toLowerCase() === cityFilter.toLowerCase());
        const matchesVenue = !venueFilter || event.venue_name === venueFilter;
        
        return matchesSearch && matchesType && matchesCity && matchesVenue;
    });
    
    // Sort by most recently updated first (descending) - default sort order
    window.filteredEvents.sort((a, b) => {
        const aDate = new Date(a.updated_at || a.created_at || 0);
        const bDate = new Date(b.updated_at || b.created_at || 0);
        return bDate - aDate; // Descending order (most recent first)
    });
    
    // Update filter summary
    const summary = document.getElementById('eventFilterSummary');
    const activeFilters = [];
    if (searchTerm) activeFilters.push(`Search: "${searchTerm}"`);
    if (typeFilter) activeFilters.push(`Type: ${typeFilter}`);
    if (cityFilter) {
        const citySelect = document.getElementById('eventCityFilter');
        const selectedCity = citySelect.options[citySelect.selectedIndex];
        activeFilters.push(`City: ${selectedCity.text}`);
    }
    if (venueFilter) activeFilters.push(`Venue: ${venueFilter}`);
    if (!showRecurringToursAdmin) {
        activeFilters.push(`Recurring Tours: Hidden`);
    }
    
    if (activeFilters.length > 0) {
        summary.textContent = `Active filters: ${activeFilters.join(' • ')} | Showing ${window.filteredEvents.length} of ${window.allEvents.length} events`;
        summary.classList.add('active');
    } else {
        summary.textContent = '';
        summary.classList.remove('active');
    }
    
    renderEventsTable();
}

function clearEventFilters() {
    document.getElementById('eventSearch').value = '';
    document.getElementById('eventTypeFilter').value = '';
    document.getElementById('eventCityFilter').value = '';
    document.getElementById('eventVenueFilter').value = '';
    
    // Note: We don't reset showRecurringToursAdmin here - that's a separate toggle
    // Re-apply filters (which will still respect the recurring tours toggle)
    if (window.allEvents) {
        applyEventFilters();
    }
}

function openAddEventModal() {
    alert('Add Event functionality will be implemented here');
}

// Populate event filters
function populateEventFilters() {
    const typeFilter = document.getElementById('eventTypeFilter');
    const cityFilter = document.getElementById('eventCityFilter');
    const venueFilter = document.getElementById('eventVenueFilter');
    
    if (!typeFilter || !cityFilter || !venueFilter || !window.allEvents) return;
    
    const types = [...new Set(window.allEvents.map(event => event.event_type).filter(Boolean))].sort();
    const cities = [...new Set(window.allEvents.map(event => {
        // Use city_id if available, otherwise use city_name
        return event.city_id ? String(event.city_id) : (event.city_name || '');
    }).filter(Boolean))].sort();
    const venues = [...new Set(window.allEvents.map(event => event.venue_name).filter(Boolean))].sort();
    
    typeFilter.innerHTML = '<option value="">All Types</option>';
    types.forEach(type => {
        typeFilter.innerHTML += '<option value="' + type + '">' + type + '</option>';
    });
    
    cityFilter.innerHTML = '<option value="">All Cities</option>';
    // Populate cities from window.allCities if available, otherwise use city names from events
    if (window.allCities && window.allCities.length > 0) {
        window.allCities.forEach(city => {
            cityFilter.innerHTML += '<option value="' + city.id + '">' + city.name + (city.state ? ', ' + city.state : '') + '</option>';
        });
    } else {
        // Fallback: use city names from events
        const cityNames = [...new Set(window.allEvents.map(event => event.city_name).filter(Boolean))].sort();
        cityNames.forEach(cityName => {
            cityFilter.innerHTML += '<option value="' + cityName + '">' + cityName + '</option>';
        });
    }
    
    venueFilter.innerHTML = '<option value="">All Venues</option>';
    venues.forEach(venue => {
        venueFilter.innerHTML += '<option value="' + venue + '">' + venue + '</option>';
    });
}

// Suppress browser extension errors (they're not our problem)
window.addEventListener('error', function(event) {
    // Ignore errors from browser extensions
    if (event.message && (
        event.message.includes('message channel closed') ||
        event.message.includes('Extension context invalidated') ||
        event.message.includes('Receiving end does not exist')
    )) {
        event.preventDefault();
        return false;
    }
});

window.addEventListener('unhandledrejection', function(event) {
    // Ignore promise rejections from browser extensions
    if (event.reason && (
        event.reason.message && (
            event.reason.message.includes('message channel closed') ||
            event.reason.message.includes('Extension context invalidated') ||
            event.reason.message.includes('Receiving end does not exist')
        )
    )) {
        event.preventDefault();
        return false;
    }
});

// Initialize when DOM is ready
