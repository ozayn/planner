#!/usr/bin/env python3
"""
Update Mexican Cultural Institute source URL to correct events path
"""

import sys
sys.path.append('.')

from app import app, db
from app import Source

EVENTS_URL = 'https://instituteofmexicodc.org/index.php/events/'

def update_source():
    with app.app_context():
        source = Source.query.filter_by(name='Mexican Cultural Institute').first()
        if not source:
            print("❌ Mexican Cultural Institute source not found")
            return False
        if source.url == EVENTS_URL:
            print(f"⚠️  URL already correct: {EVENTS_URL}")
            return True
        old_url = source.url
        source.url = EVENTS_URL
        db.session.commit()
        print(f"✅ Updated source URL")
        print(f"   Old: {old_url}")
        print(f"   New: {EVENTS_URL}")
        try:
            from scripts.update_sources_json import update_sources_json
            update_sources_json()
        except Exception as e:
            print(f"⚠️  Could not update sources.json: {e}")
        return True

if __name__ == '__main__':
    success = update_source()
    sys.exit(0 if success else 1)
