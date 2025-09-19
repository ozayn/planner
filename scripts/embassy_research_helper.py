#!/usr/bin/env python3
"""
Embassy Research Helper
Provides a systematic way to research and verify embassy social media accounts
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Embassy research data with official websites for manual verification
EMBASSY_RESEARCH_DATA = {
    'Embassy of Germany': {
        'official_website': 'https://washington.diplo.de/',
        'research_notes': 'Check their website for official social media links',
        'suggested_search': 'site:washington.diplo.de social media OR Twitter OR Instagram',
        'likely_handles': ['@germanyinusa', '@germanembassy', '@diplogermany'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Italy': {
        'official_website': 'https://ambwashingtondc.esteri.it/',
        'research_notes': 'Italian Ministry of Foreign Affairs website',
        'suggested_search': 'site:ambwashingtondc.esteri.it social media',
        'likely_handles': ['@italyindc', '@ambitaliausa', '@italyembassy'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Canada': {
        'official_website': 'https://www.canadainternational.gc.ca/washington/',
        'research_notes': 'Canadian government official site',
        'suggested_search': '@canadainusa OR @canadaembassy verified',
        'likely_handles': ['@canadainusa', '@canadaembassy'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Spain': {
        'official_website': 'http://www.exteriores.gob.es/embajadas/washington/',
        'research_notes': 'Spanish Ministry of Foreign Affairs',
        'suggested_search': '@spainusa OR @embespusa verified',
        'likely_handles': ['@spainusa', '@embespusa', '@spainembassy'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Japan': {
        'official_website': 'https://www.us.emb-japan.go.jp/',
        'research_notes': 'Already has some social media - verify completeness',
        'suggested_search': '@japanembdc OR @japanusa verified',
        'likely_handles': ['@japanembdc', '@japanusa'],
        'status': 'PARTIALLY_COMPLETE'
    },
    'Embassy of the Netherlands': {
        'official_website': 'https://www.netherlandsworldwide.nl/countries/united-states',
        'research_notes': 'Dutch government official site',
        'suggested_search': '@nlembassy OR @netherlandsusa verified',
        'likely_handles': ['@nlembassy', '@netherlandsusa'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Australia': {
        'official_website': 'https://usa.embassy.gov.au/',
        'research_notes': 'Australian government official site',
        'suggested_search': '@ausembassyusa OR @australiausa verified',
        'likely_handles': ['@ausembassyusa', '@australiausa'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Brazil': {
        'official_website': 'http://washington.itamaraty.gov.br/',
        'research_notes': 'Brazilian Ministry of Foreign Affairs',
        'suggested_search': '@brazilinusa OR @brazilembassy verified',
        'likely_handles': ['@brazilinusa', '@brazilembassy'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of India': {
        'official_website': 'https://www.indianembassyusa.gov.in/',
        'research_notes': 'Indian government official site',
        'suggested_search': '@indianembassyusa OR @indiainusa verified',
        'likely_handles': ['@indianembassyusa', '@indiainusa'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Mexico': {
        'official_website': 'https://embamex.sre.gob.mx/eua/',
        'research_notes': 'Mexican Ministry of Foreign Affairs',
        'suggested_search': '@mexicoembusa OR @mexicoinusa verified',
        'likely_handles': ['@mexicoembusa', '@mexicoinusa'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of South Korea': {
        'official_website': 'http://overseas.mofa.go.kr/us-washington-en/',
        'research_notes': 'Korean Ministry of Foreign Affairs',
        'suggested_search': '@koreanembassyusa OR @koreainusa verified',
        'likely_handles': ['@koreanembassyusa', '@koreainusa'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Sweden': {
        'official_website': 'https://www.swedenabroad.se/washington/',
        'research_notes': 'Swedish government official site',
        'suggested_search': '@swedenusa OR @swedenembassy verified',
        'likely_handles': ['@swedenusa', '@swedenembassy'],
        'status': 'NEEDS_VERIFICATION'
    },
    'Embassy of Switzerland': {
        'official_website': 'https://www.eda.admin.ch/washington',
        'research_notes': 'Swiss Federal Department of Foreign Affairs - known to have social media',
        'suggested_search': '@swissembassyusa verified',
        'likely_handles': ['@swissembassyusa', '@switzerlandusa'],
        'status': 'NEEDS_VERIFICATION'
    }
}

def generate_research_plan():
    """Generate a research plan for verifying embassy social media"""
    print("🔍 EMBASSY SOCIAL MEDIA RESEARCH PLAN")
    print("=" * 60)
    print("📋 Manual verification required for data accuracy")
    print()
    
    with app.app_context():
        embassies = Venue.query.filter_by(venue_type='embassy').all()
        
        for embassy in embassies:
            embassy_name = embassy.name
            if embassy_name in EMBASSY_RESEARCH_DATA:
                data = EMBASSY_RESEARCH_DATA[embassy_name]
                
                print(f"🏛️  {embassy_name}")
                print(f"   Website: {data['official_website']}")
                print(f"   Search: {data['suggested_search']}")
                print(f"   Likely handles: {', '.join(data['likely_handles'])}")
                print(f"   Status: {data['status']}")
                
                # Show current status
                current_social = []
                if embassy.instagram_url:
                    current_social.append(f"Instagram: {embassy.instagram_url}")
                if embassy.facebook_url:
                    current_social.append(f"Facebook: {embassy.facebook_url}")
                if embassy.twitter_url:
                    current_social.append(f"Twitter: {embassy.twitter_url}")
                
                if current_social:
                    print(f"   Current: {', '.join(current_social)}")
                else:
                    print(f"   Current: No social media accounts")
                
                print()
        
        print("📋 RESEARCH INSTRUCTIONS:")
        print("1. Visit each embassy's official website")
        print("2. Look for 'Social Media', 'Follow Us', or 'Connect' sections")
        print("3. Verify accounts have blue checkmarks when possible")
        print("4. Check recent posts to ensure account is active and official")
        print("5. Use admin interface to add verified accounts only")
        print()
        print("⚠️  IMPORTANT: Only add accounts you can verify are 100% official!")

def main():
    """Generate embassy research plan"""
    generate_research_plan()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Use the research plan above to manually verify each embassy")
    print("2. Visit official embassy websites to find social media links")
    print("3. Add verified accounts through admin interface")
    print("4. Update this script with verified accounts as you find them")
    print()
    print("📍 Remember: Data accuracy > Data completeness")

if __name__ == '__main__':
    main()
