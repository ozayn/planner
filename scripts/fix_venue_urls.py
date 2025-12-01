#!/usr/bin/env python3
"""
Fix venue URLs with real, working URLs for Washington DC venues
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue

def fix_venue_urls():
    """Fix venue URLs with real, working URLs"""
    
    with app.app_context():
        # Real URLs for Washington DC venues
        venue_url_fixes = {
            # Museums and Cultural Sites
            'Arena Stage': 'https://www.arenastage.org',
            'Capitol Building': 'https://www.visitthecapitol.gov',
            'Capitol Hill': 'https://www.visitthecapitol.gov',
            'Capitol Hill Arts Workshop': 'https://www.chaw.org',
            'Dupont Circle': 'https://www.nps.gov/rocr/planyourvisit/dupont-circle.htm',
            "Ford's Theatre": 'https://www.fords.org',
            'Franklin Delano Roosevelt Memorial': 'https://www.nps.gov/frde/index.htm',
            'Georgetown': 'https://www.georgetown.org',
            'International Spy Museum': 'https://www.spymuseum.org',
            'Jefferson Memorial': 'https://www.nps.gov/thje/index.htm',
            'Lincoln Memorial': 'https://www.nps.gov/linc/index.htm',
            'Martin Luther King Jr. Memorial': 'https://www.nps.gov/mlkm/index.htm',
            'National Air and Space Museum': 'https://airandspace.si.edu',
            'National Gallery of Art': 'https://www.nga.gov',
            'National Mall': 'https://www.nps.gov/nama/index.htm',
            'National Portrait Gallery': 'https://npg.si.edu',
            'National Zoo': 'https://nationalzoo.si.edu',
            'Rock Creek Park': 'https://www.nps.gov/rocr/index.htm',
            'Smithsonian Arthur M. Sackler Gallery': 'https://www.asia.si.edu',
            'Smithsonian Freer Gallery of Art': 'https://www.asia.si.edu',
            'Smithsonian Hirshhorn Museum and Sculpture Garden': 'https://hirshhorn.si.edu',
            'Smithsonian National Air and Space Museum': 'https://airandspace.si.edu',
            'Smithsonian National Museum of African American History and Culture': 'https://nmaahc.si.edu',
            'Smithsonian National Museum of American History': 'https://americanhistory.si.edu',
            'Smithsonian National Museum of Natural History': 'https://naturalhistory.si.edu',
            'Smithsonian National Museum of the American Indian': 'https://americanindian.si.edu',
            'Supreme Court': 'https://www.supremecourt.gov',
            'United States Botanic Garden': 'https://www.usbg.gov',
            'Vietnam Veterans Memorial': 'https://www.nps.gov/vive/index.htm',
            'Washington Monument': 'https://www.nps.gov/wamo/index.htm',
            'White House': 'https://www.whitehouse.gov',
            'World War II Memorial': 'https://www.nps.gov/wwii/index.htm',
            
            # Entertainment Venues
            '9:30 Club': 'https://www.930.com',
            'Suns Cinema': 'https://www.sunscinema.com',
            
            # Embassies (real embassy URLs)
            'Embassy of the United Kingdom': 'https://www.gov.uk/world/organisations/british-embassy-washington',
            'Embassy of France': 'https://franceintheus.org',
            'Embassy of Germany': 'https://washington.diplo.de',
            'Embassy of Italy': 'https://ambwashingtondc.esteri.it',
            'Embassy of Japan': 'https://www.us.emb-japan.go.jp',
            'Embassy of Canada': 'https://www.canadainternational.gc.ca/washington',
            'Embassy of Spain': 'https://www.exteriores.gob.es/embajadas/washington',
            'Embassy of the Netherlands': 'https://www.netherlandsworldwide.nl/countries/united-states',
            'Embassy of Australia': 'https://usa.embassy.gov.au',
            'Embassy of Brazil': 'https://washington.itamaraty.gov.br',
            'Embassy of India': 'https://www.indianembassyusa.gov.in',
            'Embassy of Mexico': 'https://embamex.sre.gob.mx/eua',
            'Embassy of South Korea': 'https://usa-mofa.go.kr/us-washington-en',
            'Embassy of Sweden': 'https://www.swedenabroad.se/en/embassies/usa-washington',
            'Embassy of Switzerland': 'https://www.eda.admin.ch/washington'
        }
        
        venues_updated = 0
        
        for venue_name, correct_url in venue_url_fixes.items():
            venue = Venue.query.filter_by(name=venue_name, city_id=1).first()
            if venue:
                old_url = venue.website_url
                venue.website_url = correct_url
                db.session.commit()
                print(f"✅ Updated {venue_name}")
                print(f"   Old: {old_url}")
                print(f"   New: {correct_url}")
                venues_updated += 1
            else:
                print(f"⚠️ Venue '{venue_name}' not found in database")
        
        print(f"\n🎉 Successfully updated {venues_updated} venue URLs!")
        return True

def main():
    """Main function"""
    success = fix_venue_urls()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)