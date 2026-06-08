#!/usr/bin/env python3
"""
Script to migrate data from SQLite to PostgreSQL on Railway
Run this after adding PostgreSQL service to Railway
"""

import os
import sys
sys.path.append('.')

from app import app, db, City, Venue, Source, Event
from sqlalchemy import create_engine, text

def migrate_to_postgres():
    """Migrate data from SQLite to PostgreSQL"""
    
    print("🔄 Starting migration from SQLite to PostgreSQL...")
    
    # Check if we have PostgreSQL connection
    postgres_url = os.getenv('DATABASE_URL')
    if not postgres_url or 'postgresql' not in postgres_url:
        print("❌ No PostgreSQL DATABASE_URL found")
        print("   Please add PostgreSQL service to Railway first")
        return False
    
    print(f"✅ PostgreSQL URL found: {postgres_url[:50]}...")
    
    with app.app_context():
        try:
            # Create PostgreSQL engine
            postgres_engine = create_engine(postgres_url)
            
            # Test connection
            with postgres_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ PostgreSQL connection successful")
            
            # Create all tables in PostgreSQL
            print("🏗️  Creating tables in PostgreSQL...")
            db.metadata.create_all(postgres_engine)
            print("✅ Tables created")
            
            # Get all data from SQLite
            print("📊 Exporting data from SQLite...")
            
            cities = City.query.all()
            venues = Venue.query.all()
            sources = Source.query.all()
            events = Event.query.all()
            
            print(f"   Cities: {len(cities)}")
            print(f"   Venues: {len(venues)}")
            print(f"   Sources: {len(sources)}")
            print(f"   Events: {len(events)}")
            
            # Insert data into PostgreSQL
            print("📥 Importing data to PostgreSQL...")
            
            # Use PostgreSQL engine for inserts
            with postgres_engine.connect() as conn:
                # Insert cities
                for city in cities:
                    conn.execute(text("""
                        INSERT INTO cities (id, name, country, timezone, latitude, longitude, 
                                          description, created_at, updated_at)
                        VALUES (:id, :name, :country, :timezone, :latitude, :longitude,
                                :description, :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': city.id,
                        'name': city.name,
                        'country': city.country,
                        'timezone': city.timezone,
                        'latitude': city.latitude,
                        'longitude': city.longitude,
                        'description': city.description,
                        'created_at': city.created_at,
                        'updated_at': city.updated_at
                    })
                
                conn.commit()
                print(f"✅ Inserted {len(cities)} cities")
                
                # Insert venues
                for venue in venues:
                    conn.execute(text("""
                        INSERT INTO venues (id, name, venue_type, description, address, opening_hours,
                                          phone_number, email, tour_info, admission_fee, website_url,
                                          image_url, latitude, longitude, facebook_url, instagram_url,
                                          twitter_url, youtube_url, tiktok_url, holiday_hours,
                                          additional_info, city_id, created_at, updated_at)
                        VALUES (:id, :name, :venue_type, :description, :address, :opening_hours,
                                :phone_number, :email, :tour_info, :admission_fee, :website_url,
                                :image_url, :latitude, :longitude, :facebook_url, :instagram_url,
                                :twitter_url, :youtube_url, :tiktok_url, :holiday_hours,
                                :additional_info, :city_id, :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': venue.id,
                        'name': venue.name,
                        'venue_type': venue.venue_type,
                        'description': venue.description,
                        'address': venue.address,
                        'opening_hours': venue.opening_hours,
                        'phone_number': venue.phone_number,
                        'email': venue.email,
                        'tour_info': venue.tour_info,
                        'admission_fee': venue.admission_fee,
                        'website_url': venue.website_url,
                        'image_url': venue.image_url,
                        'latitude': venue.latitude,
                        'longitude': venue.longitude,
                        'facebook_url': venue.facebook_url,
                        'instagram_url': venue.instagram_url,
                        'twitter_url': venue.twitter_url,
                        'youtube_url': venue.youtube_url,
                        'tiktok_url': venue.tiktok_url,
                        'holiday_hours': venue.holiday_hours,
                        'additional_info': venue.additional_info,
                        'city_id': venue.city_id,
                        'created_at': venue.created_at,
                        'updated_at': venue.updated_at
                    })
                
                conn.commit()
                print(f"✅ Inserted {len(venues)} venues")
                
                # Insert sources
                for source in sources:
                    conn.execute(text("""
                        INSERT INTO sources (id, name, handle, source_type, url, description,
                                           city_id, covers_multiple_cities, covered_cities,
                                           event_types, is_active, last_checked, last_event_found,
                                           events_found_count, reliability_score, posting_frequency,
                                           notes, scraping_pattern, created_at, updated_at)
                        VALUES (:id, :name, :handle, :source_type, :url, :description,
                                :city_id, :covers_multiple_cities, :covered_cities,
                                :event_types, :is_active, :last_checked, :last_event_found,
                                :events_found_count, :reliability_score, :posting_frequency,
                                :notes, :scraping_pattern, :created_at, :updated_at)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': source.id,
                        'name': source.name,
                        'handle': source.handle,
                        'source_type': source.source_type,
                        'url': source.url,
                        'description': source.description,
                        'city_id': source.city_id,
                        'covers_multiple_cities': source.covers_multiple_cities,
                        'covered_cities': source.covered_cities,
                        'event_types': source.event_types,
                        'is_active': source.is_active,
                        'last_checked': source.last_checked,
                        'last_event_found': source.last_event_found,
                        'events_found_count': source.events_found_count,
                        'reliability_score': source.reliability_score,
                        'posting_frequency': source.posting_frequency,
                        'notes': source.notes,
                        'scraping_pattern': source.scraping_pattern,
                        'created_at': source.created_at,
                        'updated_at': source.updated_at
                    })
                
                conn.commit()
                print(f"✅ Inserted {len(sources)} sources")
                
                # Insert events
                for event in events:
                    conn.execute(text("""
                        INSERT INTO events (id, title, description, start_date, end_date,
                                          start_time, end_time, image_url, url, is_selected,
                                          event_type, created_at, updated_at, start_location,
                                          end_location, venue_id, city_id, start_latitude,
                                          start_longitude, end_latitude, end_longitude,
                                          tour_type, max_participants, price, language,
                                          exhibition_location, curator, admission_price,
                                          festival_type, multiple_locations, difficulty_level,
                                          equipment_needed, organizer)
                        VALUES (:id, :title, :description, :start_date, :end_date,
                                :start_time, :end_time, :image_url, :url, :is_selected,
                                :event_type, :created_at, :updated_at, :start_location,
                                :end_location, :venue_id, :city_id, :start_latitude,
                                :start_longitude, :end_latitude, :end_longitude,
                                :tour_type, :max_participants, :price, :language,
                                :exhibition_location, :curator, :admission_price,
                                :festival_type, :multiple_locations, :difficulty_level,
                                :equipment_needed, :organizer)
                        ON CONFLICT (id) DO NOTHING
                    """), {
                        'id': event.id,
                        'title': event.title,
                        'description': event.description,
                        'start_date': event.start_date,
                        'end_date': event.end_date,
                        'start_time': event.start_time,
                        'end_time': event.end_time,
                        'image_url': event.image_url,
                        'url': event.url,
                        'is_selected': event.is_selected,
                        'event_type': event.event_type,
                        'created_at': event.created_at,
                        'updated_at': event.updated_at,
                        'start_location': event.start_location,
                        'end_location': event.end_location,
                        'venue_id': event.venue_id,
                        'city_id': event.city_id,
                        'start_latitude': event.start_latitude,
                        'start_longitude': event.start_longitude,
                        'end_latitude': event.end_latitude,
                        'end_longitude': event.end_longitude,
                        'tour_type': event.tour_type,
                        'max_participants': event.max_participants,
                        'price': event.price,
                        'language': event.language,
                        'exhibition_location': event.exhibition_location,
                        'curator': event.curator,
                        'admission_price': event.admission_price,
                        'festival_type': event.festival_type,
                        'multiple_locations': event.multiple_locations,
                        'difficulty_level': event.difficulty_level,
                        'equipment_needed': event.equipment_needed,
                        'organizer': event.organizer
                    })
                
                conn.commit()
                print(f"✅ Inserted {len(events)} events")
            
            print("🎉 Migration completed successfully!")
            
            # Verify data
            print("\n🔍 Verifying PostgreSQL data...")
            with postgres_engine.connect() as conn:
                cities_count = conn.execute(text("SELECT COUNT(*) FROM cities")).scalar()
                venues_count = conn.execute(text("SELECT COUNT(*) FROM venues")).scalar()
                sources_count = conn.execute(text("SELECT COUNT(*) FROM sources")).scalar()
                events_count = conn.execute(text("SELECT COUNT(*) FROM events")).scalar()
                
                print(f"   Cities: {cities_count}")
                print(f"   Venues: {venues_count}")
                print(f"   Sources: {sources_count}")
                print(f"   Events: {events_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

if __name__ == "__main__":
    success = migrate_to_postgres()
    if success:
        print("\n✅ Migration completed! Your Railway app now uses PostgreSQL.")
        print("🔗 You can now connect DBeaver to the PostgreSQL database.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
