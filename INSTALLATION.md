# Project Requirements & Understanding

## User's Core Vision
Create a web and mobile application for event planning with a focus on discovering and managing events across major cities worldwide.

## Key Requirements

### 1. Design Preferences
- **Minimal Design**: Clean, artistic, user-friendly interface
- **Font Family**: State-of-the-art/minimal artistic fonts (Playfair Display, Inter)
- **Color Palette**: Pastel colors, no dark button colors
- **UI Approach**: Icon-based interface with tooltips instead of text labels
- **Consistency**: Similar design across web and mobile platforms

### 2. Technical Preferences
- **Backend**: Python (Flask framework)
- **Port**: Avoid port 5000, use 5001
- **Scalability**: Global support for major cities worldwide
- **Architecture**: Professional project structure with organized directories
- **Database**: SQLite with SQLAlchemy ORM

### 3. Core Functionality

#### City & Time Selection
- **City Selection**: Choose from major cities (Washington DC, New York, London, Los Angeles, etc.)
- **Time Filtering**: Today, tomorrow, this week, this month
- **Display Format**: US cities as "City, State, Country", others as "City, Country"

#### Event Types
1. **Tours** (Primary Focus)
   - Museum tours with start/end times
   - Meeting locations (entrance, rotunda, specific floors)
   - Images (tour-specific or museum image)
   - Opening hours tracking (holidays, weekends, weekdays)
   - URLs to tour pages
   - Title and description
   - Timezone tracking for Google Calendar

2. **Venues**
   - Museums, buildings, locations
   - Opening hours for queried dates
   - Location and Google Maps images
   - General information
   - Instagram links for events
   - IDs for linking to tours

3. **Exhibitions**
   - Titles and date ranges
   - Descriptions and location info
   - Specific locations within museums
   - Auto-add new locations to venues

4. **Festivals**
   - Single or multi-day events
   - Single or multiple locations
   - Example: H Street Festival in DC

5. **Photowalks**
   - Start and end times
   - Start and end locations
   - Descriptions
   - Sources: websites or Instagram accounts

6. **Future Event Types**
   - Concerts, performances, theater (to be added later)

#### Event Management
- **Selection/Deselection**: Users can select or deselect events
- **Calendar Integration**: Add events to Google Calendar
- **One-day Events**: Tours, one-day festivals
- **Multi-day Events**: Exhibitions (discuss later)

### 4. Google Calendar Integration
- **Event Details**: Start/end time, meeting location, description, links
- **Geographical Location**: Venue location
- **Timezone Support**: Correct timezone for each city
- **Time Format**: Save times in 24-hour format
- **Calendar Events**: One-day events for tours/festivals, multi-day for exhibitions

### 5. Data Sources
- **Real Web Scraping**: Smithsonian, National Gallery, etc.
- **Generic Scrapers**: Usable globally for all museums and events
- **No Fake Data**: Real data only, no placeholder content

### 6. Global Scalability
- **Major Cities**: Washington DC, New York, Baltimore, Philadelphia, London, Los Angeles
- **Extensible**: Easy to add more cities
- **Timezone Support**: Proper timezone handling for each location

## Technical Implementation

### Architecture Decisions
1. **Professional Structure**: Organized directories (config/, scripts/, tests/)
2. **Modular Design**: Separate concerns (models, scrapers, calendar service)
3. **Database Design**: Proper relationships between cities, venues, and events
4. **API Design**: RESTful endpoints for web and mobile
5. **Frontend**: Minimal, responsive design with icon-based UI

### Key Features Implemented
1. **Timezone-Aware Calendar**: Google Calendar integration with proper timezone handling
2. **Real Data Scraping**: Generic framework for museum data extraction
3. **Multi-City Support**: London, Los Angeles, Washington DC with proper timezone mapping
4. **Enhanced Descriptions**: Meeting locations and URLs included in calendar events
5. **Professional UI**: Pastel colors, artistic fonts, icon-based interface

### User Experience Priorities
1. **Simplicity**: Minimal interface with clear actions
2. **Efficiency**: Quick city and time filtering
3. **Reliability**: Real data, no fake content
4. **Flexibility**: Easy to add new cities and event types
5. **Integration**: Seamless Google Calendar integration

## Success Criteria
- ✅ Web application running on port 5001
- ✅ Mobile application with similar design
- ✅ Real museum data scraping
- ✅ Google Calendar integration with timezone support
- ✅ Professional project structure
- ✅ Multi-city support (DC, London, Los Angeles)
- ✅ Icon-based UI with pastel design
- ✅ Meeting locations and URLs in calendar events

## Future Enhancements
- Additional event types (concerts, performances, theater)
- More cities and venues
- Enhanced scraping capabilities
- Mobile app optimization
- User accounts and favorites
- Social features and sharing
