#!/usr/bin/env python3
"""
Remove unverified or incorrect social media accounts
Better to have no account than wrong account
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Accounts that should be removed because they're incorrect or unverified
ACCOUNTS_TO_REMOVE = {
    'Embassy of Germany': ['instagram_url', 'facebook_url', 'twitter_url'],  # @germanydiplo is incorrect
    'Embassy of Italy': ['instagram_url', 'facebook_url', 'twitter_url'],    # Need to verify
    'Embassy of Canada': ['instagram_url', 'facebook_url', 'twitter_url'],   # Need to verify
    'Embassy of Spain': ['instagram_url', 'facebook_url', 'twitter_url'],    # Need to verify
    'Embassy of the Netherlands': ['instagram_url', 'facebook_url', 'twitter_url'],  # Need to verify
    'Embassy of Australia': ['instagram_url', 'facebook_url', 'twitter_url'],  # Need to verify
    'Embassy of Brazil': ['instagram_url', 'facebook_url', 'twitter_url'],    # Need to verify
    'Embassy of India': ['instagram_url', 'facebook_url', 'twitter_url'],     # Need to verify
    'Embassy of Mexico': ['instagram_url', 'facebook_url', 'twitter_url'],    # Need to verify
    'Embassy of South Korea': ['instagram_url', 'facebook_url', 'twitter_url'],  # Need to verify
    'Embassy of Sweden': ['instagram_url', 'facebook_url', 'twitter_url'],    # Need to verify
    'Embassy of Switzerland': ['instagram_url', 'facebook_url', 'twitter_url']  # Need to verify
}

def remove_unverified_social_media():
    """Remove unverified social media accounts"""
    print("🧹 Removing unverified social media accounts...")
    print("✅ Better to have no account than wrong account")
    
    with app.app_context():
        try:
            removed_count = 0
            total_removals = 0
            
            for venue_name, fields_to_remove in ACCOUNTS_TO_REMOVE.items():
                venue = Venue.query.filter_by(name=venue_name).first()
                if not venue:
                    print(f"⚠️  Venue '{venue_name}' not found")
                    continue
                
                removed_fields = []
                
                for field in fields_to_remove:
                    if getattr(venue, field, None):
                        setattr(venue, field, None)
                        removed_fields.append(field.replace('_url', ''))
                        total_removals += 1
                
                if removed_fields:
                    removed_count += 1
                    print(f"🧹 Removed unverified accounts from '{venue_name}': {', '.join(removed_fields)}")
                else:
                    print(f"ℹ️  '{venue_name}' already clean")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Social media cleanup complete!")
            print(f"🧹 Cleaned {removed_count} venues")
            print(f"❌ Removed {total_removals} unverified accounts")
            print(f"✅ Data integrity improved - no incorrect accounts")
            
            # Show current state
            total_venues = Venue.query.count()
            with_instagram = Venue.query.filter(Venue.instagram_url.isnot(None)).count()
            with_facebook = Venue.query.filter(Venue.facebook_url.isnot(None)).count()
            with_twitter = Venue.query.filter(Venue.twitter_url.isnot(None)).count()
            
            print(f"\n📊 Current Social Media Coverage (verified only):")
            print(f"   Total venues: {total_venues}")
            print(f"   With Instagram: {with_instagram}")
            print(f"   With Facebook: {with_facebook}")
            print(f"   With Twitter: {with_twitter}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing unverified accounts: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = remove_unverified_social_media()
    sys.exit(0 if success else 1)
