# System Architecture

*Last updated: 2025-09-09T22:27:36.517036*

## Database Layer

The application uses SQLite with SQLAlchemy ORM for data persistence.

### Key Features

- **NLP-Powered Text Normalization**: Intelligent city and country name correction
- **Automatic Timestamps**: All tables have created_at and updated_at fields
- **Comprehensive Venue Data**: Social media links, contact info, opening hours
- **Event Management**: Tours, exhibitions, festivals, photowalks, workshops, talks, films, and music
- **Geographic Support**: Cities with timezone and state/province information

### Models

- **City**: Geographic locations with timezone support
- **Venue**: Physical locations (museums, galleries, etc.)
- **Event**: Unified model for all event types including tours, exhibitions, festivals, photowalks, workshops, talks, films, and music

### NLP Integration

The system includes intelligent text normalization for:
- City names (handles typos like "tabrz" → "Tabriz")
- Country names (recognizes "US", "usa", "United States" as the same)
- Venue names (smart formatting and categorization)

### Database Management

- **Automatic Migrations**: Schema changes are tracked and applied automatically
- **Documentation Sync**: All docs are updated when schema changes
- **Backup System**: Automatic backups before major changes
- **Performance Indexes**: Optimized for common queries

## API Layer

RESTful API endpoints for:
- City management (CRUD operations)
- Venue management (CRUD operations)
- Event management (CRUD operations)
- Admin functions (cleanup, discovery, etc.)

## Frontend Layer

- Admin interface for data management
- City selection and event filtering
- Real-time updates and progress tracking

## External Integrations

- **Geocoding**: OpenStreetMap Nominatim for location data
- **Timezone Detection**: Automatic timezone assignment
- **LLM Integration**: AI-powered venue and event discovery
- **Image Processing**: Automatic venue image fetching
