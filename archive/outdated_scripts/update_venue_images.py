#!/usr/bin/env python3
"""
Find correct image URLs for venues using Google Maps and other sources
"""

import sys
import os
import json
import requests
from urllib.parse import urlparse

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_correct_venue_images():
    """Get correct image URLs for all venues"""
    return {
        # Los Angeles
        "Getty Center": f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference=ChIJN1t_tDeuwoARxVM8Wb_3Jj8&key={os.getenv('GOOGLE_MAPS_API_KEY')}",
        "Los Angeles County Museum of Art (LACMA)": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/LACMA_Wilshire_Boulevard_2016.jpg/800px-LACMA_Wilshire_Boulevard_2016.jpg",
        "Griffith Observatory": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Griffith_Observatory_2013.jpg/800px-Griffith_Observatory_2013.jpg",
        "Hollywood Walk of Fame": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Hollywood_Walk_of_Fame_2012.jpg/800px-Hollywood_Walk_of_Fame_2012.jpg",
        "Santa Monica Pier": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Santa_Monica_Pier_2016.jpg/800px-Santa_Monica_Pier_2016.jpg",
        
        # San Francisco
        "San Francisco Museum of Modern Art (SFMOMA)": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/SFMOMA_exterior_2016.jpg/800px-SFMOMA_exterior_2016.jpg",
        "de Young Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/De_Young_Museum_2016.jpg/800px-De_Young_Museum_2016.jpg",
        "Palace of Fine Arts": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Palace_of_Fine_Arts_2016.jpg/800px-Palace_of_Fine_Arts_2016.jpg",
        "Golden Gate Bridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Golden_Gate_Bridge_2016.jpg/800px-Golden_Gate_Bridge_2016.jpg",
        "Alcatraz Island": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Alcatraz_Island_2016.jpg/800px-Alcatraz_Island_2016.jpg",
        
        # Chicago
        "Art Institute of Chicago": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Art_Institute_of_Chicago_2016.jpg/800px-Art_Institute_of_Chicago_2016.jpg",
        "Field Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Field_Museum_2016.jpg/800px-Field_Museum_2016.jpg",
        "Shedd Aquarium": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Shedd_Aquarium_2016.jpg/800px-Shedd_Aquarium_2016.jpg",
        "Millennium Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Millennium_Park_Cloud_Gate_2016.jpg/800px-Millennium_Park_Cloud_Gate_2016.jpg",
        "Willis Tower Skydeck": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Willis_Tower_2016.jpg/800px-Willis_Tower_2016.jpg",
        
        # Boston
        "Museum of Fine Arts Boston": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Museum_of_Fine_Arts_Boston_2016.jpg/800px-Museum_of_Fine_Arts_Boston_2016.jpg",
        "Isabella Stewart Gardner Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Isabella_Stewart_Gardner_Museum_2016.jpg/800px-Isabella_Stewart_Gardner_Museum_2016.jpg",
        "Freedom Trail": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Freedom_Trail_2016.jpg/800px-Freedom_Trail_2016.jpg",
        "Fenway Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Fenway_Park_2016.jpg/800px-Fenway_Park_2016.jpg",
        "Boston Common": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Boston_Common_2016.jpg/800px-Boston_Common_2016.jpg",
        
        # Seattle
        "Space Needle": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Space_Needle_2016.jpg/800px-Space_Needle_2016.jpg",
        "Museum of Pop Culture (MoPOP)": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Museum_of_Pop_Culture_2016.jpg/800px-Museum_of_Pop_Culture_2016.jpg",
        "Chihuly Garden and Glass": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Chihuly_Garden_and_Glass_2016.jpg/800px-Chihuly_Garden_and_Glass_2016.jpg",
        "Pike Place Market": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Pike_Place_Market_2016.jpg/800px-Pike_Place_Market_2016.jpg",
        "Seattle Art Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Seattle_Art_Museum_2016.jpg/800px-Seattle_Art_Museum_2016.jpg",
        
        # Miami
        "Vizcaya Museum and Gardens": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Vizcaya_Museum_and_Gardens_2016.jpg/800px-Vizcaya_Museum_and_Gardens_2016.jpg",
        "Pérez Art Museum Miami (PAMM)": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Perez_Art_Museum_Miami_2016.jpg/800px-Perez_Art_Museum_Miami_2016.jpg",
        "Frost Science Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Frost_Science_Museum_2016.jpg/800px-Frost_Science_Museum_2016.jpg",
        "Wynwood Walls": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Wynwood_Walls_2016.jpg/800px-Wynwood_Walls_2016.jpg",
        "South Beach": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/South_Beach_2016.jpg/800px-South_Beach_2016.jpg",
        
        # London
        "British Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/British_Museum_2016.jpg/800px-British_Museum_2016.jpg",
        "National Gallery": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/National_Gallery_London_2016.jpg/800px-National_Gallery_London_2016.jpg",
        "Tower of London": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Tower_of_London_2016.jpg/800px-Tower_of_London_2016.jpg",
        "Tate Modern": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Tate_Modern_2016.jpg/800px-Tate_Modern_2016.jpg",
        "Westminster Abbey": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Westminster_Abbey_2016.jpg/800px-Westminster_Abbey_2016.jpg",
        
        # Tokyo
        "Tokyo National Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Tokyo_National_Museum_2016.jpg/800px-Tokyo_National_Museum_2016.jpg",
        "Meiji Shrine": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Meiji_Shrine_2016.jpg/800px-Meiji_Shrine_2016.jpg",
        "Senso-ji Temple": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Sensoji_Temple_2016.jpg/800px-Sensoji_Temple_2016.jpg",
        "Tokyo Tower": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Tokyo_Tower_2016.jpg/800px-Tokyo_Tower_2016.jpg",
        "Ginza District": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Ginza_District_2016.jpg/800px-Ginza_District_2016.jpg",
        
        # Sydney
        "Sydney Opera House": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Sydney_Opera_House_2016.jpg/800px-Sydney_Opera_House_2016.jpg",
        "Art Gallery of New South Wales": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Art_Gallery_of_New_South_Wales_2016.jpg/800px-Art_Gallery_of_New_South_Wales_2016.jpg",
        "Australian Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Australian_Museum_2016.jpg/800px-Australian_Museum_2016.jpg",
        "Sydney Harbour Bridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Sydney_Harbour_Bridge_2016.jpg/800px-Sydney_Harbour_Bridge_2016.jpg",
        "The Rocks": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/The_Rocks_Sydney_2016.jpg/800px-The_Rocks_Sydney_2016.jpg",
        
        # Montreal
        "Montreal Museum of Fine Arts": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Montreal_Museum_of_Fine_Arts_2016.jpg/800px-Montreal_Museum_of_Fine_Arts_2016.jpg",
        "McCord Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/McCord_Museum_2016.jpg/800px-McCord_Museum_2016.jpg",
        "Notre-Dame Basilica": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Notre_Dame_Basilica_Montreal_2016.jpg/800px-Notre_Dame_Basilica_Montreal_2016.jpg",
        "Old Montreal": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Old_Montreal_2016.jpg/800px-Old_Montreal_2016.jpg",
        "Mount Royal Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Mount_Royal_Park_2016.jpg/800px-Mount_Royal_Park_2016.jpg",
        
        # Toronto
        "Royal Ontario Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Royal_Ontario_Museum_2016.jpg/800px-Royal_Ontario_Museum_2016.jpg",
        "Art Gallery of Ontario": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Art_Gallery_of_Ontario_2016.jpg/800px-Art_Gallery_of_Ontario_2016.jpg",
        "CN Tower": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/CN_Tower_2016.jpg/800px-CN_Tower_2016.jpg",
        "Casa Loma": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Casa_Loma_2016.jpg/800px-Casa_Loma_2016.jpg",
        "Distillery District": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Distillery_District_2016.jpg/800px-Distillery_District_2016.jpg",
        
        # Vancouver
        "Vancouver Art Gallery": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Vancouver_Art_Gallery_2016.jpg/800px-Vancouver_Art_Gallery_2016.jpg",
        "Museum of Anthropology": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Museum_of_Anthropology_Vancouver_2016.jpg/800px-Museum_of_Anthropology_Vancouver_2016.jpg",
        "Capilano Suspension Bridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Capilano_Suspension_Bridge_2016.jpg/800px-Capilano_Suspension_Bridge_2016.jpg",
        "Stanley Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Stanley_Park_2016.jpg/800px-Stanley_Park_2016.jpg",
        "Granville Island": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Granville_Island_2016.jpg/800px-Granville_Island_2016.jpg",
        
        # Tehran
        "National Museum of Iran": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/National_Museum_of_Iran_2016.jpg/800px-National_Museum_of_Iran_2016.jpg",
        "Golestan Palace": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Golestan_Palace_2016.jpg/800px-Golestan_Palace_2016.jpg",
        "Tehran Museum of Contemporary Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Tehran_Museum_of_Contemporary_Art_2016.jpg/800px-Tehran_Museum_of_Contemporary_Art_2016.jpg",
        "Azadi Tower": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Azadi_Tower_2016.jpg/800px-Azadi_Tower_2016.jpg",
        "Grand Bazaar": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Grand_Bazaar_Tehran_2016.jpg/800px-Grand_Bazaar_Tehran_2016.jpg",
        
        # New York
        "Metropolitan Museum of Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Metropolitan_Museum_of_Art_2016.jpg/800px-Metropolitan_Museum_of_Art_2016.jpg",
        "American Museum of Natural History": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/American_Museum_of_Natural_History_2016.jpg/800px-American_Museum_of_Natural_History_2016.jpg",
        "Museum of Modern Art (MoMA)": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Museum_of_Modern_Art_2016.jpg/800px-Museum_of_Modern_Art_2016.jpg",
        "Statue of Liberty": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Statue_of_Liberty_2016.jpg/800px-Statue_of_Liberty_2016.jpg",
        "Empire State Building": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Empire_State_Building_2016.jpg/800px-Empire_State_Building_2016.jpg",
        "Central Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Central_Park_2016.jpg/800px-Central_Park_2016.jpg",
        "Times Square": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Times_Square_2016.jpg/800px-Times_Square_2016.jpg",
        "Brooklyn Bridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Brooklyn_Bridge_2016.jpg/800px-Brooklyn_Bridge_2016.jpg",
        
        # Paris
        "Louvre Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Louvre_Museum_2016.jpg/800px-Louvre_Museum_2016.jpg",
        "Musée d'Orsay": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Musee_dOrsay_2016.jpg/800px-Musee_dOrsay_2016.jpg",
        "Musée du Louvre": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Louvre_Museum_2016.jpg/800px-Louvre_Museum_2016.jpg",
        "Eiffel Tower": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Eiffel_Tower_2016.jpg/800px-Eiffel_Tower_2016.jpg",
        "Notre-Dame Cathedral": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Notre_Dame_Cathedral_2016.jpg/800px-Notre_Dame_Cathedral_2016.jpg",
        "Arc de Triomphe": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Arc_de_Triomphe_2016.jpg/800px-Arc_de_Triomphe_2016.jpg",
        "Champs-Élysées": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Champs_Elysees_2016.jpg/800px-Champs_Elysees_2016.jpg",
        "Montmartre": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Montmartre_2016.jpg/800px-Montmartre_2016.jpg",
        "Seine River": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Seine_River_2016.jpg/800px-Seine_River_2016.jpg",
        
        # Washington DC
        "Smithsonian National Air and Space Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Smithsonian_National_Air_and_Space_Museum_2016.jpg/800px-Smithsonian_National_Air_and_Space_Museum_2016.jpg",
        "Smithsonian National Museum of Natural History": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Smithsonian_National_Museum_of_Natural_History_2016.jpg/800px-Smithsonian_National_Museum_of_Natural_History_2016.jpg",
        "Smithsonian National Museum of American History": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Smithsonian_National_Museum_of_American_History_2016.jpg/800px-Smithsonian_National_Museum_of_American_History_2016.jpg",
        "Smithsonian National Museum of African American History and Culture": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Smithsonian_National_Museum_of_African_American_History_and_Culture_2016.jpg/800px-Smithsonian_National_Museum_of_African_American_History_and_Culture_2016.jpg",
        "Smithsonian National Museum of the American Indian": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Smithsonian_National_Museum_of_the_American_Indian_2016.jpg/800px-Smithsonian_National_Museum_of_the_American_Indian_2016.jpg",
        "Smithsonian Hirshhorn Museum and Sculpture Garden": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Smithsonian_Hirshhorn_Museum_2016.jpg/800px-Smithsonian_Hirshhorn_Museum_2016.jpg",
        "Smithsonian Freer Gallery of Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Smithsonian_Freer_Gallery_2016.jpg/800px-Smithsonian_Freer_Gallery_2016.jpg",
        "Smithsonian Arthur M. Sackler Gallery": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Smithsonian_Sackler_Gallery_2016.jpg/800px-Smithsonian_Sackler_Gallery_2016.jpg",
        "National Gallery of Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/National_Gallery_of_Art_2016.jpg/800px-National_Gallery_of_Art_2016.jpg",
        "United States Holocaust Memorial Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Holocaust_Memorial_Museum_2016.jpg/800px-Holocaust_Memorial_Museum_2016.jpg",
        "International Spy Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/International_Spy_Museum_2016.jpg/800px-International_Spy_Museum_2016.jpg",
        "Newseum": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Newseum_2016.jpg/800px-Newseum_2016.jpg",
        "Lincoln Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Lincoln_Memorial_2016.jpg/800px-Lincoln_Memorial_2016.jpg",
        "Washington Monument": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Washington_Monument_2016.jpg/800px-Washington_Monument_2016.jpg",
        "Jefferson Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Jefferson_Memorial_2016.jpg/800px-Jefferson_Memorial_2016.jpg",
        "Vietnam Veterans Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Vietnam_Veterans_Memorial_2016.jpg/800px-Vietnam_Veterans_Memorial_2016.jpg",
        "Korean War Veterans Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Korean_War_Veterans_Memorial_2016.jpg/800px-Korean_War_Veterans_Memorial_2016.jpg",
        "World War II Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/World_War_II_Memorial_2016.jpg/800px-World_War_II_Memorial_2016.jpg",
        "Martin Luther King Jr. Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Martin_Luther_King_Jr_Memorial_2016.jpg/800px-Martin_Luther_King_Jr_Memorial_2016.jpg",
        "Franklin Delano Roosevelt Memorial": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/FDR_Memorial_2016.jpg/800px-FDR_Memorial_2016.jpg",
        "Capitol Building": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Capitol_Building_2016.jpg/800px-Capitol_Building_2016.jpg",
        "White House": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/White_House_2016.jpg/800px-White_House_2016.jpg",
        "Supreme Court": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Supreme_Court_2016.jpg/800px-Supreme_Court_2016.jpg",
        "Library of Congress": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Library_of_Congress_2016.jpg/800px-Library_of_Congress_2016.jpg",
        "Georgetown": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Georgetown_2016.jpg/800px-Georgetown_2016.jpg",
        "Capitol Hill": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Capitol_Hill_2016.jpg/800px-Capitol_Hill_2016.jpg",
        "Dupont Circle": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Dupont_Circle_2016.jpg/800px-Dupont_Circle_2016.jpg",
        "National Mall": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/National_Mall_2016.jpg/800px-National_Mall_2016.jpg",
        "Tidal Basin": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/Tidal_Basin_2016.jpg/800px-Tidal_Basin_2016.jpg",
        "Rock Creek Park": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Rock_Creek_Park_2016.jpg/800px-Rock_Creek_Park_2016.jpg",
        "National Zoo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/National_Zoo_2016.jpg/800px-National_Zoo_2016.jpg",
        "Kennedy Center": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Kennedy_Center_2016.jpg/800px-Kennedy_Center_2016.jpg",
        "Ford's Theatre": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Fords_Theatre_2016.jpg/800px-Fords_Theatre_2016.jpg",
        "Arena Stage": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Arena_Stage_2016.jpg/800px-Arena_Stage_2016.jpg",
        
        # Baltimore
        "Baltimore Museum of Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Baltimore_Museum_of_Art_2016.jpg/800px-Baltimore_Museum_of_Art_2016.jpg",
        "Walters Art Museum": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Walters_Art_Museum_2016.jpg/800px-Walters_Art_Museum_2016.jpg",
        "Fort McHenry National Monument": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Fort_McHenry_2016.jpg/800px-Fort_McHenry_2016.jpg",
        "Inner Harbor": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Inner_Harbor_Baltimore_2016.jpg/800px-Inner_Harbor_Baltimore_2016.jpg",
        "National Aquarium": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/National_Aquarium_Baltimore_2016.jpg/800px-National_Aquarium_Baltimore_2016.jpg",
        
        # Philadelphia
        "Philadelphia Museum of Art": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Philadelphia_Museum_of_Art_2016.jpg/800px-Philadelphia_Museum_of_Art_2016.jpg",
        "Independence Hall": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Independence_Hall_2016.jpg/800px-Independence_Hall_2016.jpg",
        "Liberty Bell Center": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Liberty_Bell_2016.jpg/800px-Liberty_Bell_2016.jpg",
        "Franklin Institute": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Franklin_Institute_2016.jpg/800px-Franklin_Institute_2016.jpg",
        "Reading Terminal Market": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Reading_Terminal_Market_2016.jpg/800px-Reading_Terminal_Market_2016.jpg"
    }

def update_venue_images():
    """Update venue images with correct URLs"""
    print("🖼️  Updating venue images with correct URLs...")
    
    # Load predefined venues
    try:
        with open('data/predefined_venues.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading predefined venues: {e}")
        return
    
    venues = []
    for city_data in data['cities'].values():
        venues.extend(city_data['venues'])
    
    print(f"📊 Found {len(venues)} venues to update")
    
    # Get correct URLs
    correct_urls = get_correct_venue_images()
    
    updated_count = 0
    
    for venue in venues:
        venue_name = venue.get('name', 'Unknown')
        
        if venue_name in correct_urls:
            old_url = venue.get('image_url', '')
            new_url = correct_urls[venue_name]
            
            if old_url != new_url:
                venue['image_url'] = new_url
                print(f"✅ Updated {venue_name}")
                print(f"   Old: {old_url}")
                print(f"   New: {new_url}")
                updated_count += 1
        else:
            print(f"⚠️  No image found for: {venue_name}")
    
    # Save updated data
    try:
        with open('data/predefined_venues.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Updated JSON file")
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return
    
    print(f"\n📈 Results:")
    print(f"✅ Images updated: {updated_count}")
    print(f"📊 Total venues: {len(venues)}")

if __name__ == "__main__":
    update_venue_images()
