# Database Implementation Plan

## Phase 1: Immediate Improvements (Week 1)

### 1.1 Consolidate Models
**Priority: High**
- Remove duplicate model definitions from `app.py`
- Use centralized models from `config/models.py`
- Ensure consistent field definitions

**Tasks:**
```bash
# Move all models to config/models.py
# Update app.py to import from config.models
# Test model consistency
```

### 1.2 Add Missing Indexes
**Priority: High**
- Add indexes for frequently queried columns
- Improve query performance immediately

**SQL Commands:**
```sql
-- Add critical indexes
CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city_id);
CREATE INDEX IF NOT EXISTS idx_tours_venue ON tours(venue_id);
CREATE INDEX IF NOT EXISTS idx_cities_timezone ON cities(timezone);
```

### 1.3 Fix Data Integrity Issues
**Priority: Medium**
- Add proper constraints
- Fix missing foreign key relationships
- Ensure data consistency

## Phase 2: Schema Enhancements (Week 2-3)

### 2.1 Add Supporting Tables
**Priority: Medium**

#### Venue Hours Table
```sql
CREATE TABLE venue_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    open_time TIME NULL,
    close_time TIME NULL,
    is_closed BOOLEAN DEFAULT 0,
    special_note VARCHAR(200) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (venue_id) REFERENCES venues(id) ON DELETE CASCADE,
    UNIQUE(venue_id, day_of_week)
);
```

#### Event Categories Table
```sql
CREATE TABLE event_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(50) NULL,
    color VARCHAR(7) NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 User Features
**Priority: Medium**

#### User Favorites
```sql
CREATE TABLE user_favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    event_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, event_id),
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);
```

#### Calendar Integration Tracking
```sql
CREATE TABLE calendar_integrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    event_id INTEGER NOT NULL,
    calendar_event_id VARCHAR(200) NULL,
    integration_type VARCHAR(20) DEFAULT 'google',
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
);
```

## Phase 3: Performance Optimization (Week 4)

### 3.1 Advanced Indexing
**Priority: Medium**

```sql
-- Composite indexes for complex queries
CREATE INDEX idx_events_city_type_date ON events(city_id, event_type, start_date);
CREATE INDEX idx_venues_city_type_active ON venues(city_id, venue_type, is_active);
CREATE INDEX idx_tours_venue_type ON tours(venue_id, tour_type);
```

### 3.2 Query Optimization
**Priority: Medium**
- Analyze slow queries
- Optimize JOIN operations
- Implement query caching

### 3.3 Data Archiving
**Priority: Low**
- Archive old events
- Implement soft delete patterns
- Clean up inactive data

## Phase 4: Advanced Features (Week 5-6)

### 4.1 Event Tagging System
**Priority: Low**

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

### 4.2 Enhanced Geographic Support
**Priority: Low**
- Add country codes
- Implement location-based queries
- Add distance calculations

## Migration Scripts

### Migration 1: Add Indexes
```python
# scripts/migrations/001_add_indexes.py
def upgrade():
    db.engine.execute("CREATE INDEX IF NOT EXISTS idx_events_dates ON events(start_date, end_date)")
    db.engine.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    db.engine.execute("CREATE INDEX IF NOT EXISTS idx_venues_city ON venues(city_id)")
    # ... more indexes

def downgrade():
    db.engine.execute("DROP INDEX IF EXISTS idx_events_dates")
    # ... drop other indexes
```

### Migration 2: Add Supporting Tables
```python
# scripts/migrations/002_supporting_tables.py
def upgrade():
    # Create venue_hours table
    # Create event_categories table
    # Create user_favorites table
    pass

def downgrade():
    # Drop tables in reverse order
    pass
```

## Testing Strategy

### 1. Unit Tests
```python
# tests/test_models.py
def test_city_creation():
    city = City(name="Test City", country="Test Country", timezone="UTC")
    assert city.name == "Test City"

def test_event_polymorphism():
    tour = Tour(title="Test Tour", start_date=date.today())
    assert tour.event_type == "tour"
```

### 2. Integration Tests
```python
# tests/test_database.py
def test_event_venue_relationship():
    city = create_test_city()
    venue = create_test_venue(city)
    tour = create_test_tour(venue)
    
    assert tour.venue.city == city
```

### 3. Performance Tests
```python
# tests/test_performance.py
def test_query_performance():
    start_time = time.time()
    events = Event.query.filter_by(city_id=1).all()
    execution_time = time.time() - start_time
    
    assert execution_time < 0.1  # Should be under 100ms
```

## Monitoring and Maintenance

### 1. Database Monitoring
```python
# config/monitoring.py
class DatabaseMonitor:
    def track_query_performance(self, query, execution_time):
        if execution_time > 1.0:  # Log slow queries
            logger.warning(f"Slow query: {query} took {execution_time}s")
    
    def check_index_usage(self):
        # Monitor index effectiveness
        pass
```

### 2. Automated Maintenance
```python
# scripts/maintenance.py
def vacuum_database():
    """Clean up SQLite database"""
    db.engine.execute("VACUUM")
    
def update_statistics():
    """Update query planner statistics"""
    db.engine.execute("ANALYZE")
```

## Rollback Plan

### 1. Backup Strategy
```bash
# Daily backups
cp instance/events.db backups/events_$(date +%Y%m%d).db

# Before major changes
cp instance/events.db backups/events_pre_migration.db
```

### 2. Rollback Procedures
```python
# scripts/rollback.py
def rollback_migration(migration_id):
    """Rollback specific migration"""
    migration = get_migration(migration_id)
    migration.downgrade()
    
def restore_from_backup(backup_file):
    """Restore database from backup"""
    shutil.copy(backup_file, "instance/events.db")
```

## Success Metrics

### 1. Performance Metrics
- Query response time < 100ms for 95% of queries
- Database size growth < 10% per month
- Index usage > 80% for critical queries

### 2. Data Quality Metrics
- Foreign key constraint violations = 0
- Duplicate records = 0
- Data consistency = 100%

### 3. User Experience Metrics
- Page load time < 2 seconds
- Search results relevance > 90%
- User satisfaction > 4.5/5

## Implementation Timeline

| Week | Phase | Tasks | Deliverables |
|------|-------|-------|--------------|
| 1 | Consolidation | Fix models, add indexes | Working app with better performance |
| 2 | Enhancement | Add supporting tables | Venue hours, categories |
| 3 | Enhancement | User features | Favorites, calendar tracking |
| 4 | Optimization | Advanced indexing | Optimized queries |
| 5 | Advanced | Tagging system | Flexible categorization |
| 6 | Advanced | Geographic features | Enhanced location support |

## Risk Mitigation

### 1. Data Loss Prevention
- Multiple backup strategies
- Transaction-based migrations
- Rollback procedures

### 2. Performance Degradation
- Gradual rollout
- Performance monitoring
- Quick rollback capability

### 3. User Impact
- Maintenance windows
- Graceful degradation
- User communication

This implementation plan provides a structured approach to improving the database design while minimizing risk and ensuring continuous operation of the application.
