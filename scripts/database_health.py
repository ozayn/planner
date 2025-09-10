#!/usr/bin/env python3
"""
Database Health Check and Migration System
Ensures database schema matches model definitions and handles migrations
"""

import os
import sys
import sqlite3
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, City, Venue, Event

class DatabaseHealthChecker:
    """Comprehensive database health checking and migration system"""
    
    def __init__(self):
        self.db_path = self._get_database_path()
        self.expected_tables = {
            'cities': ['id', 'name', 'state', 'country', 'timezone', 'created_at'],
            'venues': ['id', 'name', 'venue_type', 'address', 'latitude', 'longitude', 
                      'image_url', 'instagram_url', 'facebook_url', 'twitter_url', 
                      'youtube_url', 'tiktok_url', 'opening_hours', 'holiday_hours', 
                      'phone_number', 'email', 'website_url', 'description', 'city_id', 'created_at'],
            'events': ['id', 'title', 'description', 'start_date', 'end_date', 
                      'start_time', 'end_time', 'image_url', 'url', 'is_selected', 
                      'created_at', 'event_type'],
            'tours': ['id', 'venue_id', 'meeting_location', 'tour_type', 
                     'max_participants', 'price', 'language'],
            'exhibitions': ['id', 'venue_id', 'exhibition_location', 'curator', 'admission_price'],
            'festivals': ['id', 'city_id', 'festival_type', 'multiple_locations'],
            'photowalks': ['id', 'city_id', 'start_location', 'end_location', 
                          'start_latitude', 'start_longitude', 'end_latitude', 
                          'end_longitude', 'difficulty_level', 'equipment_needed', 'organizer']
        }
    
    def _get_database_path(self) -> str:
        """Get the correct database path"""
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
            return db_path
        return None
    
    def check_database_exists(self) -> bool:
        """Check if database file exists"""
        if not self.db_path:
            print("❌ Database path not configured")
            return False
        
        exists = os.path.exists(self.db_path)
        if exists:
            size = os.path.getsize(self.db_path)
            print(f"✅ Database exists: {self.db_path} ({size} bytes)")
        else:
            print(f"❌ Database does not exist: {self.db_path}")
        return exists
    
    def check_tables_exist(self) -> Tuple[bool, List[str]]:
        """Check if all expected tables exist"""
        if not self.check_database_exists():
            return False, []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        missing_tables = []
        for table in self.expected_tables.keys():
            if table in existing_tables:
                print(f"✅ Table exists: {table}")
            else:
                print(f"❌ Table missing: {table}")
                missing_tables.append(table)
        
        return len(missing_tables) == 0, missing_tables
    
    def check_table_schema(self, table_name: str) -> Tuple[bool, List[str]]:
        """Check if table has correct schema"""
        if not self.db_path:
            return False, []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()
        
        expected_columns = self.expected_tables.get(table_name, [])
        missing_columns = []
        
        for col in expected_columns:
            if col in existing_columns:
                print(f"  ✅ Column exists: {col}")
            else:
                print(f"  ❌ Column missing: {col}")
                missing_columns.append(col)
        
        return len(missing_columns) == 0, missing_columns
    
    def check_all_schemas(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Check schemas for all tables"""
        results = {}
        for table_name in self.expected_tables.keys():
            print(f"\n🔍 Checking schema for {table_name}:")
            results[table_name] = self.check_table_schema(table_name)
        return results
    
    def create_missing_tables(self) -> bool:
        """Create missing tables using SQLAlchemy"""
        try:
            with app.app_context():
                db.create_all()
                print("✅ Created missing tables")
                return True
        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
            return False
    
    def add_missing_columns(self, table_name: str, missing_columns: List[str]) -> bool:
        """Add missing columns to a table"""
        if not missing_columns:
            return True
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            for column in missing_columns:
                # Determine column type based on model definition
                column_type = self._get_column_type(table_name, column)
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}")
                print(f"  ✅ Added column: {column}")
            
            conn.commit()
            print(f"✅ Added missing columns to {table_name}")
            return True
        except Exception as e:
            print(f"❌ Failed to add columns to {table_name}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _get_column_type(self, table_name: str, column_name: str) -> str:
        """Get SQLite column type for a given column"""
        # This is a simplified mapping - in production you'd want more sophisticated type detection
        type_mapping = {
            'id': 'INTEGER',
            'name': 'VARCHAR(200)',
            'description': 'TEXT',
            'address': 'TEXT',
            'latitude': 'FLOAT',
            'longitude': 'FLOAT',
            'image_url': 'VARCHAR(500)',
            'website_url': 'VARCHAR(200)',
            'instagram_url': 'VARCHAR(200)',
            'facebook_url': 'VARCHAR(200)',
            'twitter_url': 'VARCHAR(200)',
            'youtube_url': 'VARCHAR(200)',
            'tiktok_url': 'VARCHAR(200)',
            'opening_hours': 'TEXT',
            'holiday_hours': 'TEXT',
            'phone_number': 'VARCHAR(50)',
            'email': 'VARCHAR(200)',
            'venue_type': 'VARCHAR(50)',
            'city_id': 'INTEGER',
            'venue_id': 'INTEGER',
            'created_at': 'DATETIME',
            'title': 'VARCHAR(200)',
            'start_date': 'DATE',
            'end_date': 'DATE',
            'start_time': 'TIME',
            'end_time': 'TIME',
            'url': 'VARCHAR(500)',
            'is_selected': 'BOOLEAN',
            'event_type': 'VARCHAR(50)'
        }
        return type_mapping.get(column_name, 'TEXT')
    
    def run_full_health_check(self) -> bool:
        """Run complete database health check and fix issues"""
        print("🔍 Running Database Health Check...")
        print("=" * 50)
        
        # Check if database exists
        if not self.check_database_exists():
            print("❌ Database does not exist - cannot proceed")
            return False
        
        # Check if tables exist
        tables_exist, missing_tables = self.check_tables_exist()
        if not tables_exist:
            print(f"\n🔧 Creating missing tables: {missing_tables}")
            if not self.create_missing_tables():
                return False
        
        # Check table schemas
        print("\n🔍 Checking table schemas...")
        schema_results = self.check_all_schemas()
        
        # Fix missing columns
        all_good = True
        for table_name, (schema_ok, missing_columns) in schema_results.items():
            if not schema_ok:
                print(f"\n🔧 Adding missing columns to {table_name}: {missing_columns}")
                if not self.add_missing_columns(table_name, missing_columns):
                    all_good = False
        
        if all_good:
            print("\n✅ Database health check passed!")
        else:
            print("\n❌ Database health check failed!")
        
        return all_good
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        if not self.db_path or not os.path.exists(self.db_path):
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        for table_name in self.expected_tables.keys():
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                stats[table_name] = count
            except sqlite3.OperationalError:
                stats[table_name] = 0
        
        conn.close()
        return stats

def main():
    """Main function for command line usage"""
    checker = DatabaseHealthChecker()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'check':
            checker.run_full_health_check()
        elif command == 'stats':
            stats = checker.get_database_stats()
            print("📊 Database Statistics:")
            for table, count in stats.items():
                print(f"  {table}: {count} records")
        elif command == 'fix':
            checker.run_full_health_check()
        else:
            print("Usage: python database_health.py [check|stats|fix]")
    else:
        checker.run_full_health_check()

if __name__ == '__main__':
    main()

