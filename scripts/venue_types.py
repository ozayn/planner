#!/usr/bin/env python3
"""
Centralized Venue Types Configuration
Single source of truth for all allowed venue types
"""

def get_allowed_venue_types():
    """Get the current list of allowed venue types (centralized source of truth)"""
    return [
        'Museum', 'Science Museum', 'Gallery', 'Theater', 'Performing Arts Center', 
        'Concert Hall', 'Park', 'Botanical Garden', 'Library', 'Historic Site', 
        'Historic District', 'Historic Trail', 'Monument', 'Memorial', 'Landmark', 
        'Cultural Center', 'Arts Center', 'Community Center', 'Convention Center', 
        'Exhibition Hall', 'Auditorium', 'Stadium', 'Arena', 'Market', 
        'Shopping District', 'Art District', 'Government Building', 'Observation Tower', 
        'Observation Deck', 'Observatory', 'Aquarium', 'Zoo', 'Cathedral', 
        'Church', 'Temple', 'Shrine', 'Bridge', 'Castle', 'Palace', 'Beach', 
        'Waterfront', 'Waterway', 'Avenue', 'cafe', 'restaurant', 'bookstore', 'other'
    ]

def get_venue_type_description():
    """Get dynamic venue type description for LLM prompts"""
    allowed_types = get_allowed_venue_types()
    types_str = ', '.join(allowed_types)
    return f'Type of venue - MUST match one of these EXACT values: {types_str}'

if __name__ == '__main__':
    types = get_allowed_venue_types()
    print(f"Current allowed venue types ({len(types)}):")
    for i, venue_type in enumerate(types, 1):
        print(f"  {i:2d}. {venue_type}")
