#!/usr/bin/env python3
"""
Diagnose why Dec 10, 2025 tours might be filtered out
"""

from datetime import date, timedelta

# Simulate the date filtering logic
today = date.today()
one_month_later = today + timedelta(days=30)

print(f"Today: {today}")
print(f"One month later: {one_month_later}")
print()

# The missing tours are from Dec 10, 2025
missing_tour_date = date(2025, 12, 10)

print(f"Missing tour date: {missing_tour_date}")
print(f"tour_date >= today: {missing_tour_date >= today}")
print(f"tour_date <= one_month_later: {missing_tour_date <= one_month_later}")
print(f"Should be included: {missing_tour_date >= today and missing_tour_date <= one_month_later}")
print()

# Check if today is actually Dec 10
if today == missing_tour_date:
    print("✅ Today IS Dec 10, 2025 - tours should be included")
    print("   The filter 'tour_date >= today' should include today's tours")
elif today > missing_tour_date:
    print(f"⚠️  Today ({today}) is AFTER Dec 10, 2025")
    print(f"   The filter 'tour_date >= today' will EXCLUDE Dec 10 tours")
    print(f"   This is the problem!")
elif today < missing_tour_date:
    print(f"ℹ️  Today ({today}) is BEFORE Dec 10, 2025")
    print(f"   Dec 10 tours should be included (they're in the future)")
