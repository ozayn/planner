#!/usr/bin/env python3
"""
Enhance existing venues with social media handles and additional information
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Social media and additional info for major venues
VENUE_ENHANCEMENTS = {
    # Washington DC Venues
    'Arena Stage': {
        'instagram_url': 'https://www.instagram.com/arenastagedc',
        'facebook_url': 'https://www.facebook.com/ArenaStage',
        'twitter_url': 'https://twitter.com/ArenaStage',
        'description': 'Arena Stage is a premier regional theater in Washington, DC, known for producing bold, innovative American theater and fostering new theatrical voices.',
    },
    'Kennedy Center': {
        'instagram_url': 'https://www.instagram.com/kennedycenter',
        'facebook_url': 'https://www.facebook.com/KennedyCenter',
        'twitter_url': 'https://twitter.com/kencen',
        'youtube_url': 'https://www.youtube.com/user/KennedyCenter',
        'description': 'The John F. Kennedy Center for the Performing Arts is America\'s living memorial to President Kennedy and the nation\'s busiest performing arts facility.',
    },
    'National Gallery of Art': {
        'instagram_url': 'https://www.instagram.com/ngadc',
        'facebook_url': 'https://www.facebook.com/NationalGalleryofArt',
        'twitter_url': 'https://twitter.com/ngadc',
        'youtube_url': 'https://www.youtube.com/user/NationalGalleryArt',
        'description': 'The National Gallery of Art houses one of the world\'s finest collections of paintings, sculpture, and graphic arts from the Middle Ages to the present.',
    },
    'Smithsonian National Museum of Natural History': {
        'instagram_url': 'https://www.instagram.com/smithsoniannmnh',
        'facebook_url': 'https://www.facebook.com/naturalhistory',
        'twitter_url': 'https://twitter.com/NMNH',
        'youtube_url': 'https://www.youtube.com/user/SmithsonianNMNH',
        'description': 'The National Museum of Natural History is dedicated to inspiring curiosity, discovery, and learning about the natural world through its unparalleled research, collections, and exhibitions.',
    },
    'Smithsonian National Air and Space Museum': {
        'instagram_url': 'https://www.instagram.com/airandspace',
        'facebook_url': 'https://www.facebook.com/airandspace',
        'twitter_url': 'https://twitter.com/airandspace',
        'youtube_url': 'https://www.youtube.com/user/airandspacemuseum',
        'description': 'The National Air and Space Museum maintains the world\'s largest and most significant collection of aviation and space artifacts.',
    },
    'International Spy Museum': {
        'instagram_url': 'https://www.instagram.com/spymuseum',
        'facebook_url': 'https://www.facebook.com/IntlSpyMuseum',
        'twitter_url': 'https://twitter.com/IntlSpyMuseum',
        'description': 'The International Spy Museum is the only public museum in the United States solely dedicated to espionage and the only one in the world to provide a global perspective on this all-but-invisible profession.',
    },
    'National Zoo': {
        'instagram_url': 'https://www.instagram.com/nationalzoo',
        'facebook_url': 'https://www.facebook.com/nationalzoo',
        'twitter_url': 'https://twitter.com/nationalzoo',
        'youtube_url': 'https://www.youtube.com/user/SmithsonianNZP',
        'tiktok_url': 'https://www.tiktok.com/@nationalzoo',
        'description': 'The Smithsonian\'s National Zoo is home to 2,700 animals representing more than 390 species, with a mission of saving species through science.',
    },
    
    # New York Venues
    'Metropolitan Museum of Art': {
        'instagram_url': 'https://www.instagram.com/metmuseum',
        'facebook_url': 'https://www.facebook.com/metmuseum',
        'twitter_url': 'https://twitter.com/metmuseum',
        'youtube_url': 'https://www.youtube.com/user/metmuseum',
        'tiktok_url': 'https://www.tiktok.com/@metmuseum',
        'description': 'The Metropolitan Museum of Art presents over 5,000 years of art from every part of the globe for everyone to experience and enjoy.',
    },
    'Museum of Modern Art (MoMA)': {
        'instagram_url': 'https://www.instagram.com/themuseumofmodernart',
        'facebook_url': 'https://www.facebook.com/MuseumofModernArt',
        'twitter_url': 'https://twitter.com/MuseumModernArt',
        'youtube_url': 'https://www.youtube.com/user/MoMAvideos',
        'description': 'The Museum of Modern Art (MoMA) is a place that fuels creativity, ignites minds, and provides inspiration through its collection and exhibitions.',
    },
    'American Museum of Natural History': {
        'instagram_url': 'https://www.instagram.com/amnh',
        'facebook_url': 'https://www.facebook.com/naturalhistory',
        'twitter_url': 'https://twitter.com/AMNH',
        'youtube_url': 'https://www.youtube.com/user/AMNHorg',
        'description': 'The American Museum of Natural History is one of the world\'s preeminent scientific and cultural institutions, with collections containing over 34 million specimens.',
    },
    
    # Los Angeles Venues
    'Getty Center': {
        'instagram_url': 'https://www.instagram.com/gettymuseum',
        'facebook_url': 'https://www.facebook.com/gettymuseum',
        'twitter_url': 'https://twitter.com/gettymuseum',
        'youtube_url': 'https://www.youtube.com/user/gettymuseum',
        'description': 'The Getty Center features the Getty Museum\'s collection of European paintings, sculpture, illuminated manuscripts, decorative arts, and photography.',
    },
    'Los Angeles County Museum of Art (LACMA)': {
        'instagram_url': 'https://www.instagram.com/lacma',
        'facebook_url': 'https://www.facebook.com/lacma',
        'twitter_url': 'https://twitter.com/lacma',
        'youtube_url': 'https://www.youtube.com/user/lacmavideo',
        'tiktok_url': 'https://www.tiktok.com/@lacma',
        'description': 'LACMA is the largest art museum in the western United States, with a collection that includes over 150,000 works spanning the history of art.',
    },
    
    # San Francisco Venues
    'San Francisco Museum of Modern Art (SFMOMA)': {
        'instagram_url': 'https://www.instagram.com/sfmoma',
        'facebook_url': 'https://www.facebook.com/SFMOMA',
        'twitter_url': 'https://twitter.com/SFMOMA',
        'youtube_url': 'https://www.youtube.com/user/SFMOMAmuseum',
        'description': 'SFMOMA is a dynamic hub for modern and contemporary art, engaging audiences through innovative exhibitions and programs.',
    },
    
    # Chicago Venues
    'Art Institute of Chicago': {
        'instagram_url': 'https://www.instagram.com/artinstitutechi',
        'facebook_url': 'https://www.facebook.com/artic.edu',
        'twitter_url': 'https://twitter.com/artinstitutechi',
        'youtube_url': 'https://www.youtube.com/user/ArtInstituteChicago',
        'description': 'The Art Institute of Chicago is home to one of the oldest and largest art collections in the United States, featuring iconic works from around the globe.',
    },
    'Field Museum': {
        'instagram_url': 'https://www.instagram.com/fieldmuseum',
        'facebook_url': 'https://www.facebook.com/fieldmuseum',
        'twitter_url': 'https://twitter.com/fieldmuseum',
        'youtube_url': 'https://www.youtube.com/user/FieldMuseum',
        'tiktok_url': 'https://www.tiktok.com/@fieldmuseum',
        'description': 'The Field Museum fuels a journey of discovery across time to enable solutions for a brighter future rich in nature and culture.',
    },
    'Shedd Aquarium': {
        'instagram_url': 'https://www.instagram.com/sheddaquarium',
        'facebook_url': 'https://www.facebook.com/sheddaquarium',
        'twitter_url': 'https://twitter.com/shedd_aquarium',
        'youtube_url': 'https://www.youtube.com/user/SheddAquarium',
        'tiktok_url': 'https://www.tiktok.com/@sheddaquarium',
        'description': 'Shedd Aquarium connects people with the living world to inspire compassion, curiosity, and conservation for aquatic life.',
    },
    
    # Embassy Social Media
    'Embassy of the United Kingdom': {
        'instagram_url': 'https://www.instagram.com/ukingov',
        'facebook_url': 'https://www.facebook.com/ukinusa',
        'twitter_url': 'https://twitter.com/ukinusa',
        'description': 'The British Embassy in Washington promotes UK interests in the US and hosts cultural events, exhibitions, and programs celebrating British culture and heritage.',
    },
    'Embassy of France': {
        'instagram_url': 'https://www.instagram.com/franceintheus',
        'facebook_url': 'https://www.facebook.com/FranceInTheUS',
        'twitter_url': 'https://twitter.com/franceintheus',
        'description': 'The French Embassy promotes Franco-American friendship through cultural programming, art exhibitions, and celebrations of French culture and heritage.',
    },
    'Embassy of Germany': {
        'instagram_url': 'https://www.instagram.com/germanydiplo',
        'facebook_url': 'https://www.facebook.com/GermanyDiplo',
        'twitter_url': 'https://twitter.com/germanydiplo',
        'description': 'The German Embassy fosters German-American relations through cultural events, exhibitions, and programs showcasing German culture, innovation, and traditions.',
    },
    'Embassy of Japan': {
        'instagram_url': 'https://www.instagram.com/japanembdc',
        'facebook_url': 'https://www.facebook.com/JapanEmbDC',
        'twitter_url': 'https://twitter.com/JapanEmbDC',
        'description': 'The Japanese Embassy promotes Japan-US friendship through cultural festivals, traditional ceremonies, art exhibitions, and celebrations of Japanese culture and heritage.',
    },
}

def enhance_venue_social_media():
    """Enhance venues with social media handles and additional information"""
    print("📱 Enhancing venues with social media and additional information...")
    
    with app.app_context():
        try:
            updated_count = 0
            
            for venue_name, enhancements in VENUE_ENHANCEMENTS.items():
                # Find venue by name
                venue = Venue.query.filter_by(name=venue_name).first()
                if not venue:
                    print(f"⚠️  Venue '{venue_name}' not found")
                    continue
                
                # Update social media fields
                updated_fields = []
                
                if 'instagram_url' in enhancements and not venue.instagram_url:
                    venue.instagram_url = enhancements['instagram_url']
                    updated_fields.append('Instagram')
                
                if 'facebook_url' in enhancements and not venue.facebook_url:
                    venue.facebook_url = enhancements['facebook_url']
                    updated_fields.append('Facebook')
                
                if 'twitter_url' in enhancements and not venue.twitter_url:
                    venue.twitter_url = enhancements['twitter_url']
                    updated_fields.append('Twitter')
                
                if 'youtube_url' in enhancements and not venue.youtube_url:
                    venue.youtube_url = enhancements['youtube_url']
                    updated_fields.append('YouTube')
                
                if 'tiktok_url' in enhancements and not venue.tiktok_url:
                    venue.tiktok_url = enhancements['tiktok_url']
                    updated_fields.append('TikTok')
                
                # Update description if it's more detailed
                if 'description' in enhancements:
                    if not venue.description or len(enhancements['description']) > len(venue.description):
                        venue.description = enhancements['description']
                        updated_fields.append('Description')
                
                if updated_fields:
                    updated_count += 1
                    print(f"✅ Updated '{venue_name}': {', '.join(updated_fields)}")
                else:
                    print(f"ℹ️  '{venue_name}' already has complete information")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Social media enhancement complete!")
            print(f"📊 Enhanced {updated_count} venues")
            
            # Show sample of enhanced data
            print(f"\n📱 Sample enhanced venue:")
            sample_venue = Venue.query.filter_by(name='National Zoo').first()
            if sample_venue:
                print(f"   {sample_venue.name}:")
                print(f"   Instagram: {sample_venue.instagram_url or 'None'}")
                print(f"   Facebook: {sample_venue.facebook_url or 'None'}")
                print(f"   TikTok: {sample_venue.tiktok_url or 'None'}")
                print(f"   Description: {sample_venue.description[:100]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error enhancing venues: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = enhance_venue_social_media()
    sys.exit(0 if success else 1)
