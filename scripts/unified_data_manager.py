#!/usr/bin/env python3
"""
Unified Data Manager
Ensures consistent data loading across local and deployed environments
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event, Venue, City, Source

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedDataManager:
    """Unified data manager for both local and deployed environments"""
    
    def __init__(self):
        self.is_railway = self._detect_environment()
        self.data_path = Path("data")
        
    def _detect_environment(self) -> bool:
        """Detect if running in Railway/deployed environment"""
        return (
            os.getenv('RAILWAY_ENVIRONMENT') is not None or
            os.getenv('DATABASE_URL', '').startswith('postgresql://') or
            'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
        )
    
    def get_database_info(self) -> Dict:
        """Get current database information"""
        with app.app_context():
            return {
                'environment': 'Railway/PostgreSQL' if self.is_railway else 'Local/SQLite',
                'cities_count': City.query.count(),
                'venues_count': Venue.query.count(),
                'sources_count': Source.query.count(),
                'events_count': Event.query.count(),
                'database_url': os.getenv('DATABASE_URL', 'sqlite:///instance/events.db')[:50] + '...'
            }
    
    def validate_data_integrity(self) -> Dict:
        """Validate data integrity across all tables"""
        with app.app_context():
            issues = []
            
            # Check for orphaned sources (sources without valid city_id)
            orphaned_sources = Source.query.filter(
                ~Source.city_id.in_(db.session.query(City.id))
            ).count()
            if orphaned_sources > 0:
                issues.append(f"{orphaned_sources} sources have invalid city_id")
            
            # Check for orphaned venues
            orphaned_venues = Venue.query.filter(
                ~Venue.city_id.in_(db.session.query(City.id))
            ).count()
            if orphaned_venues > 0:
                issues.append(f"{orphaned_venues} venues have invalid city_id")
            
            # Check for orphaned events
            orphaned_events = Event.query.filter(
                ~Event.city_id.in_(db.session.query(City.id))
            ).count()
            if orphaned_events > 0:
                issues.append(f"{orphaned_events} events have invalid city_id")
            
            return {
                'valid': len(issues) == 0,
                'issues': issues,
                'timestamp': datetime.now().isoformat()
            }
    
    def load_cities(self, force_reload: bool = False) -> bool:
        """Load cities from JSON with validation"""
        logger.info("🏙️ Loading cities...")
        
        cities_file = self.data_path / "cities.json"
        if not cities_file.exists():
            logger.error("❌ cities.json not found")
            return False
        
        try:
            with open(cities_file, 'r') as f:
                data = json.load(f)
            
            cities_data = data.get('cities', {})
            if not cities_data:
                logger.error("❌ No cities data found in JSON file")
                return False
            
            with app.app_context():
                # Check if cities already exist
                existing_cities = City.query.count()
                if existing_cities > 0 and not force_reload:
                    logger.info(f"✅ Cities already loaded ({existing_cities} cities)")
                    return True
                
                if force_reload:
                    logger.info("🧹 Clearing existing cities...")
                    City.query.delete()
                    db.session.commit()
                
                # Add cities to database
                cities_added = 0
                for city_id, city_info in cities_data.items():
                    try:
                        city = City(
                            id=int(city_id),
                            name=city_info['name'],
                            state=city_info.get('state'),
                            country=city_info['country'],
                            timezone=city_info.get('timezone', 'UTC'),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        db.session.add(city)
                        cities_added += 1
                    except Exception as e:
                        logger.error(f"⚠️ Error adding city {city_info.get('name', 'Unknown')}: {e}")
                
                db.session.commit()
                logger.info(f"✅ Successfully loaded {cities_added} cities")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error loading cities: {e}")
            return False
    
    def load_sources(self, force_reload: bool = False) -> bool:
        """Load sources from JSON with validation"""
        logger.info("📰 Loading sources...")
        
        sources_file = self.data_path / "sources.json"
        if not sources_file.exists():
            logger.error("❌ sources.json not found")
            return False
        
        try:
            with open(sources_file, 'r') as f:
                data = json.load(f)
            
            sources_data = data.get('sources', {})
            if not sources_data:
                logger.error("❌ No sources data found in JSON file")
                return False
            
            with app.app_context():
                # Check if sources already exist
                existing_sources = Source.query.count()
                if existing_sources > 0 and not force_reload:
                    logger.info(f"✅ Sources already loaded ({existing_sources} sources)")
                    return True
                
                if force_reload:
                    logger.info("🧹 Clearing existing sources...")
                    Source.query.delete()
                    db.session.commit()
                
                # Validate city IDs exist
                city_ids = set(City.query.with_entities(City.id).all())
                city_ids = {cid[0] for cid in city_ids}
                
                sources_added = 0
                skipped_sources = 0
                
                for source_id, source_data in sources_data.items():
                    try:
                        city_id = source_data.get('city_id')
                        if city_id not in city_ids:
                            logger.warning(f"⚠️ Skipping source {source_data.get('name')} - invalid city_id: {city_id}")
                            skipped_sources += 1
                            continue
                        
                        # Handle list fields
                        event_types = source_data.get('event_types', [])
                        if isinstance(event_types, list):
                            event_types = json.dumps(event_types)
                        
                        covered_cities = source_data.get('covered_cities')
                        if isinstance(covered_cities, list):
                            covered_cities = json.dumps(covered_cities)
                        
                        # Create source
                        source = Source(
                            id=int(source_id),
                            name=source_data.get('name', ''),
                            handle=source_data.get('handle', ''),
                            source_type=source_data.get('source_type', 'website'),
                            url=source_data.get('url', ''),
                            description=source_data.get('description', ''),
                            city_id=city_id,
                            covers_multiple_cities=source_data.get('covers_multiple_cities', False),
                            covered_cities=covered_cities,
                            event_types=event_types,
                            is_active=source_data.get('is_active', True),
                            reliability_score=source_data.get('reliability_score', 0.0),
                            posting_frequency=source_data.get('posting_frequency', ''),
                            notes=source_data.get('notes', ''),
                            scraping_pattern=source_data.get('scraping_pattern', ''),
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        db.session.add(source)
                        sources_added += 1
                        
                    except Exception as e:
                        logger.error(f"⚠️ Error adding source {source_data.get('name', 'Unknown')}: {e}")
                        skipped_sources += 1
                        continue
                
                db.session.commit()
                logger.info(f"✅ Successfully loaded {sources_added} sources")
                if skipped_sources > 0:
                    logger.warning(f"⚠️ Skipped {skipped_sources} sources due to validation issues")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error loading sources: {e}")
            return False
    
    def load_venues(self, force_reload: bool = False) -> bool:
        """Load venues from JSON with validation"""
        logger.info("🏛️ Loading venues...")
        
        venues_file = self.data_path / "venues.json"
        if not venues_file.exists():
            logger.error("❌ venues.json not found")
            return False
        
        try:
            with open(venues_file, 'r') as f:
                data = json.load(f)
            
            venues_data = data.get('venues', {})
            if not venues_data:
                logger.error("❌ No venues data found in JSON file")
                return False
            
            with app.app_context():
                # Check if venues already exist
                existing_venues = Venue.query.count()
                if existing_venues > 0 and not force_reload:
                    logger.info(f"✅ Venues already loaded ({existing_venues} venues)")
                    return True
                
                if force_reload:
                    logger.info("🧹 Clearing existing venues...")
                    Venue.query.delete()
                    db.session.commit()
                
                venues_added = 0
                
                # Handle the nested structure: venues_data[city_id]["venues"]
                for city_id, city_data in venues_data.items():
                    city_name = city_data.get('name', 'Unknown')
                    city_venues = city_data.get('venues', [])
                    
                    # Find the city in database
                    city = City.query.filter_by(name=city_name.split(',')[0].strip()).first()
                    if not city:
                        logger.warning(f"⚠️ City not found: {city_name}")
                        continue
                    
                    for venue_data in city_venues:
                        try:
                            # Handle image_url
                            image_url = venue_data.get('image_url', '')
                            if isinstance(image_url, dict):
                                image_url = f"https://via.placeholder.com/400x300/667eea/ffffff?text={venue_data.get('name', 'Venue').replace(' ', '+')}"
                            
                            # Create venue
                            venue = Venue(
                                name=venue_data.get('name', ''),
                                venue_type=venue_data.get('venue_type', 'museum'),
                                address=venue_data.get('address', ''),
                                latitude=venue_data.get('latitude'),
                                longitude=venue_data.get('longitude'),
                                image_url=image_url,
                                instagram_url=venue_data.get('instagram_url', ''),
                                facebook_url=venue_data.get('facebook_url', ''),
                                twitter_url=venue_data.get('twitter_url', ''),
                                youtube_url=venue_data.get('youtube_url', ''),
                                tiktok_url=venue_data.get('tiktok_url', ''),
                                website_url=venue_data.get('website_url', ''),
                                description=venue_data.get('description', ''),
                                city_id=city.id,
                                opening_hours=venue_data.get('opening_hours', ''),
                                holiday_hours=venue_data.get('holiday_hours', ''),
                                phone_number=venue_data.get('phone_number', ''),
                                email=venue_data.get('email', ''),
                                tour_info=venue_data.get('tour_info', ''),
                                admission_fee=venue_data.get('admission_fee', ''),
                                additional_info=json.dumps(venue_data['additional_info']) if isinstance(venue_data.get('additional_info'), dict) else venue_data.get('additional_info'),
                                created_at=datetime.now(),
                                updated_at=datetime.now()
                            )
                            
                            db.session.add(venue)
                            venues_added += 1
                            
                        except Exception as e:
                            logger.error(f"⚠️ Error adding venue {venue_data.get('name', 'Unknown')}: {e}")
                            continue
                
                db.session.commit()
                logger.info(f"✅ Successfully loaded {venues_added} venues")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error loading venues: {e}")
            return False
    
    def sync_all_data(self, force_reload: bool = False) -> bool:
        """Sync all data with validation"""
        logger.info("🚀 UNIFIED DATA SYNC")
        logger.info("=" * 50)
        
        # Create database tables first
        logger.info("🔧 Creating database tables...")
        with app.app_context():
            try:
                db.create_all()
                logger.info("✅ Database tables created successfully")
            except Exception as e:
                logger.error(f"❌ Error creating database tables: {e}")
                return False
        
        # Load data in order (cities first, then sources/venues)
        if not self.load_cities(force_reload):
            logger.error("❌ Failed to load cities!")
            return False
        
        if not self.load_sources(force_reload):
            logger.error("❌ Failed to load sources!")
            return False
        
        if not self.load_venues(force_reload):
            logger.error("❌ Failed to load venues!")
            return False
        
        # Validate data integrity
        logger.info("🔍 Validating data integrity...")
        validation = self.validate_data_integrity()
        if not validation['valid']:
            logger.warning("⚠️ Data integrity issues found:")
            for issue in validation['issues']:
                logger.warning(f"   - {issue}")
        else:
            logger.info("✅ Data integrity validation passed")
        
        # Show final stats
        db_info = self.get_database_info()
        logger.info("\n📊 Final Database Statistics:")
        logger.info("=" * 40)
        logger.info(f"   Environment: {db_info['environment']}")
        logger.info(f"   Cities: {db_info['cities_count']}")
        logger.info(f"   Venues: {db_info['venues_count']}")
        logger.info(f"   Sources: {db_info['sources_count']}")
        logger.info(f"   Events: {db_info['events_count']}")
        logger.info("=" * 40)
        
        logger.info("\n🎉 Unified data sync completed successfully!")
        return True

def main():
    """Main function for unified data management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Data Manager')
    parser.add_argument('--force', action='store_true', help='Force reload all data')
    parser.add_argument('--validate', action='store_true', help='Only validate data integrity')
    parser.add_argument('--info', action='store_true', help='Show database info')
    
    args = parser.parse_args()
    
    manager = UnifiedDataManager()
    
    if args.info:
        db_info = manager.get_database_info()
        print("📊 Database Information:")
        print("=" * 30)
        for key, value in db_info.items():
            print(f"{key}: {value}")
        return 0
    
    if args.validate:
        validation = manager.validate_data_integrity()
        print("🔍 Data Integrity Validation:")
        print("=" * 35)
        print(f"Valid: {validation['valid']}")
        if validation['issues']:
            print("Issues:")
            for issue in validation['issues']:
                print(f"  - {issue}")
        else:
            print("✅ No issues found")
        return 0
    
    # Default: sync all data
    success = manager.sync_all_data(args.force)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
