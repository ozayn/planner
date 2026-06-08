#!/usr/bin/env python3
"""
Add major embassies in Washington DC to the venues database
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue, City

# Major embassies in Washington DC with their locations and details
DC_EMBASSIES = [
    {
        'name': 'Embassy of the United Kingdom',
        'address': '3100 Massachusetts Ave NW, Washington, DC 20008',
        'latitude': 38.9207,
        'longitude': -77.0564,
        'description': 'The British Embassy in Washington, housed in a stunning Sir Edwin Lutyens-designed building. Offers cultural events, exhibitions, and diplomatic tours.',
        'venue_type': 'embassy',
        'phone_number': '(202) 588-6500',
        'website': 'https://www.gov.uk/world/organisations/british-embassy-washington'
    },
    {
        'name': 'Embassy of France',
        'address': '4101 Reservoir Rd NW, Washington, DC 20007',
        'latitude': 38.9167,
        'longitude': -77.0711,
        'description': 'The French Embassy featuring beautiful architecture and hosting cultural events, art exhibitions, and French cultural programming.',
        'venue_type': 'embassy',
        'phone_number': '(202) 944-6000',
        'website': 'https://us.ambafrance.org'
    },
    {
        'name': 'Embassy of Germany',
        'address': '4645 Reservoir Rd NW, Washington, DC 20007',
        'latitude': 38.9156,
        'longitude': -77.0789,
        'description': 'Modern German Embassy hosting cultural events, exhibitions, and programs promoting German-American relations.',
        'venue_type': 'embassy',
        'phone_number': '(202) 298-4000',
        'website': 'https://washington.diplo.de'
    },
    {
        'name': 'Embassy of Italy',
        'address': '3000 Whitehaven St NW, Washington, DC 20008',
        'latitude': 38.9189,
        'longitude': -77.0533,
        'description': 'Italian Embassy known for its cultural programming, art exhibitions, and promotion of Italian culture and heritage.',
        'venue_type': 'embassy',
        'phone_number': '(202) 612-4400',
        'website': 'https://ambwashingtondc.esteri.it'
    },
    {
        'name': 'Embassy of Japan',
        'address': '2520 Massachusetts Ave NW, Washington, DC 20008',
        'latitude': 38.9108,
        'longitude': -77.0478,
        'description': 'Japanese Embassy hosting cultural events, traditional ceremonies, and exhibitions showcasing Japanese art and culture.',
        'venue_type': 'embassy',
        'phone_number': '(202) 238-6700',
        'website': 'https://www.us.emb-japan.go.jp'
    },
    {
        'name': 'Embassy of Canada',
        'address': '501 Pennsylvania Ave NW, Washington, DC 20001',
        'latitude': 38.8938,
        'longitude': -77.0186,
        'description': 'Canadian Embassy located near the Capitol, hosting cultural events and promoting Canadian-American relations.',
        'venue_type': 'embassy',
        'phone_number': '(202) 682-1740',
        'website': 'https://www.canadainternational.gc.ca/washington'
    },
    {
        'name': 'Embassy of Spain',
        'address': '2375 Pennsylvania Ave NW, Washington, DC 20037',
        'latitude': 38.9025,
        'longitude': -77.0522,
        'description': 'Spanish Embassy featuring cultural programming, flamenco performances, and Spanish art exhibitions.',
        'venue_type': 'embassy',
        'phone_number': '(202) 452-0100',
        'website': 'http://www.exteriores.gob.us/embajadas/washington'
    },
    {
        'name': 'Embassy of the Netherlands',
        'address': '4200 Linnean Ave NW, Washington, DC 20008',
        'latitude': 38.9289,
        'longitude': -77.0711,
        'description': 'Dutch Embassy known for innovative cultural programs and exhibitions highlighting Dutch art, design, and culture.',
        'venue_type': 'embassy',
        'phone_number': '(202) 244-5300',
        'website': 'https://www.netherlandsworldwide.nl/countries/united-states'
    },
    {
        'name': 'Embassy of Australia',
        'address': '1601 Massachusetts Ave NW, Washington, DC 20036',
        'latitude': 38.9089,
        'longitude': -77.0378,
        'description': 'Australian Embassy hosting cultural events, art exhibitions, and programs promoting Australian culture and tourism.',
        'venue_type': 'embassy',
        'phone_number': '(202) 797-3000',
        'website': 'https://usa.embassy.gov.au'
    },
    {
        'name': 'Embassy of Brazil',
        'address': '3006 Massachusetts Ave NW, Washington, DC 20008',
        'latitude': 38.9192,
        'longitude': -77.0539,
        'description': 'Brazilian Embassy featuring vibrant cultural programming including music, dance, art exhibitions, and Brazilian cultural celebrations.',
        'venue_type': 'embassy',
        'phone_number': '(202) 238-2700',
        'website': 'http://washington.itamaraty.gov.br'
    },
    {
        'name': 'Embassy of India',
        'address': '2107 Massachusetts Ave NW, Washington, DC 20008',
        'latitude': 38.9094,
        'longitude': -77.0434,
        'description': 'Indian Embassy hosting cultural festivals, classical music performances, art exhibitions, and celebrations of Indian heritage.',
        'venue_type': 'embassy',
        'phone_number': '(202) 939-7000',
        'website': 'https://www.indianembassyusa.gov.in'
    },
    {
        'name': 'Embassy of Mexico',
        'address': '1911 Pennsylvania Ave NW, Washington, DC 20006',
        'latitude': 38.9015,
        'longitude': -77.0432,
        'description': 'Mexican Embassy featuring Mexican cultural programming, art exhibitions, and celebrations of Mexican traditions and heritage.',
        'venue_type': 'embassy',
        'phone_number': '(202) 728-1600',
        'website': 'https://embamex.sre.gob.mx/eua'
    },
    {
        'name': 'Embassy of South Korea',
        'address': '2450 Massachusetts Ave NW, Washington, DC 20008',
        'latitude': 38.9101,
        'longitude': -77.0469,
        'description': 'Korean Embassy hosting K-culture events, traditional performances, art exhibitions, and Korean cultural programming.',
        'venue_type': 'embassy',
        'phone_number': '(202) 939-5600',
        'website': 'http://overseas.mofa.go.kr/us-washington-en'
    },
    {
        'name': 'Embassy of Sweden',
        'address': '2900 K St NW, Washington, DC 20007',
        'latitude': 38.9017,
        'longitude': -77.0597,
        'description': 'Swedish Embassy known for design exhibitions, sustainability programs, and Nordic cultural events.',
        'venue_type': 'embassy',
        'phone_number': '(202) 467-2600',
        'website': 'https://www.swedenabroad.se/washington'
    },
    {
        'name': 'Embassy of Switzerland',
        'address': '2900 Cathedral Ave NW, Washington, DC 20008',
        'latitude': 38.9289,
        'longitude': -77.0622,
        'description': 'Swiss Embassy hosting cultural events, exhibitions, and programs showcasing Swiss innovation, culture, and traditions.',
        'venue_type': 'embassy',
        'phone_number': '(202) 745-7900',
        'website': 'https://www.eda.admin.ch/washington'
    }
]

def add_dc_embassies():
    """Add DC embassies to the venues database"""
    print("🏛️ Adding DC embassies to venues database...")
    
    with app.app_context():
        try:
            # Get Washington DC city
            dc_city = City.query.filter_by(name='Washington', country='United States').first()
            if not dc_city:
                print("❌ Washington DC city not found in database")
                return False
            
            print(f"✅ Found Washington DC (ID: {dc_city.id})")
            
            added_count = 0
            skipped_count = 0
            
            for embassy_data in DC_EMBASSIES:
                # Check if embassy already exists
                existing_embassy = Venue.query.filter_by(
                    name=embassy_data['name'],
                    city_id=dc_city.id
                ).first()
                
                if existing_embassy:
                    print(f"⚠️  Skipped '{embassy_data['name']}' - already exists")
                    skipped_count += 1
                    continue
                
                # Create new embassy venue
                embassy = Venue(
                    name=embassy_data['name'],
                    address=embassy_data['address'],
                    city_id=dc_city.id,
                    latitude=embassy_data['latitude'],
                    longitude=embassy_data['longitude'],
                    description=embassy_data['description'],
                    venue_type=embassy_data['venue_type'],
                    phone_number=embassy_data['phone_number'],
                    website_url=embassy_data['website'],
                    opening_hours='By appointment - Contact embassy for cultural events and tours',
                    admission_fee='Free for cultural events (varies by event)'
                )
                
                db.session.add(embassy)
                added_count += 1
                print(f"✅ Added '{embassy_data['name']}'")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Embassy addition complete!")
            print(f"📊 Added {added_count} new embassies")
            print(f"⚠️  Skipped {skipped_count} existing embassies")
            
            # Show final count
            total_venues = Venue.query.filter_by(city_id=dc_city.id).count()
            embassy_venues = Venue.query.filter_by(city_id=dc_city.id, venue_type='embassy').count()
            print(f"📈 Washington DC now has {total_venues} total venues ({embassy_venues} embassies)")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding embassies: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = add_dc_embassies()
    sys.exit(0 if success else 1)
