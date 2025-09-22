# Setup Guide

*Last updated: 2025-09-09T22:27:36.517036*

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
