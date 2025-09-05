import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, db, City, Venue, Tour, Exhibition, Festival, Photowalk
from datetime import datetime, date, time, timedelta
import pytz

def seed_cities():
    """Seed major cities with their timezones"""
    cities_data = [
        {'name': 'Washington', 'state': 'DC', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'New York', 'state': 'NY', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'Baltimore', 'state': 'MD', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'Philadelphia', 'state': 'PA', 'country': 'United States', 'timezone': 'America/New_York'},
        {'name': 'London', 'state': None, 'country': 'United Kingdom', 'timezone': 'Europe/London'},
        {'name': 'Los Angeles', 'state': 'CA', 'country': 'United States', 'timezone': 'America/Los_Angeles'},
        {'name': 'Paris', 'state': None, 'country': 'France', 'timezone': 'Europe/Paris'},
        {'name': 'Tokyo', 'state': None, 'country': 'Japan', 'timezone': 'Asia/Tokyo'},
        {'name': 'Sydney', 'state': None, 'country': 'Australia', 'timezone': 'Australia/Sydney'},
    ]
    
    for city_data in cities_data:
        city = City.query.filter_by(name=city_data['name']).first()
        if not city:
            city = City(**city_data)
            db.session.add(city)
    
    db.session.commit()
    print("Cities seeded successfully")

def seed_washington_dc_venues():
    """Seed Washington DC venues"""
    dc = City.query.filter_by(name='Washington').first()
    if not dc:
        print("Washington DC not found")
        return
    
    venues_data = [
        {
            'name': 'Smithsonian National Museum of Natural History',
            'venue_type': 'museum',
            'address': '10th St. & Constitution Ave. NW, Washington, DC 20560',
            'latitude': 38.8913,
            'longitude': -77.0263,
            'website_url': 'https://naturalhistory.si.edu',
            'description': 'The world\'s most visited natural history museum',
            'city_id': dc.id
        },
        {
            'name': 'National Gallery of Art',
            'venue_type': 'museum',
            'address': '6th St. & Constitution Ave. NW, Washington, DC 20565',
            'latitude': 38.8914,
            'longitude': -77.0199,
            'website_url': 'https://www.nga.gov',
            'description': 'One of the world\'s premier art museums',
            'city_id': dc.id
        },
        {
            'name': 'Smithsonian National Air and Space Museum',
            'venue_type': 'museum',
            'address': '600 Independence Ave. SW, Washington, DC 20560',
            'latitude': 38.8882,
            'longitude': -77.0199,
            'website_url': 'https://airandspace.si.edu',
            'description': 'The world\'s largest collection of historic aircraft and spacecraft',
            'city_id': dc.id
        }
    ]
    
    for venue_data in venues_data:
        venue = Venue.query.filter_by(name=venue_data['name']).first()
        if not venue:
            venue = Venue(**venue_data)
            db.session.add(venue)
    
    db.session.commit()
    print("Washington DC venues seeded successfully")

def seed_sample_tours():
    """Seed sample tours"""
    dc = City.query.filter_by(name='Washington').first()
    natural_history = Venue.query.filter_by(name='Smithsonian National Museum of Natural History').first()
    national_gallery = Venue.query.filter_by(name='National Gallery of Art').first()
    
    if not dc or not natural_history or not national_gallery:
        print("Required venues not found")
        return
    
    tours_data = [
        {
            'title': 'Dinosaur Discovery Tour',
            'description': 'Explore the world of dinosaurs with our expert guides. See fossils up close and learn about prehistoric life.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(10, 0),
            'end_time': time(11, 0),
            'meeting_location': 'Main entrance, Constitution Avenue',
            'tour_type': 'specialized',
            'language': 'English',
            'venue_id': natural_history.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://naturalhistory.si.edu/visit/tours'
        },
        {
            'title': 'Ocean Life Exploration',
            'description': 'Dive deep into the mysteries of ocean life. Discover marine ecosystems and conservation efforts.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(14, 0),
            'end_time': time(15, 30),
            'meeting_location': 'Ocean Hall entrance',
            'tour_type': 'specialized',
            'language': 'English',
            'venue_id': natural_history.id,
            'image_url': 'https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=400',
            'url': 'https://naturalhistory.si.edu/visit/tours'
        },
        {
            'title': 'Renaissance Masterpieces Tour',
            'description': 'Discover the beauty of Renaissance art with our knowledgeable docents. See works by Leonardo, Raphael, and more.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(12, 0),
            'end_time': time(13, 0),
            'meeting_location': 'West Building Rotunda',
            'tour_type': 'docent',
            'language': 'English',
            'venue_id': national_gallery.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.nga.gov/visit/tours.html'
        },
        {
            'title': 'Impressionist Collection Walk',
            'description': 'Explore the stunning Impressionist collection featuring Monet, Degas, and Renoir.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(15, 0),
            'end_time': time(16, 0),
            'meeting_location': 'East Building entrance',
            'tour_type': 'general',
            'language': 'English',
            'venue_id': national_gallery.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.nga.gov/visit/tours.html'
        }
    ]
    
    for tour_data in tours_data:
        tour = Tour(**tour_data)
        db.session.add(tour)
    
    db.session.commit()
    print("Sample tours seeded successfully")

def seed_sample_exhibitions():
    """Seed sample exhibitions"""
    natural_history = Venue.query.filter_by(name='Smithsonian National Museum of Natural History').first()
    national_gallery = Venue.query.filter_by(name='National Gallery of Art').first()
    
    if not natural_history or not national_gallery:
        print("Required venues not found")
        return
    
    exhibitions_data = [
        {
            'title': 'Fossils and Evolution',
            'description': 'A comprehensive look at the fossil record and the evolution of life on Earth.',
            'start_date': date.today() - timedelta(days=30),
            'end_date': date.today() + timedelta(days=60),
            'exhibition_location': 'Hall of Fossils, 2nd Floor',
            'venue_id': natural_history.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://naturalhistory.si.edu/exhibitions'
        },
        {
            'title': 'Modern Art Movements',
            'description': 'Explore the revolutionary art movements of the 20th century.',
            'start_date': date.today() - timedelta(days=15),
            'end_date': date.today() + timedelta(days=45),
            'exhibition_location': 'East Building, Level 2',
            'venue_id': national_gallery.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.nga.gov/exhibitions'
        }
    ]
    
    for exhibition_data in exhibitions_data:
        exhibition = Exhibition(**exhibition_data)
        db.session.add(exhibition)
    
    db.session.commit()
    print("Sample exhibitions seeded successfully")

def seed_london_venues():
    """Seed London venues"""
    london = City.query.filter_by(name='London').first()
    if not london:
        print("London not found")
        return
    
    venues_data = [
        {
            'name': 'British Museum',
            'venue_type': 'museum',
            'address': 'Great Russell St, London WC1B 3DG, UK',
            'latitude': 51.5194,
            'longitude': -0.1270,
            'website_url': 'https://www.britishmuseum.org',
            'description': 'World-famous museum of human history, art and culture',
            'city_id': london.id
        },
        {
            'name': 'Tate Modern',
            'venue_type': 'museum',
            'address': 'Bankside, London SE1 9TG, UK',
            'latitude': 51.5076,
            'longitude': -0.0994,
            'website_url': 'https://www.tate.org.uk/visit/tate-modern',
            'description': 'Modern and contemporary art museum',
            'city_id': london.id
        },
        {
            'name': 'Natural History Museum',
            'venue_type': 'museum',
            'address': 'Cromwell Rd, South Kensington, London SW7 5BD, UK',
            'latitude': 51.4966,
            'longitude': -0.1764,
            'website_url': 'https://www.nhm.ac.uk',
            'description': 'World-class natural history museum',
            'city_id': london.id
        }
    ]
    
    for venue_data in venues_data:
        venue = Venue.query.filter_by(name=venue_data['name'], city_id=london.id).first()
        if not venue:
            venue = Venue(**venue_data)
            db.session.add(venue)
    
    db.session.commit()
    print("London venues seeded successfully")

def seed_london_tours():
    """Seed London tours"""
    london = City.query.filter_by(name='London').first()
    british_museum = Venue.query.filter_by(name='British Museum', city_id=london.id).first()
    tate_modern = Venue.query.filter_by(name='Tate Modern', city_id=london.id).first()
    
    if not london or not british_museum or not tate_modern:
        print("Required London venues not found")
        return
    
    tours_data = [
        {
            'title': 'Ancient Egypt Highlights Tour',
            'description': 'Discover the treasures of ancient Egypt including the Rosetta Stone and mummies.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(11, 0),
            'end_time': time(12, 0),
            'meeting_location': 'Great Court, main entrance',
            'tour_type': 'specialized',
            'language': 'English',
            'venue_id': british_museum.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.britishmuseum.org/visit/tours'
        },
        {
            'title': 'Modern Art Masterpieces',
            'description': 'Explore contemporary art from around the world in this guided tour.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(14, 30),
            'end_time': time(15, 30),
            'meeting_location': 'Turbine Hall entrance',
            'tour_type': 'docent',
            'language': 'English',
            'venue_id': tate_modern.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.tate.org.uk/visit/tate-modern/tours'
        },
        {
            'title': 'Dinosaur Discovery Walk',
            'description': 'Meet the dinosaurs and explore prehistoric life in this family-friendly tour.',
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'start_time': time(10, 30),
            'end_time': time(11, 30),
            'meeting_location': 'Hintze Hall, main entrance',
            'tour_type': 'family',
            'language': 'English',
            'venue_id': Venue.query.filter_by(name='Natural History Museum', city_id=london.id).first().id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.nhm.ac.uk/visit/tours'
        }
    ]
    
    for tour_data in tours_data:
        tour = Tour(**tour_data)
        db.session.add(tour)
    
    db.session.commit()
    print("London tours seeded successfully")

def seed_los_angeles_venues():
    """Seed Los Angeles venues"""
    la = City.query.filter_by(name='Los Angeles').first()
    if not la:
        print("Los Angeles not found")
        return
    
    venues_data = [
        {
            'name': 'Getty Center',
            'venue_type': 'museum',
            'address': '1200 Getty Center Dr, Los Angeles, CA 90049, USA',
            'latitude': 34.0780,
            'longitude': -118.4743,
            'website_url': 'https://www.getty.edu/visit/center/',
            'description': 'World-class art museum with stunning architecture',
            'city_id': la.id
        },
        {
            'name': 'Los Angeles County Museum of Art (LACMA)',
            'venue_type': 'museum',
            'address': '5905 Wilshire Blvd, Los Angeles, CA 90036, USA',
            'latitude': 34.0638,
            'longitude': -118.3594,
            'website_url': 'https://www.lacma.org',
            'description': 'The largest art museum in the western United States',
            'city_id': la.id
        },
        {
            'name': 'Griffith Observatory',
            'venue_type': 'observatory',
            'address': '2800 E Observatory Rd, Los Angeles, CA 90027, USA',
            'latitude': 34.1183,
            'longitude': -118.3003,
            'website_url': 'https://griffithobservatory.org',
            'description': 'Iconic observatory with stunning city views',
            'city_id': la.id
        }
    ]
    
    for venue_data in venues_data:
        venue = Venue.query.filter_by(name=venue_data['name'], city_id=la.id).first()
        if not venue:
            venue = Venue(**venue_data)
            db.session.add(venue)
    
    db.session.commit()
    print("Los Angeles venues seeded successfully")

def seed_los_angeles_tours():
    """Seed Los Angeles tours"""
    la = City.query.filter_by(name='Los Angeles').first()
    getty_center = Venue.query.filter_by(name='Getty Center', city_id=la.id).first()
    lacma = Venue.query.filter_by(name='Los Angeles County Museum of Art (LACMA)', city_id=la.id).first()
    
    if not la or not getty_center or not lacma:
        print("Required Los Angeles venues not found")
        return
    
    tours_data = [
        {
            'title': 'European Art Masterpieces Tour',
            'description': 'Explore the Getty\'s collection of European paintings, sculptures, and decorative arts.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(10, 30),
            'end_time': time(11, 30),
            'meeting_location': 'Main entrance, Getty Center',
            'tour_type': 'docent',
            'language': 'English',
            'venue_id': getty_center.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.getty.edu/visit/center/tours'
        },
        {
            'title': 'Modern Art Collection Walk',
            'description': 'Discover contemporary art from around the world at LACMA.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(14, 0),
            'end_time': time(15, 0),
            'meeting_location': 'BCAM entrance, LACMA',
            'tour_type': 'specialized',
            'language': 'English',
            'venue_id': lacma.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://www.lacma.org/visit/tours'
        },
        {
            'title': 'Sunset Photography Session',
            'description': 'Capture the iconic LA skyline during golden hour at Griffith Observatory.',
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'start_time': time(18, 0),
            'end_time': time(19, 30),
            'meeting_location': 'Observatory entrance',
            'tour_type': 'photography',
            'language': 'English',
            'venue_id': Venue.query.filter_by(name='Griffith Observatory', city_id=la.id).first().id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://griffithobservatory.org/visit/tours'
        }
    ]
    
    for tour_data in tours_data:
        tour = Tour(**tour_data)
        db.session.add(tour)
    
    db.session.commit()
    print("Los Angeles tours seeded successfully")

def seed_sample_photowalks():
    """Seed sample photowalks"""
    dc = City.query.filter_by(name='Washington').first()
    
    if not dc:
        print("Washington DC not found")
        return
    
    photowalks_data = [
        {
            'title': 'Monument Photography Walk',
            'description': 'Capture the beauty of DC\'s iconic monuments during golden hour.',
            'start_date': date.today(),
            'end_date': date.today(),
            'start_time': time(17, 0),
            'end_time': time(19, 0),
            'start_location': 'Lincoln Memorial',
            'end_location': 'Washington Monument',
            'start_latitude': 38.8893,
            'start_longitude': -77.0502,
            'end_latitude': 38.8895,
            'end_longitude': -77.0353,
            'difficulty_level': 'beginner',
            'equipment_needed': 'Camera or smartphone',
            'organizer': 'DC Photography Club',
            'city_id': dc.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://dcphotoclub.com'
        },
        {
            'title': 'Cherry Blossom Photo Session',
            'description': 'Join us for a special photography session during cherry blossom season.',
            'start_date': date.today() + timedelta(days=1),
            'end_date': date.today() + timedelta(days=1),
            'start_time': time(8, 0),
            'end_time': time(10, 0),
            'start_location': 'Tidal Basin',
            'end_location': 'Jefferson Memorial',
            'start_latitude': 38.8842,
            'start_longitude': -77.0375,
            'end_latitude': 38.8814,
            'end_longitude': -77.0365,
            'difficulty_level': 'intermediate',
            'equipment_needed': 'DSLR or mirrorless camera recommended',
            'organizer': 'National Park Service',
            'city_id': dc.id,
            'image_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400',
            'url': 'https://nps.gov'
        }
    ]
    
    for photowalk_data in photowalks_data:
        photowalk = Photowalk(**photowalk_data)
        db.session.add(photowalk)
    
    db.session.commit()
    print("Sample photowalks seeded successfully")

def seed_all_data():
    """Seed all sample data"""
    with app.app_context():
        seed_cities()
        seed_washington_dc_venues()
        seed_london_venues()
        seed_los_angeles_venues()
        seed_sample_tours()
        seed_london_tours()
        seed_los_angeles_tours()
        seed_sample_exhibitions()
        seed_sample_photowalks()
        print("All data seeded successfully!")

if __name__ == '__main__':
    seed_all_data()
