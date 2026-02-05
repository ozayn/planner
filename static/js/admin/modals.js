// Image Upload Functions
function showEventDetails(clickEvent, eventId) {
    // Show the modal immediately - first thing, no checks
    const modal = document.getElementById('eventDetailsModal');
    const contentDiv = document.getElementById('eventDetailsContent');
    modal.style.display = 'block';
    contentDiv.innerHTML = '<div style="padding: 20px; text-align: center;">Loading...</div>';
    
    // Defer all processing - use requestAnimationFrame for smoother experience
    requestAnimationFrame(() => {
        // Find the event data
        const event = window.allEvents && window.allEvents.find(e => e.id == eventId);
        if (!event) {
            modal.style.display = 'none';
            return;
        }
        
        // Generate and populate content
        const content = generateEventDetailsHTML(event);
        contentDiv.innerHTML = content;
    });
}

function showVenueDetails(clickEvent, venueId) {
    // Get elements once
    const modal = document.getElementById('venueDetailsModal');
    const contentDiv = document.getElementById('venueDetailsContent');
    
    // Show modal instantly using cssText for maximum performance
    modal.style.cssText = 'display: block !important;';
    contentDiv.innerHTML = '<div style="padding: 20px; text-align: center;">Loading...</div>';
    
    // Defer all processing
    requestAnimationFrame(() => {
        const venue = window.allVenues && window.allVenues.find(v => v.id == venueId || String(v.id) === String(venueId));
        if (!venue) {
            modal.style.display = 'none';
            return;
        }
        
        contentDiv.innerHTML = generateVenueDetailsHTML(venue);
        
        // Lazy load images
        requestAnimationFrame(() => {
            modal.querySelectorAll('img[data-src]').forEach(img => {
                img.src = img.getAttribute('data-src');
                img.removeAttribute('data-src');
            });
        });
    });
}

function showCityDetails(clickEvent, cityId) {
    // Get elements once
    const modal = document.getElementById('cityDetailsModal');
    const contentDiv = document.getElementById('cityDetailsContent');
    
    // Show modal instantly using cssText for maximum performance
    modal.style.cssText = 'display: block !important;';
    contentDiv.innerHTML = '<div style="padding: 20px; text-align: center;">Loading...</div>';
    
    // Defer all processing
    requestAnimationFrame(() => {
        const city = window.allCities && window.allCities.find(c => c.id == cityId || String(c.id) === String(cityId));
        if (!city) {
            modal.style.display = 'none';
            return;
        }
        
        contentDiv.innerHTML = generateCityDetailsHTML(city);
    });
}

function showSourceDetails(clickEvent, sourceId) {
    // Prevent if clicking on a link or button
    if (clickEvent && clickEvent.target) {
        const target = clickEvent.target;
        const isLink = target.tagName === 'A' || target.closest('a');
        const isButton = target.tagName === 'BUTTON' || target.closest('button');
        if (isLink || isButton) {
            return;
        }
    }
    
    // Find the source data
    const source = window.allSources.find(s => s.id == sourceId);
    if (!source) {
        alert('Source not found');
        return;
    }
    
    // Populate the source details modal
    const content = generateSourceDetailsHTML(source);
    document.getElementById('sourceDetailsContent').innerHTML = content;
    
    // Show the modal
    document.getElementById('sourceDetailsModal').style.display = 'block';
}

function generateEventDetailsHTML(event) {
    // Helper function to format timestamps (converts UTC to local timezone)
    const formatTimestamp = (timestamp) => {
        if (!timestamp) return '';
        try {
            // Ensure normalizeUTCTimestamp is accessible (defined at top level)
            if (typeof normalizeUTCTimestamp === 'function') {
                // Normalize UTC timestamp (append 'Z' if missing timezone)
                const normalizedTimestamp = normalizeUTCTimestamp(timestamp);
                const date = new Date(normalizedTimestamp);
                // Format using browser's locale and timezone automatically
                const options = { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                };
                return date.toLocaleString(undefined, options);
            } else {
                // Fallback if function not available
                const date = new Date(timestamp + (timestamp.includes('T') && !timestamp.endsWith('Z') && !timestamp.match(/[+-]\d{2}:?\d{2}$/) ? 'Z' : ''));
                return date.toLocaleString(undefined, {
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                });
            }
        } catch (e) {
            console.error('Error formatting timestamp:', e, timestamp);
            return timestamp; // Fallback to original if parsing fails
        }
    };
    
    // Helper function to add field only if value exists
    const addField = (label, value, isLink = false, isTimestamp = false) => {
        if (!value || value === 'N/A' || value === '') return '';
        let displayValue = value;
        if (isTimestamp) {
            displayValue = formatTimestamp(value);
        } else if (isLink) {
            displayValue = `<a href="${value}" target="_blank">${value}</a>`;
        }
        return `<div style="margin-bottom: 8px;"><strong>${label}:</strong> ${displayValue}</div>`;
    };
    
    // Helper function to calculate duration between two times
    const calculateDuration = (startTime, endTime) => {
        if (!startTime || !endTime) return null;
        try {
            const start = new Date('2000-01-01 ' + startTime);
            const end = new Date('2000-01-01 ' + endTime);
            const diffMs = end - start;
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
            
            if (diffHours > 0 && diffMinutes > 0) {
                return `${diffHours}h ${diffMinutes}m`;
            } else if (diffHours > 0) {
                return `${diffHours}h`;
            } else {
                return `${diffMinutes}m`;
            }
        } catch (e) {
            return null;
        }
    };
    
    // Format description to show more text
    const formatDescription = (desc) => {
        if (!desc) return '';
        // Show first 500 characters, with "..." if longer
        if (desc.length > 500) {
            return desc.substring(0, 500) + '...';
        }
        return desc;
    };
    
    const displayImageUrl = event.image_url || (event.venue_id && window.allVenues && (() => {
        const v = window.allVenues.find(x => x.id === event.venue_id);
        return v && v.image_url ? v.image_url : null;
    })());
    
    let html = `
        <!-- Event Header with Image -->
        <div class="event-details-header" style="display: grid; grid-template-columns: ${displayImageUrl ? '1fr 300px' : '1fr'}; gap: 20px; margin-bottom: 25px;">
            <div>
                <div style="background: linear-gradient(135deg, #ff8c42 0%, #ff6b35 100%); color: white; padding: 25px; border-radius: 12px; text-align: center;">
                    <h2 style="margin: 0; font-size: 26px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">${event.title || 'Untitled Event'}</h2>
                    <div style="margin-top: 8px; font-size: 16px; opacity: 0.9;">
                        ${event.event_type ? `<span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; margin-right: 8px;">${event.event_type}</span>` : ''}
                        ${event.venue_name ? `<span style="opacity: 0.8;">📍 ${event.venue_name}</span>` : ''}
                    </div>
                </div>
                ${event.description ? `
                    <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #ff8c42;">
                        <h4 style="margin: 0 0 8px 0; color: #4a5568; font-size: 14px; font-weight: 600;">📝 Description</h4>
                        <p style="margin: 0; color: #2d3748; line-height: 1.6; white-space: pre-wrap;">${formatDescription(event.description)}</p>
                        ${event.description.length > 500 ? `<small style="color: #666; font-style: italic;">(Truncated - full description available in database)</small>` : ''}
                    </div>
                ` : ''}
            </div>
            ${displayImageUrl ? `
                <div>
                    <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 14px;">🖼️ Event Image</h4>
                    <a href="${displayImageUrl.startsWith('/') ? (window.location.origin || '') + displayImageUrl : displayImageUrl}" target="_blank" style="display: block; text-decoration: none; border-radius: 12px; overflow: hidden; background: #f5f5f5; min-height: 120px;">
                        <img src="${displayImageUrl.replace(/"/g, '&quot;')}" alt="${(event.title || 'Event').replace(/"/g, '&quot;')}" 
                             style="width: 100%; max-width: 100%; height: auto; display: block; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; transition: transform 0.2s; background: #f5f5f5;"
                             onerror="this.onerror=null; this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='flex';"
                             onmouseover="this.style.transform='scale(1.02)'"
                             onmouseout="this.style.transform='scale(1)'">
                        <div class="image-fallback-placeholder" style="display: none; flex-direction: column; align-items: center; justify-content: center; min-height: 120px; background: #f0f0f0; border-radius: 12px; color: #666; font-size: 13px; padding: 16px; text-align: center;">
                            Image could not be loaded.<br><small>Add GOOGLE_MAPS_API_KEY to .env for venue photos</small>
                        </div>
                    </a>
                    <small style="display: block; margin-top: 8px; color: #666; text-align: center;">Click to open in new tab</small>
                </div>
            ` : ''}
        </div>
        
        <div class="event-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📋 Basic Information</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 6px; font-size: 0.875rem;"><strong>ID:</strong> ${event.id}</div>
                    ${addField('Type', event.event_type)}
                    ${addField('Price', event.price ? `$${event.price}` : (event.admission_price ? `$${event.admission_price}` : null))}
                    ${addField('Language', event.language)}
                    ${addField('Organizer', event.organizer)}
                    ${addField('Is Online', event.is_online ? 'Yes (Virtual Event)' : 'No')}
                    <div style="margin-bottom: 8px;"><strong>Selected:</strong> ${event.is_selected ? 'Yes' : 'No'}</div>
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📅 Date & Time</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Start Date', event.start_date)}
                    ${addField('End Date', event.end_date)}
                    ${addField('Start Time', event.start_time)}
                    ${addField('End Time', event.end_time)}
                    ${addField('Duration', event.start_time && event.end_time ? calculateDuration(event.start_time, event.end_time) : null)}
                    <div style="margin-bottom: 8px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196f3;">
                        <strong>🌍 Timezone:</strong> ${event.city_timezone || 'Not specified'}
                        ${event.city_timezone ? `<br><small style="color: #666;">All times shown in local timezone</small>` : ''}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="event-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📍 Location</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Start Location', event.start_location)}
                    ${addField('End Location', event.end_location)}
                    ${addField('City', event.city_name)}
                    ${addField('Venue', event.venue_name)}
                    ${addField('Venue Address', event.venue_address)}
                    ${addField('Coordinates', event.start_latitude && event.start_longitude ? `${event.start_latitude}, ${event.start_longitude}` : null)}
                    ${event.maps_link ? `<div style="margin-top: 10px;"><a href="${event.maps_link}" target="_blank" style="color: #2196f3; text-decoration: none; font-weight: 600;">🗺️ Open in Google Maps →</a></div>` : ''}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🔗 Sources & Links</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Source', event.source)}
                    ${(function() {
                        const normalizeUrl = (u) => (u || '').trim().replace(/\/$/, '');
                        const seen = new Set();
                        const entries = [];
                        [[event.source_url, 'Source URL'], [event.url, 'Event URL'], [event.social_media_url, 'Social Media URL'], [event.registration_url, 'Registration URL']].forEach(([url, label]) => {
                            const key = normalizeUrl(url);
                            if (url && key && !seen.has(key)) { seen.add(key); entries.push({url, label}); }
                        });
                        return entries.map(({url, label}) => addField(entries.length > 1 ? label : 'URL', url, true)).join('');
                    })()}
                    ${addField('Social Media Platform', event.social_media_platform)}
                    ${addField('Social Media Handle', event.social_media_handle ? `@${event.social_media_handle}` : null)}
                </div>
            </div>
        </div>
        
        ${event.is_registration_required ? `
            <div style="margin-bottom: 20px;">
                <h4 style="margin-bottom: 10px; color: #4a5568;">🎫 Registration</h4>
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <div style="margin-bottom: 8px;"><strong>Registration Required:</strong> Yes</div>
                    ${addField('Registration Opens Date', event.registration_opens_date)}
                    ${addField('Registration Opens Time', event.registration_opens_time)}
                    ${addField('Registration Info', event.registration_info)}
                </div>
            </div>
        ` : ''}
    `;
    
    // Add event-specific fields based on event type
    if (event.event_type === 'tour') {
        const tourFields = [];
        if (event.tour_type) tourFields.push(addField('Tour Type', event.tour_type));
        if (event.max_participants) tourFields.push(addField('Max Participants', event.max_participants));
        if (event.price) tourFields.push(addField('Price', `$${event.price}`));
        if (event.language) tourFields.push(addField('Language', event.language));
        
        if (tourFields.length > 0) {
            html += `
                <div>
                    <h4 style="margin-bottom: 10px; color: #4a5568;">🚶 Tour Details</h4>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        ${tourFields.join('')}
                    </div>
                </div>
            `;
        }
    } else if (event.event_type === 'exhibition') {
        const exhibitionFields = [];
        if (event.exhibition_location) exhibitionFields.push(addField('Exhibition Location', event.exhibition_location));
        if (event.curator) exhibitionFields.push(addField('Curator', event.curator));
        if (event.admission_price) exhibitionFields.push(addField('Admission Price', `$${event.admission_price}`));
        if (event.artists) exhibitionFields.push(addField('Artists', event.artists));
        if (event.exhibition_type) exhibitionFields.push(addField('Exhibition Type', event.exhibition_type));
        if (event.collection_period) exhibitionFields.push(addField('Collection Period', event.collection_period));
        if (event.number_of_artworks) exhibitionFields.push(addField('Number of Artworks', event.number_of_artworks));
        if (event.opening_reception_date) {
            const receptionDate = new Date(event.opening_reception_date + 'T00:00:00').toLocaleDateString();
            const receptionTime = event.opening_reception_time ? ` at ${event.opening_reception_time}` : '';
            exhibitionFields.push(addField('Opening Reception', receptionDate + receptionTime));
        }
        if (event.is_permanent) exhibitionFields.push(addField('Permanent Collection', 'Yes'));
        if (event.related_exhibitions) exhibitionFields.push(addField('Related Exhibitions', event.related_exhibitions));
        
        if (exhibitionFields.length > 0) {
            html += `
                <div>
                    <h4 style="margin-bottom: 10px; color: #4a5568;">🎨 Exhibition Details</h4>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        ${exhibitionFields.join('')}
                    </div>
                </div>
            `;
        }
    } else if (event.event_type === 'festival') {
        const festivalFields = [];
        if (event.festival_type) festivalFields.push(addField('Festival Type', event.festival_type));
        festivalFields.push(`<div style="margin-bottom: 8px;"><strong>Multiple Locations:</strong> ${event.multiple_locations ? 'Yes' : 'No'}</div>`);
        
        if (festivalFields.length > 0) {
            html += `
                <div>
                    <h4 style="margin-bottom: 10px; color: #4a5568;">🎪 Festival Details</h4>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        ${festivalFields.join('')}
                    </div>
                </div>
            `;
        }
    } else if (event.event_type === 'photowalk') {
        const photowalkFields = [];
        if (event.difficulty_level) photowalkFields.push(addField('Difficulty Level', event.difficulty_level));
        if (event.equipment_needed) photowalkFields.push(addField('Equipment Needed', event.equipment_needed));
        if (event.organizer) photowalkFields.push(addField('Organizer', event.organizer));
        
        if (photowalkFields.length > 0) {
            html += `
                <div>
                    <h4 style="margin-bottom: 10px; color: #4a5568;">📸 Photowalk Details</h4>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                        ${photowalkFields.join('')}
                    </div>
                </div>
            `;
        }
    }
    
    // Add system information
    html += `
        <div>
            <h4 style="margin-bottom: 10px; color: #4a5568;">⚙️ System Information</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                ${addField('Created', event.created_at, false, true)}
                ${addField('Updated', event.updated_at, false, true)}
            </div>
        </div>
    `;
    
    return html;
}

function generateVenueDetailsHTML(venue) {
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
        <!-- Venue Header -->
        <div class="venue-details-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; text-align: center;">
            <h2 style="margin: 0; font-size: 28px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">${venue.name}</h2>
            <div style="margin-top: 8px; font-size: 16px; opacity: 0.9;">
                ${venue.venue_type ? `<span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; margin-right: 8px;">${venue.venue_type}</span>` : ''}
                ${venue.city_name ? `<span style="opacity: 0.8;">📍 ${venue.city_name}</span>` : ''}
            </div>
        </div>
        
        <div class="venue-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🏢 Basic Information</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 6px; font-size: 0.875rem;"><strong>ID:</strong> ${venue.id}</div>
                    ${addField('Type', venue.venue_type)}
                    ${addField('Description', venue.description)}
                    ${addField('City', venue.city_name)}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📍 Location & Contact</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Address', venue.address)}
                    ${addField('Phone', venue.phone_number || venue.phone)}
                    ${addField('Email', venue.email)}
                    ${addField('Website', venue.website_url || venue.website, true)}
                    ${addField('Coordinates', venue.latitude && venue.longitude ? `${venue.latitude}, ${venue.longitude}` : null)}
                    <div style="margin-bottom: 8px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196f3;">
                        <strong>🌍 City Timezone:</strong> ${venue.city_timezone || 'Not specified'}
                        ${venue.city_timezone ? `<br><small style="color: #666;">All venue times in local timezone</small>` : ''}
                    </div>
                </div>
            </div>
        </div>
        
        <div class="venue-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🕒 Hours & Pricing</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Opening Hours', venue.opening_hours)}
                    ${addField('Admission Fee', venue.admission_fee)}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">📱 Social Media</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    ${addField('Instagram', venue.instagram_url || venue.instagram, true)}
                    ${addField('Twitter', venue.twitter_url || venue.twitter, true)}
                    ${addField('Facebook', venue.facebook_url || venue.facebook, true)}
                    ${addField('YouTube', venue.youtube_url || venue.youtube, true)}
                    ${addField('TikTok', venue.tiktok_url || venue.tiktok, true)}
                </div>
            </div>
        </div>
        
        ${venue.image_url && venue.image_url.trim() ? `
        <div style="margin-bottom: 20px;">
            <h4 style="margin-bottom: 10px; color: #4a5568;">🖼️ Venue Image</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                ${(() => {
                    // Check if it's a photo reference (long string without http)
                    let imageSrc = venue.image_url;
                    let imageHref = venue.image_url;
                    if (venue.image_url && venue.image_url.trim() && !venue.image_url.startsWith('http') && venue.image_url.length > 50) {
                        // It's likely a Google Maps photo reference - use the image API endpoint
                        imageSrc = '/api/image/' + venue.image_url;
                        imageHref = '/api/image/' + venue.image_url;
                    }
                    return `
                        <a href="${imageHref}" target="_blank" style="color: #2196f3; text-decoration: none;">
                            <img data-src="${imageSrc}" alt="Venue Image" style="max-width: 300px; max-height: 200px; border-radius: 8px; cursor: pointer; border: 2px solid #e0e0e0; background: #f5f5f5;" 
                                 onerror="this.style.display='none'; const fallbackDiv = this.parentElement.querySelector('.image-fallback'); if (fallbackDiv) { fallbackDiv.style.display='inline-block'; }">
                            <div class="image-fallback" style="display: none; padding: 10px; background: #f5f5f5; border-radius: 4px; color: #666;">
                                <a href="${imageHref}" target="_blank" style="color: #2196f3;">View Venue Image</a>
                            </div>
                        </a>
                    `;
                })()}
            </div>
        </div>
        ` : ''}
        
        <div>
            <h4 style="margin-bottom: 10px; color: #4a5568;">⚙️ System Information</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                ${addField('Created', venue.created_at, false, true)}
                ${addField('Updated', venue.updated_at, false, true)}
            </div>
        </div>
    `;
    
    return html;
}

function generateCityDetailsHTML(city) {
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
        <!-- City Header -->
        <div class="city-details-header" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; text-align: center;">
            <h2 style="margin: 0; font-size: 28px; font-weight: 600; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">${city.display_name || city.name}</h2>
            <div style="margin-top: 8px; font-size: 16px; opacity: 0.9;">
                ${city.timezone ? `<span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; margin-right: 8px;">🌍 ${city.timezone}</span>` : ''}
                ${city.state ? `<span style="opacity: 0.8;">📍 ${city.state}, ${city.country}</span>` : `<span style="opacity: 0.8;">📍 ${city.country}</span>`}
            </div>
        </div>
        
        <div class="city-details-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🏙️ Basic Information</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 6px; font-size: 0.875rem;"><strong>ID:</strong> ${city.id}</div>
                    ${addField('Name', city.name)}
                    ${addField('Display Name', city.display_name)}
                    ${addField('State/Province', city.state)}
                    ${addField('Country', city.country)}
                </div>
            </div>
            
            <div>
                <h4 style="margin-bottom: 10px; color: #4a5568; font-size: 0.9375rem;">🌍 Location & Timezone</h4>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="margin-bottom: 8px; padding: 8px; background: #e3f2fd; border-radius: 4px; border-left: 4px solid #2196f3;">
                        <strong>🌍 Timezone:</strong> ${city.timezone || 'Not specified'}
                        ${city.timezone ? `<br><small style="color: #666;">All events in this city use this timezone</small>` : ''}
                    </div>
                    ${addField('Latitude', city.latitude)}
                    ${addField('Longitude', city.longitude)}
                </div>
            </div>
        </div>
        
        <div>
            <h4 style="margin-bottom: 10px; color: #4a5568;">⚙️ System Information</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                ${addField('Created', city.created_at, false, true)}
                ${addField('Updated', city.updated_at, false, true)}
            </div>
        </div>
    `;
    
    return html;
}

