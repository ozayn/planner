import sqlite3
import os

db_path = 'instance/events.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check for State College city
    cursor.execute("SELECT id, name FROM cities WHERE name LIKE '%State College%'")
    city = cursor.fetchone()
    if city:
        city_id, city_name = city
        print(f"Found City: {city_name} (ID: {city_id})")
        
        # Check for Webster's in this city
        cursor.execute("SELECT id, name, venue_type, is_active FROM venues WHERE city_id = ? AND name LIKE '%Webster%'", (city_id,))
        venues = cursor.fetchall()
        if venues:
            print(f"Found {len(venues)} matching venues:")
            for v in venues:
                print(f"  ID: {v[0]}, Name: {v[1]}, Type: {v[2]}, Active: {v[3]}")
        else:
            print("No Webster's venue found in this city.")
    else:
        print("State College city not found.")
    
    conn.close()
else:
    print("Database not found")
