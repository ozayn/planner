#!/usr/bin/env python3
"""
Fix Database Configuration
Ensures the database path is consistent across the application
"""

import os
import sys

def fix_database_config():
    """Fix database configuration to use the correct path"""
    
    # Check current .env file
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update DATABASE_URL if it's wrong
        if 'DATABASE_URL=sqlite:///events.db' in content:
            print("🔧 Fixing database URL in .env file...")
            content = content.replace('DATABASE_URL=sqlite:///events.db', 'DATABASE_URL=sqlite:///instance/events.db')
            
            with open(env_file, 'w') as f:
                f.write(content)
            print("✅ Updated .env file")
        else:
            print("✅ .env file already has correct database URL")
    else:
        print("⚠️  No .env file found")
    
    # Ensure instance directory exists
    instance_dir = 'instance'
    if not os.path.exists(instance_dir):
        print("🔧 Creating instance directory...")
        os.makedirs(instance_dir)
        print("✅ Created instance directory")
    else:
        print("✅ Instance directory exists")
    
    # Check if database exists in correct location
    db_path = os.path.join(instance_dir, 'events.db')
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"✅ Database exists in correct location: {db_path} ({size} bytes)")
    else:
        print(f"⚠️  Database does not exist in correct location: {db_path}")
    
    # Check if old database exists and should be moved
    old_db_path = 'events.db'
    if os.path.exists(old_db_path):
        size = os.path.getsize(old_db_path)
        if size > 0:
            print(f"⚠️  Old database exists: {old_db_path} ({size} bytes)")
            print("   Consider moving data from old database to new location")
        else:
            print(f"✅ Old empty database exists: {old_db_path} (can be ignored)")

if __name__ == '__main__':
    fix_database_config()
