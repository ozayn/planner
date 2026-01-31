import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found.")
                print("Please follow the instructions in GOOGLE_OAUTH_SETUP.md to get your credentials.")
                print("Download the 'OAuth 2.0 Client ID' JSON file and rename it to 'credentials.json'.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def create_recurring_event(service, summary, start_hour, timezone, description):
    """Creates a daily 1-hour recurring event."""
    
    # Get today's date
    now = datetime.datetime.now()
    start_time = datetime.datetime(now.year, now.month, now.day, start_hour, 0, 0)
    end_time = start_time + datetime.timedelta(hours=1)
    
    event = {
        'summary': summary,
        'location': 'Virtual / VDG App',
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': timezone,
        },
        'recurrence': [
            'RRULE:FREQ=DAILY'
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f'Event created: {event.get("htmlLink")}')
    except HttpError as error:
        print(f'An error occurred: {error}')

def main():
    creds = authenticate()
    if not creds:
        return

    service = build('calendar', 'v3', credentials=creds)

    # Define the sittings we want to add
    # You can comment out the ones you don't want
    
    sittings = [
        # Eastern Time (Local for DC)
        {"name": "Dhamma Sitting (ET)", "hours": [5, 6, 7, 8, 19, 20, 21, 22], "tz": "America/New_York"},
        
        # Central Time
        {"name": "Dhamma Sitting (CT)", "hours": [4, 5, 6, 7, 18, 19, 20, 21], "tz": "America/Chicago"},
        
        # Mountain Time
        {"name": "Dhamma Sitting (MT)", "hours": [3, 4, 5, 6, 17, 18, 19, 20], "tz": "America/Denver"},
        
        # Pacific Time
        {"name": "Dhamma Sitting (PT)", "hours": [2, 3, 4, 5, 16, 17, 18, 19], "tz": "America/Los_Angeles"},
        
        # India Standard Time (IST) - Hourly windows
        # 5:30 AM - 10:30 AM IST and 3:30 PM - 8:30 PM IST
        {"name": "Dhamma Sitting (IST)", "hours": [5, 6, 7, 8, 9, 10, 15, 16, 17, 18, 19, 20], "tz": "Asia/Kolkata"},
        
        # Indochina Time (ICT)
        {"name": "Dhamma Sitting (ICT)", "hours": [5, 20], "tz": "Asia/Ho_Chi_Minh"},
    ]

    description = (
        "Dhamma Virtual Group Sitting\n\n"
        "Access via VDG App or FreeConferenceCall.\n"
        "For details, visit: https://www.dhamma.org/en/os/locations/virtual_events\n"
        "Old Student login: oldstudent / behappy"
    )

    print("Adding events to your Google Calendar...")
    for sitting in sittings:
        for hour in sitting["hours"]:
            create_recurring_event(service, sitting["name"], hour, sitting["tz"], description)

if __name__ == '__main__':
    main()
