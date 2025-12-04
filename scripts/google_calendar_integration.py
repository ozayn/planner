#!/usr/bin/env python3
"""
Google Calendar Integration

This module handles creating Google Calendar events from extracted event data
"""

import os
import logging
from datetime import datetime, date, time
from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    import pickle
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False
    logging.warning("Google Calendar libraries not available")

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Data structure for Google Calendar event"""
    summary: str
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    attendees: Optional[list] = None
    reminders: Optional[dict] = None

class GoogleCalendarManager:
    """Manages Google Calendar integration"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.token_file = 'calendar_token.pickle'
        self.credentials_file = 'calendar_credentials.json'
    
    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            logger.error("Google Calendar libraries not available")
            return False
        
        try:
            # Load existing credentials
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # If there are no valid credentials, get new ones
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # Check if we have client credentials
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"Google Calendar credentials file not found: {self.credentials_file}")
                        return False
                    
                    flow = Flow.from_client_secrets_file(
                        self.credentials_file, 
                        scopes=self.scopes
                    )
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    
                    # Get authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"Please visit this URL to authorize the application: {auth_url}")
                    
                    # Get authorization code from user
                    auth_code = input('Enter the authorization code: ')
                    flow.fetch_token(code=auth_code)
                    
                    self.credentials = flow.credentials
                
                # Save credentials for next run
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Build the service
            self.service = build('calendar', 'v3', credentials=self.credentials)
            logger.info("Successfully authenticated with Google Calendar")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Calendar: {e}")
            return False
    
    def create_event(self, event_data: CalendarEvent, calendar_id: str = 'primary') -> Optional[str]:
        """Create a Google Calendar event"""
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            # Build event body
            event_body = {
                'summary': event_data.summary,
                'description': event_data.description or '',
                'location': event_data.location or '',
            }
            
            # Set start and end times with proper timezone
            timezone = event_data.timezone or 'UTC'
            if event_data.start_datetime and event_data.end_datetime:
                event_body['start'] = {
                    'dateTime': event_data.start_datetime.isoformat(),
                    'timeZone': timezone,
                }
                event_body['end'] = {
                    'dateTime': event_data.end_datetime.isoformat(),
                    'timeZone': timezone,
                }
            elif event_data.start_datetime:
                # All-day event
                event_body['start'] = {
                    'date': event_data.start_datetime.date().isoformat(),
                }
                # Use end_datetime if available, otherwise use start_datetime
                # For exhibitions, this ensures the full date range is used
                end_date = event_data.end_datetime.date() if event_data.end_datetime else event_data.start_datetime.date()
                event_body['end'] = {
                    'date': end_date.isoformat(),
                }
            
            # Add attendees if provided
            if event_data.attendees:
                event_body['attendees'] = [
                    {'email': email} for email in event_data.attendees
                ]
            
            # Add reminders
            if event_data.reminders:
                event_body['reminders'] = event_data.reminders
            else:
                # Default reminders
                event_body['reminders'] = {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 10},        # 10 minutes before
                    ],
                }
            
            # Create the event
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            logger.info(f"Created Google Calendar event: {event.get('htmlLink')}")
            return event.get('id')
            
        except Exception as e:
            logger.error(f"Error creating Google Calendar event: {e}")
            return None
    
    def update_event(self, event_id: str, event_data: CalendarEvent, calendar_id: str = 'primary') -> bool:
        """Update an existing Google Calendar event"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            event['summary'] = event_data.summary
            if event_data.description:
                event['description'] = event_data.description
            if event_data.location:
                event['location'] = event_data.location
            
            # Update times if provided
            if event_data.start_datetime and event_data.end_datetime:
                event['start'] = {
                    'dateTime': event_data.start_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                }
                event['end'] = {
                    'dateTime': event_data.end_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                }
            
            # Update the event
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"Updated Google Calendar event: {updated_event.get('htmlLink')}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating Google Calendar event: {e}")
            return False
    
    def delete_event(self, event_id: str, calendar_id: str = 'primary') -> bool:
        """Delete a Google Calendar event"""
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"Deleted Google Calendar event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting Google Calendar event: {e}")
            return False
    
    def list_events(self, calendar_id: str = 'primary', max_results: int = 10) -> list:
        """List upcoming events from Google Calendar"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return events
            
        except Exception as e:
            logger.error(f"Error listing Google Calendar events: {e}")
            return []
    
    def get_calendar_list(self) -> list:
        """Get list of available calendars"""
        if not self.service:
            if not self.authenticate():
                return []
        
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            return calendars
            
        except Exception as e:
            logger.error(f"Error getting calendar list: {e}")
            return []

def create_calendar_event_from_extracted_data(extracted_data, venue_data=None, city_data=None) -> Optional[CalendarEvent]:
    """Create a CalendarEvent from extracted event data"""
    try:
        # Build summary (title)
        summary = extracted_data.title or "Event"
        
        # Build description with additional information
        description_parts = []
        if extracted_data.description:
            description_parts.append(extracted_data.description)
        
        # Add event type and details
        if extracted_data.event_type:
            description_parts.append(f"Event Type: {extracted_data.event_type.title()}")
        
        # Add venue information if available
        if venue_data:
            description_parts.append(f"Venue: {venue_data.get('name', 'Unknown')}")
            if venue_data.get('address'):
                description_parts.append(f"Venue Address: {venue_data['address']}")
        
        # Add pricing information
        if extracted_data.price:
            description_parts.append(f"Price: ${extracted_data.price}")
        
        # Add organizer information
        if extracted_data.organizer:
            description_parts.append(f"Organizer: {extracted_data.organizer}")
        
        # Add end location if different from start location
        if extracted_data.end_location and extracted_data.end_location != extracted_data.start_location:
            description_parts.append(f"End Location: {extracted_data.end_location}")
        
        # Add social media and web links
        if extracted_data.social_media_platform and extracted_data.social_media_handle:
            platform_name = extracted_data.social_media_platform.title()
            description_parts.append(f"{platform_name}: @{extracted_data.social_media_handle}")
        elif hasattr(extracted_data, 'instagram_handle') and extracted_data.instagram_handle:
            # Legacy Instagram support
            description_parts.append(f"Instagram: @{extracted_data.instagram_handle}")
        
        if extracted_data.social_media_url:
            description_parts.append(f"Social Media URL: {extracted_data.social_media_url}")
        elif extracted_data.url:
            description_parts.append(f"Website: {extracted_data.url}")
        
        # Add source information
        if extracted_data.source:
            description_parts.append(f"Source: {extracted_data.source}")
        
        if extracted_data.source_url:
            description_parts.append(f"Source URL: {extracted_data.source_url}")
        
        # Add confidence score for debugging
        if hasattr(extracted_data, 'confidence') and extracted_data.confidence:
            description_parts.append(f"Extraction Confidence: {int(extracted_data.confidence * 100)}%")
        
        description = '\n\n'.join(description_parts) if description_parts else None
        
        # Build location - use comma-separated format for NGA and Hirshhorn, tags for others
        location = None
        venue_name = None
        venue_address = None
        
        if venue_data:
            venue_name = venue_data.get('name')
            venue_address = venue_data.get('address')
        
        # Check if this is an NGA or Hirshhorn event
        is_nga = False
        is_hirshhorn = False
        if venue_name:
            venue_name_lower = venue_name.lower()
            is_nga = 'national gallery' in venue_name_lower or 'nga' in venue_name_lower
            is_hirshhorn = 'hirshhorn' in venue_name_lower
        
        # For NGA and Hirshhorn events, use comma-separated format
        if is_nga or is_hirshhorn:
            if venue_name and venue_address:
                location = f"{venue_name}, {venue_address}"
            elif venue_address:
                location = venue_address
            elif venue_name:
                # Use venue name with hardcoded address as fallback
                if is_nga:
                    location = f"{venue_name}, Constitution Ave NW, Washington, DC 20565, USA"
                elif is_hirshhorn:
                    location = f"{venue_name}, Independence Ave SW, Washington, DC 20560, USA"
                else:
                    location = venue_name
            else:
                # Final fallback
                if is_nga:
                    location = 'National Gallery of Art, Constitution Ave NW, Washington, DC 20565, USA'
                elif is_hirshhorn:
                    location = 'Smithsonian Hirshhorn Museum and Sculpture Garden, Independence Ave SW, Washington, DC 20560, USA'
        else:
            # For other events, use <location> and <address> tags
            if venue_name and venue_address:
                location = f"<location>{venue_name}</location><address>{venue_address}</address>"
            elif venue_address:
                location = f"<address>{venue_address}</address>"
            elif venue_name:
                location = f"<location>{venue_name}</location>"
            elif extracted_data.location:
                location = extracted_data.location
            elif extracted_data.start_location:
                # Only use start_location as fallback if no venue info available
                location = extracted_data.start_location
        
        # Build start and end datetimes with timezone
        start_datetime = None
        end_datetime = None
        timezone_str = 'UTC'  # Default timezone
        
        # Get timezone from city data if available
        if city_data and city_data.get('timezone'):
            timezone_str = city_data['timezone']
        elif hasattr(extracted_data, 'city_timezone') and extracted_data.city_timezone:
            timezone_str = extracted_data.city_timezone
        
        try:
            import pytz
            tz = pytz.timezone(timezone_str)
        except:
            tz = pytz.UTC
        
        if extracted_data.start_date:
            # Handle end date - if no end date provided, assume same as start date
            end_date = extracted_data.end_date or extracted_data.start_date
            
            # For exhibitions without times, treat as all-day events spanning the full date range
            # For other events without times, use default times
            is_exhibition = extracted_data.event_type and extracted_data.event_type.lower() == 'exhibition'
            
            if extracted_data.start_time:
                start_datetime = tz.localize(datetime.combine(extracted_data.start_date, extracted_data.start_time))
            elif is_exhibition:
                # For exhibitions without times, use start of day (will be converted to all-day event)
                start_datetime = tz.localize(datetime.combine(extracted_data.start_date, time(0, 0)))
            else:
                start_datetime = tz.localize(datetime.combine(extracted_data.start_date, time(9, 0)))  # Default to 9 AM
            
            if extracted_data.end_time:
                end_datetime = tz.localize(datetime.combine(end_date, extracted_data.end_time))
            elif is_exhibition:
                # For exhibitions without times, use end of end_date (will be converted to all-day event)
                # Add 1 day to end_date for all-day events (Google Calendar convention: end date is exclusive)
                from datetime import timedelta
                end_date_plus_one = end_date + timedelta(days=1)
                end_datetime = tz.localize(datetime.combine(end_date_plus_one, time(0, 0)))
            elif extracted_data.end_date:
                end_datetime = tz.localize(datetime.combine(end_date, time(17, 0)))  # Default to 5 PM
            else:
                # Default duration: 1 hour if start time provided, otherwise based on event type
                if extracted_data.start_time:
                    duration_hours = 1
                else:
                    duration_hours = 2 if extracted_data.event_type == 'tour' else 3
                end_datetime = start_datetime.replace(hour=start_datetime.hour + duration_hours)
        
        return CalendarEvent(
            summary=summary,
            description=description,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            location=location,
            timezone=timezone_str
        )
        
    except Exception as e:
        logger.error(f"Error creating calendar event from extracted data: {e}")
        return None

def main():
    """Test the Google Calendar integration"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        print("Google Calendar libraries not available")
        return
    
    manager = GoogleCalendarManager()
    
    if manager.authenticate():
        print("Successfully authenticated with Google Calendar")
        
        # Test creating an event
        test_event = CalendarEvent(
            summary="Test Event from Image Processor",
            description="This is a test event created from extracted image data",
            start_datetime=datetime.now().replace(hour=14, minute=0, second=0, microsecond=0),
            end_datetime=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0),
            location="Test Location"
        )
        
        event_id = manager.create_event(test_event)
        if event_id:
            print(f"Created test event with ID: {event_id}")
        else:
            print("Failed to create test event")
    else:
        print("Failed to authenticate with Google Calendar")

if __name__ == "__main__":
    main()
