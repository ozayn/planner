#!/usr/bin/env python3
"""
Add NYC Event Sources
Adds popular NYC event sources for event scraping
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import from the main app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Source

def add_nyc_sources():
    """Add NYC event sources to the database"""
    
    with app.app_context():
        # NYC sources data
        nyc_sources = [
            {
                "name": "NYC Arts",
                "handle": "@nycarts",
                "source_type": "instagram",
                "url": "https://www.instagram.com/nycarts/",
                "description": "Official NYC arts and culture account showcasing events, exhibitions, and cultural happenings across all five boroughs.",
                "city_id": 2,  # NYC
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"art_exhibitions\", \"cultural_events\", \"gallery_openings\", \"artist_showcases\", \"visual_arts\", \"theater\", \"music\", \"dance\", \"performances\"]",
                "is_active": True,
                "reliability_score": 5.0,
                "posting_frequency": "daily",
                "notes": "Official NYC government arts account. Highly reliable source for major cultural events and exhibitions across NYC.",
                "scraping_pattern": "Look for posts about art exhibitions, gallery openings, cultural events, and artist showcases. Monitor hashtags like #NYCArts, #NYCCulture, #ArtExhibitions, #GalleryOpenings.",
            },
            {
                "name": "Time Out New York",
                "handle": "@timeoutnewyork",
                "source_type": "instagram",
                "url": "https://www.instagram.com/timeoutnewyork/",
                "description": "Time Out New York covers the best events, restaurants, attractions, and cultural happenings in New York City.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"cultural_events\", \"food_events\", \"music\", \"theater\", \"art_exhibitions\", \"festivals\", \"community_events\", \"nightlife\", \"family_events\"]",
                "is_active": True,
                "reliability_score": 4.8,
                "posting_frequency": "daily",
                "notes": "Established NYC culture and events publication. Excellent source for comprehensive event coverage across all categories.",
                "scraping_pattern": "Look for posts about events, exhibitions, concerts, theater, food events, and cultural happenings. Monitor hashtags like #TimeOutNYC, #NYCEvents, #NYCCulture, #NYCFood.",
            },
            {
                "name": "The Metropolitan Museum of Art",
                "handle": "@metmuseum",
                "source_type": "instagram",
                "url": "https://www.instagram.com/metmuseum/",
                "description": "The Met Museum's official Instagram showcasing exhibitions, events, and behind-the-scenes content from one of the world's greatest museums.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"art_exhibitions\", \"museum_events\", \"lectures\", \"workshops\", \"cultural_events\", \"artist_talks\", \"gallery_tours\"]",
                "is_active": True,
                "reliability_score": 5.0,
                "posting_frequency": "daily",
                "notes": "Official Met Museum account. Premier source for major art exhibitions, museum events, and cultural programming.",
                "scraping_pattern": "Look for posts about new exhibitions, museum events, lectures, workshops, and special programming. Monitor hashtags like #MetMuseum, #ArtExhibitions, #NYCArt, #MuseumEvents.",
            },
            {
                "name": "MoMA",
                "handle": "@themuseumofmodernart",
                "source_type": "instagram",
                "url": "https://www.instagram.com/themuseumofmodernart/",
                "description": "Museum of Modern Art's official Instagram featuring contemporary art exhibitions, events, and modern art highlights.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"art_exhibitions\", \"contemporary_art\", \"museum_events\", \"artist_talks\", \"film_screenings\", \"performance_art\", \"workshops\"]",
                "is_active": True,
                "reliability_score": 5.0,
                "posting_frequency": "daily",
                "notes": "Official MoMA account. Leading source for contemporary art exhibitions, modern art events, and cutting-edge cultural programming.",
                "scraping_pattern": "Look for posts about contemporary art exhibitions, modern art events, artist talks, film screenings, and performance art. Monitor hashtags like #MoMA, #ModernArt, #ContemporaryArt, #NYCArt.",
            },
            {
                "name": "Brooklyn Museum",
                "handle": "@brooklynmuseum",
                "source_type": "instagram",
                "url": "https://www.instagram.com/brooklynmuseum/",
                "description": "Brooklyn Museum's official Instagram showcasing diverse exhibitions, community events, and cultural programming.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"art_exhibitions\", \"cultural_events\", \"community_events\", \"artist_showcases\", \"workshops\", \"lectures\", \"family_events\"]",
                "is_active": True,
                "reliability_score": 4.9,
                "posting_frequency": "daily",
                "notes": "Official Brooklyn Museum account. Great source for diverse art exhibitions, community events, and Brooklyn cultural programming.",
                "scraping_pattern": "Look for posts about art exhibitions, community events, artist showcases, workshops, and cultural programming. Monitor hashtags like #BrooklynMuseum, #BrooklynArt, #NYCArt, #CommunityEvents.",
            },
            {
                "name": "NYC Parks",
                "handle": "@nycparks",
                "source_type": "instagram",
                "url": "https://www.instagram.com/nycparks/",
                "description": "NYC Parks official Instagram featuring outdoor events, park activities, and nature-based programming across the city.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"outdoor_events\", \"park_events\", \"nature_events\", \"family_events\", \"fitness_events\", \"community_events\", \"seasonal_events\"]",
                "is_active": True,
                "reliability_score": 4.8,
                "posting_frequency": "daily",
                "notes": "Official NYC Parks account. Excellent source for outdoor events, park activities, and nature-based programming across all boroughs.",
                "scraping_pattern": "Look for posts about park events, outdoor activities, nature programming, fitness events, and seasonal celebrations. Monitor hashtags like #NYCParks, #OutdoorEvents, #ParkEvents, #NYCNature.",
            },
            {
                "name": "Lincoln Center",
                "handle": "@lincolncenter",
                "source_type": "instagram",
                "url": "https://www.instagram.com/lincolncenter/",
                "description": "Lincoln Center's official Instagram showcasing world-class performing arts events, concerts, and cultural programming.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"music\", \"theater\", \"dance\", \"opera\", \"classical_music\", \"performances\", \"cultural_events\", \"concerts\"]",
                "is_active": True,
                "reliability_score": 5.0,
                "posting_frequency": "daily",
                "notes": "Official Lincoln Center account. Premier source for world-class performing arts events, classical music, opera, and cultural performances.",
                "scraping_pattern": "Look for posts about concerts, performances, opera, classical music, theater, and dance events. Monitor hashtags like #LincolnCenter, #ClassicalMusic, #NYCTheater, #PerformingArts.",
            },
            {
                "name": "Brooklyn Academy of Music",
                "handle": "@bam_brooklyn",
                "source_type": "instagram",
                "url": "https://www.instagram.com/bam_brooklyn/",
                "description": "BAM's official Instagram featuring cutting-edge performances, contemporary art, and avant-garde cultural events.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"contemporary_art\", \"avant_garde\", \"experimental_theater\", \"dance\", \"music\", \"film_screenings\", \"cultural_events\", \"performances\"]",
                "is_active": True,
                "reliability_score": 4.9,
                "posting_frequency": "daily",
                "notes": "Official BAM account. Leading source for cutting-edge performances, experimental art, and avant-garde cultural programming.",
                "scraping_pattern": "Look for posts about experimental performances, contemporary art, avant-garde events, film screenings, and cutting-edge cultural programming. Monitor hashtags like #BAM, #ExperimentalArt, #AvantGarde, #BrooklynCulture.",
            },
            {
                "name": "NYC.com",
                "handle": "nyc.com",
                "source_type": "website",
                "url": "https://www.nyc.com",
                "description": "Comprehensive NYC events calendar covering attractions, events, restaurants, and activities across all five boroughs.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"cultural_events\", \"attractions\", \"food_events\", \"music\", \"theater\", \"art_exhibitions\", \"festivals\", \"community_events\", \"family_events\"]",
                "is_active": True,
                "reliability_score": 4.5,
                "posting_frequency": "daily",
                "notes": "Comprehensive NYC events website. Good source for broad coverage of events and attractions across all categories.",
                "scraping_pattern": "Look for event listings, attraction information, restaurant events, and activity recommendations. Monitor for event announcements and cultural programming updates.",
            },
            {
                "name": "Gothamist",
                "handle": "@gothamist",
                "source_type": "instagram",
                "url": "https://www.instagram.com/gothamist/",
                "description": "Gothamist covers NYC news, events, and culture with a focus on local happenings and community events.",
                "city_id": 2,
                "covers_multiple_cities": False,
                "covered_cities": "",
                "event_types": "[\"community_events\", \"cultural_events\", \"local_news\", \"political_events\", \"festivals\", \"neighborhood_events\", \"free_events\"]",
                "is_active": True,
                "reliability_score": 4.6,
                "posting_frequency": "daily",
                "notes": "Local NYC news and culture publication. Good source for community events, neighborhood happenings, and local cultural programming.",
                "scraping_pattern": "Look for posts about community events, neighborhood happenings, local culture, festivals, and free events. Monitor hashtags like #Gothamist, #NYCLocal, #CommunityEvents, #NeighborhoodEvents.",
            }
        ]
        
        print(f"🏙️ Adding {len(nyc_sources)} NYC event sources...")
        
        sources_added = 0
        sources_skipped = 0
        
        for source_data in nyc_sources:
            try:
                # Check if source already exists
                existing_source = Source.query.filter_by(
                    name=source_data["name"],
                    city_id=source_data["city_id"]
                ).first()
                
                if existing_source:
                    print(f"⚠️ Source already exists: {source_data['name']}")
                    sources_skipped += 1
                    continue
                
                # Create new source
                source = Source()
                source.name = source_data["name"]
                source.handle = source_data["handle"]
                source.source_type = source_data["source_type"]
                source.url = source_data["url"]
                source.description = source_data["description"]
                source.city_id = source_data["city_id"]
                source.covers_multiple_cities = source_data["covers_multiple_cities"]
                source.covered_cities = source_data["covered_cities"]
                source.event_types = source_data["event_types"]
                source.is_active = source_data["is_active"]
                source.reliability_score = source_data["reliability_score"]
                source.posting_frequency = source_data["posting_frequency"]
                source.notes = source_data["notes"]
                source.scraping_pattern = source_data["scraping_pattern"]
                source.last_checked = None
                source.created_at = datetime.now()
                source.updated_at = datetime.now()
                
                # Add to database
                db.session.add(source)
                sources_added += 1
                
                print(f"✅ Added: {source_data['name']} ({source_data['source_type']})")
                
            except Exception as e:
                print(f"❌ Error adding source '{source_data['name']}': {e}")
                sources_skipped += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n🎉 Successfully added {sources_added} NYC sources")
        if sources_skipped > 0:
            print(f"⚠️ Skipped {sources_skipped} sources (already existed or errors)")
        
        return sources_added > 0

def main():
    """Main function"""
    success = add_nyc_sources()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
