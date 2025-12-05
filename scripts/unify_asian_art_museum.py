#!/usr/bin/env python3
"""
Unify Smithsonian Arthur M. Sackler Gallery and Freer Gallery of Art
into Smithsonian National Museum of Asian Art
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Event, Venue

def unify_venues():
    """Unify venues 23 and 24 into a single venue"""
    with app.app_context():
        venue_23 = Venue.query.get(23)
        venue_24 = Venue.query.get(24)
        
        if not venue_23 or not venue_24:
            print("❌ One or both venues not found")
            return
        
        print(f"Before unification:")
        print(f"  Venue 23: {venue_23.name}")
        print(f"  Venue 24: {venue_24.name}")
        
        # Check events
        events_23 = Event.query.filter_by(venue_id=23).count()
        events_24 = Event.query.filter_by(venue_id=24).count()
        print(f"\nEvents associated:")
        print(f"  Venue 23: {events_23} events")
        print(f"  Venue 24: {events_24} events")
        
        # Merge venue 24's events to venue 23
        if events_24 > 0:
            Event.query.filter_by(venue_id=24).update({Event.venue_id: 23})
            print(f"  ✅ Migrated {events_24} events from venue 24 to venue 23")
        
        # Update venue 23 with unified name and best information
        venue_23.name = "Smithsonian National Museum of Asian Art"
        
        # Merge addresses - use the more complete one or combine
        # Both addresses are valid (different entrances), but we'll keep the main one
        if len(venue_23.address or "") < len(venue_24.address or ""):
            venue_23.address = venue_24.address
        
        # Merge social media - combine unique values
        if venue_24.instagram_url and venue_24.instagram_url != venue_23.instagram_url:
            # Keep the more general one or combine
            if 'freergallery' in venue_24.instagram_url:
                venue_23.instagram_url = venue_24.instagram_url  # Freer is the main account
        
        if venue_24.twitter_url and venue_24.twitter_url != venue_23.twitter_url:
            if 'FreerGallery' in venue_24.twitter_url:
                venue_23.twitter_url = venue_24.twitter_url
        
        # Facebook is already shared
        # Keep venue 23's data as primary
        
        # Delete venue 24
        db.session.delete(venue_24)
        db.session.commit()
        
        print(f"\n✅ Unified into:")
        print(f"  Venue 23: {venue_23.name}")
        print(f"  Address: {venue_23.address}")
        print(f"  Website: {venue_23.website_url}")
        print(f"  Instagram: {venue_23.instagram_url}")
        print(f"  Twitter: {venue_23.twitter_url}")
        print(f"\n✅ Deleted duplicate venue 24")
        print(f"✅ All changes committed to database")

if __name__ == '__main__':
    unify_venues()
