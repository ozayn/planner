#!/usr/bin/env python3
"""
Standardize venue types in the database for consistency
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Venue type standardization mapping
VENUE_TYPE_MAPPING = {
    # Museums (combine all museum types)
    'Museum': 'museum',
    'museum': 'museum',
    'Science Museum': 'museum',
    
    # Arts & Culture
    'Arts Center': 'arts_center',
    'Cultural Center': 'arts_center',
    'Performing Arts Center': 'arts_center',
    'Theater': 'theater',
    'Concert Hall': 'concert_hall',
    'Art District': 'arts_district',
    
    # Historic & Religious
    'Historic District': 'historic_site',
    'Historic Site': 'historic_site',
    'Historic Trail': 'historic_site',
    'Memorial': 'memorial',
    'Monument': 'monument',
    'Landmark': 'landmark',
    'Castle': 'historic_site',
    'Palace': 'historic_site',
    'Cathedral': 'religious_site',
    'Church': 'religious_site',
    'Temple': 'religious_site',
    'Shrine': 'religious_site',
    
    # Government & Civic
    'Government Building': 'government',
    'Library': 'library',
    
    # Parks & Recreation
    'Park': 'park',
    'Botanical Garden': 'garden',
    'Zoo': 'zoo',
    'Aquarium': 'aquarium',
    'Beach': 'beach',
    
    # Observation & Views
    'Observation Deck': 'observation',
    'Observation Tower': 'observation',
    'Observatory': 'observation',
    
    # Shopping & Commercial
    'Market': 'market',
    'Shopping': 'shopping',
    'Shopping District': 'shopping',
    
    # Transportation & Infrastructure
    'Bridge': 'landmark',
    'Avenue': 'landmark',
    'Waterfront': 'waterfront',
    'Waterway': 'waterfront',
    'Stadium': 'stadium'
}

def standardize_venue_types():
    """Standardize all venue types in the database"""
    print("🔄 Starting venue type standardization...")
    
    with app.app_context():
        try:
            # Get all venues
            venues = Venue.query.all()
            print(f"📊 Found {len(venues)} venues to process")
            
            updated_count = 0
            type_changes = {}
            
            for venue in venues:
                old_type = venue.venue_type
                if old_type in VENUE_TYPE_MAPPING:
                    new_type = VENUE_TYPE_MAPPING[old_type]
                    if old_type != new_type:
                        venue.venue_type = new_type
                        updated_count += 1
                        
                        # Track changes for reporting
                        if old_type not in type_changes:
                            type_changes[old_type] = []
                        type_changes[old_type].append(venue.name)
                        
                        print(f"  Updated '{venue.name}': {old_type} → {new_type}")
                else:
                    print(f"⚠️  Unknown venue type '{old_type}' for venue '{venue.name}'")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n✅ Standardization complete!")
            print(f"📊 Updated {updated_count} venues")
            
            # Show summary of changes
            if type_changes:
                print("\n📋 Summary of changes:")
                for old_type, venues in type_changes.items():
                    new_type = VENUE_TYPE_MAPPING[old_type]
                    print(f"  {old_type} → {new_type}: {len(venues)} venues")
            
            # Show final venue type distribution
            print("\n📊 Final venue type distribution:")
            final_types = {}
            for venue in Venue.query.all():
                vtype = venue.venue_type
                final_types[vtype] = final_types.get(vtype, 0) + 1
            
            for vtype, count in sorted(final_types.items()):
                print(f"  {vtype}: {count}")
                
            return True
            
        except Exception as e:
            print(f"❌ Error during standardization: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = standardize_venue_types()
    sys.exit(0 if success else 1)
