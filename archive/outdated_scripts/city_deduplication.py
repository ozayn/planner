#!/usr/bin/env python3
"""
City Deduplication and Validation Script
Prevents duplicate cities and ensures data quality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City
from scripts.utils import normalize_city_with_nlp

def find_duplicate_cities():
    """Find potential duplicate cities using NLP normalization"""
    with app.app_context():
        print("🔍 Scanning for duplicate cities...")
        
        cities = City.query.all()
        duplicates = []
        
        for i, city1 in enumerate(cities):
            for city2 in cities[i+1:]:
                # Normalize both city names for comparison
                norm1 = normalize_city_with_nlp(city1.name)
                norm2 = normalize_city_with_nlp(city2.name)
                
                # Check if they're the same city
                if norm1 == norm2 or are_same_city(city1, city2):
                    duplicates.append((city1, city2))
                    print(f"  🚨 Potential duplicate:")
                    print(f"     ID {city1.id}: {city1.name}, {city1.state}, {city1.country}")
                    print(f"     ID {city2.id}: {city2.name}, {city2.state}, {city2.country}")
        
        if not duplicates:
            print("✅ No duplicate cities found")
        
        return duplicates

def are_same_city(city1, city2):
    """Check if two cities represent the same location"""
    # Same country and state
    if city1.country == city2.country and city1.state == city2.state:
        # Check for common city name variations
        name1 = city1.name.lower().strip()
        name2 = city2.name.lower().strip()
        
        # Handle common variations
        variations = [
            ("new york city", "new york"),
            ("los angeles", "la"),
            ("san francisco", "sf"),
            ("washington dc", "washington"),
            ("washington d.c.", "washington"),
        ]
        
        for var1, var2 in variations:
            if (name1 == var1 and name2 == var2) or (name1 == var2 and name2 == var1):
                return True
        
        # Exact match
        if name1 == name2:
            return True
    
    return False

def validate_city_data():
    """Validate city data quality"""
    with app.app_context():
        print("\n📋 Validating city data quality...")
        
        cities = City.query.all()
        issues = []
        
        for city in cities:
            # Check for missing required fields
            if not city.name or not city.name.strip():
                issues.append(f"City ID {city.id}: Missing name")
            
            if not city.country or not city.country.strip():
                issues.append(f"City ID {city.id}: Missing country")
            
            if not city.timezone or not city.timezone.strip():
                issues.append(f"City ID {city.id}: Missing timezone")
            
            # Check for unusual state values
            if city.state and city.state.lower() in ['new york', 'california', 'texas']:
                # These should be abbreviated
                issues.append(f"City ID {city.id}: State should be abbreviated ({city.state})")
        
        if issues:
            print("⚠️ Data quality issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ All city data looks good")

def suggest_city_standards():
    """Suggest city naming standards"""
    print("\n📝 Suggested City Naming Standards:")
    print("  • Use full city names: 'New York City' not 'New York'")
    print("  • Abbreviate states: 'NY' not 'New York'")
    print("  • Use standard timezones: 'America/New_York'")
    print("  • Include country for international cities")
    print("  • Avoid duplicates by checking existing cities first")

if __name__ == '__main__':
    find_duplicate_cities()
    validate_city_data()
    suggest_city_standards()

