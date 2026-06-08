#!/usr/bin/env python3
"""
Refresh a venue's image by fetching a new photo reference from Google Places API.
Use when an image shows "Image unavailable" due to an expired photo reference.

Usage:
  python scripts/refresh_venue_image.py "National Portrait Gallery"
  python scripts/refresh_venue_image.py "National Portrait Gallery" --city "Washington"
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue
from scripts.utils import get_google_maps_photo_reference


def refresh_venue_image(venue_name: str, city: str = None) -> bool:
    """Refresh image for a venue by name. Returns True if updated."""
    with app.app_context():
        venue = Venue.query.filter(Venue.name.ilike(venue_name)).first()
        if not venue:
            print(f"❌ Venue not found: {venue_name}")
            return False

        # Get city for search if not provided
        search_city = city or (venue.city.name if venue.city else "Washington")
        search_state = "DC" if "washington" in search_city.lower() else ""

        print(f"🔄 Refreshing image for: {venue.name} (ID: {venue.id})")
        print(f"   Searching: {venue_name}, {search_city}")

        photo_ref = get_google_maps_photo_reference(
            venue_name, city=search_city, state=search_state, country="USA"
        )

        if not photo_ref:
            print(f"❌ Could not fetch new photo reference for {venue_name}")
            return False

        venue.image_url = photo_ref
        db.session.commit()
        print(f"✅ Updated {venue.name} with fresh photo reference")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh venue image (expired photo reference)")
    parser.add_argument("venue_name", help="Venue name (e.g. 'National Portrait Gallery')")
    parser.add_argument("--city", default=None, help="City for Places API search")
    args = parser.parse_args()

    success = refresh_venue_image(args.venue_name, args.city)
    sys.exit(0 if success else 1)
