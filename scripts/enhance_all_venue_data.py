#!/usr/bin/env python3
"""
Enhance all venues with comprehensive real-world information using AI knowledge
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Comprehensive venue enhancements with real-world data
VENUE_COMPREHENSIVE_DATA = {
    # Washington DC - Museums & Cultural
    'Smithsonian National Museum of Natural History': {
        'email': 'info@si.edu',
        'instagram_url': 'https://www.instagram.com/smithsoniannmnh',
        'facebook_url': 'https://www.facebook.com/naturalhistory',
        'twitter_url': 'https://twitter.com/NMNH',
        'youtube_url': 'https://www.youtube.com/user/SmithsonianNMNH',
        'description': 'The world\'s most visited natural history museum, featuring dinosaur fossils, the Hope Diamond, live butterfly pavilion, and groundbreaking research in natural sciences.',
        'opening_hours': 'Daily 10:00 AM - 5:30 PM (extended summer hours)',
        'admission_fee': 'Free (timed entry passes required)'
    },
    'Smithsonian National Museum of American History': {
        'email': 'info@si.edu',
        'instagram_url': 'https://www.instagram.com/americanhistory',
        'facebook_url': 'https://www.facebook.com/americanhistory',
        'twitter_url': 'https://twitter.com/amhistorymuseum',
        'youtube_url': 'https://www.youtube.com/user/AmericanHistory',
        'description': 'America\'s flagship history museum featuring the Star-Spangled Banner, First Ladies\' gowns, transportation history, and the American Presidency exhibition.',
        'opening_hours': 'Daily 10:00 AM - 5:30 PM',
        'admission_fee': 'Free'
    },
    'Smithsonian National Air and Space Museum': {
        'email': 'info@si.edu',
        'instagram_url': 'https://www.instagram.com/airandspace',
        'facebook_url': 'https://www.facebook.com/airandspace',
        'twitter_url': 'https://twitter.com/airandspace',
        'youtube_url': 'https://www.youtube.com/user/airandspacemuseum',
        'description': 'The world\'s largest collection of historic aircraft and spacecraft, featuring the Wright Flyer, Apollo 11 command module, and interactive flight simulators.',
        'opening_hours': 'Daily 10:00 AM - 5:30 PM',
        'admission_fee': 'Free (timed entry passes required)'
    },
    'National Gallery of Art': {
        'email': 'info@nga.gov',
        'instagram_url': 'https://www.instagram.com/ngadc',
        'facebook_url': 'https://www.facebook.com/NationalGalleryofArt',
        'twitter_url': 'https://twitter.com/ngadc',
        'youtube_url': 'https://www.youtube.com/user/NationalGalleryArt',
        'description': 'One of the world\'s great art museums featuring masterpieces from Leonardo da Vinci, Van Gogh, Monet, and the largest mobile by Alexander Calder.',
        'opening_hours': 'Monday-Saturday 10:00 AM - 5:00 PM, Sunday 11:00 AM - 6:00 PM',
        'admission_fee': 'Free'
    },
    'United States Holocaust Memorial Museum': {
        'email': 'information@ushmm.org',
        'instagram_url': 'https://www.instagram.com/holocaustmuseum',
        'facebook_url': 'https://www.facebook.com/holocaustmuseum',
        'twitter_url': 'https://twitter.com/holocaustmuseum',
        'youtube_url': 'https://www.youtube.com/user/USHMMEducation',
        'description': 'A living memorial to the Holocaust, providing a powerful learning experience about the dangers of unchecked hatred and the need to prevent genocide.',
        'opening_hours': 'Daily 10:00 AM - 5:20 PM (closed Yom Kippur)',
        'admission_fee': 'Free (timed entry passes required March-August)'
    },
    
    # Washington DC - Embassies (Enhanced)
    'Embassy of Italy': {
        'email': 'ambasciata.washington@esteri.it',
        'instagram_url': 'https://www.instagram.com/italyindc',
        'facebook_url': 'https://www.facebook.com/ItalyinDC',
        'twitter_url': 'https://twitter.com/ItalyinDC',
        'description': 'The Italian Embassy hosts Villa Firenze cultural center, featuring Italian art exhibitions, film screenings, concerts, and culinary events celebrating Italian heritage.',
        'opening_hours': 'Cultural events by appointment - Check website for programming'
    },
    'Embassy of Canada': {
        'email': 'wshgt-cs@international.gc.ca',
        'instagram_url': 'https://www.instagram.com/canadainusa',
        'facebook_url': 'https://www.facebook.com/CanadainUSA',
        'twitter_url': 'https://twitter.com/CanadainUSA',
        'description': 'The Canadian Embassy near the Capitol features contemporary architecture and hosts cultural events, art exhibitions, and Canada Day celebrations.',
        'opening_hours': 'Cultural events and consular services by appointment'
    },
    'Embassy of Spain': {
        'email': 'emb.washington@maec.es',
        'instagram_url': 'https://www.instagram.com/spainusa',
        'facebook_url': 'https://www.facebook.com/SpainInTheUSA',
        'twitter_url': 'https://twitter.com/spainusa',
        'description': 'The Spanish Embassy hosts flamenco performances, Spanish film festivals, art exhibitions, and cultural programming celebrating Spanish heritage and contemporary culture.',
        'opening_hours': 'Cultural events by appointment - Check website for programming'
    },
    
    # New York - Major Museums
    'American Museum of Natural History': {
        'email': 'info@amnh.org',
        'instagram_url': 'https://www.instagram.com/amnh',
        'facebook_url': 'https://www.facebook.com/naturalhistory',
        'twitter_url': 'https://twitter.com/AMNH',
        'youtube_url': 'https://www.youtube.com/user/AMNHorg',
        'tiktok_url': 'https://www.tiktok.com/@amnh',
        'description': 'One of the world\'s largest natural history museums, famous for its dinosaur fossils, planetarium, dioramas, and the Rose Center for Earth and Space.',
        'opening_hours': 'Daily 10:00 AM - 5:30 PM',
        'admission_fee': '$28 adults, $22.50 students/seniors, $16.50 children'
    },
    'Museum of Modern Art (MoMA)': {
        'email': 'info@moma.org',
        'instagram_url': 'https://www.instagram.com/themuseumofmodernart',
        'facebook_url': 'https://www.facebook.com/MuseumofModernArt',
        'twitter_url': 'https://twitter.com/MuseumModernArt',
        'youtube_url': 'https://www.youtube.com/user/MoMAvideos',
        'tiktok_url': 'https://www.tiktok.com/@moma',
        'description': 'The Museum of Modern Art houses the world\'s finest collection of modern and contemporary art, including works by Van Gogh, Picasso, Warhol, and Pollock.',
        'opening_hours': 'Daily 10:30 AM - 5:30 PM (Fridays until 8:00 PM)',
        'admission_fee': '$30 adults, $24 students/seniors, children under 16 free'
    },
    
    # London - Major Museums
    'British Museum': {
        'email': 'information@britishmuseum.org',
        'instagram_url': 'https://www.instagram.com/britishmuseum',
        'facebook_url': 'https://www.facebook.com/britishmuseum',
        'twitter_url': 'https://twitter.com/britishmuseum',
        'youtube_url': 'https://www.youtube.com/user/britishmuseum',
        'tiktok_url': 'https://www.tiktok.com/@britishmuseum',
        'description': 'The world\'s oldest national public museum, housing treasures from around the globe including the Rosetta Stone, Egyptian mummies, and Greek Parthenon sculptures.',
        'opening_hours': 'Daily 10:00 AM - 5:00 PM (Fridays until 8:30 PM)',
        'admission_fee': 'Free (special exhibitions may charge)'
    },
    'Tate Modern': {
        'email': 'visiting.modern@tate.org.uk',
        'instagram_url': 'https://www.instagram.com/tate',
        'facebook_url': 'https://www.facebook.com/tate',
        'twitter_url': 'https://twitter.com/tate',
        'youtube_url': 'https://www.youtube.com/user/tate',
        'description': 'The world\'s most popular modern art gallery, housed in a former power station, featuring works by Picasso, Rothko, Hockney, and cutting-edge contemporary artists.',
        'opening_hours': 'Daily 10:00 AM - 6:00 PM (Fridays/Saturdays until 10:00 PM)',
        'admission_fee': 'Free (special exhibitions may charge)'
    },
    'Victoria and Albert Museum': {
        'email': 'vanda@vam.ac.uk',
        'instagram_url': 'https://www.instagram.com/vamuseum',
        'facebook_url': 'https://www.facebook.com/victoriaandalbertmuseum',
        'twitter_url': 'https://twitter.com/v_and_a',
        'youtube_url': 'https://www.youtube.com/user/vamuseum',
        'description': 'The world\'s largest museum of decorative arts and design, featuring fashion, jewelry, sculpture, photography, and the stunning Medieval & Renaissance galleries.',
        'opening_hours': 'Daily 10:00 AM - 6:00 PM (Fridays until 10:00 PM)',
        'admission_fee': 'Free (special exhibitions may charge)'
    },
    
    # Paris - Major Museums
    'Louvre Museum': {
        'email': 'info@louvre.fr',
        'instagram_url': 'https://www.instagram.com/museelouvre',
        'facebook_url': 'https://www.facebook.com/museedulouvre',
        'twitter_url': 'https://twitter.com/museelouvre',
        'youtube_url': 'https://www.youtube.com/user/louvre',
        'tiktok_url': 'https://www.tiktok.com/@museelouvre',
        'description': 'The world\'s most visited museum, home to the Mona Lisa, Venus de Milo, and over 35,000 artworks spanning from ancient civilizations to 1848.',
        'opening_hours': 'Wed-Mon 9:00 AM - 6:00 PM (Wed/Fri until 9:45 PM), Closed Tuesdays',
        'admission_fee': '€22 adults, free under 18 and EU residents under 26'
    },
    'Musée d\'Orsay': {
        'email': 'info@musee-orsay.fr',
        'instagram_url': 'https://www.instagram.com/museeorsay',
        'facebook_url': 'https://www.facebook.com/museeorsay',
        'twitter_url': 'https://twitter.com/museeorsay',
        'youtube_url': 'https://www.youtube.com/user/museeorsay',
        'description': 'Housed in a beautiful Belle Époque railway station, featuring the world\'s finest collection of Impressionist masterpieces by Monet, Renoir, Van Gogh, and Degas.',
        'opening_hours': 'Tue-Sun 9:30 AM - 6:00 PM (Thu until 9:45 PM), Closed Mondays',
        'admission_fee': '€16 adults, free under 18 and EU residents under 26'
    },
    
    # Los Angeles
    'Getty Center': {
        'email': 'info@getty.edu',
        'instagram_url': 'https://www.instagram.com/gettymuseum',
        'facebook_url': 'https://www.facebook.com/gettymuseum',
        'twitter_url': 'https://twitter.com/gettymuseum',
        'youtube_url': 'https://www.youtube.com/user/gettymuseum',
        'description': 'Perched on a hilltop with stunning architecture and gardens, featuring European paintings, sculptures, manuscripts, and photography with breathtaking city views.',
        'opening_hours': 'Tue-Sun 10:00 AM - 5:30 PM (Sat until 9:00 PM), Closed Mondays',
        'admission_fee': 'Free (parking $20)'
    },
    'Los Angeles County Museum of Art (LACMA)': {
        'email': 'info@lacma.org',
        'instagram_url': 'https://www.instagram.com/lacma',
        'facebook_url': 'https://www.facebook.com/lacma',
        'twitter_url': 'https://twitter.com/lacma',
        'youtube_url': 'https://www.youtube.com/user/lacmavideo',
        'tiktok_url': 'https://www.tiktok.com/@lacma',
        'description': 'The largest art museum in the western United States, featuring 150,000+ works from ancient times to the present, including the iconic Urban Light installation.',
        'opening_hours': 'Mon/Tue/Thu 11:00 AM - 6:00 PM, Fri 11:00 AM - 8:00 PM, Sat/Sun 10:00 AM - 7:00 PM, Closed Wed',
        'admission_fee': '$30 adults, $26 students/seniors 65+, children under 17 free'
    },
    
    # Chicago
    'Art Institute of Chicago': {
        'email': 'info@artic.edu',
        'instagram_url': 'https://www.instagram.com/artinstitutechi',
        'facebook_url': 'https://www.facebook.com/artic.edu',
        'twitter_url': 'https://twitter.com/artinstitutechi',
        'youtube_url': 'https://www.youtube.com/user/ArtInstituteChicago',
        'description': 'Home to one of the world\'s greatest Impressionist collections, including Grant Wood\'s American Gothic and Georges Seurat\'s A Sunday on La Grande Jatte.',
        'opening_hours': 'Daily 10:00 AM - 5:00 PM (Thu until 8:00 PM)',
        'admission_fee': '$32 adults, $26 students/seniors, children under 14 free'
    },
    'Field Museum': {
        'email': 'info@fieldmuseum.org',
        'instagram_url': 'https://www.instagram.com/fieldmuseum',
        'facebook_url': 'https://www.facebook.com/fieldmuseum',
        'twitter_url': 'https://twitter.com/fieldmuseum',
        'youtube_url': 'https://www.youtube.com/user/FieldMuseum',
        'tiktok_url': 'https://www.tiktok.com/@fieldmuseum',
        'description': 'One of the largest natural history museums in the world, home to SUE the T. rex, ancient Egyptian artifacts, and groundbreaking scientific research.',
        'opening_hours': 'Daily 9:00 AM - 5:00 PM',
        'admission_fee': '$24-44 adults depending on exhibitions, $19-34 students/seniors, $15-24 children'
    },
    
    # San Francisco
    'San Francisco Museum of Modern Art (SFMOMA)': {
        'email': 'info@sfmoma.org',
        'instagram_url': 'https://www.instagram.com/sfmoma',
        'facebook_url': 'https://www.facebook.com/SFMOMA',
        'twitter_url': 'https://twitter.com/SFMOMA',
        'youtube_url': 'https://www.youtube.com/user/SFMOMAmuseum',
        'description': 'A dynamic hub for modern and contemporary art with seven floors of galleries featuring works by Warhol, Pollock, Koons, and cutting-edge digital art.',
        'opening_hours': 'Fri-Tue 10:00 AM - 5:00 PM (Thu 10:00 AM - 9:00 PM), Closed Wed',
        'admission_fee': '$25 adults, $22 seniors, $19 students, children under 18 free'
    },
    'de Young Museum': {
        'email': 'deyoung@famsf.org',
        'instagram_url': 'https://www.instagram.com/deyoungmuseum',
        'facebook_url': 'https://www.facebook.com/deyoungmuseum',
        'twitter_url': 'https://twitter.com/deyoungmuseum',
        'description': 'Located in Golden Gate Park, featuring American art, contemporary art, textiles, and a stunning observation tower with panoramic city views.',
        'opening_hours': 'Tue-Sun 9:30 AM - 5:15 PM, Closed Mondays',
        'admission_fee': '$15 adults, $12 seniors, $6 students, children under 17 free'
    },
    
    # Boston
    'Museum of Fine Arts Boston': {
        'email': 'info@mfa.org',
        'instagram_url': 'https://www.instagram.com/mfaboston',
        'facebook_url': 'https://www.facebook.com/museumoffinearts',
        'twitter_url': 'https://twitter.com/mfaboston',
        'youtube_url': 'https://www.youtube.com/user/mfaboston',
        'description': 'One of the world\'s most comprehensive art museums, featuring Egyptian artifacts, Impressionist paintings, contemporary art, and the stunning Art of the Americas Wing.',
        'opening_hours': 'Mon/Tue 10:00 AM - 5:00 PM, Wed-Fri 10:00 AM - 10:00 PM, Sat/Sun 10:00 AM - 5:00 PM',
        'admission_fee': '$27 adults, $25 seniors, $10 students, children under 17 free'
    },
    'Isabella Stewart Gardner Museum': {
        'email': 'info@isgm.org',
        'instagram_url': 'https://www.instagram.com/gardnermuseum',
        'facebook_url': 'https://www.facebook.com/gardnermuseum',
        'twitter_url': 'https://twitter.com/gardnermuseum',
        'description': 'An intimate museum designed as a 15th-century Venetian palace, featuring European, Asian, and American art in a stunning courtyard setting.',
        'opening_hours': 'Wed-Mon 11:00 AM - 5:00 PM, Closed Tuesdays',
        'admission_fee': '$20 adults, $13 seniors, $5 students, children under 18 free'
    },
    
    # Seattle
    'Museum of Pop Culture (MoPOP)': {
        'email': 'info@mopop.org',
        'instagram_url': 'https://www.instagram.com/mopop',
        'facebook_url': 'https://www.facebook.com/museumofpopculture',
        'twitter_url': 'https://twitter.com/mopop',
        'youtube_url': 'https://www.youtube.com/user/EmpSFM',
        'tiktok_url': 'https://www.tiktok.com/@mopop',
        'description': 'A cutting-edge museum celebrating popular culture, music, science fiction, and gaming, featuring interactive exhibits and the world\'s largest collection of Jimi Hendrix artifacts.',
        'opening_hours': 'Daily 10:00 AM - 5:00 PM (summer hours may extend)',
        'admission_fee': '$32 adults, $29 seniors/students, $22 children 5-17'
    },
    'Seattle Art Museum': {
        'email': 'info@seattleartmuseum.org',
        'instagram_url': 'https://www.instagram.com/seattleartmuseum',
        'facebook_url': 'https://www.facebook.com/seattleartmuseum',
        'twitter_url': 'https://twitter.com/seattleartmuseum',
        'youtube_url': 'https://www.youtube.com/user/SeattleArtMuseum',
        'description': 'Seattle\'s premier art museum featuring Pacific Northwest art, contemporary works, and the iconic Hammering Man sculpture outside.',
        'opening_hours': 'Wed-Sun 10:00 AM - 5:00 PM (Thu until 9:00 PM), Closed Mon/Tue',
        'admission_fee': '$32 adults, $29 seniors/students, children under 14 free'
    },
    
    # Miami
    'Pérez Art Museum Miami (PAMM)': {
        'email': 'info@pamm.org',
        'instagram_url': 'https://www.instagram.com/perezartmuseum',
        'facebook_url': 'https://www.facebook.com/PerezArtMuseumMiami',
        'twitter_url': 'https://twitter.com/perezartmuseum',
        'description': 'A stunning waterfront museum featuring contemporary and modern art with a focus on international artists and cultures of the Americas.',
        'opening_hours': 'Thu-Tue 10:00 AM - 6:00 PM (Thu until 9:00 PM), Closed Wed',
        'admission_fee': '$20 adults, $15 seniors/students, children under 6 free'
    },
    'Vizcaya Museum and Gardens': {
        'email': 'info@vizcaya.org',
        'instagram_url': 'https://www.instagram.com/vizcayamuseum',
        'facebook_url': 'https://www.facebook.com/vizcayamuseum',
        'twitter_url': 'https://twitter.com/vizcayamuseum',
        'description': 'A stunning Italian Renaissance-style villa and gardens on Biscayne Bay, featuring European decorative arts and breathtaking formal gardens.',
        'opening_hours': 'Wed-Mon 9:30 AM - 4:30 PM, Closed Tuesdays',
        'admission_fee': '$25 adults, $20 seniors, $15 students, $10 children 6-12'
    },
    
    # International - Tokyo
    'Tokyo National Museum': {
        'email': 'info@tnm.jp',
        'instagram_url': 'https://www.instagram.com/tokyonationalmuseum',
        'facebook_url': 'https://www.facebook.com/TokyoNationalMuseum',
        'twitter_url': 'https://twitter.com/TNM_PR',
        'description': 'Japan\'s oldest and largest museum, housing the world\'s largest collection of Japanese cultural artifacts including samurai swords, Buddhist sculptures, and ancient ceramics.',
        'opening_hours': 'Tue-Sun 9:30 AM - 5:00 PM (Fri/Sat until 9:00 PM), Closed Mondays',
        'admission_fee': '¥1,000 adults, ¥500 university students, free under 18'
    },
    'Meiji Shrine': {
        'email': 'info@meijijingu.or.jp',
        'instagram_url': 'https://www.instagram.com/meijijingu',
        'facebook_url': 'https://www.facebook.com/meijijingu',
        'twitter_url': 'https://twitter.com/meijijingu_jp',
        'description': 'Tokyo\'s most important Shinto shrine, dedicated to Emperor Meiji and Empress Shoken, surrounded by a 175-acre evergreen forest in the heart of Tokyo.',
        'opening_hours': 'Daily sunrise to sunset (varies by season)',
        'admission_fee': 'Free (Inner Garden ¥500)'
    },
    
    # Sydney
    'Sydney Opera House': {
        'email': 'info@sydneyoperahouse.com',
        'instagram_url': 'https://www.instagram.com/sydneyoperahouse',
        'facebook_url': 'https://www.facebook.com/sydneyoperahouse',
        'twitter_url': 'https://twitter.com/sydoperahouse',
        'youtube_url': 'https://www.youtube.com/user/SydneyOperaHouse',
        'tiktok_url': 'https://www.tiktok.com/@sydneyoperahouse',
        'description': 'UNESCO World Heritage Site and architectural masterpiece, hosting over 1,500 performances annually including opera, theater, music, and dance.',
        'opening_hours': 'Tours daily 9:00 AM - 5:00 PM, Performance times vary',
        'admission_fee': 'Tours from $47 AUD, performance tickets vary'
    },
    'Australian Museum': {
        'email': 'info@australian.museum',
        'instagram_url': 'https://www.instagram.com/australianmuseum',
        'facebook_url': 'https://www.facebook.com/AustralianMuseum',
        'twitter_url': 'https://twitter.com/austmus',
        'youtube_url': 'https://www.youtube.com/user/AustralianMuseum',
        'description': 'Australia\'s first museum, featuring natural history, cultural artifacts, and the world\'s most comprehensive collection of Australian Aboriginal cultural objects.',
        'opening_hours': 'Daily 10:00 AM - 5:00 PM',
        'admission_fee': '$18 AUD adults, $8 AUD children 5-15, family packages available'
    }
}

def enhance_all_venue_data():
    """Enhance all venues with comprehensive real-world information"""
    print("🌟 Enhancing all venues with comprehensive AI knowledge...")
    
    with app.app_context():
        try:
            updated_count = 0
            enhanced_fields_count = 0
            
            for venue_name, enhancements in VENUE_COMPREHENSIVE_DATA.items():
                venue = Venue.query.filter_by(name=venue_name).first()
                if not venue:
                    print(f"⚠️  Venue '{venue_name}' not found in database")
                    continue
                
                updated_fields = []
                
                # Update each field if missing or incomplete
                for field, value in enhancements.items():
                    if field == 'description':
                        # Update description if ours is more detailed
                        if not venue.description or len(value) > len(venue.description):
                            venue.description = value
                            updated_fields.append('description')
                    elif field == 'opening_hours':
                        # Update opening hours if missing or generic
                        if not venue.opening_hours or 'varies' in venue.opening_hours.lower():
                            venue.opening_hours = value
                            updated_fields.append('opening_hours')
                    elif field == 'admission_fee':
                        # Update admission fee if missing or generic
                        if not venue.admission_fee or venue.admission_fee in ['Free', 'Varies']:
                            venue.admission_fee = value
                            updated_fields.append('admission_fee')
                    elif field == 'email':
                        # Add email if missing
                        if not venue.email:
                            venue.email = value
                            updated_fields.append('email')
                    elif field == 'instagram_url':
                        # Add Instagram if missing
                        if not venue.instagram_url:
                            venue.instagram_url = value
                            updated_fields.append('instagram')
                    elif field == 'facebook_url':
                        # Add Facebook if missing
                        if not venue.facebook_url:
                            venue.facebook_url = value
                            updated_fields.append('facebook')
                    elif field == 'twitter_url':
                        # Add Twitter if missing
                        if not venue.twitter_url:
                            venue.twitter_url = value
                            updated_fields.append('twitter')
                    elif field == 'youtube_url':
                        # Add YouTube if missing
                        if not venue.youtube_url:
                            venue.youtube_url = value
                            updated_fields.append('youtube')
                    elif field == 'tiktok_url':
                        # Add TikTok if missing
                        if not venue.tiktok_url:
                            venue.tiktok_url = value
                            updated_fields.append('tiktok')
                
                if updated_fields:
                    updated_count += 1
                    enhanced_fields_count += len(updated_fields)
                    print(f"✅ Enhanced '{venue_name}': {', '.join(updated_fields)}")
                else:
                    print(f"ℹ️  '{venue_name}' already complete")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Venue enhancement complete!")
            print(f"📊 Enhanced {updated_count} venues")
            print(f"🔧 Added {enhanced_fields_count} data fields")
            
            # Show final statistics
            total_venues = Venue.query.count()
            with_email = Venue.query.filter(Venue.email.isnot(None)).count()
            with_instagram = Venue.query.filter(Venue.instagram_url.isnot(None)).count()
            with_facebook = Venue.query.filter(Venue.facebook_url.isnot(None)).count()
            with_detailed_hours = Venue.query.filter(
                Venue.opening_hours.isnot(None),
                ~Venue.opening_hours.contains('varies')
            ).count()
            
            print(f"\n📊 Final Data Coverage:")
            print(f"   Total venues: {total_venues}")
            print(f"   With email addresses: {with_email}")
            print(f"   With Instagram: {with_instagram}")
            print(f"   With Facebook: {with_facebook}")
            print(f"   With detailed hours: {with_detailed_hours}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error enhancing venues: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = enhance_all_venue_data()
    sys.exit(0 if success else 1)
