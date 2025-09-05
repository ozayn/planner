# Professional Database Design

## Overview
This document outlines the professional database design for the Event Planner application, focusing on scalability, maintainability, and performance.

## Current State Analysis

### Strengths
- ✅ Polymorphic inheritance for event types
- ✅ Proper foreign key relationships
- ✅ Timezone support for cities
- ✅ Flexible venue-event relationships

### Issues Identified
- ❌ Duplicate model definitions (app.py vs config/models.py)
- ❌ Missing database indexes for performance
- ❌ No audit trail (created_at/updated_at inconsistency)
- ❌ Missing data validation constraints
- ❌ No soft delete functionality
- ❌ Limited scalability for large datasets

## Professional Database Schema Design

### 1. Core Tables

#### Cities Table
```sql
CREATE TABLE cities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    state VARCHAR(50) NULL,  -- For US states
    country VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    country_code VARCHAR(3) NOT NULL,  -- ISO country code
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, state, country),
    INDEX idx_cities_country (country),
    INDEX idx_cities_timezone (timezone),
    INDEX idx_cities_active (is_active)
);
```

#### Venues Table
```sql
CREATE TABLE venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    venue_type VARCHAR(50) NOT NULL,
    address TEXT,
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,
    image_url VARCHAR(500),
    instagram_url VARCHAR(200),
    website_url VARCHAR(200),
    description TEXT,
    city_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (city_id) REFERENCES cities(id),
    INDEX idx_venues_city (city_id),
    INDEX idx_venues_type (venue_type),
    INDEX idx_venues_active (is_active),
    INDEX idx_venues_location (latitude, longitude)
);
```

#### Events Table (Base)
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    start_time TIME NULL,
    end_time TIME NULL,
    image_url VARCHAR(500),
    url VARCHAR(500),
    is_selected BOOLEAN DEFAULT 1,
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, cancelled, completed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_events_type (event_type),
    INDEX idx_events_dates (start_date, end_date),
    INDEX idx_events_status (status),
    INDEX idx_events_selected (is_selected),
    INDEX idx_events_created (created_at)
);
```

### 2. Event Type Tables

#### Tours Table
```sql
CREATE TABLE tours (
    id INTEGER PRIMARY KEY,
    venue_id INTEGER NOT NULL,
    meeting_location VARCHAR(200),
    tour_type VARCHAR(50),
    max_participants INTEGER,
    price DECIMAL(10, 2) NULL,
    language VARCHAR(50) DEFAULT 'English',
    difficulty_level VARCHAR(20) NULL,
    duration_minutes INTEGER NULL,
    
    FOREIGN KEY (id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (venue_id) REFERENCES venues(id),
    INDEX idx_tours_venue (venue_id),
    INDEX idx_tours_type (tour_type),
    INDEX idx_tours_language (language)
);
```

#### Exhibitions Table
```sql
CREATE TABLE exhibitions (
    id INTEGER PRIMARY KEY,
    venue_id INTEGER NOT NULL,
    exhibition_location VARCHAR(200),
    curator VARCHAR(200),
    admission_price DECIMAL(10, 2) NULL,
    age_restriction VARCHAR(50) NULL,
    accessibility_info TEXT NULL,
    
    FOREIGN KEY (id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (venue_id) REFERENCES venues(id),
    INDEX idx_exhibitions_venue (venue_id),
    INDEX idx_exhibitions_curator (curator)
);
```

#### Festivals Table
```sql
CREATE TABLE festivals (
    id INTEGER PRIMARY KEY,
    city_id INTEGER NOT NULL,
    festival_type VARCHAR(100),
    multiple_locations BOOLEAN DEFAULT 0,
    organizer VARCHAR(200) NULL,
    ticket_url VARCHAR(500) NULL,
    
    FOREIGN KEY (id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (city_id) REFERENCES cities(id),
    INDEX idx_festivals_city (city_id),
    INDEX idx_festivals_type (festival_type)
);
```

#### Photowalks Table
```sql
CREATE TABLE photowalks (
    id INTEGER PRIMARY KEY,
    city_id INTEGER NOT NULL,
    start_location VARCHAR(200),
    end_location VARCHAR(200),
    start_latitude DECIMAL(10, 8) NULL,
    start_longitude DECIMAL(11, 8) NULL,
    end_latitude DECIMAL(10, 8) NULL,
    end_longitude DECIMAL(11, 8) NULL,
    difficulty_level VARCHAR(50),
    equipment_needed TEXT,
    organizer VARCHAR(200),
    max_participants INTEGER NULL,
    
    FOREIGN KEY (id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (city_id) REFERENCES cities(id),
    INDEX idx_photowalks_city (city_id),
    INDEX idx_photowalks_difficulty (difficulty_level),
    INDEX idx_photowalks_location (start_latitude, start_longitude)
);
```

### 3. Supporting Tables

#### Venue Hours Table
```sql
CREATE TABLE venue_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0=Sunday, 1=Monday, etc.
    open_time TIME NULL,
    close_time TIME NULL,
    is_closed BOOLEAN DEFAULT 0,
    special_note VARCHAR(200) NULL,
    
    FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE,
    UNIQUE(venue_id, day_of_week),
    INDEX idx_venue_hours_venue (venue_id)
);
```

#### Event Categories Table
```sql
CREATE TABLE event_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50) NULL,
    color VARCHAR(7) NULL,  -- Hex color code
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Event Tags Table
```sql
CREATE TABLE event_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE event_tag_assignments (
    event_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (event_id, tag_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES event_tags(id) ON DELETE CASCADE
);
```

#### User Favorites Table
```sql
CREATE TABLE user_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,  -- Could be session ID or user ID
    event_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, event_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    INDEX idx_favorites_user (user_id),
    INDEX idx_favorites_event (event_id)
);
```

#### Calendar Integrations Table
```sql
CREATE TABLE calendar_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    event_id INTEGER NOT NULL,
    calendar_event_id VARCHAR(200) NULL,  -- External calendar event ID
    integration_type VARCHAR(20) DEFAULT 'google',  -- google, outlook, etc.
    status VARCHAR(20) DEFAULT 'pending',  -- pending, synced, failed
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    INDEX idx_calendar_user (user_id),
    INDEX idx_calendar_event (event_id),
    INDEX idx_calendar_status (status)
);
```

## Database Design Principles

### 1. Normalization
- **3NF Compliance**: Eliminate redundant data
- **Referential Integrity**: Proper foreign key constraints
- **Atomic Values**: Each field contains single values

### 2. Performance Optimization
- **Strategic Indexing**: Indexes on frequently queried columns
- **Composite Indexes**: For multi-column queries
- **Covering Indexes**: Include frequently accessed columns

### 3. Scalability
- **Partitioning Strategy**: Consider date-based partitioning for events
- **Archiving**: Move old events to archive tables
- **Caching**: Implement Redis for frequently accessed data

### 4. Data Integrity
- **Constraints**: NOT NULL, UNIQUE, CHECK constraints
- **Triggers**: Automatic timestamp updates
- **Validation**: Application-level validation

### 5. Audit Trail
- **Timestamps**: created_at, updated_at on all tables
- **Soft Deletes**: is_active flags instead of hard deletes
- **Change Logging**: Track important data changes

## Migration Strategy

### Phase 1: Schema Cleanup
1. Consolidate duplicate models
2. Add missing indexes
3. Implement proper constraints

### Phase 2: New Features
1. Add supporting tables (venue_hours, categories, tags)
2. Implement user favorites
3. Add calendar integration tracking

### Phase 3: Performance Optimization
1. Add composite indexes
2. Implement query optimization
3. Add caching layer

## Backup and Recovery

### Backup Strategy
- **Daily Full Backups**: Complete database dump
- **Incremental Backups**: Hourly transaction logs
- **Point-in-Time Recovery**: For critical data loss

### Recovery Procedures
- **Automated Recovery**: Scripts for common scenarios
- **Data Validation**: Post-recovery integrity checks
- **Rollback Plans**: Quick rollback procedures

## Monitoring and Maintenance

### Performance Monitoring
- **Query Performance**: Track slow queries
- **Index Usage**: Monitor index effectiveness
- **Connection Pooling**: Monitor database connections

### Maintenance Tasks
- **Regular VACUUM**: SQLite maintenance
- **Index Rebuilding**: Periodic index optimization
- **Statistics Updates**: Keep query planner informed

## Security Considerations

### Data Protection
- **Input Validation**: Prevent SQL injection
- **Access Control**: Role-based permissions
- **Encryption**: Sensitive data encryption

### Compliance
- **GDPR Compliance**: User data handling
- **Data Retention**: Automatic cleanup policies
- **Audit Logging**: Track data access

## Next Steps

1. **Implement Schema Changes**: Create migration scripts
2. **Update Models**: Refactor SQLAlchemy models
3. **Add Indexes**: Implement performance optimizations
4. **Testing**: Comprehensive database testing
5. **Documentation**: Update API documentation

This professional database design provides a solid foundation for scaling the Event Planner application while maintaining data integrity and performance.
