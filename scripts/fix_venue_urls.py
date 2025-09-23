#!/usr/bin/env python3
"""
Fix Venue URLs

This script updates venue URLs with correct, working URLs for major DC venues.
"""

import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import app, db, Venue

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Correct venue URLs mapping
CORRECT_URLS = {
    'Arena Stage': 'https://www.arenastage.org',
    'Capitol Building': 'https://www.visitthecapitol.gov',
    'Capitol Hill': 'https://www.capitolhill.org',
    'Capitol Hill Arts Workshop': 'https://www.chaw.org',
    'Dupont Circle': 'https://www.dupontcircle.org',
    'Ford\'s Theatre': 'https://www.fords.org',
    'Franklin Delano Roosevelt Memorial': 'https://www.nps.gov/frde/index.htm',
    'Georgetown': 'https://www.georgetown.org',
    'International Spy Museum': 'https://www.spymuseum.org',
    'Jefferson Memorial': 'https://www.nps.gov/thje/index.htm',
    'Kennedy Center': 'https://www.kennedy-center.org',
    'Library of Congress': 'https://www.loc.gov',
    'Lincoln Memorial': 'https://www.nps.gov/linc/index.htm',
    'National Air and Space Museum': 'https://airandspace.si.edu',
    'National Archives': 'https://www.archives.gov',
    'National Gallery of Art': 'https://www.nga.gov',
    'National Mall': 'https://www.nps.gov/nama/index.htm',
    'National Museum of American History': 'https://americanhistory.si.edu',
    'National Museum of Natural History': 'https://naturalhistory.si.edu',
    'National Portrait Gallery': 'https://www.npg.si.edu',
    'National Zoo': 'https://nationalzoo.si.edu',
    'Pentagon': 'https://pentagontours.osd.mil',
    'Smithsonian Institution': 'https://www.si.edu',
    'Supreme Court': 'https://www.supremecourt.gov',
    'Union Station': 'https://www.unionstationdc.com',
    'Washington Monument': 'https://www.nps.gov/wamo/index.htm',
    'White House': 'https://www.whitehouse.gov',
    'World War II Memorial': 'https://www.nps.gov/wwii/index.htm',
}

def fix_venue_urls():
    """Fix venue URLs with correct ones"""
    try:
        with app.app_context():
            updated_count = 0
            
            for venue_name, correct_url in CORRECT_URLS.items():
                venue = Venue.query.filter_by(name=venue_name).first()
                if venue:
                    old_url = venue.website_url
                    venue.website_url = correct_url
                    logger.info(f"Updated {venue_name}: {old_url} -> {correct_url}")
                    updated_count += 1
                else:
                    logger.warning(f"Venue not found: {venue_name}")
            
            # Commit changes
            db.session.commit()
            logger.info(f"✅ Updated {updated_count} venue URLs")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error fixing venue URLs: {e}")
        db.session.rollback()
        return False

def main():
    """Main function"""
    success = fix_venue_urls()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
