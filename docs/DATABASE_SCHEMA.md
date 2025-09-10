# Database Schema

*Last updated: 2025-01-09T23:30:00.000000*

## Overview

This document describes the current database schema for the Planner application. The application uses a **unified Event model** approach where all event types are stored in a single `events` table with an `event_type` field to distinguish between them.

## Architecture Overview

The database uses a **unified events architecture** with three main tables:
- `cities`: Geographic locations
- `venues`: Cultural institutions and locations  
- `events`: **Single unified table** for all event types (tours, exhibitions, festivals, photowalks)

**Important**: There are NO separate tables for different event types. All events are stored in the unified `events` table.

## Tables

### Cities

| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | Yes |
| name | VARCHAR(100) | No |  | No |
| state | VARCHAR(50) | Yes |  | No |
| country | VARCHAR(100) | No |  | No |
| timezone | VARCHAR(50) | No |  | No |
| created_at | DATETIME | Yes |  | No |
| updated_at | DATETIME | Yes | '2025-09-09T22:23:00.358548' | No |

### Events (Unified Model)

| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | Yes |
| title | VARCHAR(200) | No |  | No |
| description | TEXT | Yes |  | No |
| start_date | DATE | No |  | No |
| end_date | DATE | Yes |  | No |
| start_time | TIME | Yes |  | No |
| end_time | TIME | Yes |  | No |
| image_url | VARCHAR(500) | Yes |  | No |
| url | VARCHAR(500) | Yes |  | No |
| is_selected | BOOLEAN | Yes |  | No |
| event_type | VARCHAR(50) | No |  | No |
| created_at | DATETIME | Yes |  | No |
| updated_at | DATETIME | Yes | '2025-09-09T22:23:00.358548' | No |
| city_id | INTEGER | Yes |  | No |
| venue_id | INTEGER | Yes |  | No |

#### Location Fields (Multi-purpose)
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| start_location | VARCHAR(200) | Yes |  | No |
| end_location | VARCHAR(200) | Yes |  | No |
| start_latitude | FLOAT | Yes |  | No |
| start_longitude | FLOAT | Yes |  | No |
| end_latitude | FLOAT | Yes |  | No |
| end_longitude | FLOAT | Yes |  | No |

#### Tour-specific Fields
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| tour_type | VARCHAR(50) | Yes |  | No |
| max_participants | INTEGER | Yes |  | No |
| price | FLOAT | Yes |  | No |
| language | VARCHAR(50) | Yes | 'English' | No |

#### Exhibition-specific Fields
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| exhibition_location | VARCHAR(200) | Yes |  | No |
| curator | VARCHAR(200) | Yes |  | No |
| admission_price | FLOAT | Yes |  | No |

#### Festival-specific Fields
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| festival_type | VARCHAR(100) | Yes |  | No |
| multiple_locations | BOOLEAN | Yes | False | No |

#### Photowalk-specific Fields
| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| difficulty_level | VARCHAR(50) | Yes |  | No |
| equipment_needed | TEXT | Yes |  | No |
| organizer | VARCHAR(200) | Yes |  | No |

### Venues

| Column | Type | Nullable | Default | Primary Key |
|--------|------|----------|---------|-------------|
| id | INTEGER | No |  | Yes |
| name | VARCHAR(200) | No |  | No |
| venue_type | VARCHAR(50) | No |  | No |
| address | TEXT | Yes |  | No |
| latitude | FLOAT | Yes |  | No |
| longitude | FLOAT | Yes |  | No |
| image_url | VARCHAR(500) | Yes |  | No |
| instagram_url | VARCHAR(200) | Yes |  | No |
| facebook_url | VARCHAR(200) | Yes |  | No |
| twitter_url | VARCHAR(200) | Yes |  | No |
| youtube_url | VARCHAR(200) | Yes |  | No |
| tiktok_url | VARCHAR(200) | Yes |  | No |
| website_url | VARCHAR(200) | Yes |  | No |
| description | TEXT | Yes |  | No |
| city_id | INTEGER | No |  | No |
| created_at | DATETIME | Yes |  | No |
| opening_hours | TEXT | Yes |  | No |
| holiday_hours | TEXT | Yes |  | No |
| phone_number | VARCHAR(50) | Yes |  | No |
| email | VARCHAR(200) | Yes |  | No |
| tour_info | TEXT | Yes |  | No |
| admission_fee | TEXT | Yes |  | No |
| updated_at | DATETIME | Yes | '2025-09-09T22:23:00.358548' | No |

## Event Types

The `event_type` field in the events table can have the following values:
- `tour`: Museum tours, guided walks, etc.
- `exhibition`: Art exhibitions, museum displays, etc.
- `festival`: Cultural festivals, music events, etc.
- `photowalk`: Photography walks and tours

**Note**: The API uses singular forms (`tour`, `exhibition`, `festival`, `photowalk`) to match the database values.

## Relationships

- **Cities** → **Venues**: One-to-many (city can have multiple venues)
- **Cities** → **Events**: One-to-many (city can have multiple events)
- **Venues** → **Events**: One-to-many (venue can have multiple events)
- **Events** can be associated with either a city (for city-wide events) or a venue (for venue-specific events)

## Notes

- The unified Event model approach simplifies CRUD operations and reduces database complexity
- Event-specific fields are nullable and only populated when relevant to the event type
- All events share common fields like title, description, dates, and times
- Location fields serve multiple purposes depending on event type (meeting point, exhibition location, start/end points)

