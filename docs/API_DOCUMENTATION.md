# API Documentation

*Last updated: 2025-09-09T22:27:36.517036*

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
  {
    "id": 1,
    "name": "Washington",
    "state": "District of Columbia",
    "country": "United States",
    "display_name": "Washington, District of Columbia",
    "timezone": "America/New_York"
  }
]
```

#### Add City
```http
POST /api/admin/add-city
Content-Type: application/json

{
  "name": "tabrz",
  "country": "iran"
}
```

Response:
```json
{
  "success": true,
  "message": "City "Tabriz, Iran" added successfully",
  "city_id": 23,
  "city": {
    "id": 23,
    "name": "Tabriz",
    "country": "Iran",
    "timezone": "Asia/Tehran"
  }
}
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

{
  "name": "National Museum",
  "venue_type": "museum",
  "city_id": 1,
  "address": "123 Main St",
  "description": "A great museum"
}
```

#### Discover Venues
```http
POST /api/admin/discover-venues
Content-Type: application/json

{
  "city_id": 1
}
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

{
  "title": "Art Exhibition",
  "event_type": "exhibition",
  "start_date": "2025-01-15",
  "end_date": "2025-03-15"
}
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
{
  "cities": 25,
  "venues": 150,
  "events": 300
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message description"
}
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
   curl -X POST http://localhost:5001/api/admin/add-city \
     -H "Content-Type: application/json" \
     -d '{"name": "tabrz", "country": "iran"}'
   ```

2. **Discover venues**:
   ```bash
   curl -X POST http://localhost:5001/api/admin/discover-venues \
     -H "Content-Type: application/json" \
     -d '{"city_id": 23}'
   ```

3. **List events**:
   ```bash
   curl "http://localhost:5001/api/events?city_id=23&time_range=this_week"
   ```
