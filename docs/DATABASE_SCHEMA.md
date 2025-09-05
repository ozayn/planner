# Database Schema Visualization

## Entity Relationship Diagram

```mermaid
erDiagram
    CITIES {
        int id PK
        string name
        string state
        string country
        string timezone
        string country_code
        decimal latitude
        decimal longitude
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    VENUES {
        int id PK
        string name
        string venue_type
        text address
        decimal latitude
        decimal longitude
        string image_url
        string instagram_url
        string website_url
        text description
        int city_id FK
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    EVENTS {
        int id PK
        string title
        text description
        date start_date
        date end_date
        time start_time
        time end_time
        string image_url
        string url
        boolean is_selected
        string event_type
        string status
        timestamp created_at
        timestamp updated_at
    }
    
    TOURS {
        int id PK,FK
        int venue_id FK
        string meeting_location
        string tour_type
        int max_participants
        decimal price
        string language
        string difficulty_level
        int duration_minutes
    }
    
    EXHIBITIONS {
        int id PK,FK
        int venue_id FK
        string exhibition_location
        string curator
        decimal admission_price
        string age_restriction
        text accessibility_info
    }
    
    FESTIVALS {
        int id PK,FK
        int city_id FK
        string festival_type
        boolean multiple_locations
        string organizer
        string ticket_url
    }
    
    PHOTOWALKS {
        int id PK,FK
        int city_id FK
        string start_location
        string end_location
        decimal start_latitude
        decimal start_longitude
        decimal end_latitude
        decimal end_longitude
        string difficulty_level
        text equipment_needed
        string organizer
        int max_participants
    }
    
    VENUE_HOURS {
        int id PK
        int venue_id FK
        int day_of_week
        time open_time
        time close_time
        boolean is_closed
        string special_note
    }
    
    EVENT_CATEGORIES {
        int id PK
        string name
        text description
        string icon
        string color
        boolean is_active
        timestamp created_at
    }
    
    EVENT_TAGS {
        int id PK
        string name
        string color
        timestamp created_at
    }
    
    EVENT_TAG_ASSIGNMENTS {
        int event_id PK,FK
        int tag_id PK,FK
        timestamp created_at
    }
    
    USER_FAVORITES {
        int id PK
        string user_id
        int event_id FK
        timestamp created_at
    }
    
    CALENDAR_INTEGRATIONS {
        int id PK
        string user_id
        int event_id FK
        string calendar_event_id
        string integration_type
        string status
        text error_message
        timestamp created_at
        timestamp updated_at
    }
    
    %% Relationships
    CITIES ||--o{ VENUES : "has"
    CITIES ||--o{ FESTIVALS : "hosts"
    CITIES ||--o{ PHOTOWALKS : "hosts"
    
    VENUES ||--o{ TOURS : "offers"
    VENUES ||--o{ EXHIBITIONS : "hosts"
    VENUES ||--o{ VENUE_HOURS : "has"
    
    EVENTS ||--o| TOURS : "extends"
    EVENTS ||--o| EXHIBITIONS : "extends"
    EVENTS ||--o| FESTIVALS : "extends"
    EVENTS ||--o| PHOTOWALKS : "extends"
    
    EVENTS ||--o{ EVENT_TAG_ASSIGNMENTS : "tagged"
    EVENT_TAGS ||--o{ EVENT_TAG_ASSIGNMENTS : "assigned"
    
    EVENTS ||--o{ USER_FAVORITES : "favorited"
    EVENTS ||--o{ CALENDAR_INTEGRATIONS : "integrated"
```

## Key Design Features

### 1. Polymorphic Inheritance
- **Events Table**: Base table for all event types
- **Specialized Tables**: Tours, Exhibitions, Festivals, Photowalks
- **Single Table Inheritance**: Efficient queries across event types

### 2. Geographic Support
- **Cities**: Full geographic data with timezone support
- **Venues**: Precise location coordinates
- **Photowalks**: Start/end location tracking

### 3. Flexible Relationships
- **Venues**: Can host multiple event types
- **Cities**: Can host city-wide events (festivals, photowalks)
- **Tags**: Many-to-many relationship for flexible categorization

### 4. User Features
- **Favorites**: User-specific event preferences
- **Calendar Integration**: Track external calendar sync status
- **Session Support**: Works with or without user accounts

### 5. Performance Optimizations
- **Strategic Indexes**: On frequently queried columns
- **Composite Indexes**: For multi-column queries
- **Soft Deletes**: Maintain data integrity

## Index Strategy

### Primary Indexes
```sql
-- Cities
CREATE INDEX idx_cities_country ON cities(country);
CREATE INDEX idx_cities_timezone ON cities(timezone);
CREATE INDEX idx_cities_active ON cities(is_active);

-- Venues
CREATE INDEX idx_venues_city ON venues(city_id);
CREATE INDEX idx_venues_type ON venues(venue_type);
CREATE INDEX idx_venues_location ON venues(latitude, longitude);

-- Events
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_dates ON events(start_date, end_date);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_selected ON events(is_selected);

-- Tours
CREATE INDEX idx_tours_venue ON tours(venue_id);
CREATE INDEX idx_tours_type ON tours(tour_type);
CREATE INDEX idx_tours_language ON tours(language);

-- User Features
CREATE INDEX idx_favorites_user ON user_favorites(user_id);
CREATE INDEX idx_calendar_user ON calendar_integrations(user_id);
```

### Composite Indexes
```sql
-- Event filtering
CREATE INDEX idx_events_city_type ON events(city_id, event_type, start_date);
CREATE INDEX idx_events_date_range ON events(start_date, end_date, status);

-- Venue operations
CREATE INDEX idx_venues_city_type ON venues(city_id, venue_type, is_active);
```

## Data Flow

### 1. Event Creation
1. Create base event record
2. Create specific event type record
3. Link to venue/city
4. Add tags and categories
5. Update indexes

### 2. Event Querying
1. Filter by city and date range
2. Join with event type tables
3. Include venue information
4. Apply user preferences
5. Return paginated results

### 3. User Interactions
1. Track favorites
2. Sync with external calendars
3. Maintain user session data
4. Log user preferences

This schema provides a solid foundation for a scalable event management system with proper normalization, performance optimization, and user features.
