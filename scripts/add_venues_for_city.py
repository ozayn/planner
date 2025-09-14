#!/usr/bin/env python3
"""
Add Venues for City Script
Fetches venues for a city using knowledge, fills all fields, gets Google Maps images, and updates database
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import Flask app and models
from app import app, db, Venue, City
from scripts.utils import get_google_maps_image

def get_venues_for_city_knowledge(city_name, country):
    """Get venues for a city using knowledge base"""
    
    # Knowledge base of venues by city
    venues_knowledge = {
        "Washington": {
            "country": "United States",
            "venues": [
                {
                    "name": "Smithsonian National Air and Space Museum",
                    "venue_type": "Museum",
                    "address": "600 Independence Ave SW, Washington, DC 20560",
                    "opening_hours": "10:00 AM - 5:30 PM",
                    "phone_number": "(202) 633-2214",
                    "email": "info@si.edu",
                    "description": "The world's largest collection of aviation and space artifacts, including the Wright Brothers' plane and Apollo 11 command module.",
                    "tour_info": "Free admission. Guided tours daily. Audio tours available. Planetarium shows and IMAX films.",
                    "admission_fee": "Free",
                    "website_url": "https://airandspace.si.edu",
                    "instagram_url": "@airandspace",
                    "facebook_url": "https://www.facebook.com/AirandSpaceMuseum",
                    "twitter_url": "@AirandSpace",
                    "youtube_url": "https://www.youtube.com/c/airandspace",
                    "tiktok_url": ""
                },
                {
                    "name": "National Gallery of Art",
                    "venue_type": "Museum",
                    "address": "Constitution Ave NW, Washington, DC 20565",
                    "opening_hours": "10:00 AM - 5:00 PM",
                    "phone_number": "(202) 737-4215",
                    "email": "visitor-services@nga.gov",
                    "description": "One of the world's finest art museums with an extensive collection of European and American art.",
                    "tour_info": "Free admission. Guided tours available. Audio guides and mobile app tours. Special exhibitions may require tickets.",
                    "admission_fee": "Free",
                    "website_url": "https://www.nga.gov",
                    "instagram_url": "@ngadc",
                    "facebook_url": "https://www.facebook.com/NationalGalleryofArt",
                    "twitter_url": "@ngadc",
                    "youtube_url": "https://www.youtube.com/c/ngadc",
                    "tiktok_url": ""
                }
            ]
        },
        "New York": {
            "country": "United States",
            "venues": [
                {
                    "name": "Metropolitan Museum of Art",
                    "venue_type": "Museum",
                    "address": "1000 5th Ave, New York, NY 10028",
                    "opening_hours": "10:00 AM - 5:00 PM (Thu-Mon), 10:00 AM - 9:00 PM (Fri-Sat)",
                    "phone_number": "(212) 535-7710",
                    "email": "information@metmuseum.org",
                    "description": "One of the world's largest and finest art museums, with over 2 million works spanning 5,000 years.",
                    "tour_info": "Admission: $30 adults, $22 seniors, $17 students. Guided tours available. Audio guides and mobile app.",
                    "admission_fee": "$30",
                    "website_url": "https://www.metmuseum.org",
                    "instagram_url": "@metmuseum",
                    "facebook_url": "https://www.facebook.com/metmuseum",
                    "twitter_url": "@metmuseum",
                    "youtube_url": "https://www.youtube.com/c/metmuseum",
                    "tiktok_url": ""
                },
                {
                    "name": "Museum of Modern Art (MoMA)",
                    "venue_type": "Museum",
                    "address": "11 W 53rd St, New York, NY 10019",
                    "opening_hours": "10:30 AM - 5:30 PM (Mon-Thu), 10:30 AM - 9:00 PM (Fri)",
                    "phone_number": "(212) 708-9400",
                    "email": "info@moma.org",
                    "description": "Premier museum of modern and contemporary art, featuring works by Picasso, Van Gogh, Warhol, and more.",
                    "tour_info": "Admission: $25 adults, $18 seniors, $14 students. Free admission for children under 16. Audio guides available.",
                    "admission_fee": "$25",
                    "website_url": "https://www.moma.org",
                    "instagram_url": "@themuseumofmodernart",
                    "facebook_url": "https://www.facebook.com/MuseumofModernArt",
                    "twitter_url": "@MuseumModernArt",
                    "youtube_url": "https://www.youtube.com/c/momavideos",
                    "tiktok_url": ""
                }
            ]
        },
        "London": {
            "country": "United Kingdom",
            "venues": [
                {
                    "name": "British Museum",
                    "venue_type": "Museum",
                    "address": "Great Russell St, London WC1B 3DG, UK",
                    "opening_hours": "10:00 AM - 5:00 PM (Mon-Sun), 10:00 AM - 8:30 PM (Fri)",
                    "phone_number": "+44 20 7323 8299",
                    "email": "info@britishmuseum.org",
                    "description": "World-famous museum of human history, art and culture, with over 8 million works including the Rosetta Stone.",
                    "tour_info": "Free admission. Guided tours available. Audio guides and mobile app. Special exhibitions may require tickets.",
                    "admission_fee": "Free",
                    "website_url": "https://www.britishmuseum.org",
                    "instagram_url": "@britishmuseum",
                    "facebook_url": "https://www.facebook.com/britishmuseum",
                    "twitter_url": "@britishmuseum",
                    "youtube_url": "https://www.youtube.com/c/britishmuseum",
                    "tiktok_url": ""
                },
                {
                    "name": "Tate Modern",
                    "venue_type": "Museum",
                    "address": "Bankside, London SE1 9TG, UK",
                    "opening_hours": "10:00 AM - 6:00 PM (Sun-Thu), 10:00 AM - 10:00 PM (Fri-Sat)",
                    "phone_number": "+44 20 7887 8888",
                    "email": "info@tate.org.uk",
                    "description": "International modern and contemporary art museum housed in a former power station on the Thames.",
                    "tour_info": "Free admission to permanent collection. Paid exhibitions available. Guided tours and audio guides.",
                    "admission_fee": "Free (permanent collection)",
                    "website_url": "https://www.tate.org.uk/visit/tate-modern",
                    "instagram_url": "@tate",
                    "facebook_url": "https://www.facebook.com/tate",
                    "twitter_url": "@Tate",
                    "youtube_url": "https://www.youtube.com/c/tate",
                    "tiktok_url": ""
                }
            ]
        },
        "Princeton": {
            "country": "United States",
            "venues": [
                {
                    "name": "Princeton University Art Museum",
                    "venue_type": "Museum",
                    "address": "McCormick Hall, Princeton, NJ 08544",
                    "opening_hours": "10:00 AM - 5:00 PM (Tue-Sat), 12:00 PM - 5:00 PM (Sun)",
                    "phone_number": "(609) 258-3788",
                    "email": "artmuseum@princeton.edu",
                    "description": "One of the finest university art museums in the country, with over 100,000 works spanning 5,000 years of world culture.",
                    "tour_info": "Free admission. Guided tours available. Audio guides and mobile app. Special exhibitions and events.",
                    "admission_fee": "Free",
                    "website_url": "https://artmuseum.princeton.edu",
                    "instagram_url": "@princetonartmuseum",
                    "facebook_url": "https://www.facebook.com/princetonartmuseum",
                    "twitter_url": "@PrincetonArtMuse",
                    "youtube_url": "https://www.youtube.com/c/princetonartmuseum",
                    "tiktok_url": ""
                },
                {
                    "name": "Morven Museum & Garden",
                    "venue_type": "Historic Site",
                    "address": "55 Stockton St, Princeton, NJ 08540",
                    "opening_hours": "10:00 AM - 4:00 PM (Wed-Sun)",
                    "phone_number": "(609) 924-8144",
                    "email": "info@morven.org",
                    "description": "Historic house museum and garden featuring colonial and Federal period artifacts, beautiful gardens, and educational programs.",
                    "tour_info": "Admission: $10 adults, $8 seniors, $6 students. Guided tours available. Garden tours and special events.",
                    "admission_fee": "$10",
                    "website_url": "https://morven.org",
                    "instagram_url": "@morvenmuseum",
                    "facebook_url": "https://www.facebook.com/MorvenMuseum",
                    "twitter_url": "@MorvenMuseum",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Princeton Battlefield State Park",
                    "venue_type": "Historic Site",
                    "address": "500 Mercer Rd, Princeton, NJ 08540",
                    "opening_hours": "8:00 AM - 4:30 PM (Daily)",
                    "phone_number": "(609) 921-0074",
                    "email": "princetonbattlefield@dep.nj.gov",
                    "description": "Site of the 1777 Battle of Princeton during the American Revolution, featuring historic markers and walking trails.",
                    "tour_info": "Free admission. Self-guided tours available. Historic markers and interpretive signs. Walking trails and picnic areas.",
                    "admission_fee": "Free",
                    "website_url": "https://www.nj.gov/dep/parksandforests/parks/princeton.html",
                    "instagram_url": "",
                    "facebook_url": "https://www.facebook.com/PrincetonBattlefield",
                    "twitter_url": "",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Nassau Hall",
                    "venue_type": "Historic Site",
                    "address": "Princeton University, Princeton, NJ 08544",
                    "opening_hours": "9:00 AM - 5:00 PM (Mon-Fri)",
                    "phone_number": "(609) 258-3000",
                    "email": "visitor@princeton.edu",
                    "description": "Historic building built in 1756, served as the temporary U.S. Capitol and is now the administrative center of Princeton University.",
                    "tour_info": "Free admission. Guided campus tours available. Historic markers and plaques. Part of Princeton University campus tours.",
                    "admission_fee": "Free",
                    "website_url": "https://www.princeton.edu/visit",
                    "instagram_url": "@princeton",
                    "facebook_url": "https://www.facebook.com/Princeton",
                    "twitter_url": "@Princeton",
                    "youtube_url": "https://www.youtube.com/c/princeton",
                    "tiktok_url": ""
                },
                {
                    "name": "Princeton University Chapel",
                    "venue_type": "Historic Site",
                    "address": "Princeton University, Princeton, NJ 08544",
                    "opening_hours": "8:00 AM - 10:00 PM (Daily)",
                    "phone_number": "(609) 258-3047",
                    "email": "chapel@princeton.edu",
                    "description": "Magnificent Gothic Revival chapel completed in 1928, featuring stunning architecture and beautiful stained glass windows.",
                    "tour_info": "Free admission. Self-guided tours available. Guided tours by appointment. Regular worship services and concerts.",
                    "admission_fee": "Free",
                    "website_url": "https://chapel.princeton.edu",
                    "instagram_url": "@princetonchapel",
                    "facebook_url": "https://www.facebook.com/PrincetonChapel",
                    "twitter_url": "",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Palmer Square",
                    "venue_type": "Shopping District",
                    "address": "Palmer Square, Princeton, NJ 08542",
                    "opening_hours": "10:00 AM - 9:00 PM (Mon-Sat), 12:00 PM - 6:00 PM (Sun)",
                    "phone_number": "(609) 924-7450",
                    "email": "info@palmersquare.com",
                    "description": "Charming shopping and dining district in the heart of Princeton, featuring boutique stores, restaurants, and cafes.",
                    "tour_info": "Free to walk around. Various shops and restaurants with individual hours. Special events and festivals throughout the year.",
                    "admission_fee": "Free",
                    "website_url": "https://www.palmersquare.com",
                    "instagram_url": "@palmersquare",
                    "facebook_url": "https://www.facebook.com/PalmerSquarePrinceton",
                    "twitter_url": "@PalmerSquare",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Princeton Public Library",
                    "venue_type": "Cultural Center",
                    "address": "65 Witherspoon St, Princeton, NJ 08542",
                    "opening_hours": "9:00 AM - 9:00 PM (Mon-Thu), 9:00 AM - 6:00 PM (Fri), 9:00 AM - 5:00 PM (Sat), 1:00 PM - 5:00 PM (Sun)",
                    "phone_number": "(609) 924-9529",
                    "email": "info@princetonlibrary.org",
                    "description": "Modern public library offering extensive collections, digital resources, and cultural programming in the heart of Princeton.",
                    "tour_info": "Free admission. Library cards available for residents and visitors. Computer access, meeting rooms, and study spaces.",
                    "admission_fee": "Free",
                    "website_url": "https://www.princetonlibrary.org",
                    "instagram_url": "@princetonlibrary",
                    "facebook_url": "https://www.facebook.com/PrincetonPublicLibrary",
                    "twitter_url": "@PrincetonLibrary",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Princeton Cemetery",
                    "venue_type": "Historic Site",
                    "address": "29 Greenview Ave, Princeton, NJ 08542",
                    "opening_hours": "7:00 AM - 7:00 PM (Daily)",
                    "phone_number": "(609) 924-1369",
                    "email": "info@princetoncemetery.org",
                    "description": "Historic cemetery established in 1757, final resting place of many notable figures including Aaron Burr and Grover Cleveland.",
                    "tour_info": "Free admission. Self-guided tours with map available. Guided tours by appointment. Historic markers and notable gravesites.",
                    "admission_fee": "Free",
                    "website_url": "https://www.princetoncemetery.org",
                    "instagram_url": "",
                    "facebook_url": "",
                    "twitter_url": "",
                    "youtube_url": "",
                    "tiktok_url": ""
                },
                {
                    "name": "Princeton University Store",
                    "venue_type": "Shopping",
                    "address": "36 University Pl, Princeton, NJ 08540",
                    "opening_hours": "9:00 AM - 7:00 PM (Mon-Fri), 10:00 AM - 6:00 PM (Sat), 11:00 AM - 5:00 PM (Sun)",
                    "phone_number": "(609) 921-8500",
                    "email": "customer.service@princeton.edu",
                    "description": "University bookstore offering Princeton merchandise, textbooks, clothing, and gifts in a historic building.",
                    "tour_info": "Free admission. Wide selection of Princeton branded items. Textbooks and academic supplies. Gift items and souvenirs.",
                    "admission_fee": "Free",
                    "website_url": "https://store.princeton.edu",
                    "instagram_url": "@princetonstore",
                    "facebook_url": "https://www.facebook.com/PrincetonUniversityStore",
                    "twitter_url": "",
                    "youtube_url": "",
                    "tiktok_url": ""
                }
            ]
        }
    }
    
    # Normalize city name for lookup
    city_key = city_name.title()
    
    if city_key in venues_knowledge:
        city_data = venues_knowledge[city_key]
        if city_data["country"].lower() == country.lower():
            return city_data["venues"]
    
    return []

def add_venues_for_city(city_name, country=None, state=None):
    """Add venues for a city using knowledge and Google Maps images"""
    
    print(f"🏛️ Adding venues for {city_name}...")
    print("=" * 60)
    
    with app.app_context():
        try:
            # Find the city in database
            if state:
                city = City.query.filter_by(name=city_name, country=country, state=state).first()
            else:
                city = City.query.filter_by(name=city_name, country=country).first()
            
            if not city:
                print(f"❌ City '{city_name}' not found in database")
                return False
            
            print(f"✅ Found city: {city.name}, {city.state}, {city.country}")
            
            # Get venues using knowledge
            venues_data = get_venues_for_city_knowledge(city_name, city.country)
            
            if not venues_data:
                print(f"❌ No venues found in knowledge base for {city_name}")
                return False
            
            print(f"📊 Found {len(venues_data)} venues in knowledge base")
            
            added_count = 0
            updated_count = 0
            
            for venue_data in venues_data:
                venue_name = venue_data['name']
                print(f"\n🔍 Processing venue: {venue_name}")
                
                # Check if venue already exists
                existing_venue = Venue.query.filter_by(name=venue_name, city_id=city.id).first()
                
                if existing_venue:
                    print(f"  ⚠️ Venue already exists, updating...")
                    # Update existing venue
                    for field, value in venue_data.items():
                        if hasattr(existing_venue, field) and field != 'name':
                            setattr(existing_venue, field, value)
                    
                    existing_venue.updated_at = datetime.utcnow()
                    updated_count += 1
                    venue = existing_venue
                else:
                    print(f"  ✅ Creating new venue...")
                    # Create new venue
                    venue = Venue(
                        name=venue_name,
                        venue_type=venue_data.get('venue_type', 'museum'),
                        description=venue_data.get('description', ''),
                        address=venue_data.get('address', ''),
                        opening_hours=venue_data.get('opening_hours', ''),
                        phone_number=venue_data.get('phone_number', ''),
                        email=venue_data.get('email', ''),
                        tour_info=venue_data.get('tour_info', ''),
                        admission_fee=venue_data.get('admission_fee', ''),
                        website_url=venue_data.get('website_url', ''),
                        latitude=None,  # Will be filled by geocoding if needed
                        longitude=None,
                        instagram_url=venue_data.get('instagram_url', ''),
                        facebook_url=venue_data.get('facebook_url', ''),
                        twitter_url=venue_data.get('twitter_url', ''),
                        youtube_url=venue_data.get('youtube_url', ''),
                        tiktok_url=venue_data.get('tiktok_url', ''),
                        holiday_hours='',
                        additional_info='',
                        city_id=city.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.session.add(venue)
                    added_count += 1
                
                # Get Google Maps image
                print(f"  📸 Fetching Google Maps image...")
                image_url = get_google_maps_image(
                    venue_name=venue_name,
                    city=city_name,
                    country=city.country,
                    state=city.state
                )
                
                if image_url:
                    venue.image_url = image_url
                    print(f"    ✅ Image URL updated")
                else:
                    print(f"    ⚠️ Could not fetch image URL")
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n💾 Committing changes to database...")
            print(f"✅ Successfully processed {len(venues_data)} venues")
            print(f"   Added: {added_count} new venues")
            print(f"   Updated: {updated_count} existing venues")
            
            # Update venues.json
            print(f"\n📄 Updating venues.json...")
            try:
                from scripts.update_venues_json import update_venues_json
                update_venues_json()
            except Exception as json_error:
                print(f"⚠️ Warning: Could not update venues.json: {json_error}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding venues: {e}")
            return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python add_venues_for_city.py <city_name> [country] [state]")
        print("Examples:")
        print("  python add_venues_for_city.py Washington")
        print("  python add_venues_for_city.py London United_Kingdom")
        print("  python add_venues_for_city.py New_York United_States New_York")
        return
    
    city_name = sys.argv[1].replace('_', ' ')
    country = sys.argv[2].replace('_', ' ') if len(sys.argv) > 2 else None
    state = sys.argv[3].replace('_', ' ') if len(sys.argv) > 3 else None
    
    success = add_venues_for_city(city_name, country, state)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
