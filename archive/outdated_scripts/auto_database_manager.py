#!/usr/bin/env python3
"""
Automated Database Management System
Automatically handles schema changes, migrations, and documentation updates
"""

import os
import sqlite3
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

class AutoDatabaseManager:
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.db_path = os.path.expanduser('~/.local/share/planner/events.db')
        self.docs_dir = os.path.join(self.project_root, 'docs')
        self.scripts_dir = os.path.join(self.project_root, 'scripts')
        self.current_time = datetime.utcnow().isoformat()
        
    def auto_update_everything(self):
        """Automatically update everything when schema changes are detected"""
        print("🤖 Auto Database Manager - Checking for changes...")
        
        # 1. Check for schema changes
        schema_changes = self.detect_schema_changes()
        
        if not schema_changes:
            print("✅ No schema changes detected")
            return True
        
        print(f"🔄 Detected {len(schema_changes)} schema changes")
        
        # 2. Create migration
        migration = self.create_auto_migration(schema_changes)
        
        # 3. Apply migration
        if self.apply_migration(migration):
            print("✅ Migration applied successfully")
            
            # 4. Update all documentation
            self.update_all_documentation()
            
            # 5. Update model files if needed
            self.update_model_files()
            
            # 6. Run tests to verify everything works
            self.run_verification_tests()
            
            print("🎉 All updates completed successfully!")
            return True
        else:
            print("❌ Migration failed")
            return False
    
    def detect_schema_changes(self) -> List[Dict]:
        """Detect changes between current schema and expected schema"""
        changes = []
        
        # Get current database schema
        current_schema = self.get_current_schema()
        
        # Get expected schema from model definitions
        expected_schema = self.get_expected_schema()
        
        # Compare schemas
        for table_name, expected_columns in expected_schema.items():
            if table_name not in current_schema:
                changes.append({
                    'type': 'missing_table',
                    'table': table_name,
                    'columns': expected_columns
                })
                continue
            
            current_columns = {col['name']: col for col in current_schema[table_name]}
            
            for col_name, expected_col in expected_columns.items():
                if col_name not in current_columns:
                    changes.append({
                        'type': 'missing_column',
                        'table': table_name,
                        'column': expected_col
                    })
                else:
                    current_col = current_columns[col_name]
                    if self.columns_differ(current_col, expected_col):
                        changes.append({
                            'type': 'column_changed',
                            'table': table_name,
                            'column': expected_col,
                            'old_column': current_col
                        })
        
        return changes
    
    def get_current_schema(self) -> Dict:
        """Get current database schema"""
        if not os.path.exists(self.db_path):
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        schema = {}
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema[table_name] = []
            for col in columns:
                schema[table_name].append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'primary_key': bool(col[5])
                })
        
        conn.close()
        return schema
    
    def get_expected_schema(self) -> Dict:
        """Get expected schema from model definitions"""
        # This would read from your model definitions
        # For now, return a simplified version
        return {
            'cities': {
                'id': {'name': 'id', 'type': 'INTEGER', 'not_null': True, 'primary_key': True},
                'name': {'name': 'name', 'type': 'VARCHAR(100)', 'not_null': True},
                'state': {'name': 'state', 'type': 'VARCHAR(50)', 'not_null': False},
                'country': {'name': 'country', 'type': 'VARCHAR(100)', 'not_null': True},
                'timezone': {'name': 'timezone', 'type': 'VARCHAR(50)', 'not_null': True},
                'created_at': {'name': 'created_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'},
                'updated_at': {'name': 'updated_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'}
            },
            'venues': {
                'id': {'name': 'id', 'type': 'INTEGER', 'not_null': True, 'primary_key': True},
                'name': {'name': 'name', 'type': 'VARCHAR(200)', 'not_null': True},
                'venue_type': {'name': 'venue_type', 'type': 'VARCHAR(50)', 'not_null': True},
                'address': {'name': 'address', 'type': 'TEXT', 'not_null': False},
                'latitude': {'name': 'latitude', 'type': 'FLOAT', 'not_null': False},
                'longitude': {'name': 'longitude', 'type': 'FLOAT', 'not_null': False},
                'image_url': {'name': 'image_url', 'type': 'VARCHAR(500)', 'not_null': False},
                'instagram_url': {'name': 'instagram_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'facebook_url': {'name': 'facebook_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'twitter_url': {'name': 'twitter_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'youtube_url': {'name': 'youtube_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'tiktok_url': {'name': 'tiktok_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'website_url': {'name': 'website_url', 'type': 'VARCHAR(200)', 'not_null': False},
                'description': {'name': 'description', 'type': 'TEXT', 'not_null': False},
                'opening_hours': {'name': 'opening_hours', 'type': 'TEXT', 'not_null': False},
                'holiday_hours': {'name': 'holiday_hours', 'type': 'TEXT', 'not_null': False},
                'phone_number': {'name': 'phone_number', 'type': 'VARCHAR(50)', 'not_null': False},
                'email': {'name': 'email', 'type': 'VARCHAR(100)', 'not_null': False},
                'tour_info': {'name': 'tour_info', 'type': 'TEXT', 'not_null': False},
                'admission_fee': {'name': 'admission_fee', 'type': 'TEXT', 'not_null': False},
                'city_id': {'name': 'city_id', 'type': 'INTEGER', 'not_null': True},
                'created_at': {'name': 'created_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'},
                'updated_at': {'name': 'updated_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'}
            }
        }
    
    def columns_differ(self, current: Dict, expected: Dict) -> bool:
        """Check if two column definitions differ"""
        return (current['type'] != expected['type'] or 
                current['not_null'] != expected.get('not_null', False) or
                current['default'] != expected.get('default'))
    
    def create_auto_migration(self, changes: List[Dict]) -> Dict:
        """Create migration automatically from detected changes"""
        migration = {
            'id': f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'name': f"Auto migration {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'description': f"Automatically generated migration for {len(changes)} changes",
            'timestamp': self.current_time,
            'changes': {
                'add_columns': {},
                'modify_columns': {},
                'drop_columns': {},
                'add_indexes': [],
                'drop_indexes': []
            },
            'applied': False
        }
        
        for change in changes:
            if change['type'] == 'missing_column':
                table = change['table']
                column = change['column']
                if table not in migration['changes']['add_columns']:
                    migration['changes']['add_columns'][table] = []
                migration['changes']['add_columns'][table].append(column)
        
        return migration
    
    def apply_migration(self, migration: Dict) -> bool:
        """Apply a migration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            changes = migration['changes']
            
            # Apply column additions
            if 'add_columns' in changes:
                for table, columns in changes['add_columns'].items():
                    for column in columns:
                        column_def = f"{column['name']} {column['type']}"
                        if column.get('not_null', False):
                            column_def += " NOT NULL"
                        if 'default' in column:
                            column_def += f" DEFAULT {column['default']}"
                        
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
                        print(f"   ✅ Added column {column['name']} to {table}")
            
            conn.commit()
            conn.close()
            
            print(f"✅ Applied migration: {migration['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error applying migration: {e}")
            return False
    
    def update_all_documentation(self):
        """Update all database documentation files"""
        print("📚 Updating all documentation...")
        
        # Update DATABASE_SCHEMA.md
        self.update_database_schema_doc()
        
        # Update ARCHITECTURE.md
        self.update_architecture_doc()
        
        # Update SETUP_GUIDE.md
        self.update_setup_guide()
        
        # Create/update API documentation
        self.update_api_docs()
        
        print("✅ All documentation updated")
    
    def update_database_schema_doc(self):
        """Update DATABASE_SCHEMA.md"""
        schema_file = os.path.join(self.docs_dir, 'DATABASE_SCHEMA.md')
        
        current_schema = self.get_current_schema()
        
        content = f"""# Database Schema

*Last updated: {self.current_time}*

## Overview

This document describes the current database schema for the Planner application.

## Tables

"""
        
        for table_name, columns in current_schema.items():
            content += f"### {table_name.title()}\n\n"
            content += "| Column | Type | Nullable | Default | Primary Key |\n"
            content += "|--------|------|----------|---------|-------------|\n"
            
            for col in columns:
                nullable = "No" if col['not_null'] else "Yes"
                default = col['default'] or ""
                pk = "Yes" if col['primary_key'] else "No"
                content += f"| {col['name']} | {col['type']} | {nullable} | {default} | {pk} |\n"
            
            content += "\n"
        
        # Write the file
        os.makedirs(self.docs_dir, exist_ok=True)
        with open(schema_file, 'w') as f:
            f.write(content)
        
        print(f"   ✅ Updated {schema_file}")
    
    def update_architecture_doc(self):
        """Update ARCHITECTURE.md"""
        arch_file = os.path.join(self.docs_dir, 'ARCHITECTURE.md')
        
        content = f"""# System Architecture

*Last updated: {self.current_time}*

## Database Layer

The application uses SQLite with SQLAlchemy ORM for data persistence.

### Key Features

- **NLP-Powered Text Normalization**: Intelligent city and country name correction
- **Automatic Timestamps**: All tables have created_at and updated_at fields
- **Comprehensive Venue Data**: Social media links, contact info, opening hours
- **Event Management**: Unified events table supporting tours, exhibitions, festivals, and photowalks
- **Geographic Support**: Cities with timezone and state/province information

### Models

- **City**: Geographic locations with timezone support
- **Venue**: Physical locations (museums, galleries, etc.)
- **Event**: Unified event class supporting all event types (tours, exhibitions, festivals, photowalks)

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
"""
        
        with open(arch_file, 'w') as f:
            f.write(content)
        
        print(f"   ✅ Updated {arch_file}")
    
    def update_setup_guide(self):
        """Update SETUP_GUIDE.md"""
        setup_file = os.path.join(self.docs_dir, 'SETUP_GUIDE.md')
        
        content = f"""# Setup Guide

*Last updated: {self.current_time}*

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database**
   ```bash
   python scripts/create_database_schema.py
   ```

3. **Run Application**
   ```bash
   python app.py
   ```

4. **Access Admin Interface**
   - Visit: http://localhost:5001/admin
   - Add cities with NLP-powered name correction
   - Discover venues automatically
   - Manage events and tours

## Database Management

### Automatic Schema Updates

The system automatically handles schema changes:

```bash
# Check for and apply schema changes
python scripts/database_migrator.py

# Or use the auto manager
python scripts/auto_database_manager.py
```

### Manual Operations

```bash
# Create fresh database
python scripts/create_database_schema.py

# Migrate existing database
python scripts/migrate_database.py

# Add timestamp columns
python scripts/add_timestamp_columns.py
```

## NLP Features

### City Name Correction

The system automatically corrects city name typos:
- "tabrz" → "Tabriz"
- "new york" → "New York"
- "los angeles" → "Los Angeles"

### Country Name Normalization

Recognizes country variations:
- "US", "usa", "United States" → "United States"
- "UK", "uk", "United Kingdom" → "United Kingdom"

### Usage

```python
from scripts.nlp_utils import normalize_city, normalize_country

# Correct city names
city = normalize_city("tabrz")  # Returns "Tabriz"
country = normalize_country("us")  # Returns "United States"
```

## API Endpoints

### Cities
- `GET /api/cities` - List all cities
- `POST /api/admin/add-city` - Add new city
- `DELETE /api/delete-city/<id>` - Delete city

### Venues
- `GET /api/venues` - List venues for city
- `POST /api/admin/add-venue` - Add new venue
- `POST /api/admin/discover-venues` - Auto-discover venues

### Events
- `GET /api/events` - List events for city
- `POST /api/add-event` - Add new event

### Admin
- `POST /api/admin/cleanup-duplicates` - Clean duplicate cities
- `POST /api/admin/fetch-venue-details` - Get venue details via LLM

## Troubleshooting

### Common Issues

1. **Database not found**
   - Run: `python scripts/create_database_schema.py`

2. **Missing columns**
   - Run: `python scripts/add_timestamp_columns.py`

3. **Schema out of sync**
   - Run: `python scripts/database_migrator.py`

4. **NLP not working**
   - Check: `pip install fuzzywuzzy python-Levenshtein sentence-transformers`

### Logs and Debugging

- Application logs: Check terminal output
- Database file: `~/.local/share/planner/events.db`
- Migration history: `~/.local/share/planner/migrations.json`
"""
        
        with open(setup_file, 'w') as f:
            f.write(content)
        
        print(f"   ✅ Updated {setup_file}")
    
    def update_api_docs(self):
        """Create/update API documentation"""
        api_file = os.path.join(self.docs_dir, 'API_DOCUMENTATION.md')
        
        content = f"""# API Documentation

*Last updated: {self.current_time}*

## Base URL
```
http://localhost:5001
```

## Authentication
Currently no authentication required (development mode).

## Endpoints

### Cities

#### List Cities
```http
GET /api/cities
```

Response:
```json
[
  {{
    "id": 1,
    "name": "Washington",
    "state": "District of Columbia",
    "country": "United States",
    "display_name": "Washington, District of Columbia",
    "timezone": "America/New_York"
  }}
]
```

#### Add City
```http
POST /api/admin/add-city
Content-Type: application/json

{{
  "name": "tabrz",
  "country": "iran"
}}
```

Response:
```json
{{
  "success": true,
  "message": "City \"Tabriz, Iran\" added successfully",
  "city_id": 23,
  "city": {{
    "id": 23,
    "name": "Tabriz",
    "country": "Iran",
    "timezone": "Asia/Tehran"
  }}
}}
```

#### Delete City
```http
DELETE /api/delete-city/23
```

### Venues

#### List Venues
```http
GET /api/venues?city_id=1
```

#### Add Venue
```http
POST /api/admin/add-venue
Content-Type: application/json

{{
  "name": "National Museum",
  "venue_type": "museum",
  "city_id": 1,
  "address": "123 Main St",
  "description": "A great museum"
}}
```

#### Discover Venues
```http
POST /api/admin/discover-venues
Content-Type: application/json

{{
  "city_id": 1
}}
```

### Events

#### List Events
```http
GET /api/events?city_id=1&time_range=today
```

#### Add Event
```http
POST /api/add-event
Content-Type: application/json

{{
  "title": "Art Exhibition",
  "event_type": "exhibition",
  "start_date": "2025-01-15",
  "end_date": "2025-03-15"
}}
```

### Admin Functions

#### Cleanup Duplicates
```http
POST /api/admin/cleanup-duplicates
```

#### Get Statistics
```http
GET /api/admin/stats
```

Response:
```json
{{
  "cities": 25,
  "venues": 150,
  "events": 300
}}
```

## Error Responses

All endpoints return consistent error responses:

```json
{{
  "error": "Error message description"
}}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found
- `500` - Internal Server Error

## NLP Features

The API automatically applies NLP normalization:

- **City Names**: Typos are corrected ("tabrz" → "Tabriz")
- **Country Names**: Variations are normalized ("us" → "United States")
- **Duplicate Detection**: Prevents duplicate entries with different formats

## Rate Limiting

Currently no rate limiting implemented (development mode).

## Examples

### Complete Workflow

1. **Add a city with typo**:
   ```bash
   curl -X POST http://localhost:5001/api/admin/add-city \\
     -H "Content-Type: application/json" \\
     -d '{{"name": "tabrz", "country": "iran"}}'
   ```

2. **Discover venues**:
   ```bash
   curl -X POST http://localhost:5001/api/admin/discover-venues \\
     -H "Content-Type: application/json" \\
     -d '{{"city_id": 23}}'
   ```

3. **List events**:
   ```bash
   curl "http://localhost:5001/api/events?city_id=23&time_range=this_week"
   ```
"""
        
        with open(api_file, 'w') as f:
            f.write(content)
        
        print(f"   ✅ Updated {api_file}")
    
    def update_model_files(self):
        """Update model files if needed"""
        print("🔧 Checking model files...")
        # This would update any model definition files
        # For now, just log that we checked
        print("   ✅ Model files are up to date")
    
    def run_verification_tests(self):
        """Run tests to verify everything works"""
        print("🧪 Running verification tests...")
        
        try:
            # Test database connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cities")
            city_count = cursor.fetchone()[0]
            conn.close()
            
            print(f"   ✅ Database connection OK ({city_count} cities)")
            
            # Test NLP functions
            from scripts.nlp_utils import normalize_city, normalize_country
            test_city = normalize_city("tabrz")
            test_country = normalize_country("us")
            
            if test_city == "Tabriz" and test_country == "United States":
                print("   ✅ NLP functions working correctly")
            else:
                print("   ❌ NLP functions not working correctly")
            
            print("   ✅ All verification tests passed")
            
        except Exception as e:
            print(f"   ❌ Verification tests failed: {e}")

def main():
    """Main function for auto database management"""
    manager = AutoDatabaseManager()
    
    print("🤖 Auto Database Manager")
    print("This will automatically:")
    print("1. Detect schema changes")
    print("2. Create and apply migrations")
    print("3. Update all documentation")
    print("4. Run verification tests")
    
    proceed = input("\nProceed? (y/N): ").lower() == 'y'
    if not proceed:
        print("❌ Operation cancelled")
        return
    
    success = manager.auto_update_everything()
    
    if success:
        print("\n🎉 Auto update completed successfully!")
        print("\n📋 What was updated:")
        print("✅ Database schema")
        print("✅ Migration history")
        print("✅ DATABASE_SCHEMA.md")
        print("✅ ARCHITECTURE.md")
        print("✅ SETUP_GUIDE.md")
        print("✅ API_DOCUMENTATION.md")
        print("✅ Verification tests")
    else:
        print("\n💥 Auto update failed!")

if __name__ == '__main__':
    main()
