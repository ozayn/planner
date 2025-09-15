#!/usr/bin/env python3
"""
Utility script to manage predefined_venues.json copy system
Allows safe editing of venue data without affecting the original file
"""

import json
import os
import shutil
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_json_paths():
    """Get paths for original and venues JSON files"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    original_path = os.path.join(data_dir, 'predefined_venues.json')
    venues_path = os.path.join(data_dir, 'venues.json')
    return original_path, venues_path

def create_copy():
    """Create a fresh copy of predefined_venues.json as venues.json"""
    original_path, venues_path = get_json_paths()
    
    if not os.path.exists(original_path):
        print(f"❌ Original file not found: {original_path}")
        return False
    
    try:
        shutil.copy2(original_path, venues_path)
        print(f"✅ Created fresh venues.json from predefined_venues.json")
        print(f"📁 Working file: {venues_path}")
        return True
    except Exception as e:
        print(f"❌ Error creating copy: {e}")
        return False

def apply_copy_to_original():
    """Apply changes from venues.json back to original file"""
    original_path, venues_path = get_json_paths()
    
    if not os.path.exists(venues_path):
        print(f"❌ Working file not found: {venues_path}")
        print("💡 Run 'create_copy' first")
        return False
    
    try:
        # Create backup of original
        backup_path = f"{original_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(original_path, backup_path)
        print(f"📋 Created backup: {backup_path}")
        
        # Apply venues.json to original
        shutil.copy2(venues_path, original_path)
        print(f"✅ Applied venues.json to original: {original_path}")
        print(f"📁 Working file: {venues_path}")
        return True
    except Exception as e:
        print(f"❌ Error applying copy: {e}")
        return False

def show_status():
    """Show status of original and venues files"""
    original_path, venues_path = get_json_paths()
    
    print("📊 JSON File Status:")
    print("=" * 50)
    
    # Original file status
    if os.path.exists(original_path):
        original_size = os.path.getsize(original_path)
        original_mtime = datetime.fromtimestamp(os.path.getmtime(original_path))
        print(f"📁 Original: {original_path}")
        print(f"   Size: {original_size:,} bytes")
        print(f"   Modified: {original_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"❌ Original not found: {original_path}")
    
    print()
    
    # Working file status
    if os.path.exists(venues_path):
        venues_size = os.path.getsize(venues_path)
        venues_mtime = datetime.fromtimestamp(os.path.getmtime(venues_path))
        print(f"📁 Working file: {venues_path}")
        print(f"   Size: {venues_size:,} bytes")
        print(f"   Modified: {venues_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if working file is newer
        if os.path.exists(original_path):
            if venues_mtime > datetime.fromtimestamp(os.path.getmtime(original_path)):
                print("   ⚠️  Working file is newer than original")
            else:
                print("   ✅ Working file is up to date")
    else:
        print(f"❌ Working file not found: {venues_path}")
        print("💡 Run 'create_copy' to create one")

def compare_files():
    """Compare original and venues files"""
    original_path, venues_path = get_json_paths()
    
    if not os.path.exists(original_path):
        print(f"❌ Original file not found: {original_path}")
        return
    
    if not os.path.exists(venues_path):
        print(f"❌ Working file not found: {venues_path}")
        print("💡 Run 'create_copy' first")
        return
    
    try:
        # Load both files
        with open(original_path, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(venues_path, 'r', encoding='utf-8') as f:
            venues_data = json.load(f)
        
        print("🔍 Comparing Original vs Working file:")
        print("=" * 50)
        
        # Compare metadata
        original_venues = original_data.get('metadata', {}).get('total_venues', 0)
        venues_venues = venues_data.get('metadata', {}).get('total_venues', 0)
        
        print(f"📊 Total venues:")
        print(f"   Original: {original_venues}")
        print(f"   Working file: {venues_venues}")
        
        if venues_venues > original_venues:
            print(f"   ✅ Working file has {venues_venues - original_venues} more venues")
        elif venues_venues < original_venues:
            print(f"   ⚠️  Working file has {original_venues - venues_venues} fewer venues")
        else:
            print(f"   ✅ Same number of venues")
        
        # Compare cities
        original_cities = len(original_data.get('cities', []))
        venues_cities = len(venues_data.get('cities', []))
        
        print(f"\n🏙️ Total cities:")
        print(f"   Original: {original_cities}")
        print(f"   Working file: {venues_cities}")
        
        if venues_cities != original_cities:
            print(f"   ⚠️  Different number of cities!")
        
    except Exception as e:
        print(f"❌ Error comparing files: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🔧 JSON Management Tool")
        print("=" * 50)
        print("Usage: python scripts/manage_venue_json.py <command>")
        print()
        print("Commands:")
        print("  create_copy    - Create a fresh venues.json from predefined_venues.json")
        print("  apply_copy     - Apply venues.json changes back to original")
        print("  status         - Show status of original and venues files")
        print("  compare        - Compare original and venues files")
        print("  help           - Show this help message")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'create_copy':
        create_copy()
    elif command == 'apply_copy':
        apply_copy_to_original()
    elif command == 'status':
        show_status()
    elif command == 'compare':
        compare_files()
    elif command == 'help':
        main()
    else:
        print(f"❌ Unknown command: {command}")
        print("💡 Run 'python scripts/manage_venue_json.py help' for usage")

if __name__ == "__main__":
    main()
