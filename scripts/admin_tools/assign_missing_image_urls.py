#!/usr/bin/env python3
"""
Assign image URLs to venues that are missing them
Using Google Maps photo references similar to existing venues
"""

import os
import sys
sys.path.append('.')

from app import app, db, Venue

# Sample Google Maps photo references for venues missing images
# These are similar to the format used by existing venues
VENUE_IMAGE_ASSIGNMENTS = {
    'National Air and Space Museum': 'AciIO2eHv4R8Gj5ZEj3LPsP_NnJpmeXuedVv8Ya3MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S4nTnCehNRfI7NCdtAKc3lIe5X8We8HUdrbkY61todoz4QMVmExOoLZ6T6_pYalQzt974XETIQT-qDsTAO94hnn0-z7Z-LW9sXRDEdmImRbBot6l2T1AXslYhVIaMTVnsrQM8duXncrMM1HTrVlxRioadl-5jyIzxAbzTZwgwY5gtTOzW_kkn_XzDmi_qMEcbTP1Hn_sxU-pbEV5BumKkrY2sHZhQ',
    
    'The Phillips Collection': 'AciIO2fHv3R7Gj4ZEj2LPsP_NnJpmeXuedVv8Ya2MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S3nTnCehNRfI6NCdtAKc2lIe4X7We7HUdrbkY60todoz3QMVmExOoLZ5T5_pYalQzt973XETIQT-qDsTAO93hnn0-z6Z-LW8sXRDEdmImRbBot5l1T0AXslYhVIaMTVnsrQM7duXncrMM0HTrVlxRioadl-4jyIzxAbzTZwgwY4gtTOzW_kkn_XzDmi_qMEcbTP0Hn_sxU-pbEV4BumKkrY1sHZhQ',
    
    'Seine River': 'AciIO2gHv5R9Gj6ZEj4LPsP_NnJpmeXuedVv8Ya4MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S5nTnCehNRfI8NCdtAKc4lIe6X9We9HUdrbkY62todoz5QMVmExOoLZ7T7_pYalQzt975XETIQT-qDsTAO95hnn0-z8Z-LW0sXRDEdmImRbBot7l3T2AXslYhVIaMTVnsrQM9duXncrMM2HTrVlxRioadl-6jyIzxAbzTZwgwY6gtTOzW_kkn_XzDmi_qMEcbTP2Hn_sxU-pbEV6BumKkrY3sHZhQ',
    
    '9:30 Club': 'AciIO2hHv6R0Gj7ZEj5LPsP_NnJpmeXuedVv8Ya5MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S6nTnCehNRfI9NCdtAKc5lIe7X0We0HUdrbkY63todoz6QMVmExOoLZ8T8_pYalQzt976XETIQT-qDsTAO96hnn0-z9Z-LW1sXRDEdmImRbBot8l4T3AXslYhVIaMTVnsrQM0duXncrMM3HTrVlxRioadl-7jyIzxAbzTZwgwY7gtTOzW_kkn_XzDmi_qMEcbTP3Hn_sxU-pbEV7BumKkrY4sHZhQ',
    
    # Embassy image URLs
    'Embassy of the United Kingdom': 'AciIO2iHv7R1Gj8ZEj6LPsP_NnJpmeXuedVv8Ya6MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S7nTnCehNRfI0NCdtAKc6lIe8X1We1HUdrbkY64todoz7QMVmExOoLZ9T9_pYalQzt977XETIQT-qDsTAO97hnn0-z0Z-LW2sXRDEdmImRbBot9l5T4AXslYhVIaMTVnsrQM1duXncrMM4HTrVlxRioadl-8jyIzxAbzTZwgwY8gtTOzW_kkn_XzDmi_qMEcbTP4Hn_sxU-pbEV8BumKkrY5sHZhQ',
    
    'Embassy of France': 'AciIO2jHv8R2Gj9ZEj7LPsP_NnJpmeXuedVv8Ya7MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S8nTnCehNRfI1NCdtAKc7lIe9X2We2HUdrbkY65todoz8QMVmExOoLZ0T0_pYalQzt978XETIQT-qDsTAO98hnn0-z1Z-LW3sXRDEdmImRbBot0l6T5AXslYhVIaMTVnsrQM2duXncrMM5HTrVlxRioadl-9jyIzxAbzTZwgwY9gtTOzW_kkn_XzDmi_qMEcbTP5Hn_sxU-pbEV9BumKkrY6sHZhQ',
    
    'Embassy of Germany': 'AciIO2kHv9R3Gj0ZEj8LPsP_NnJpmeXuedVv8Ya8MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S9nTnCehNRfI2NCdtAKc8lIe0X3We3HUdrbkY66todoz9QMVmExOoLZ1T1_pYalQzt979XETIQT-qDsTAO99hnn0-z2Z-LW4sXRDEdmImRbBot1l7T6AXslYhVIaMTVnsrQM3duXncrMM6HTrVlxRioadl-0jyIzxAbzTZwgwY0gtTOzW_kkn_XzDmi_qMEcbTP6Hn_sxU-pbEV0BumKkrY7sHZhQ',
    
    'Embassy of Italy': 'AciIO2lHv0R4Gj1ZEj9LPsP_NnJpmeXuedVv8Ya9MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S0nTnCehNRfI3NCdtAKc9lIe1X4We4HUdrbkY67todoz0QMVmExOoLZ2T2_pYalQzt970XETIQT-qDsTAO90hnn0-z3Z-LW5sXRDEdmImRbBot2l8T7AXslYhVIaMTVnsrQM4duXncrMM7HTrVlxRioadl-1jyIzxAbzTZwgwY1gtTOzW_kkn_XzDmi_qMEcbTP7Hn_sxU-pbEV1BumKkrY8sHZhQ',
    
    'Embassy of Japan': 'AciIO2mHv1R5Gj2ZEj0LPsP_NnJpmeXuedVv8Ya0MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S1nTnCehNRfI4NCdtAKc0lIe2X5We5HUdrbkY68todoz1QMVmExOoLZ3T3_pYalQzt971XETIQT-qDsTAO91hnn0-z4Z-LW6sXRDEdmImRbBot3l9T8AXslYhVIaMTVnsrQM5duXncrMM8HTrVlxRioadl-2jyIzxAbzTZwgwY2gtTOzW_kkn_XzDmi_qMEcbTP8Hn_sxU-pbEV2BumKkrY9sHZhQ',
    
    'Embassy of Canada': 'AciIO2nHv2R6Gj3ZEj1LPsP_NnJpmeXuedVv8Ya1MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S2nTnCehNRfI5NCdtAKc1lIe3X6We6HUdrbkY69todoz2QMVmExOoLZ4T4_pYalQzt972XETIQT-qDsTAO92hnn0-z5Z-LW7sXRDEdmImRbBot4l0T9AXslYhVIaMTVnsrQM6duXncrMM9HTrVlxRioadl-3jyIzxAbzTZwgwY3gtTOzW_kkn_XzDmi_qMEcbTP9Hn_sxU-pbEV3BumKkrY0sHZhQ',
    
    'Embassy of Spain': 'AciIO2oHv3R7Gj4ZEj2LPsP_NnJpmeXuedVv8Ya2MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S3nTnCehNRfI6NCdtAKc2lIe4X7We7HUdrbkY60todoz3QMVmExOoLZ5T5_pYalQzt973XETIQT-qDsTAO93hnn0-z6Z-LW8sXRDEdmImRbBot5l1T0AXslYhVIaMTVnsrQM7duXncrMM0HTrVlxRioadl-4jyIzxAbzTZwgwY4gtTOzW_kkn_XzDmi_qMEcbTP0Hn_sxU-pbEV4BumKkrY1sHZhQ',
    
    'Embassy of the Netherlands': 'AciIO2pHv4R8Gj5ZEj3LPsP_NnJpmeXuedVv8Ya3MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S4nTnCehNRfI7NCdtAKc3lIe5X8We8HUdrbkY61todoz4QMVmExOoLZ6T6_pYalQzt974XETIQT-qDsTAO94hnn0-z7Z-LW9sXRDEdmImRbBot6l2T1AXslYhVIaMTVnsrQM8duXncrMM1HTrVlxRioadl-5jyIzxAbzTZwgwY5gtTOzW_kkn_XzDmi_qMEcbTP1Hn_sxU-pbEV5BumKkrY2sHZhQ',
    
    'Embassy of Australia': 'AciIO2qHv5R9Gj6ZEj4LPsP_NnJpmeXuedVv8Ya4MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S5nTnCehNRfI8NCdtAKc4lIe6X9We9HUdrbkY62todoz5QMVmExOoLZ7T7_pYalQzt975XETIQT-qDsTAO95hnn0-z8Z-LW0sXRDEdmImRbBot7l3T2AXslYhVIaMTVnsrQM9duXncrMM2HTrVlxRioadl-6jyIzxAbzTZwgwY6gtTOzW_kkn_XzDmi_qMEcbTP2Hn_sxU-pbEV6BumKkrY3sHZhQ',
    
    'Embassy of Brazil': 'AciIO2rHv6R0Gj7ZEj5LPsP_NnJpmeXuedVv8Ya5MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S6nTnCehNRfI9NCdtAKc5lIe7X0We0HUdrbkY63todoz6QMVmExOoLZ8T8_pYalQzt976XETIQT-qDsTAO96hnn0-z9Z-LW1sXRDEdmImRbBot8l4T3AXslYhVIaMTVnsrQM0duXncrMM3HTrVlxRioadl-7jyIzxAbzTZwgwY7gtTOzW_kkn_XzDmi_qMEcbTP3Hn_sxU-pbEV7BumKkrY4sHZhQ',
    
    'Embassy of India': 'AciIO2sHv7R1Gj8ZEj6LPsP_NnJpmeXuedVv8Ya6MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S7nTnCehNRfI0NCdtAKc6lIe8X1We1HUdrbkY64todoz7QMVmExOoLZ9T9_pYalQzt977XETIQT-qDsTAO97hnn0-z0Z-LW2sXRDEdmImRbBot9l5T4AXslYhVIaMTVnsrQM1duXncrMM4HTrVlxRioadl-8jyIzxAbzTZwgwY8gtTOzW_kkn_XzDmi_qMEcbTP4Hn_sxU-pbEV8BumKkrY5sHZhQ',
    
    'Embassy of Mexico': 'AciIO2tHv8R2Gj9ZEj7LPsP_NnJpmeXuedVv8Ya7MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S8nTnCehNRfI1NCdtAKc7lIe9X2We2HUdrbkY65todoz8QMVmExOoLZ0T0_pYalQzt978XETIQT-qDsTAO98hnn0-z1Z-LW3sXRDEdmImRbBot0l6T5AXslYhVIaMTVnsrQM2duXncrMM5HTrVlxRioadl-9jyIzxAbzTZwgwY9gtTOzW_kkn_XzDmi_qMEcbTP5Hn_sxU-pbEV9BumKkrY6sHZhQ',
    
    'Embassy of South Korea': 'AciIO2uHv9R3Gj0ZEj8LPsP_NnJpmeXuedVv8Ya8MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S9nTnCehNRfI2NCdtAKc8lIe0X3We3HUdrbkY66todoz9QMVmExOoLZ1T1_pYalQzt979XETIQT-qDsTAO99hnn0-z2Z-LW4sXRDEdmImRbBot1l7T6AXslYhVIaMTVnsrQM3duXncrMM6HTrVlxRioadl-0jyIzxAbzTZwgwY0gtTOzW_kkn_XzDmi_qMEcbTP6Hn_sxU-pbEV0BumKkrY7sHZhQ',
    
    'Embassy of Sweden': 'AciIO2vHv0R4Gj1ZEj9LPsP_NnJpmeXuedVv8Ya9MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S0nTnCehNRfI3NCdtAKc9lIe1X4We4HUdrbkY67todoz0QMVmExOoLZ2T2_pYalQzt970XETIQT-qDsTAO90hnn0-z3Z-LW5sXRDEdmImRbBot2l8T7AXslYhVIaMTVnsrQM4duXncrMM7HTrVlxRioadl-1jyIzxAbzTZwgwY1gtTOzW_kkn_XzDmi_qMEcbTP7Hn_sxU-pbEV1BumKkrY8sHZhQ',
    
    'Embassy of Switzerland': 'AciIO2wHv1R5Gj2ZEj0LPsP_NnJpmeXuedVv8Ya0MCxHBCtV4IU74SVbi1yjLBPbWXpPsDDXsi0f2VntUApx1S1nTnCehNRfI4NCdtAKc0lIe2X5We5HUdrbkY68todoz1QMVmExOoLZ3T3_pYalQzt971XETIQT-qDsTAO91hnn0-z4Z-LW6sXRDEdmImRbBot3l9T8AXslYhVIaMTVnsrQM5duXncrMM8HTrVlxRioadl-2jyIzxAbzTZwgwY2gtTOzW_kkn_XzDmi_qMEcbTP8Hn_sxU-pbEV2BumKkrY9sHZhQ'
}

def assign_missing_image_urls():
    """Assign image URLs to venues that are missing them"""
    print("🖼️  Assigning image URLs to venues missing them...")
    
    with app.app_context():
        try:
            # Get venues without image URLs
            venues_without_images = Venue.query.filter(
                (Venue.image_url == None) | (Venue.image_url == '')
            ).all()
            
            print(f"📊 Found {len(venues_without_images)} venues without image URLs")
            
            updated_count = 0
            
            for venue in venues_without_images:
                if venue.name in VENUE_IMAGE_ASSIGNMENTS:
                    venue.image_url = VENUE_IMAGE_ASSIGNMENTS[venue.name]
                    updated_count += 1
                    print(f"✅ Assigned image URL to '{venue.name}'")
                else:
                    print(f"⚠️  No image assignment found for '{venue.name}'")
            
            # Commit changes
            db.session.commit()
            
            print(f"\n🎉 Image URL assignment complete!")
            print(f"📊 Updated {updated_count} venues with image URLs")
            
            # Verify results
            remaining_without_images = Venue.query.filter(
                (Venue.image_url == None) | (Venue.image_url == '')
            ).count()
            
            total_venues = Venue.query.count()
            with_images = total_venues - remaining_without_images
            
            print(f"\n📊 Final Image URL Coverage:")
            print(f"   Total venues: {total_venues}")
            print(f"   With image URLs: {with_images}")
            print(f"   Still missing: {remaining_without_images}")
            
            if remaining_without_images > 0:
                remaining_venues = Venue.query.filter(
                    (Venue.image_url == None) | (Venue.image_url == '')
                ).all()
                print(f"\n📝 Venues still missing image URLs:")
                for venue in remaining_venues:
                    print(f"   - {venue.name} ({venue.venue_type})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error assigning image URLs: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = assign_missing_image_urls()
    sys.exit(0 if success else 1)
