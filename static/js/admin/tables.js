function renderDynamicTable(tableId, data, tableType = 'default') {
    const tableBody = document.getElementById(tableId);
    if (!tableBody) {
        console.error('Table body not found:', tableId);
        return;
    }
    
    // Verify we're rendering to the correct table
    const expectedSection = tableId.replace('Table', '');
    const parentSection = tableBody.closest('.data-section');
    if (parentSection && parentSection.id !== expectedSection) {
        console.error('WARNING: Rendering', tableType, 'data to table in section', parentSection.id, 'but expected section', expectedSection);
    }
    
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="100" class="no-results">🔍 No data found</td></tr>';
        return;
    }
    
    // Get the first item to determine available fields dynamically
    const sampleItem = data[0];
    const availableFields = Object.keys(sampleItem);
    
    // Define field display preferences (order, visibility, formatting)
    const fieldConfig = getFieldConfig(tableType);
    
    // Filter and order fields based on configuration
    const orderedFields = fieldConfig.order.filter(field => availableFields.includes(field));
    
    // Add any new fields not in the config (for future-proofing)
    const newFields = availableFields.filter(field => !fieldConfig.order.includes(field));
    orderedFields.push(...newFields);
    
    // Generate table headers - find the desktop table
    let table = null;
    if (tableId === 'eventsTable') {
        table = document.getElementById('eventsTableDesktop');
    } else if (tableId === 'citiesTable') {
        table = document.getElementById('citiesTableDesktop');
    } else if (tableId === 'venuesTable') {
        table = document.getElementById('venuesTableDesktop');
    } else if (tableId === 'sourcesTable') {
        table = document.getElementById('sourcesTableDesktop');
        if (!table && tableType === 'sources') {
            // Fallback: find table by tbody parent
            const tbody = document.getElementById('sourcesTable');
            if (tbody) {
                table = tbody.closest('table');
            }
            // Another fallback: find in sources section
            if (!table) {
                const sourcesSection = document.getElementById('sources');
                if (sourcesSection) {
                    table = sourcesSection.querySelector('table.data-table');
                }
            }
        }
    } else {
        // Fallback to original method
        const tbody = document.getElementById(tableId);
        if (tbody) {
            table = tbody.closest('table');
        }
    }
    
    if (!table) {
        console.error('Table not found for tableId:', tableId, 'tableType:', tableType);
        if (tableType === 'sources') {
            console.error('Sources table lookup failed. Available elements:');
            console.error('sourcesTableDesktop:', document.getElementById('sourcesTableDesktop'));
            console.error('sourcesTable:', document.getElementById('sourcesTable'));
            const sourcesSection = document.getElementById('sources');
            console.error('sources section:', sourcesSection);
            if (sourcesSection) {
                const allTables = sourcesSection.querySelectorAll('table');
                console.error('All tables in sources section:', allTables);
            }
        }
        return;
    }
    
    // Ensure table is visible
    table.style.setProperty('display', 'table', 'important');
    table.style.setProperty('visibility', 'visible', 'important');
    table.style.setProperty('opacity', '1', 'important');
    table.style.setProperty('width', '100%', 'important');
    table.style.setProperty('position', 'relative', 'important');
    table.style.setProperty('z-index', '1', 'important');
    table.style.setProperty('background-color', '#ffffff', 'important');
    table.style.setProperty('border-collapse', 'collapse', 'important');
    
    const tableHead = table.querySelector('thead tr');
    if (tableHead) {
        let headerRow = '';
        
        // Add checkbox and calendar icon headers for events table
        if (tableType === 'events') {
            headerRow += '<th style="width: 40px; text-align: center;"><input type="checkbox" id="selectAllEvents" onchange="toggleSelectAllEvents(this)" title="Select All"></th>';
            headerRow += '<th>📅</th>';
        }
        
        orderedFields.forEach(field => {
            const config = fieldConfig.fields[field] || { label: formatFieldName(field), visible: true };
            if (config.visible !== false) {
                // Add class for description and additional_info columns to apply narrow styling
                const cellClass = (field === 'description' || field === 'additional_info') ? ` class="${field}"` : '';
                if (config.sortable !== false) {
                    headerRow += `<th${cellClass} onclick="sortTable('${tableId}', '${field}')" style="cursor: pointer; user-select: none;" title="Click to sort">${config.label} ↕</th>`;
                } else {
                    headerRow += `<th${cellClass}>${config.label}</th>`;
                }
            }
        });
        
        // Always include Actions header
        headerRow += '<th>Actions</th>';
        
        tableHead.innerHTML = headerRow;
    } else {
        console.error('Table head row not found for tableId:', tableId, 'table:', table);
    }
    
    // Generate data rows
    let rowsHTML = '';
    try {
        rowsHTML = data.map(item => {
        // Make all table rows clickable (double-click)
        let rowClickable = '';
        if (tableType === 'events') {
            rowClickable = 'ondblclick="showEventDetails(event, ' + item.id + ')" style="cursor: pointer;"';
        } else if (tableType === 'venues') {
            rowClickable = 'ondblclick="showVenueDetails(event, ' + item.id + ')" style="cursor: pointer;"';
        } else if (tableType === 'cities') {
            rowClickable = 'ondblclick="showCityDetails(event, ' + item.id + ')" style="cursor: pointer;"';
        } else if (tableType === 'sources') {
            rowClickable = 'ondblclick="showSourceDetails(event, ' + item.id + ')" style="cursor: pointer;"';
        }
        let row = `<tr id="${tableType}-row-${item.id}" ${rowClickable}>`;
        
        // Add checkbox and calendar icon for events
        if (tableType === 'events') {
            const checkbox = `<td style="text-align: center; padding: 8px; width: 40px;" onclick="event.stopPropagation();">
                <input type="checkbox" class="event-checkbox" value="${item.id}" onchange="updateBulkExportButton()" onclick="event.stopPropagation();">
            </td>`;
            row += checkbox;
            const calendarIcon = `<td style="text-align: center; padding: 8px;" onclick="event.stopPropagation();">
                <button onclick="event.stopPropagation(); addEventToCalendar(${item.id})" 
                        class="icon-btn calendar-btn"
                        title="Add to Calendar">
                    📅
                </button>
            </td>`;
            row += calendarIcon;
        }
        
        orderedFields.forEach(field => {
            const config = fieldConfig.fields[field] || { label: formatFieldName(field), visible: true };
            if (config.visible !== false) {
                const value = formatFieldValue(field, item[field], config);
                // Add class for description and additional_info columns to apply narrow styling
                const cellClass = (field === 'description' || field === 'additional_info') ? ` class="${field}"` : '';
                // Ensure cells have content - use &nbsp; if empty to prevent collapse
                const cellContent = value || '&nbsp;';
                row += `<td${cellClass} style="padding: 10px 8px; min-height: 30px;">${cellContent}</td>`;
            }
        });
        
        // Add actions column - use data attributes for event delegation
        row += `<td class="actions-cell">${generateActionButtons(item.id, tableType)}</td>`;
        
        row += '</tr>';
        return row;
        }).join('');
    } catch (error) {
        console.error('Error generating table rows:', error);
        rowsHTML = '<tr><td colspan="100" class="no-results">❌ Error rendering table: ' + error.message + '</td></tr>';
    }
    
    if (rowsHTML.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="100" class="no-results">🔍 Error rendering table</td></tr>';
    } else {
        tableBody.innerHTML = rowsHTML;
        // Verify rows were inserted
        const insertedRows = tableBody.querySelectorAll('tr');
        if (insertedRows.length === 0) {
            console.error('ERROR: Rows HTML generated but no rows found in DOM after insertion!');
        } else {
            // Ensure table body is visible
            tableBody.style.setProperty('display', 'table-row-group', 'important');
            tableBody.style.setProperty('visibility', 'visible', 'important');
            tableBody.style.setProperty('opacity', '1', 'important');
            
            // Attach event listeners using event delegation for better reliability
            // Note: WeakMap prevents duplicate listeners, but event delegation means
            // listeners work for all current and future rows
            attachTableEventListeners(tableBody, tableType);
        }
    }
    
    // Render mobile card views for all table types
    if (tableType === 'events' && tableId === 'eventsTable') {
        renderEventsMobileCards(data);
    } else if (tableType === 'cities' && tableId === 'citiesTable') {
        renderCitiesMobileCards(data);
    } else if (tableType === 'venues' && tableId === 'venuesTable') {
        renderVenuesMobileCards(data);
    } else if (tableType === 'sources' && tableId === 'sourcesTable') {
        renderSourcesMobileCards(data);
    }
    
    // Always update view mode after rendering to ensure correct display
    // Use a small delay to ensure DOM is ready
    setTimeout(() => {
        updateAllTablesViewMode();
        // For sources, ensure at least one view is visible
        // If mobile view doesn't have content, show desktop even on mobile
        if (tableType === 'sources' && tableId === 'sourcesTable') {
            const sourcesDesktop = document.getElementById('sourcesTableDesktop');
            const sourcesMobile = document.getElementById('sourcesTableMobile');
            
            if (sourcesDesktop && sourcesMobile) {
                const mobileDisplay = window.getComputedStyle(sourcesMobile).display;
                const desktopDisplay = window.getComputedStyle(sourcesDesktop).display;
                const mobileHasContent = sourcesMobile.innerHTML.trim().length > 0 && 
                                         !sourcesMobile.innerHTML.includes('Loading sources...') &&
                                         !sourcesMobile.innerHTML.includes('no-results');
                
                // Ensure mobile container is visible if it should be shown
                if (mobileDisplay === 'block') {
                    sourcesMobile.style.setProperty('display', 'block', 'important');
                    sourcesMobile.style.setProperty('visibility', 'visible', 'important');
                    sourcesMobile.style.setProperty('opacity', '1', 'important');
                }
                
                // If both are hidden or mobile is shown but has no content, show desktop
                if ((desktopDisplay === 'none' && mobileDisplay === 'none') || 
                    (mobileDisplay === 'block' && !mobileHasContent)) {
                    sourcesDesktop.style.setProperty('display', 'table', 'important');
                    sourcesMobile.style.setProperty('display', 'none', 'important');
                }
            }
        }
    }, 0);
}

// Render events as mobile-friendly cards
function renderEventsMobileCards(data) {
    const mobileContainer = document.getElementById('eventsTableMobile');
    if (!mobileContainer) return;
    
    if (!data || data.length === 0) {
        mobileContainer.innerHTML = '<div class="no-results">🔍 No events found</div>';
        return;
    }
    
    const fieldConfig = getFieldConfig('events');
    const cardsHTML = data.map(item => {
        const title = item.title || 'Untitled Event';
        const eventType = item.event_type || 'event';
        const startDate = item.start_date || '';
        const startTime = item.start_time || '';
        const venueName = item.venue_name || '';
        const cityName = item.city_name || '';
        const description = item.description || '';
        
        // Format date/time
        let dateTimeStr = '';
        if (startDate) {
            const date = new Date(startDate);
            dateTimeStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            if (startTime) {
                dateTimeStr += ' at ' + startTime;
            }
        }
        
        return `
            <div class="event-mobile-card" id="event-card-${item.id}" onclick="showEventDetails(event, ${item.id})">
                <div class="event-card-header">
                    <div class="event-card-title-row">
                        <input type="checkbox" class="event-checkbox-mobile" value="${item.id}" onchange="updateBulkExportButton()" onclick="event.stopPropagation();">
                        <h3 class="event-card-title">${title}</h3>
                        <button class="event-card-calendar-btn" onclick="event.stopPropagation(); addEventToCalendar(${item.id})" title="Add to Calendar">📅</button>
                    </div>
                    <span class="event-type-badge ${getEventTypeBadgeClass(eventType)}">${eventType}</span>
                </div>
                <div class="event-card-body">
                    ${dateTimeStr ? `<div class="event-card-field"><span class="field-label">📅 When:</span> <span class="field-value">${dateTimeStr}</span></div>` : ''}
                    ${venueName ? `<div class="event-card-field"><span class="field-label">🏛️ Venue:</span> <span class="field-value">${venueName}</span></div>` : ''}
                    ${cityName ? `<div class="event-card-field"><span class="field-label">🌍 City:</span> <span class="field-value">${cityName}</span></div>` : ''}
                    ${description ? `<div class="event-card-field event-card-description"><span class="field-label">📝 Description:</span> <span class="field-value">${description.substring(0, 100)}${description.length > 100 ? '...' : ''}</span></div>` : ''}
                </div>
                <div class="event-card-actions">
                    ${generateActionButtons(item.id, 'events')}
                </div>
            </div>
        `;
    }).join('');
    
    mobileContainer.innerHTML = cardsHTML;
    
    // Show/hide based on screen size
    updateEventsViewMode();
}

// Render cities as mobile-friendly cards
function renderCitiesMobileCards(data) {
    const mobileContainer = document.getElementById('citiesTableMobile');
    if (!mobileContainer) return;
    
    if (!data || data.length === 0) {
        mobileContainer.innerHTML = '<div class="no-results">🔍 No cities found</div>';
        return;
    }
    
    const cardsHTML = data.map(item => {
        const displayName = item.display_name || item.name || 'Unknown City';
        const country = item.country || '';
        const state = item.state || '';
        const timezone = item.timezone || '';
        const venueCount = item.venue_count || 0;
        const eventCount = item.event_count || 0;
        
        return `
            <div class="city-mobile-card" id="city-card-${item.id}" onclick="showCityDetails(event, ${item.id})">
                <div class="mobile-card-header">
                    <h3 class="mobile-card-title">${displayName}</h3>
                </div>
                <div class="mobile-card-body">
                    ${country ? `<div class="mobile-card-field"><span class="field-label">🌍 Country:</span> <span class="field-value">${country}</span></div>` : ''}
                    ${state ? `<div class="mobile-card-field"><span class="field-label">📍 State:</span> <span class="field-value">${state}</span></div>` : ''}
                    ${timezone ? `<div class="mobile-card-field"><span class="field-label">🕐 Timezone:</span> <span class="field-value">${timezone}</span></div>` : ''}
                    <div class="mobile-card-field">
                        <span class="field-label">🏛️ Venues:</span> <span class="field-value">${venueCount}</span>
                        <span class="field-label" style="margin-left: 16px;">🎭 Events:</span> <span class="field-value">${eventCount}</span>
                    </div>
                </div>
                <div class="mobile-card-actions">
                    ${generateActionButtons(item.id, 'cities')}
                </div>
            </div>
        `;
    }).join('');
    
    mobileContainer.innerHTML = cardsHTML;
    updateAllTablesViewMode();
}

// Render venues as mobile-friendly cards
function renderVenuesMobileCards(data) {
    const mobileContainer = document.getElementById('venuesTableMobile');
    if (!mobileContainer) return;
    
    if (!data || data.length === 0) {
        mobileContainer.innerHTML = '<div class="no-results">🔍 No venues found</div>';
        return;
    }
    
    const cardsHTML = data.map(item => {
        const name = item.name || 'Unknown Venue';
        const venueType = item.venue_type || '';
        const cityName = item.city_name || '';
        const address = item.address || '';
        const website = item.website_url || '';
        
        return `
            <div class="venue-mobile-card" id="venue-card-${item.id}" onclick="showVenueDetails(event, ${item.id})">
                <div class="mobile-card-header">
                    <h3 class="mobile-card-title">${name}</h3>
                    ${venueType ? `<span class="venue-type-badge">${venueType}</span>` : ''}
                </div>
                <div class="mobile-card-body">
                    ${cityName ? `<div class="mobile-card-field"><span class="field-label">🌍 City:</span> <span class="field-value">${cityName}</span></div>` : ''}
                    ${address ? `<div class="mobile-card-field"><span class="field-label">📍 Address:</span> <span class="field-value">${address.substring(0, 60)}${address.length > 60 ? '...' : ''}</span></div>` : ''}
                    ${website ? `<div class="mobile-card-field"><span class="field-label">🌐 Website:</span> <span class="field-value"><a href="${website}" target="_blank" onclick="event.stopPropagation();">Visit</a></span></div>` : ''}
                </div>
                <div class="mobile-card-actions">
                    ${generateActionButtons(item.id, 'venues')}
                </div>
            </div>
        `;
    }).join('');
    
    mobileContainer.innerHTML = cardsHTML;
    updateAllTablesViewMode();
}

// Render sources as mobile-friendly cards
function renderSourcesMobileCards(data) {
    const mobileContainer = document.getElementById('sourcesTableMobile');
    if (!mobileContainer) {
        console.error('sourcesTableMobile container not found!');
        return;
    }
    
    if (!data || data.length === 0) {
        mobileContainer.innerHTML = '<div class="no-results">🔍 No sources found</div>';
        return;
    }
    
    try {
        const cardsHTML = data.map(item => {
            const name = item.name || 'Unknown Source';
            const handle = item.handle || '';
            const sourceType = item.source_type || '';
            const cityName = item.city_name || '';
            const isActive = item.is_active ? '🟢 Active' : '🔴 Inactive';
            const eventsFound = item.events_found_count || 0;
            
            return `
                <div class="source-mobile-card" id="source-card-${item.id}" onclick="showSourceDetails(event, ${item.id})">
                    <div class="mobile-card-header">
                        <h3 class="mobile-card-title">${name}</h3>
                        <span class="source-type-badge">${sourceType}</span>
                    </div>
                    <div class="mobile-card-body">
                        ${handle ? `<div class="mobile-card-field"><span class="field-label">📱 Handle:</span> <span class="field-value">${handle}</span></div>` : ''}
                        ${cityName ? `<div class="mobile-card-field"><span class="field-label">🌍 City:</span> <span class="field-value">${cityName}</span></div>` : ''}
                        <div class="mobile-card-field">
                            <span class="field-label">Status:</span> <span class="field-value">${isActive}</span>
                            <span class="field-label" style="margin-left: 16px;">Events:</span> <span class="field-value">${eventsFound}</span>
                        </div>
                    </div>
                    <div class="mobile-card-actions">
                        ${generateActionButtons(item.id, 'sources')}
                    </div>
                </div>
            `;
        }).join('');
        
        mobileContainer.innerHTML = cardsHTML;
        
        // Ensure mobile container is visible after rendering
        mobileContainer.style.setProperty('display', 'block', 'important');
        mobileContainer.style.setProperty('visibility', 'visible', 'important');
        mobileContainer.style.setProperty('opacity', '1', 'important');
    } catch (error) {
        console.error('Error rendering sources mobile cards:', error);
        mobileContainer.innerHTML = '<div class="no-results" style="color: #dc3545;">❌ Error rendering sources: ' + error.message + '</div>';
    }
}

// Update all tables view mode (table vs cards) based on screen size
function updateAllTablesViewMode() {
    const isMobile = window.innerWidth <= 768;
    
    // Events
    const eventsDesktop = document.getElementById('eventsTableDesktop');
    const eventsMobile = document.getElementById('eventsTableMobile');
    if (eventsDesktop && eventsMobile) {
        eventsDesktop.style.setProperty('display', isMobile ? 'none' : 'table', 'important');
        eventsMobile.style.setProperty('display', isMobile ? 'block' : 'none', 'important');
    }
    
    // Cities
    const citiesDesktop = document.getElementById('citiesTableDesktop');
    const citiesMobile = document.getElementById('citiesTableMobile');
    if (citiesDesktop && citiesMobile) {
        citiesDesktop.style.setProperty('display', isMobile ? 'none' : 'table', 'important');
        citiesMobile.style.setProperty('display', isMobile ? 'block' : 'none', 'important');
    }
    
    // Venues
    const venuesDesktop = document.getElementById('venuesTableDesktop');
    const venuesMobile = document.getElementById('venuesTableMobile');
    if (venuesDesktop && venuesMobile) {
        venuesDesktop.style.setProperty('display', isMobile ? 'none' : 'table', 'important');
        venuesMobile.style.setProperty('display', isMobile ? 'block' : 'none', 'important');
    }
    
    // Sources - be more careful here
    const sourcesDesktop = document.getElementById('sourcesTableDesktop');
    const sourcesMobile = document.getElementById('sourcesTableMobile');
    
    if (sourcesDesktop) {
        if (sourcesMobile) {
            // Check if mobile has content - if not, show desktop even on mobile
            const mobileHasContent = sourcesMobile.innerHTML.trim().length > 0 && 
                                     !sourcesMobile.innerHTML.includes('Loading sources...') &&
                                     !sourcesMobile.innerHTML.includes('no-results');
            
            if (isMobile && mobileHasContent) {
                // Mobile view has content, use it
                sourcesDesktop.style.setProperty('display', 'none', 'important');
                sourcesMobile.style.setProperty('display', 'block', 'important');
            } else {
                // Desktop view or mobile has no content - show desktop
                sourcesDesktop.style.setProperty('display', 'table', 'important');
                sourcesMobile.style.setProperty('display', 'none', 'important');
            }
        } else {
            // If mobile doesn't exist, always show desktop
            sourcesDesktop.style.setProperty('display', 'table', 'important');
        }
    } else {
        console.error('Sources desktop table not found!');
    }
}

// Legacy function name for backward compatibility
function updateEventsViewMode() {
    updateAllTablesViewMode();
}

// Update view mode on window resize
window.addEventListener('resize', updateAllTablesViewMode);

// Field configuration for different table types
function getFieldConfig(tableType) {
    const configs = {
        venues: {
            order: ['id', 'name', 'venue_type', 'city_name', 'address', 'opening_hours', 'phone_number', 'email', 'website_url', 'ticketing_url', 'image_url', 'latitude', 'longitude', 'facebook_url', 'instagram_url', 'twitter_url', 'youtube_url', 'tiktok_url', 'holiday_hours', 'admission_fee', 'tour_info', 'description', 'additional_info', 'created_at', 'updated_at'],
            fields: {
                id: { label: 'ID', visible: true, sortable: true },
                name: { label: 'Name', visible: true, sortable: true },
                venue_type: { label: 'Type', visible: true, sortable: true },
                city_name: { label: 'City', visible: true, sortable: true },
                address: { label: 'Address', visible: true, sortable: true },
                opening_hours: { label: 'Hours', visible: true, sortable: false },
                phone_number: { label: 'Phone', visible: true, sortable: false },
                email: { label: 'Email', visible: true, sortable: false },
                website_url: { label: 'Website', visible: true, sortable: false },
                ticketing_url: { label: 'Ticketing', visible: true, sortable: false },
                image_url: { label: 'Image', visible: true, sortable: false },
                latitude: { label: 'Latitude', visible: true, sortable: true },
                longitude: { label: 'Longitude', visible: true, sortable: true },
                facebook_url: { label: 'Facebook', visible: true, sortable: false },
                instagram_url: { label: 'Instagram', visible: true, sortable: false },
                twitter_url: { label: 'Twitter', visible: true, sortable: false },
                youtube_url: { label: 'YouTube', visible: true, sortable: false },
                tiktok_url: { label: 'TikTok', visible: true, sortable: false },
                holiday_hours: { label: 'Holiday Hours', visible: true, sortable: false },
                admission_fee: { label: 'Admission', visible: true, sortable: false },
                tour_info: { label: 'Tour Info', visible: true, sortable: false },
                description: { label: 'Description', visible: true, sortable: false },
                additional_info: { label: 'Additional Info', visible: true, sortable: false },
                created_at: { label: 'Created', visible: true, sortable: true },
                updated_at: { label: 'Updated', visible: true, sortable: true }
            }
        },
        sources: {
            order: ['id', 'name', 'handle', 'source_type', 'city_name', 'is_active', 'events_found_count'],
            fields: {
                id: { label: 'ID', visible: true, sortable: true },
                name: { label: 'Name', visible: true, sortable: true },
                handle: { label: 'Handle', visible: true, sortable: true },
                source_type: { label: 'Type', visible: true, sortable: true },
                city_name: { label: 'City', visible: true, sortable: true },
                event_types: { label: 'Event Types', visible: false, sortable: false },
                reliability_score: { label: 'Reliability', visible: false, sortable: true },
                posting_frequency: { label: 'Frequency', visible: false, sortable: true },
                is_active: { label: 'Active', visible: true, sortable: true },
                events_found_count: { label: 'Events', visible: true, sortable: true },
                last_checked: { label: 'Last Checked', visible: false, sortable: true },
                created_at: { label: 'Created', visible: false, sortable: true },
                updated_at: { label: 'Updated', visible: false, sortable: true }
            }
        },
        events: {
            order: ['id', 'title', 'description', 'start_date', 'start_time', 'end_date', 'end_time', 'event_type', 'venue_name', 'city_name', 'created_at', 'updated_at'],
            fields: {
                id: { label: 'ID', visible: true, sortable: true },
                title: { label: 'Title', visible: true, sortable: true },
                description: { label: 'Description', visible: true, sortable: false },
                start_date: { label: 'Start Date', visible: true, sortable: true },
                start_time: { label: 'Start Time', visible: true, sortable: true },
                end_date: { label: 'End Date', visible: true, sortable: true },
                end_time: { label: 'End Time', visible: true, sortable: true },
                event_type: { label: 'Type', visible: true, sortable: true },
                venue_name: { label: 'Venue', visible: true, sortable: true },
                city_name: { label: 'City', visible: true, sortable: true },
                created_at: { label: 'Created', visible: true, sortable: true },
                updated_at: { label: 'Updated', visible: true, sortable: true }
            }
        },
        cities: {
            order: ['id', 'name', 'state', 'country', 'display_name', 'timezone', 'venue_count', 'event_count', 'created_at', 'updated_at'],
            fields: {
                id: { label: 'ID', visible: true, sortable: true },
                name: { label: 'Name', visible: true, sortable: true },
                state: { label: 'State', visible: true, sortable: true },
                country: { label: 'Country', visible: true, sortable: true },
                display_name: { label: 'Display Name', visible: true, sortable: true },
                timezone: { label: 'Timezone', visible: true, sortable: true },
                venue_count: { label: 'Venues', visible: true, sortable: true },
                event_count: { label: 'Events', visible: true, sortable: true },
                created_at: { label: 'Created', visible: true, sortable: true },
                updated_at: { label: 'Updated', visible: true, sortable: true }
            }
        }
    };
    
    return configs[tableType] || {
        order: ['id'],
        fields: { id: { label: 'ID', visible: true } }
    };
}

// Format field names for unknown fields
function formatFieldName(fieldName) {
    return fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Helper function to normalize UTC timestamps (append 'Z' if missing timezone)
function normalizeUTCTimestamp(timestamp) {
    if (!timestamp || typeof timestamp !== 'string') {
        return timestamp;
    }
    const dateStr = timestamp.trim();
    // If it's an ISO datetime without timezone indicator, append 'Z' for UTC
    if (dateStr.includes('T') && !dateStr.endsWith('Z') && !dateStr.match(/[+-]\d{2}:?\d{2}$/)) {
        return dateStr + 'Z';
    }
    return dateStr;
}

// Format field values based on field type and configuration
function formatFieldValue(fieldName, value, config = {}) {
    if (value === null || value === undefined || value === '') {
        return '';
    }
    
    // Special formatting for specific fields
    switch (fieldName) {
        case 'website_url':
        case 'url':
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1976d2; text-decoration: none;">${value}</a>`;
        
        case 'ticketing_url':
            // Format ticketing URLs (Eventbrite, Ticketmaster, etc.) as clickable links
            // Show the full URL so users can see and copy it
            if (value.includes('eventbrite.com')) {
                return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1976d2; text-decoration: none; word-break: break-all;">${value}</a>`;
            } else if (value.includes('ticketmaster.com') || value.includes('ticketmaster')) {
                return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #026CDF; text-decoration: none; word-break: break-all;">${value}</a>`;
            }
            // Generic ticketing URL
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1976d2; text-decoration: none; word-break: break-all;">${value}</a>`;
        
        case 'youtube_url':
            // Handle both full URLs and channel names
            if (value.startsWith('@')) {
                // It's already a channel handle like @username
                const channel = value.substring(1); // Remove @
                return `<a href="https://www.youtube.com/@${channel}" target="_blank" onclick="event.stopPropagation();" style="color: #FF0000; text-decoration: none;">${value}</a>`;
            } else if (value.includes('youtube.com')) {
                // It's a full URL - extract the meaningful part
                const channelMatch = value.match(/youtube\.com\/(?:c\/|user\/|@)?([^\/\?]+)/);
                if (channelMatch) {
                    const channel = channelMatch[1];
                    // Clean up the channel name for display
                    const displayName = channel.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #FF0000; text-decoration: none;">${displayName}</a>`;
                }
            }
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #FF0000; text-decoration: none;">YouTube</a>`;
        
        case 'tiktok_url':
            // Handle both full URLs and usernames
            if (value.startsWith('@')) {
                // It's already a username like @username
                const username = value.substring(1); // Remove @
                return `<a href="https://www.tiktok.com/@${username}" target="_blank" onclick="event.stopPropagation();" style="color: #000000; text-decoration: none;">${value}</a>`;
            } else if (value.includes('tiktok.com')) {
                // It's a full URL
                const tiktokMatch = value.match(/tiktok\.com\/@([^\/\?]+)/);
                if (tiktokMatch) {
                    const username = tiktokMatch[1];
                    return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #000000; text-decoration: none;">@${username}</a>`;
                }
            }
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #000000; text-decoration: none;">TikTok</a>`;
        
        case 'facebook_url':
            // Extract page name from Facebook URL
            const facebookMatch = value.match(/facebook\.com\/([^\/\?]+)/);
            if (facebookMatch) {
                const pageName = facebookMatch[1];
                return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1877F2; text-decoration: none;">${pageName}</a>`;
            }
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1877F2; text-decoration: none;">Facebook</a>`;
        
        case 'instagram_url':
            // Handle both full URLs and @handles
            if (value.startsWith('@')) {
                // It's already a handle like @username
                const handle = value.substring(1); // Remove @
                return `<a href="https://www.instagram.com/${handle}/" target="_blank" onclick="event.stopPropagation();" style="color: #E4405F; text-decoration: none;">${value}</a>`;
            } else if (value.includes('instagram.com')) {
                // It's a full URL
                const instagramMatch = value.match(/instagram\.com\/([^\/\?]+)/);
                if (instagramMatch) {
                    const handle = instagramMatch[1];
                    return `<a href="https://www.instagram.com/${handle}/" target="_blank" onclick="event.stopPropagation();" style="color: #E4405F; text-decoration: none;">@${handle}</a>`;
                }
            }
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #E4405F; text-decoration: none;">Instagram</a>`;
        
        case 'twitter_url':
            // Handle both full URLs and @handles
            if (value.startsWith('@')) {
                // It's already a handle like @username
                const handle = value.substring(1); // Remove @
                return `<a href="https://twitter.com/${handle}" target="_blank" onclick="event.stopPropagation();" style="color: #1DA1F2; text-decoration: none;">${value}</a>`;
            } else if (value.includes('twitter.com')) {
                // It's a full URL
                const twitterMatch = value.match(/twitter\.com\/([^\/\?]+)/);
                if (twitterMatch) {
                    const handle = twitterMatch[1];
                    return `<a href="https://twitter.com/${handle}" target="_blank" onclick="event.stopPropagation();" style="color: #1DA1F2; text-decoration: none;">@${handle}</a>`;
                }
            }
            return `<a href="${value}" target="_blank" onclick="event.stopPropagation();" style="color: #1DA1F2; text-decoration: none;">Twitter</a>`;
        
        case 'image_url':
            // Just show "View" text in table - no link to prevent browser from trying to load image
            // The image can be viewed in the details modal
            return value ? '<span style="color: #666;">View in details</span>' : '';
        
        case 'handle':
            if (value.startsWith('@') && value.includes('instagram')) {
                const handle = value.replace('@', '');
                return `<a href="https://www.instagram.com/${handle}" target="_blank" style="color: #E4405F; text-decoration: none;">${value}</a>`;
            }
            return value;
        
        case 'source_type':
            return `<span class="badge badge-${value}">${value}</span>`;
        
        case 'venue_type':
            return `<span class="badge">${value}</span>`;
        
        case 'event_type':
            return `<span class="badge badge-event">${value}</span>`;
        
        case 'is_active':
            return value ? '✅' : '❌';
        
        case 'reliability_score':
            return `${value}/10`;
        
        case 'event_types':
            // Handle event types as array or string with improved styling
            if (Array.isArray(value)) {
                // Already an array from the API
                return value.map(type => {
                    const cleanType = type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    const badgeClass = getEventTypeBadgeClass(type);
                    return `<span class="badge ${badgeClass}" title="${type}">${cleanType}</span>`;
                }).join(' ');
            } else if (value && typeof value === 'string') {
                try {
                    // Try to parse as JSON array
                    const types = JSON.parse(value);
                    if (Array.isArray(types)) {
                        return types.map(type => {
                            const cleanType = type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                            const badgeClass = getEventTypeBadgeClass(type);
                            return `<span class="badge ${badgeClass}" title="${type}">${cleanType}</span>`;
                        }).join(' ');
                    }
                } catch (e) {
                    // If not JSON, treat as comma-separated
                    return value.split(',').map(type => {
                        const cleanType = type.trim().replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        const badgeClass = getEventTypeBadgeClass(type.trim());
                        return `<span class="badge ${badgeClass}" title="${type.trim()}">${cleanType}</span>`;
                    }).join(' ');
                }
            }
            return '';
        
        case 'created_at':
        case 'updated_at':
        case 'last_checked':
            try {
                // Format datetime with time (timestamps are stored in UTC)
                if (value && typeof value === 'string') {
                    // Normalize UTC timestamp (append 'Z' if missing timezone)
                    const normalizedTimestamp = normalizeUTCTimestamp(value);
                    
                    // Parse as UTC and convert to browser's local timezone
                    const date = new Date(normalizedTimestamp);
                    if (!isNaN(date.getTime())) {
                        // Use browser's locale and timezone automatically (no hardcoding)
                        // toLocaleString() automatically uses browser's timezone and locale
                        return date.toLocaleString(undefined, {
                            month: '2-digit',
                            day: '2-digit',
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: true
                        });
                    }
                    // Fallback: try to parse as date string
                    const [year, month, day] = value.split('-');
                    if (year && month && day) {
                        return `${month}/${day}/${year}`;
                    }
                }
                return value || '';
            } catch (e) {
                console.error('Error formatting timestamp:', e, value);
                return value || '';
            }
        
        case 'start_date':
        case 'end_date':
            try {
                // Parse date string directly without timezone conversion
                if (value && typeof value === 'string') {
                    const [year, month, day] = value.split('-');
                    return `${month}/${day}/${year}`;
                }
                return value;
            } catch (e) {
                return value;
            }
        
        case 'start_time':
        case 'end_time':
            try {
                return new Date(`2000-01-01T${value}`).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            } catch (e) {
                return value;
            }
        
        case 'description':
        case 'tour_info':
            if (value.length > 100) {
                return `<span title="${value}">${value.substring(0, 100)}...</span>`;
            }
            return value;
        
        case 'additional_info':
            try {
                const info = JSON.parse(value);
                if (info.closure_status) {
                    const status = info.closure_status;
                    const reason = info.closure_reason || '';
                    let statusIcon = '';
                    let statusClass = '';
                    
                    if (status === 'closed') {
                        statusIcon = '🔴';
                        statusClass = 'closure-closed';
                    } else if (status === 'open') {
                        statusIcon = '🟢';
                        statusClass = 'closure-open';
                    } else {
                        statusIcon = '🟡';
                        statusClass = 'closure-unknown';
                    }
                    
                    return `<div class="closure-status ${statusClass}">
                        <strong>${statusIcon} ${status.toUpperCase()}</strong>
                        ${reason ? `<br><small>${reason}</small>` : ''}
                    </div>`;
                }
            } catch (e) {
                // If not JSON, treat as regular text
            }
            
            if (value.length > 100) {
                return `<span title="${value}">${value.substring(0, 100)}...</span>`;
            }
            return value;
        
        case 'venue_count':
        case 'event_count':
            const count = parseInt(value) || 0;
            const badgeClass = count === 0 ? 'badge-zero' : count >= 5 ? 'badge-high' : 'badge';
            return `<span class="badge ${badgeClass}">${count}</span>`;
        
        default:
            return value;
    }
}

// Generate action buttons based on table type
function generateActionButtons(id, tableType) {
    const isMobile = window.innerWidth <= 768;
    // Keep onclick for backward compatibility, but event delegation will also work
    const getEditFunc = (type) => {
        switch(type) {
            case 'venues': return 'editVenue';
            case 'sources': return 'editSource';
            case 'events': return 'editEvent';
            case 'cities': return 'editCity';
            default: return 'editItem';
        }
    };
    const getDeleteFunc = (type) => {
        switch(type) {
            case 'venues': return 'deleteVenue';
            case 'sources': return 'deleteSource';
            case 'events': return 'deleteEvent';
            case 'cities': return 'deleteCity';
            default: return 'deleteItem';
        }
    };
    
    const editFunc = getEditFunc(tableType);
    const deleteFunc = getDeleteFunc(tableType);
    
    // On mobile, show text labels with icons for better usability
    if (isMobile) {
        return `<button onclick="event.stopPropagation(); ${editFunc}(${id})" class="icon-btn edit-icon-btn mobile-action-btn" data-edit-id="${id}" data-edit-type="${tableType}" title="Edit"><span class="btn-icon">✏️</span><span class="btn-text">Edit</span></button> <button onclick="event.stopPropagation(); ${deleteFunc}(${id})" class="icon-btn delete-icon-btn mobile-action-btn" data-delete-id="${id}" data-delete-type="${tableType}" title="Delete"><span class="btn-icon">🗑️</span><span class="btn-text">Delete</span></button>`;
    } else {
        // Desktop: show icons only
        return `<button onclick="event.stopPropagation(); ${editFunc}(${id})" class="icon-btn edit-icon-btn" data-edit-id="${id}" data-edit-type="${tableType}" title="Edit">✏️</button> <button onclick="event.stopPropagation(); ${deleteFunc}(${id})" class="icon-btn delete-icon-btn" data-delete-id="${id}" data-delete-type="${tableType}" title="Delete">🗑️</button>`;
    }
}

// Attach event listeners to table rows and buttons using event delegation
// Use WeakMap to track which table bodies already have listeners attached
const tableListenersMap = new WeakMap();

function attachTableEventListeners(tableBody, tableType) {
    // Check if listeners are already attached to this table body
    if (tableListenersMap.has(tableBody)) {
        return; // Listeners already attached, skip
    }
    
    // Mark this table body as having listeners attached
    tableListenersMap.set(tableBody, true);
    
    // Handle row double-click
    tableBody.addEventListener('dblclick', function(e) {
        const row = e.target.closest('tr');
        if (!row || row.classList.contains('no-results')) return;
        
        const rowId = row.id;
        const match = rowId.match(new RegExp(`${tableType}-row-(\\d+)`));
        if (!match) return;
        
        // Don't trigger if clicking on buttons or links
        if (e.target.closest('button') || e.target.closest('a') || e.target.closest('input')) {
            return;
        }
        
        const id = parseInt(match[1]);
        e.stopPropagation();
        e.preventDefault();
        
        switch(tableType) {
            case 'events':
                if (typeof showEventDetails === 'function') showEventDetails(e, id);
                break;
            case 'venues':
                if (typeof showVenueDetails === 'function') showVenueDetails(e, id);
                break;
            case 'cities':
                if (typeof showCityDetails === 'function') showCityDetails(e, id);
                break;
            case 'sources':
                if (typeof showSourceDetails === 'function') showSourceDetails(e, id);
                break;
        }
    });
    
    // Handle edit button clicks - use data attributes for reliability
    tableBody.addEventListener('click', function(e) {
        const editBtn = e.target.closest('.edit-icon-btn');
        if (!editBtn) return;
        
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        // Try data attributes first (more reliable)
        const id = editBtn.getAttribute('data-edit-id');
        const btnType = editBtn.getAttribute('data-edit-type') || tableType;
        
        if (id) {
            const itemId = parseInt(id);
            switch(btnType) {
                case 'events':
                    if (typeof editEvent === 'function') {
                        editEvent(itemId);
                    } else {
                        console.error('editEvent function not found');
                    }
                    break;
                case 'venues':
                    if (typeof editVenue === 'function') {
                        editVenue(itemId);
                    } else {
                        console.error('editVenue function not found');
                    }
                    break;
                case 'cities':
                    if (typeof editCity === 'function') {
                        editCity(itemId);
                    } else {
                        console.error('editCity function not found');
                    }
                    break;
                case 'sources':
                    if (typeof editSource === 'function') {
                        editSource(itemId);
                    } else {
                        console.error('editSource function not found');
                    }
                    break;
            }
            return;
        }
        
        // Fallback to onclick attribute parsing
        const onclickAttr = editBtn.getAttribute('onclick');
        if (onclickAttr) {
            const match = onclickAttr.match(/edit\w+\((\d+)\)/);
            if (match) {
                const itemId = parseInt(match[1]);
                switch(tableType) {
                    case 'events':
                        if (typeof editEvent === 'function') editEvent(itemId);
                        break;
                    case 'venues':
                        if (typeof editVenue === 'function') editVenue(itemId);
                        break;
                    case 'cities':
                        if (typeof editCity === 'function') editCity(itemId);
                        break;
                    case 'sources':
                        if (typeof editSource === 'function') editSource(itemId);
                        break;
                }
            }
        }
    });
    
    // Handle delete button clicks - use data attributes for reliability
    tableBody.addEventListener('click', function(e) {
        const deleteBtn = e.target.closest('.delete-icon-btn');
        if (!deleteBtn) return;
        
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        // Try data attributes first (more reliable)
        const id = deleteBtn.getAttribute('data-delete-id');
        const btnType = deleteBtn.getAttribute('data-delete-type') || tableType;
        
        if (id) {
            const itemId = parseInt(id);
            switch(btnType) {
                case 'events':
                    if (typeof deleteEvent === 'function') deleteEvent(itemId);
                    break;
                case 'venues':
                    if (typeof deleteVenue === 'function') deleteVenue(itemId);
                    break;
                case 'cities':
                    if (typeof deleteCity === 'function') deleteCity(itemId);
                    break;
                case 'sources':
                    if (typeof deleteSource === 'function') deleteSource(itemId);
                    break;
            }
            return;
        }
        
        // Fallback to onclick attribute parsing
        const onclickAttr = deleteBtn.getAttribute('onclick');
        if (onclickAttr) {
            const match = onclickAttr.match(/delete\w+\((\d+)\)/);
            if (match) {
                const itemId = parseInt(match[1]);
                switch(tableType) {
                    case 'events':
                        if (typeof deleteEvent === 'function') deleteEvent(itemId);
                        break;
                    case 'venues':
                        if (typeof deleteVenue === 'function') deleteVenue(itemId);
                        break;
                    case 'cities':
                        if (typeof deleteCity === 'function') deleteCity(itemId);
                        break;
                    case 'sources':
                        if (typeof deleteSource === 'function') deleteSource(itemId);
                        break;
                }
            }
        }
    });
}
