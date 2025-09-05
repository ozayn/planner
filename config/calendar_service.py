import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from typing import Dict, Optional, List

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    """Service for Google Calendar integration"""
    
    def __init__(self, credentials_path: str, token_path: str):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
    
    def create_event(self, event_data: Dict) -> Optional[str]:
        """Create a calendar event"""
        try:
            event = self.service.events().insert(
                calendarId='primary',
                body=event_data
            ).execute()
            
            return event.get('id')
            
        except HttpError as error:
            print(f"Error creating calendar event: {error}")
            return None
    
    def update_event(self, event_id: str, event_data: Dict) -> bool:
        """Update an existing calendar event"""
        try:
            self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event_data
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Error updating calendar event: {error}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event"""
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Error deleting calendar event: {error}")
            return False

class CalendarEventBuilder:
    """Builder for creating Google Calendar events from our event data"""
    
    @staticmethod
    def build_tour_event(tour_data: Dict, city_timezone: str) -> Dict:
        """Build calendar event for a tour"""
        # Parse dates and times
        start_date = datetime.strptime(tour_data['start_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(tour_data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(tour_data['end_time'], '%H:%M').time()
        
        # Create datetime objects with timezone
        tz = pytz.timezone(city_timezone)
        start_datetime = tz.localize(datetime.combine(start_date, start_time))
        end_datetime = tz.localize(datetime.combine(start_date, end_time))
        
        # Build description
        description_parts = []
        if tour_data.get('description'):
            description_parts.append(tour_data['description'])
        
        if tour_data.get('meeting_location'):
            description_parts.append(f"Meeting Location: {tour_data['meeting_location']}")
        
        if tour_data.get('venue_name'):
            description_parts.append(f"Venue: {tour_data['venue_name']}")
        
        if tour_data.get('url'):
            description_parts.append(f"More Info: {tour_data['url']}")
        
        description = '\n\n'.join(description_parts)
        
        # Build location string
        location_parts = []
        if tour_data.get('venue_name'):
            location_parts.append(tour_data['venue_name'])
        if tour_data.get('meeting_location'):
            location_parts.append(tour_data['meeting_location'])
        
        location = ', '.join(location_parts) if location_parts else None
        
        return {
            'summary': tour_data['title'],
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'location': location,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
    
    @staticmethod
    def build_exhibition_event(exhibition_data: Dict, city_timezone: str) -> Dict:
        """Build calendar event for an exhibition"""
        # Parse dates
        start_date = datetime.strptime(exhibition_data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(exhibition_data['end_date'], '%Y-%m-%d').date()
        
        # Create datetime objects with timezone
        tz = pytz.timezone(city_timezone)
        start_datetime = tz.localize(datetime.combine(start_date, datetime.min.time()))
        end_datetime = tz.localize(datetime.combine(end_date, datetime.max.time()))
        
        # Build description
        description_parts = []
        if exhibition_data.get('description'):
            description_parts.append(exhibition_data['description'])
        
        if exhibition_data.get('exhibition_location'):
            description_parts.append(f"Location: {exhibition_data['exhibition_location']}")
        
        if exhibition_data.get('venue_name'):
            description_parts.append(f"Venue: {exhibition_data['venue_name']}")
        
        if exhibition_data.get('url'):
            description_parts.append(f"More Info: {exhibition_data['url']}")
        
        description = '\n\n'.join(description_parts)
        
        # Build location string
        location_parts = []
        if exhibition_data.get('venue_name'):
            location_parts.append(exhibition_data['venue_name'])
        if exhibition_data.get('exhibition_location'):
            location_parts.append(exhibition_data['exhibition_location'])
        
        location = ', '.join(location_parts) if location_parts else None
        
        return {
            'summary': exhibition_data['title'],
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'location': location,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
    
    @staticmethod
    def build_festival_event(festival_data: Dict, city_timezone: str) -> Dict:
        """Build calendar event for a festival"""
        # Parse dates
        start_date = datetime.strptime(festival_data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(festival_data['end_date'], '%Y-%m-%d').date()
        
        # Create datetime objects with timezone
        tz = pytz.timezone(city_timezone)
        start_datetime = tz.localize(datetime.combine(start_date, datetime.min.time()))
        end_datetime = tz.localize(datetime.combine(end_date, datetime.max.time()))
        
        # Build description
        description_parts = []
        if festival_data.get('description'):
            description_parts.append(festival_data['description'])
        
        if festival_data.get('city_name'):
            description_parts.append(f"City: {festival_data['city_name']}")
        
        if festival_data.get('url'):
            description_parts.append(f"More Info: {festival_data['url']}")
        
        description = '\n\n'.join(description_parts)
        
        return {
            'summary': festival_data['title'],
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }
    
    @staticmethod
    def build_photowalk_event(photowalk_data: Dict, city_timezone: str) -> Dict:
        """Build calendar event for a photowalk"""
        # Parse dates and times
        start_date = datetime.strptime(photowalk_data['start_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(photowalk_data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(photowalk_data['end_time'], '%H:%M').time()
        
        # Create datetime objects with timezone
        tz = pytz.timezone(city_timezone)
        start_datetime = tz.localize(datetime.combine(start_date, start_time))
        end_datetime = tz.localize(datetime.combine(start_date, end_time))
        
        # Build description
        description_parts = []
        if photowalk_data.get('description'):
            description_parts.append(photowalk_data['description'])
        
        if photowalk_data.get('start_location'):
            description_parts.append(f"Start Location: {photowalk_data['start_location']}")
        
        if photowalk_data.get('end_location'):
            description_parts.append(f"End Location: {photowalk_data['end_location']}")
        
        if photowalk_data.get('equipment_needed'):
            description_parts.append(f"Equipment Needed: {photowalk_data['equipment_needed']}")
        
        if photowalk_data.get('organizer'):
            description_parts.append(f"Organizer: {photowalk_data['organizer']}")
        
        if photowalk_data.get('url'):
            description_parts.append(f"More Info: {photowalk_data['url']}")
        
        description = '\n\n'.join(description_parts)
        
        # Build location string
        location_parts = []
        if photowalk_data.get('start_location'):
            location_parts.append(f"Start: {photowalk_data['start_location']}")
        if photowalk_data.get('end_location'):
            location_parts.append(f"End: {photowalk_data['end_location']}")
        
        location = ' | '.join(location_parts) if location_parts else None
        
        return {
            'summary': photowalk_data['title'],
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': city_timezone,
            },
            'location': location,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

def get_calendar_service() -> Optional[GoogleCalendarService]:
    """Get Google Calendar service instance"""
    try:
        credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials.json')
        token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_PATH', 'token.json')
        
        return GoogleCalendarService(credentials_path, token_path)
    except Exception as e:
        print(f"Error initializing Google Calendar service: {e}")
        return None
