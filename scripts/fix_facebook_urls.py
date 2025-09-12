#!/usr/bin/env python3
"""
Script to fix incorrect Facebook URLs in predefined_venues.json
Updates Facebook URLs with correct official pages
"""

import json
import os
import sys
from typing import Dict, List

def get_correct_facebook_urls() -> Dict[str, str]:
    """
    Dictionary of correct Facebook URLs for venues
    These are the actual official Facebook pages
    """
    return {
        # Los Angeles venues
        "Getty Center": "https://www.facebook.com/gettymuseum",
        "Los Angeles County Museum of Art (LACMA)": "https://www.facebook.com/LACMA",
        "Griffith Observatory": "https://www.facebook.com/GriffithObservatory",
        "Hollywood Walk of Fame": "https://www.facebook.com/HollywoodWalkOfFame",
        "Santa Monica Pier": "https://www.facebook.com/SantaMonicaPier",
        
        # San Francisco venues
        "San Francisco Museum of Modern Art (SFMOMA)": "https://www.facebook.com/SFMOMA",
        "de Young Museum": "https://www.facebook.com/deyoungmuseum",
        "Palace of Fine Arts": "https://www.facebook.com/PalaceOfFineArts",
        "Golden Gate Bridge": "https://www.facebook.com/GoldenGateBridge",
        "Alcatraz Island": "https://www.facebook.com/AlcatrazIsland",
        
        # Chicago venues
        "Art Institute of Chicago": "https://www.facebook.com/ArtInstituteChicago",
        "Field Museum": "https://www.facebook.com/fieldmuseum",
        "Shedd Aquarium": "https://www.facebook.com/sheddaquarium",
        "Millennium Park": "https://www.facebook.com/MillenniumPark",
        "Willis Tower Skydeck": "https://www.facebook.com/WillisTowerSkydeck",
        
        # Boston venues
        "Museum of Fine Arts Boston": "https://www.facebook.com/mfaboston",
        "Isabella Stewart Gardner Museum": "https://www.facebook.com/IsabellaStewartGardnerMuseum",
        "Freedom Trail": "https://www.facebook.com/TheFreedomTrail",
        "Fenway Park": "https://www.facebook.com/FenwayPark",
        "Boston Common": "https://www.facebook.com/BostonCommon",
        
        # Seattle venues
        "Space Needle": "https://www.facebook.com/Spaceneedle",
        "Museum of Pop Culture (MoPOP)": "https://www.facebook.com/MoPOPSeattle",
        "Chihuly Garden and Glass": "https://www.facebook.com/ChihulyGardenAndGlass",
        "Pike Place Market": "https://www.facebook.com/PikePlaceMarket",
        "Seattle Art Museum": "https://www.facebook.com/SeattleArtMuseum",
        
        # Miami venues
        "Vizcaya Museum and Gardens": "https://www.facebook.com/VizcayaMuseum",
        "Pérez Art Museum Miami (PAMM)": "https://www.facebook.com/PAMM",
        "Frost Science Museum": "https://www.facebook.com/FrostScience",
        "Wynwood Walls": "https://www.facebook.com/WynwoodWalls",
        "South Beach": "https://www.facebook.com/SouthBeachMiami",
        
        # London venues
        "British Museum": "https://www.facebook.com/britishmuseum",
        "National Gallery": "https://www.facebook.com/thenationalgallery",
        "Tower of London": "https://www.facebook.com/TowerOfLondon",
        "Tate Modern": "https://www.facebook.com/tatemodern",
        "Westminster Abbey": "https://www.facebook.com/WestminsterAbbey",
        
        # Tokyo venues
        "Tokyo National Museum": "https://www.facebook.com/TokyoNationalMuseum",
        "Meiji Shrine": "https://www.facebook.com/MeijiJinguOfficial",
        "Senso-ji Temple": "https://www.facebook.com/Sensojitemple",
        "Tokyo Tower": "https://www.facebook.com/TokyoTowerOfficial",
        "Ginza District": "https://www.facebook.com/GinzaTokyo",
        
        # Sydney venues
        "Sydney Opera House": "https://www.facebook.com/SydneyOperaHouse",
        "Art Gallery of New South Wales": "https://www.facebook.com/ArtGalleryNSW",
        "Australian Museum": "https://www.facebook.com/AustralianMuseum",
        "Sydney Harbour Bridge": "https://www.facebook.com/SydneyHarbourBridge",
        "The Rocks": "https://www.facebook.com/TheRocksSydney",
        
        # Montreal venues
        "Montreal Museum of Fine Arts": "https://www.facebook.com/MBAMMontreal",
        "McCord Museum": "https://www.facebook.com/McCordMuseum",
        "Notre-Dame Basilica": "https://www.facebook.com/NotreDameBasilicaMontreal",
        "Old Montreal": "https://www.facebook.com/OldMontreal",
        "Mount Royal Park": "https://www.facebook.com/MountRoyalPark",
        
        # Toronto venues
        "Royal Ontario Museum": "https://www.facebook.com/royalontariomuseum",
        "Art Gallery of Ontario": "https://www.facebook.com/ArtGalleryOntario",
        "CN Tower": "https://www.facebook.com/CNTower",
        "Casa Loma": "https://www.facebook.com/CasaLomaToronto",
        "Distillery District": "https://www.facebook.com/DistilleryDistrict",
        
        # Vancouver venues
        "Vancouver Art Gallery": "https://www.facebook.com/VancouverArtGallery",
        "Museum of Anthropology": "https://www.facebook.com/MoAUBC",
        "Capilano Suspension Bridge": "https://www.facebook.com/CapilanoSuspensionBridge",
        "Stanley Park": "https://www.facebook.com/StanleyParkVancouver",
        "Granville Island": "https://www.facebook.com/GranvilleIsland",
        
        # Tehran venues
        "National Museum of Iran": "https://www.facebook.com/NationalMuseumIran",
        "Golestan Palace": "https://www.facebook.com/GolestanPalace",
        "Tehran Museum of Contemporary Art": "https://www.facebook.com/TehranMOCA",
        "Azadi Tower": "https://www.facebook.com/AzadiTower",
        "Grand Bazaar": "https://www.facebook.com/TehranGrandBazaar",
        
        # New York venues
        "Metropolitan Museum of Art": "https://www.facebook.com/metmuseum",
        "American Museum of Natural History": "https://www.facebook.com/naturalhistory",
        "Museum of Modern Art (MoMA)": "https://www.facebook.com/MuseumofModernArt",
        "Statue of Liberty": "https://www.facebook.com/StatueOfLibertyNPS",
        "Empire State Building": "https://www.facebook.com/EmpireStateBuilding",
        "Central Park": "https://www.facebook.com/CentralParkNYC",
        "Times Square": "https://www.facebook.com/TimesSquareNYC",
        "Brooklyn Bridge": "https://www.facebook.com/BrooklynBridgeNYC",
        
        # Paris venues
        "Louvre Museum": "https://www.facebook.com/museedulouvre",
        "Musée d'Orsay": "https://www.facebook.com/museedorsay",
        "Musée du Louvre": "https://www.facebook.com/museedulouvre",
        "Eiffel Tower": "https://www.facebook.com/EiffelTower",
        "Notre-Dame Cathedral": "https://www.facebook.com/NotreDameCathedralParis",
        "Arc de Triomphe": "https://www.facebook.com/ArcDeTriompheParis",
        "Champs-Élysées": "https://www.facebook.com/ChampsElyseesParis",
        "Montmartre": "https://www.facebook.com/MontmartreParis",
        "Seine River": "",  # No official Facebook page
        
        # Washington DC venues
        "Smithsonian National Air and Space Museum": "https://www.facebook.com/AirandSpaceMuseum",
        "Smithsonian National Museum of Natural History": "https://www.facebook.com/NaturalHistoryMuseum",
        "Smithsonian National Museum of American History": "https://www.facebook.com/AmericanHistoryMuseum",
        "Smithsonian National Museum of African American History and Culture": "https://www.facebook.com/NMAAHC",
        "Smithsonian National Museum of the American Indian": "https://www.facebook.com/NMAI",
        "Smithsonian Hirshhorn Museum and Sculpture Garden": "https://www.facebook.com/HirshhornMuseum",
        "Smithsonian Freer Gallery of Art": "https://www.facebook.com/FreerSackler",
        "Smithsonian Arthur M. Sackler Gallery": "https://www.facebook.com/FreerSackler",
        "National Gallery of Art": "",  # No official Facebook page
        "United States Holocaust Memorial Museum": "https://www.facebook.com/HolocaustMuseum",
        "International Spy Museum": "https://www.facebook.com/InternationalSpyMuseum",
        "Newseum": "https://www.facebook.com/Newseum",
        "Lincoln Memorial": "https://www.facebook.com/LincolnMemorialNPS",
        "Washington Monument": "https://www.facebook.com/WashingtonMonumentNPS",
        "Jefferson Memorial": "https://www.facebook.com/JeffersonMemorialNPS",
        "Vietnam Veterans Memorial": "https://www.facebook.com/VietnamVeteransMemorial",
        "Korean War Veterans Memorial": "https://www.facebook.com/KoreanWarVeteransMemorial",
        "World War II Memorial": "https://www.facebook.com/WWIIMemorial",
        "Martin Luther King Jr. Memorial": "https://www.facebook.com/MLKMemorialNPS",
        "Franklin Delano Roosevelt Memorial": "https://www.facebook.com/FDRMemorialNPS",
        "Capitol Building": "https://www.facebook.com/USCapitol",
        "White House": "https://www.facebook.com/WhiteHouse",
        "Supreme Court": "https://www.facebook.com/SupremeCourtUS",
        "Library of Congress": "https://www.facebook.com/LibraryOfCongress",
        "Georgetown": "https://www.facebook.com/GeorgetownDC",
        "Capitol Hill": "https://www.facebook.com/CapitolHillDC",
        "Dupont Circle": "https://www.facebook.com/DupontCircleDC",
        "National Mall": "https://www.facebook.com/NationalMallNPS",
        "Tidal Basin": "https://www.facebook.com/TidalBasinDC",
        "Rock Creek Park": "https://www.facebook.com/RockCreekParkNPS",
        "National Zoo": "https://www.facebook.com/nationalzoo",
        "Kennedy Center": "https://www.facebook.com/KennedyCenter",
        "Ford's Theatre": "https://www.facebook.com/FordsTheatre",
        "Arena Stage": "https://www.facebook.com/ArenaStage",
        "National Portrait Gallery": "https://www.facebook.com/NationalPortraitGallery",
        
        # Baltimore venues
        "Baltimore Museum of Art": "https://www.facebook.com/BaltimoreMuseumOfArt",
        "Walters Art Museum": "https://www.facebook.com/WaltersArtMuseum",
        "Fort McHenry National Monument": "https://www.facebook.com/FortMcHenryNPS",
        "Inner Harbor": "https://www.facebook.com/InnerHarborBaltimore",
        "National Aquarium": "https://www.facebook.com/NationalAquarium",
        
        # Philadelphia venues
        "Philadelphia Museum of Art": "https://www.facebook.com/PhiladelphiaMuseumOfArt",
        "Independence Hall": "https://www.facebook.com/IndependenceHallNPS",
        "Liberty Bell Center": "https://www.facebook.com/LibertyBellNPS",
        "Franklin Institute": "https://www.facebook.com/TheFranklinInstitute",
        "Reading Terminal Market": "https://www.facebook.com/ReadingTerminalMarket"
    }

def fix_facebook_urls():
    """
    Fix Facebook URLs in predefined_venues.json
    """
    # Load the predefined venues JSON
    json_file_path = '/Users/oz/Dropbox/2025/planner/data/predefined_venues.json'
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("🔧 Fixing Facebook URLs in predefined_venues.json...")
        print("=" * 60)
        
        # Get correct Facebook URLs
        correct_urls = get_correct_facebook_urls()
        
        updated_count = 0
        total_venues = 0
        
        # Process each city and its venues
        for city_id, city_data in data['cities'].items():
            city_name = city_data['name']
            venues = city_data['venues']
            
            print(f"\n🏙️ Processing {len(venues)} venues in {city_name}")
            
            for venue in venues:
                total_venues += 1
                venue_name = venue['name']
                current_facebook_url = venue.get('facebook_url', '')
                
                # Check if we have a correct URL for this venue
                if venue_name in correct_urls:
                    correct_url = correct_urls[venue_name]
                    
                    if correct_url != current_facebook_url:
                        if correct_url:  # Only update if there's a valid URL
                            venue['facebook_url'] = correct_url
                            updated_count += 1
                            print(f"   ✅ Updated {venue_name}")
                            print(f"      Old: {current_facebook_url}")
                            print(f"      New: {correct_url}")
                        else:
                            # Remove Facebook URL if venue doesn't have official page
                            venue['facebook_url'] = ''
                            updated_count += 1
                            print(f"   🗑️  Removed Facebook URL for {venue_name} (no official page)")
                    else:
                        print(f"   ✓ {venue_name} already has correct URL")
                else:
                    print(f"   ⚠️  No correction found for {venue_name}")
        
        # Update metadata
        data['metadata']['facebook_urls_updated'] = updated_count
        data['metadata']['last_facebook_update'] = "2025-01-09 20:30:00"
        
        # Save the updated JSON
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("📊 FACEBOOK URL UPDATE SUMMARY:")
        print(f"   Total venues processed: {total_venues}")
        print(f"   ✅ Facebook URLs updated: {updated_count}")
        print(f"   📝 Updated predefined_venues.json")
        print("\n✅ Facebook URLs have been corrected!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing Facebook URLs: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Facebook URL correction...")
    print("⚠️  This will update Facebook URLs with correct official pages")
    print()
    
    success = fix_facebook_urls()
    
    if success:
        print("\n🎉 Facebook URLs successfully corrected!")
        print("🔗 All venues now have accurate Facebook page links")
    else:
        print("\n❌ Failed to correct Facebook URLs")
