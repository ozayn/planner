#!/usr/bin/env python3
"""
Restore venue social media data from backup
"""

import os
import sys
import json
sys.path.append('.')

from app import app, db, Venue

def restore_social_media_from_backup():
    """Restore social media data from the backup file"""
    print("🔄 Restoring venue social media data from backup...")
    
    backup_file = 'data/backups/venues.json.backup.20250918_184808'
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    try:
        # Load backup data
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        total_venues_in_backup = sum(len(city_data.get('venues', [])) for city_data in backup_data.values() if isinstance(city_data, dict))
        print(f"📊 Loaded backup with {total_venues_in_backup} venues across {len(backup_data)} cities")
        
        with app.app_context():
            updated_count = 0
            
            # Process each city in the backup
            for city_id, city_data in backup_data.items():
                if not isinstance(city_data, dict) or 'venues' not in city_data:
                    continue
                
                # Process each venue in the city
                for venue_data in city_data['venues']:
                    venue_name = venue_data.get('name')
                    if not venue_name:
                        continue
                    
                    # Find the venue in the current database
                    venue = Venue.query.filter_by(name=venue_name).first()
                    if not venue:
                        print(f"⚠️  Venue '{venue_name}' not found in current database")
                        continue
                    
                    # Restore social media fields
                    updated_fields = []
                    
                    if venue_data.get('instagram_url') and not venue.instagram_url:
                        instagram_url = venue_data['instagram_url']
                        # Convert @handle to full URL if needed
                        if instagram_url.startswith('@'):
                            instagram_url = f"https://www.instagram.com/{instagram_url[1:]}"
                        venue.instagram_url = instagram_url
                        updated_fields.append('Instagram')
                    
                    if venue_data.get('facebook_url') and not venue.facebook_url:
                        venue.facebook_url = venue_data['facebook_url']
                        updated_fields.append('Facebook')
                    
                    if venue_data.get('twitter_url') and not venue.twitter_url:
                        twitter_url = venue_data['twitter_url']
                        # Convert @handle to full URL if needed
                        if twitter_url.startswith('@'):
                            twitter_url = f"https://twitter.com/{twitter_url[1:]}"
                        venue.twitter_url = twitter_url
                        updated_fields.append('Twitter')
                    
                    if venue_data.get('youtube_url') and not venue.youtube_url:
                        venue.youtube_url = venue_data['youtube_url']
                        updated_fields.append('YouTube')
                    
                    if venue_data.get('tiktok_url') and not venue.tiktok_url:
                        venue.tiktok_url = venue_data['tiktok_url']
                        updated_fields.append('TikTok')
                    
                    # Restore other fields if they're missing
                    if venue_data.get('email') and not venue.email:
                        venue.email = venue_data['email']
                        updated_fields.append('Email')
                    
                    if venue_data.get('website_url') and not venue.website_url:
                        venue.website_url = venue_data['website_url']
                        updated_fields.append('Website')
                    
                    # Update description if the backup has a longer one
                    if venue_data.get('description'):
                        if not venue.description or len(venue_data['description']) > len(venue.description):
                            venue.description = venue_data['description']
                            updated_fields.append('Description')
                    
                    if updated_fields:
                        updated_count += 1
                        print(f"✅ Restored '{venue_name}': {', '.join(updated_fields)}")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Social media restoration complete!")
            print(f"📊 Restored data for {updated_count} venues")
            
            # Verify restoration
            total_venues = Venue.query.count()
            with_instagram = Venue.query.filter(Venue.instagram_url.isnot(None)).count()
            with_facebook = Venue.query.filter(Venue.facebook_url.isnot(None)).count()
            with_twitter = Venue.query.filter(Venue.twitter_url.isnot(None)).count()
            
            print(f"\n📊 Final Social Media Coverage:")
            print(f"   Total venues: {total_venues}")
            print(f"   With Instagram: {with_instagram}")
            print(f"   With Facebook: {with_facebook}")
            print(f"   With Twitter: {with_twitter}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error restoring social media data: {e}")
        if 'app' in locals():
            db.session.rollback()
        return False

if __name__ == '__main__':
    success = restore_social_media_from_backup()
    sys.exit(0 if success else 1)
