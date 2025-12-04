/**
 * Unified Calendar Export Module
 * 
 * This module provides a single source of truth for all calendar export functionality
 * across the application (home page and admin page).
 * 
 * Usage:
 *   - Include this script in your HTML: <script src="/static/js/calendar-export.js"></script>
 *   - Use CalendarExport.addToCalendar(eventId, eventsArray) for individual exports
 *   - Use CalendarExport.generateICS(events) for bulk exports
 *   - Use CalendarExport.generateGoogleCalendarUrl(event, startDate, endDate, isAllDay) for direct URL generation
 */

(function(window) {
    'use strict';

    // Configuration
    let CALENDAR_DEBUG = false; // Set to true for debug logging
    const VENUE_ADDRESSES = {
        NGA: 'National Gallery of Art, Constitution Ave. NW, Washington, DC 20565, USA',
        HIRSHHORN: 'Smithsonian Hirshhorn Museum and Sculpture Garden, Independence Ave SW, Washington, DC 20560, USA',
        WEBSTERS: "Webster's Bookstore Cafe, 133 E Beaver Ave, State College, PA 16801, USA"
    };

    /**
     * Detect special venue types (NGA, Hirshhorn, Webster's)
     */
    function detectVenueType(venue_name, title, url, start_location) {
        const venueNameLower = (venue_name || '').toLowerCase();
        const titleLower = (title || '').toLowerCase();
        const urlLower = (url || '').toLowerCase();
        const startLocLower = (start_location || '').toLowerCase();
        
        const isNGA = (
            venueNameLower.includes('national gallery') || venueNameLower.includes('nga') ||
            titleLower.includes('national gallery') || titleLower.includes('finding awe') ||
            urlLower.includes('nga.gov') ||
            ((startLocLower.includes('west building') || startLocLower.includes('east building')) &&
             (startLocLower.includes('gallery') || startLocLower.includes('floor')))
        );
        
        const isHirshhorn = venueNameLower.includes('hirshhorn');
        
        const isWebsters = (
            venueNameLower.includes("webster's") || venueNameLower.includes('websters') ||
            titleLower.includes("webster's") || titleLower.includes('websters') ||
            urlLower.includes('webstersbooksandcafe.com')
        );
        
        return { isNGA, isHirshhorn, isWebsters };
    }

    /**
     * Get calendar location for event
     */
    function getCalendarLocation(event) {
        const { isNGA, isHirshhorn, isWebsters } = detectVenueType(
            event.venue_name, event.title, event.url, event.start_location
        );
        const hasVenueName = event.venue_name && typeof event.venue_name === 'string' && event.venue_name.trim().length > 0;
        const hasVenueAddress = event.venue_address && typeof event.venue_address === 'string' && event.venue_address.trim().length > 0;
        
        // Special venue handling
        if (isNGA) {
            if (hasVenueName && hasVenueAddress) {
                return `${event.venue_name.trim()}, ${event.venue_address.trim()}`;
            } else if (hasVenueAddress) {
                return event.venue_address.trim();
            } else if (hasVenueName) {
                return `${event.venue_name.trim()}, Constitution Ave. NW, Washington, DC 20565, USA`;
            }
            return VENUE_ADDRESSES.NGA;
        }
        
        if (isHirshhorn) {
            if (hasVenueName && hasVenueAddress) {
                return `${event.venue_name.trim()}, ${event.venue_address.trim()}`;
            } else if (hasVenueAddress) {
                return event.venue_address.trim();
            } else if (hasVenueName) {
                return `${event.venue_name.trim()}, Independence Ave SW, Washington, DC 20560, USA`;
            }
            return VENUE_ADDRESSES.HIRSHHORN;
        }
        
        if (isWebsters) {
            return VENUE_ADDRESSES.WEBSTERS;
        }
        
        // General venue handling
        if (hasVenueName && hasVenueAddress) {
            return `${event.venue_name.trim()}, ${event.venue_address.trim()}`;
        } else if (hasVenueAddress) {
            return event.venue_address.trim();
        } else if (hasVenueName) {
            const location = event.venue_name.trim();
            if (event.city_name && typeof event.city_name === 'string' && event.city_name.trim()) {
                return `${location}, ${event.city_name.trim()}`;
            }
            return location;
        } else if (event.start_location && typeof event.start_location === 'string' && event.start_location.trim()) {
            return event.start_location.trim();
        }
        
        return '';
    }

    /**
     * Build enhanced description for calendar events
     */
    function buildEnhancedDescription(event) {
        const descriptionParts = [];
        
        // Add meeting location if different from venue name
        if (event.start_location && event.start_location.trim()) {
            const startLocLower = event.start_location.toLowerCase().trim();
            const venueLower = (event.venue_name || '').toLowerCase().trim();
            if (!venueLower || (startLocLower !== venueLower && !startLocLower.includes(venueLower) && !venueLower.includes(startLocLower))) {
                descriptionParts.push(`Meeting Location: ${event.start_location.trim()}`);
            }
        }
        
        if (event.description) {
            descriptionParts.push(event.description);
        }
        
        if (event.event_type) {
            descriptionParts.push(`Event Type: ${event.event_type.charAt(0).toUpperCase() + event.event_type.slice(1)}`);
        }
        
        if (event.end_location && event.end_location !== event.start_location) {
            descriptionParts.push(`End Location: ${event.end_location}`);
        }
        
        if (event.social_media_platform && event.social_media_handle) {
            const platformName = event.social_media_platform.charAt(0).toUpperCase() + event.social_media_platform.slice(1);
            descriptionParts.push(`${platformName}: @${event.social_media_handle}`);
        }
        
        if (event.social_media_page_name) {
            descriptionParts.push(`Page/Group: ${event.social_media_page_name}`);
        }
        
        if (event.social_media_posted_by) {
            descriptionParts.push(`Posted By: ${event.social_media_posted_by}`);
        }
        
        if (event.social_media_url) {
            descriptionParts.push(`Social Media URL: ${event.social_media_url}`);
        }
        
        if (event.url) {
            descriptionParts.push(`Website: ${event.url}`);
        }
        
        if (event.source) {
            descriptionParts.push(`Source: ${event.source}`);
        }
        
        if (event.source_url) {
            descriptionParts.push(`Source URL: ${event.source_url}`);
        }
        
        if (event.organizer) {
            descriptionParts.push(`Organizer: ${event.organizer}`);
        }
        
        if (event.price) {
            descriptionParts.push(`Price: $${event.price}`);
        }
        
        return descriptionParts.join('\n\n');
    }

    /**
     * Format date for Google Calendar all-day events (YYYYMMDD format)
     * Takes a date string (YYYY-MM-DD) or Date object
     */
    function formatDateOnlyForGoogle(dateInput) {
        let dateStr;
        if (typeof dateInput === 'string') {
            dateStr = dateInput;
        } else {
            // Date object - extract date parts directly without timezone conversion
            const year = dateInput.getFullYear();
            const month = String(dateInput.getMonth() + 1).padStart(2, '0');
            const day = String(dateInput.getDate()).padStart(2, '0');
            return `${year}${month}${day}`;
        }
        // String input: remove dashes
        return dateStr.replace(/-/g, '');
    }

    /**
     * Format date with time for Google Calendar (directly from date/time strings, no timezone conversion)
     * The timezone is specified separately via the ctz parameter
     */
    function formatDateTimeForGoogle(dateStr, timeStr) {
        // dateStr format: YYYY-MM-DD
        // timeStr format: HH:MM or HH:MM:SS
        const datePart = dateStr.replace(/-/g, '');
        const timeParts = (timeStr || '00:00:00').split(':');
        const hour = (timeParts[0] || '00').padStart(2, '0');
        const minute = (timeParts[1] || '00').padStart(2, '0');
        const second = (timeParts[2] || '00').padStart(2, '0');
        
        return `${datePart}T${hour}${minute}${second}`;
    }

    /**
     * Parse event dates and determine if it's all-day (exhibition)
     */
    function parseEventDates(event) {
        // Parse start date
        const [year, month, day] = event.start_date.split('-').map(Number);
        const startDate = new Date(year, month - 1, day);
        startDate.setHours(0, 0, 0, 0);
        
        // Check if it's an exhibition (all-day event)
        const isAllDay = event.event_type === 'exhibition' && !event.start_time;
        
        let endDate;
        
        if (isAllDay) {
            // For exhibitions, use end_date if available (multi-day), otherwise use start_date (single-day)
            if (event.end_date && event.end_date !== event.start_date) {
                const [endYear, endMonth, endDay] = event.end_date.split('-').map(Number);
                endDate = new Date(endYear, endMonth - 1, endDay);
                endDate.setHours(0, 0, 0, 0);
            } else {
                endDate = new Date(startDate);
                endDate.setHours(0, 0, 0, 0);
            }
            
            // For all-day events, Google Calendar uses exclusive end date (day after)
            const exclusiveEndDate = new Date(endDate);
            exclusiveEndDate.setDate(exclusiveEndDate.getDate() + 1);
            exclusiveEndDate.setHours(0, 0, 0, 0);
            
            return { startDate, endDate: exclusiveEndDate, isAllDay: true };
        } else {
            // For timed events
            if (event.start_time) {
                const [hours, minutes] = event.start_time.split(':');
                startDate.setHours(parseInt(hours), parseInt(minutes || 0));
            }
            
            endDate = new Date(startDate);
            if (event.end_time) {
                const [hours, minutes] = event.end_time.split(':');
                endDate.setHours(parseInt(hours), parseInt(minutes || 0));
            } else {
                endDate.setHours(endDate.getHours() + 2); // Default 2-hour duration
            }
            
            return { startDate, endDate, isAllDay: false };
        }
    }

    /**
     * Generate Google Calendar URL for an event
     */
    function generateGoogleCalendarUrl(event, startDate, endDate, isAllDay = false) {
        if (CALENDAR_DEBUG) {
            console.log('generateGoogleCalendarUrl called', { isAllDay, event_type: event.event_type, event });
        }
        
        // Get timezone from event - prioritize city_timezone, fallback to city lookup
        let eventTimezone = event.city_timezone;
        
        // If no city_timezone, try to get it from city_id or city_name
        if (!eventTimezone && event.city_id) {
            // Try to find city timezone from the events array context if available
            // This is a fallback - ideally city_timezone should always be in the event object
            if (CALENDAR_DEBUG) {
                console.warn('Event missing city_timezone, attempting lookup from city_id:', event.city_id);
            }
        }
        
        // Final fallback - but this should rarely be needed if events are properly loaded
        if (!eventTimezone) {
            eventTimezone = 'America/New_York';
            if (CALENDAR_DEBUG) {
                console.warn('Using default timezone America/New_York for event:', event.title);
            }
        }
        
        if (CALENDAR_DEBUG) {
            console.log('Using timezone:', eventTimezone, 'for event:', event.title);
        }
        let startDateTime, endDateTime;
        
        // IMPORTANT: Use event date/time strings directly - NO Date object conversion
        // The times are already in the correct local time for the event's timezone
        // We just format them as strings and specify the timezone via ctz parameter
        // This prevents any timezone shifting
        
        // Get date strings directly from event (format: YYYY-MM-DD)
        const startDateStr = event.start_date;
        const endDateStr = event.end_date || event.start_date;
        
        if (isAllDay || event.event_type === 'exhibition') {
            // All-day events: use date only format (YYYYMMDD)
            startDateTime = formatDateOnlyForGoogle(startDateStr);
            endDateTime = formatDateOnlyForGoogle(endDateStr);
        } else if (event.start_time && event.end_time) {
            // Timed events: use date/time strings directly from event data
            // NO Date object manipulation - just format the strings as-is
            startDateTime = formatDateTimeForGoogle(startDateStr, event.start_time);
            endDateTime = formatDateTimeForGoogle(endDateStr, event.end_time);
        } else {
            // No time specified: treat as all-day
            startDateTime = formatDateOnlyForGoogle(startDateStr);
            endDateTime = formatDateOnlyForGoogle(endDateStr);
        }
        
        const enhancedDescription = buildEnhancedDescription(event);
        const calendarLocation = getCalendarLocation(event);
        
        // Build Google Calendar URL
        const params = new URLSearchParams({
            action: 'TEMPLATE',
            text: event.title,
            dates: `${startDateTime}/${endDateTime}`,
            details: enhancedDescription,
            location: calendarLocation,
            ctz: eventTimezone
        });

        const calendarUrl = `https://calendar.google.com/calendar/render?${params}`;
        
        if (CALENDAR_DEBUG) {
            console.log('Google Calendar URL generated:', {
                event: event.title,
                dates: `${startDateTime}/${endDateTime}`,
                location: calendarLocation,
                url: calendarUrl
            });
        }
        
        return calendarUrl;
    }

    /**
     * Escape special characters for ICS format
     */
    function escapeICS(text) {
        if (!text) return '';
        return String(text)
            .replace(/\\/g, '\\\\')
            .replace(/;/g, '\\;')
            .replace(/,/g, '\\,')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '');
    }

    /**
     * Format date for ICS (YYYYMMDD)
     */
    function formatDateForICS(dateStr) {
        if (!dateStr) return '';
        return dateStr.replace(/-/g, '');
    }

    /**
     * Format date/time for ICS (YYYYMMDDTHHMMSS)
     */
    function formatDateTimeForICS(dateStr, timeStr) {
        if (!dateStr) return '';
        const date = dateStr.replace(/-/g, '');
        if (!timeStr) return date;
        const timeParts = timeStr.split(':');
        const time = (timeParts[0] || '00').padStart(2, '0') + 
                    (timeParts[1] || '00').padStart(2, '0') + 
                    (timeParts[2] || '00').padStart(2, '0');
        return `${date}T${time}`;
    }

    /**
     * Generate VTIMEZONE information for ICS format
     * 
     * Note: Most modern calendar applications (Google Calendar, Apple Calendar, Outlook)
     * will recognize standard IANA timezone names (e.g., "America/Los_Angeles") and
     * look up the proper DST rules from their internal database. We just need to provide
     * the TZID - the calendar app will handle the rest.
     */
    function generateVTIMEZONE(timezoneStr) {
        // Minimal VTIMEZONE definition - calendar apps will look up proper rules
        // We just need to provide the TZID so they know which timezone to use
        return `BEGIN:VTIMEZONE\r\nTZID:${timezoneStr}\r\nX-LIC-LOCATION:${timezoneStr}\r\nEND:VTIMEZONE\r\n`;
    }

    /**
     * Generate ICS event string for a single event
     */
    function generateICSEvent(event) {
        // Get current timestamp for DTSTAMP
        const now = new Date();
        const dtstamp = formatDateTimeForICS(
            now.toISOString().split('T')[0],
            now.toTimeString().split(' ')[0].substring(0, 8)
        );
        
        // Get timezone from event - prioritize city_timezone
        let eventTimezone = event.city_timezone;
        
        // Final fallback - but this should rarely be needed if events are properly loaded
        if (!eventTimezone) {
            eventTimezone = 'America/New_York';
            if (CALENDAR_DEBUG) {
                console.warn('ICS: Using default timezone America/New_York for event:', event.title);
            }
        }
        
        // Determine if all-day (exhibition)
        const isAllDay = event.event_type === 'exhibition' && !event.start_time;
        
        let startDateTime, endDateTime;
        
        if (isAllDay) {
            // All-day event: use DATE format (YYYYMMDD)
            startDateTime = formatDateForICS(event.start_date);
            // Use end_date if available (multi-day), otherwise use start_date (single-day)
            let endDate = event.end_date || event.start_date;
            // For all-day events, end date should be exclusive (day after)
            const endDateObj = new Date(endDate);
            endDateObj.setDate(endDateObj.getDate() + 1);
            endDateTime = formatDateForICS(endDateObj.toISOString().split('T')[0]);
        } else {
            // Timed event
            startDateTime = formatDateTimeForICS(event.start_date, event.start_time);
            endDateTime = formatDateTimeForICS(event.end_date || event.start_date, event.end_time || event.start_time);
        }
        
        // Generate unique ID
        const uid = `event-${event.id}-${Date.now()}@planner`;
        
        // Build description
        const description = buildEnhancedDescription(event);
        const location = getCalendarLocation(event);
        
        // Build ICS event
        let icsEvent = 'BEGIN:VEVENT\r\n';
        icsEvent += `UID:${uid}\r\n`;
        icsEvent += `DTSTAMP:${dtstamp}\r\n`;
        
        if (isAllDay) {
            icsEvent += `DTSTART;VALUE=DATE:${startDateTime}\r\n`;
            icsEvent += `DTEND;VALUE=DATE:${endDateTime}\r\n`;
        } else {
            // For timed events, include timezone
            icsEvent += `DTSTART;TZID=${eventTimezone}:${startDateTime}\r\n`;
            icsEvent += `DTEND;TZID=${eventTimezone}:${endDateTime}\r\n`;
        }
        
        icsEvent += `SUMMARY:${escapeICS(event.title || 'Untitled Event')}\r\n`;
        
        if (description) {
            icsEvent += `DESCRIPTION:${escapeICS(description)}\r\n`;
        }
        
        if (location) {
            icsEvent += `LOCATION:${escapeICS(location)}\r\n`;
        }
        
        if (event.url) {
            icsEvent += `URL:${escapeICS(event.url)}\r\n`;
        }
        
        icsEvent += 'END:VEVENT\r\n';
        
        return icsEvent;
    }

    /**
     * Generate ICS content for multiple events
     */
    function generateICS(events, calendarName = 'Planner Events') {
        let icsContent = 'BEGIN:VCALENDAR\r\n';
        icsContent += 'VERSION:2.0\r\n';
        icsContent += 'PRODID:-//Event Planner//EN\r\n';
        icsContent += 'CALSCALE:GREGORIAN\r\n';
        icsContent += 'METHOD:PUBLISH\r\n';
        icsContent += `X-WR-CALNAME:${calendarName}\r\n`;
        icsContent += `X-WR-CALDESC:Events from Planner\r\n`;
        
        // Collect unique timezones from events
        const timezones = new Set();
        events.forEach(event => {
            if (event.city_timezone) {
                timezones.add(event.city_timezone);
            } else if (event.start_time || (event.event_type !== 'exhibition')) {
                // For timed events without timezone, default to America/New_York
                timezones.add('America/New_York');
            }
        });
        
        // Add VTIMEZONE definitions for each unique timezone
        timezones.forEach(tz => {
            icsContent += generateVTIMEZONE(tz);
        });
        
        // Add events
        events.forEach(event => {
            icsContent += generateICSEvent(event);
        });
        
        icsContent += 'END:VCALENDAR\r\n';
        return icsContent;
    }

    /**
     * Add a single event to calendar (opens Google Calendar)
     */
    function addToCalendar(eventId, eventsArray) {
        const event = eventsArray.find(e => e.id === eventId);
        if (!event) {
            console.error('Event not found:', eventId);
            if (typeof showNotification === 'function') {
                showNotification('Event not found', 'error');
            } else {
                alert('Event not found');
            }
            return;
        }

        const { startDate, endDate, isAllDay } = parseEventDates(event);
        const googleCalendarUrl = generateGoogleCalendarUrl(event, startDate, endDate, isAllDay);
        window.open(googleCalendarUrl, '_blank');
        
        if (typeof showNotification === 'function') {
            showNotification('Opening Google Calendar...', 'info');
        }
    }

    /**
     * Export multiple events to calendar (downloads ICS file)
     */
    function exportToCalendar(events, filename = null) {
        if (!events || events.length === 0) {
            if (typeof showNotification === 'function') {
                showNotification('No events to export', 'error');
            } else {
                alert('No events to export');
            }
            return;
        }
        
        // Generate filename if not provided
        if (!filename) {
            const today = new Date().toISOString().split('T')[0];
            filename = `planner_events_${today}.ics`;
        }
        
        const icsContent = generateICS(events);
        const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        if (typeof showNotification === 'function') {
            showNotification(`Exported ${events.length} events to calendar`, 'success');
        }
    }

    // Public API
    window.CalendarExport = {
        // Main functions
        addToCalendar: addToCalendar,
        exportToCalendar: exportToCalendar,
        generateICS: generateICS,
        generateGoogleCalendarUrl: generateGoogleCalendarUrl,
        generateICSEvent: generateICSEvent,
        
        // Helper functions (exposed for advanced usage)
        getCalendarLocation: getCalendarLocation,
        buildEnhancedDescription: buildEnhancedDescription,
        parseEventDates: parseEventDates,
        detectVenueType: detectVenueType,
        generateVTIMEZONE: generateVTIMEZONE,
        
        // Configuration
        VENUE_ADDRESSES: VENUE_ADDRESSES,
        setDebug: function(enabled) {
            CALENDAR_DEBUG = enabled;
        }
    };

})(window);

