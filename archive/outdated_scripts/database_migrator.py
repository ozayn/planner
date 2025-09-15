#!/usr/bin/env python3
"""
Database Schema Migration System
Automatically tracks and applies database schema changes
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any

class DatabaseMigrator:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser('~/.local/share/planner/events.db')
        self.migrations_file = os.path.join(os.path.dirname(self.db_path), 'migrations.json')
        self.current_time = datetime.utcnow().isoformat()
        
    def get_current_schema(self) -> Dict[str, List[Dict]]:
        """Get current database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        schema = {}
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema[table_name] = []
            for col in columns:
                schema[table_name].append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default': col[4],
                    'primary_key': bool(col[5])
                })
        
        conn.close()
        return schema
    
    def load_migrations(self) -> List[Dict]:
        """Load migration history"""
        if os.path.exists(self.migrations_file):
            with open(self.migrations_file, 'r') as f:
                return json.load(f)
        return []
    
    def save_migrations(self, migrations: List[Dict]):
        """Save migration history"""
        os.makedirs(os.path.dirname(self.migrations_file), exist_ok=True)
        with open(self.migrations_file, 'w') as f:
            json.dump(migrations, f, indent=2)
    
    def add_migration(self, migration_name: str, description: str, changes: Dict):
        """Add a new migration to the history"""
        migrations = self.load_migrations()
        
        migration = {
            'id': len(migrations) + 1,
            'name': migration_name,
            'description': description,
            'timestamp': self.current_time,
            'changes': changes,
            'applied': False
        }
        
        migrations.append(migration)
        self.save_migrations(migrations)
        return migration
    
    def apply_migration(self, migration: Dict) -> bool:
        """Apply a specific migration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            changes = migration['changes']
            
            # Apply column additions
            if 'add_columns' in changes:
                for table, columns in changes['add_columns'].items():
                    for column in columns:
                        self._add_column(cursor, table, column)
            
            # Apply column modifications
            if 'modify_columns' in changes:
                for table, columns in changes['modify_columns'].items():
                    for column in columns:
                        self._modify_column(cursor, table, column)
            
            # Apply column deletions
            if 'drop_columns' in changes:
                for table, columns in changes['drop_columns'].items():
                    for column in columns:
                        self._drop_column(cursor, table, column)
            
            # Apply index changes
            if 'add_indexes' in changes:
                for index in changes['add_indexes']:
                    self._add_index(cursor, index)
            
            if 'drop_indexes' in changes:
                for index_name in changes['drop_indexes']:
                    self._drop_index(cursor, index_name)
            
            # Apply data updates
            if 'update_data' in changes:
                for table, updates in changes['update_data'].items():
                    for update in updates:
                        self._update_data(cursor, table, update)
            
            conn.commit()
            conn.close()
            
            # Mark migration as applied
            migrations = self.load_migrations()
            for m in migrations:
                if m['id'] == migration['id']:
                    m['applied'] = True
                    m['applied_at'] = self.current_time
                    break
            self.save_migrations(migrations)
            
            print(f"✅ Applied migration: {migration['name']}")
            return True
            
        except Exception as e:
            print(f"❌ Error applying migration {migration['name']}: {e}")
            return False
    
    def _add_column(self, cursor, table: str, column: Dict):
        """Add a column to a table"""
        column_def = f"{column['name']} {column['type']}"
        
        if column.get('not_null', False):
            column_def += " NOT NULL"
        
        if 'default' in column:
            column_def += f" DEFAULT {column['default']}"
        
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        print(f"   ✅ Added column {column['name']} to {table}")
    
    def _modify_column(self, cursor, table: str, column: Dict):
        """Modify a column (SQLite limitation: need to recreate table)"""
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        print(f"   ⚠️ SQLite limitation: Cannot modify column {column['name']} in {table}")
        print(f"   💡 Consider using add_column + drop_column approach")
    
    def _drop_column(self, cursor, table: str, column_name: str):
        """Drop a column from a table"""
        # SQLite doesn't support DROP COLUMN in older versions
        # For newer versions (3.35.0+), we can use:
        try:
            cursor.execute(f"ALTER TABLE {table} DROP COLUMN {column_name}")
            print(f"   ✅ Dropped column {column_name} from {table}")
        except sqlite3.Error:
            print(f"   ⚠️ Cannot drop column {column_name} from {table} (SQLite version limitation)")
    
    def _add_index(self, cursor, index: Dict):
        """Add an index"""
        index_name = index['name']
        table = index['table']
        columns = index['columns']
        
        cursor.execute(f"CREATE INDEX {index_name} ON {table} ({columns})")
        print(f"   ✅ Created index {index_name}")
    
    def _drop_index(self, cursor, index_name: str):
        """Drop an index"""
        cursor.execute(f"DROP INDEX {index_name}")
        print(f"   ✅ Dropped index {index_name}")
    
    def _update_data(self, cursor, table: str, update: Dict):
        """Update data in a table"""
        sql = update['sql']
        params = update.get('params', [])
        
        cursor.execute(sql, params)
        print(f"   ✅ Updated data in {table}")
    
    def create_migration_from_models(self, models_config: Dict) -> Dict:
        """Create migration based on model definitions"""
        current_schema = self.get_current_schema()
        changes = {
            'add_columns': {},
            'modify_columns': {},
            'drop_columns': {},
            'add_indexes': [],
            'drop_indexes': []
        }
        
        for table_name, model_config in models_config.items():
            if table_name not in current_schema:
                # Table doesn't exist, will be created by SQLAlchemy
                continue
            
            current_columns = {col['name']: col for col in current_schema[table_name]}
            model_columns = model_config['columns']
            
            # Find missing columns
            missing_columns = []
            for col_name, col_config in model_columns.items():
                if col_name not in current_columns:
                    missing_columns.append(col_config)
            
            if missing_columns:
                changes['add_columns'][table_name] = missing_columns
            
            # Find columns that need modification
            modified_columns = []
            for col_name, col_config in model_columns.items():
                if col_name in current_columns:
                    current_col = current_columns[col_name]
                    if (current_col['type'] != col_config['type'] or 
                        current_col['not_null'] != col_config.get('not_null', False) or
                        current_col['default'] != col_config.get('default')):
                        modified_columns.append(col_config)
            
            if modified_columns:
                changes['modify_columns'][table_name] = modified_columns
        
        return changes
    
    def run_pending_migrations(self):
        """Run all pending migrations"""
        migrations = self.load_migrations()
        pending = [m for m in migrations if not m.get('applied', False)]
        
        if not pending:
            print("✅ No pending migrations")
            return True
        
        print(f"🔄 Running {len(pending)} pending migrations...")
        
        for migration in pending:
            if not self.apply_migration(migration):
                print(f"❌ Migration failed: {migration['name']}")
                return False
        
        print("✅ All migrations completed successfully!")
        return True

# Predefined model configurations
MODEL_CONFIGS = {
    'cities': {
        'columns': {
            'id': {'name': 'id', 'type': 'INTEGER', 'not_null': True, 'primary_key': True},
            'name': {'name': 'name', 'type': 'VARCHAR(100)', 'not_null': True},
            'state': {'name': 'state', 'type': 'VARCHAR(50)', 'not_null': False},
            'country': {'name': 'country', 'type': 'VARCHAR(100)', 'not_null': True},
            'timezone': {'name': 'timezone', 'type': 'VARCHAR(50)', 'not_null': True},
            'created_at': {'name': 'created_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'},
            'updated_at': {'name': 'updated_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'}
        }
    },
    'venues': {
        'columns': {
            'id': {'name': 'id', 'type': 'INTEGER', 'not_null': True, 'primary_key': True},
            'name': {'name': 'name', 'type': 'VARCHAR(200)', 'not_null': True},
            'venue_type': {'name': 'venue_type', 'type': 'VARCHAR(50)', 'not_null': True},
            'address': {'name': 'address', 'type': 'TEXT', 'not_null': False},
            'latitude': {'name': 'latitude', 'type': 'FLOAT', 'not_null': False},
            'longitude': {'name': 'longitude', 'type': 'FLOAT', 'not_null': False},
            'image_url': {'name': 'image_url', 'type': 'VARCHAR(500)', 'not_null': False},
            'instagram_url': {'name': 'instagram_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'facebook_url': {'name': 'facebook_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'twitter_url': {'name': 'twitter_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'youtube_url': {'name': 'youtube_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'tiktok_url': {'name': 'tiktok_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'website_url': {'name': 'website_url', 'type': 'VARCHAR(200)', 'not_null': False},
            'description': {'name': 'description', 'type': 'TEXT', 'not_null': False},
            'opening_hours': {'name': 'opening_hours', 'type': 'TEXT', 'not_null': False},
            'holiday_hours': {'name': 'holiday_hours', 'type': 'TEXT', 'not_null': False},
            'phone_number': {'name': 'phone_number', 'type': 'VARCHAR(50)', 'not_null': False},
            'email': {'name': 'email', 'type': 'VARCHAR(100)', 'not_null': False},
            'tour_info': {'name': 'tour_info', 'type': 'TEXT', 'not_null': False},
            'admission_fee': {'name': 'admission_fee', 'type': 'TEXT', 'not_null': False},
            'city_id': {'name': 'city_id', 'type': 'INTEGER', 'not_null': True},
            'created_at': {'name': 'created_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'},
            'updated_at': {'name': 'updated_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'}
        }
    },
    'events': {
        'columns': {
            'id': {'name': 'id', 'type': 'INTEGER', 'not_null': True, 'primary_key': True},
            'title': {'name': 'title', 'type': 'VARCHAR(200)', 'not_null': True},
            'description': {'name': 'description', 'type': 'TEXT', 'not_null': False},
            'start_date': {'name': 'start_date', 'type': 'DATE', 'not_null': True},
            'end_date': {'name': 'end_date', 'type': 'DATE', 'not_null': False},
            'start_time': {'name': 'start_time', 'type': 'TIME', 'not_null': False},
            'end_time': {'name': 'end_time', 'type': 'TIME', 'not_null': False},
            'image_url': {'name': 'image_url', 'type': 'VARCHAR(500)', 'not_null': False},
            'url': {'name': 'url', 'type': 'VARCHAR(500)', 'not_null': False},
            'is_selected': {'name': 'is_selected', 'type': 'BOOLEAN', 'not_null': False, 'default': '1'},
            'event_type': {'name': 'event_type', 'type': 'VARCHAR(50)', 'not_null': False},
            'created_at': {'name': 'created_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'},
            'updated_at': {'name': 'updated_at', 'type': 'DATETIME', 'not_null': True, 'default': 'CURRENT_TIMESTAMP'}
        }
    }
}

def create_migration_for_model_changes():
    """Create a migration for current model changes"""
    migrator = DatabaseMigrator()
    
    print("🔍 Analyzing model changes...")
    changes = migrator.create_migration_from_models(MODEL_CONFIGS)
    
    if not any(changes.values()):
        print("✅ No schema changes detected")
        return
    
    migration_name = f"update_models_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    description = "Update database schema to match current model definitions"
    
    migration = migrator.add_migration(migration_name, description, changes)
    
    print(f"📝 Created migration: {migration_name}")
    print(f"   Description: {description}")
    
    if changes['add_columns']:
        print("   📋 Columns to add:")
        for table, columns in changes['add_columns'].items():
            for col in columns:
                print(f"     - {table}.{col['name']} ({col['type']})")
    
    if changes['modify_columns']:
        print("   🔄 Columns to modify:")
        for table, columns in changes['modify_columns'].items():
            for col in columns:
                print(f"     - {table}.{col['name']} ({col['type']})")
    
    return migration

if __name__ == '__main__':
    print("🔄 Database Migration System")
    print("1. Create migration for model changes")
    print("2. Run pending migrations")
    print("3. Show migration history")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    migrator = DatabaseMigrator()
    
    if choice == '1':
        migration = create_migration_for_model_changes()
        if migration:
            apply_now = input("\nApply migration now? (y/N): ").lower() == 'y'
            if apply_now:
                migrator.apply_migration(migration)
    
    elif choice == '2':
        migrator.run_pending_migrations()
    
    elif choice == '3':
        migrations = migrator.load_migrations()
        if migrations:
            print(f"\n📋 Migration History ({len(migrations)} migrations):")
            for m in migrations:
                status = "✅ Applied" if m.get('applied', False) else "⏳ Pending"
                print(f"  {m['id']}. {m['name']} - {status}")
                print(f"     {m['description']}")
                print(f"     Created: {m['timestamp']}")
                if m.get('applied_at'):
                    print(f"     Applied: {m['applied_at']}")
                print()
        else:
            print("📋 No migrations found")
    
    else:
        print("❌ Invalid option")

