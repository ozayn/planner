#!/usr/bin/env python3
"""
Compare Events table schema between local and deployed databases
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event
from dotenv import load_dotenv

load_dotenv()

def get_local_schema():
    """Get local SQLite events table schema"""
    db_path = 'instance/events.db'
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(events)")
    columns = cursor.fetchall()
    
    schema = {}
    for col in columns:
        # SQLite PRAGMA format: (cid, name, type, notnull, default_value, pk)
        schema[col[1]] = {
            'type': col[2],
            'nullable': not col[3],
            'default': col[4],
            'primary_key': bool(col[5])
        }
    
    conn.close()
    return schema

def get_deployed_schema():
    """Get deployed PostgreSQL events table schema via API"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'https://planner.ozayn.com/api/admin/events'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        if not data or not isinstance(data, list) or len(data) == 0:
            # No events to infer schema from, try to get schema info another way
            return None
        
        # Infer schema from first event's keys
        first_event = data[0]
        schema = {}
        for key, value in first_event.items():
            if value is None:
                schema[key] = {'type': 'nullable', 'nullable': True}
            elif isinstance(value, bool):
                schema[key] = {'type': 'boolean', 'nullable': True}
            elif isinstance(value, int):
                schema[key] = {'type': 'integer', 'nullable': True}
            elif isinstance(value, str):
                schema[key] = {'type': 'string', 'nullable': True}
            elif isinstance(value, float):
                schema[key] = {'type': 'float', 'nullable': True}
            else:
                schema[key] = {'type': str(type(value).__name__), 'nullable': True}
        
        return schema
    except Exception as e:
        print(f"Error getting deployed schema: {e}")
        return None

def get_model_schema():
    """Get schema from SQLAlchemy Event model"""
    schema = {}
    
    # Get all columns from the Event model
    for column in Event.__table__.columns:
        schema[column.name] = {
            'type': str(column.type),
            'nullable': column.nullable,
            'default': str(column.default.arg) if column.default else None,
            'primary_key': column.primary_key
        }
    
    return schema

def compare_schemas(local_schema, deployed_schema, model_schema):
    """Compare schemas and report differences"""
    print("=" * 80)
    print("EVENTS TABLE SCHEMA COMPARISON")
    print("=" * 80)
    
    all_keys = set()
    if local_schema:
        all_keys.update(local_schema.keys())
    if deployed_schema:
        all_keys.update(deployed_schema.keys())
    if model_schema:
        all_keys.update(model_schema.keys())
    
    print(f"\nTotal columns found: {len(all_keys)}")
    print("\n" + "-" * 80)
    print("COLUMN COMPARISON:")
    print("-" * 80)
    
    differences = []
    matches = []
    
    for key in sorted(all_keys):
        local_col = local_schema.get(key) if local_schema else None
        deployed_col = deployed_schema.get(key) if deployed_schema else None
        model_col = model_schema.get(key) if model_schema else None
        
        status = []
        if local_col:
            status.append("LOCAL")
        if deployed_col:
            status.append("DEPLOYED")
        if model_col:
            status.append("MODEL")
        
        status_str = " | ".join(status)
        
        # Check for differences
        if local_schema and deployed_schema:
            if key not in local_schema:
                differences.append(f"❌ {key:30} | Missing in LOCAL | Present in DEPLOYED")
            elif key not in deployed_schema:
                differences.append(f"❌ {key:30} | Present in LOCAL | Missing in DEPLOYED")
            else:
                matches.append(f"✅ {key:30} | {status_str}")
        elif local_schema and model_schema:
            if key not in local_schema:
                differences.append(f"❌ {key:30} | Missing in LOCAL | Present in MODEL")
            elif key not in model_schema:
                differences.append(f"❌ {key:30} | Present in LOCAL | Missing in MODEL")
            else:
                matches.append(f"✅ {key:30} | {status_str}")
        else:
            matches.append(f"⚠️  {key:30} | {status_str}")
    
    # Print matches first
    for match in matches:
        print(match)
    
    # Print differences
    if differences:
        print("\n" + "-" * 80)
        print("DIFFERENCES FOUND:")
        print("-" * 80)
        for diff in differences:
            print(diff)
    else:
        print("\n" + "-" * 80)
        print("✅ NO DIFFERENCES FOUND - Schemas match!")
        print("-" * 80)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Local schema columns:    {len(local_schema) if local_schema else 'N/A'}")
    print(f"Deployed schema columns: {len(deployed_schema) if deployed_schema else 'N/A'}")
    print(f"Model schema columns:    {len(model_schema) if model_schema else 'N/A'}")
    print(f"Total unique columns:    {len(all_keys)}")
    print(f"Differences:             {len(differences)}")
    
    return len(differences) == 0

def main():
    print("Loading schemas...")
    
    # Get local schema
    print("1. Getting local SQLite schema...")
    local_schema = get_local_schema()
    if local_schema:
        print(f"   ✅ Found {len(local_schema)} columns in local database")
    else:
        print("   ⚠️  Local database not found or empty")
    
    # Get deployed schema
    print("2. Getting deployed PostgreSQL schema...")
    deployed_schema = get_deployed_schema()
    if deployed_schema:
        print(f"   ✅ Found {len(deployed_schema)} columns in deployed database")
    else:
        print("   ⚠️  Could not get deployed schema (no events or API error)")
    
    # Get model schema
    print("3. Getting SQLAlchemy model schema...")
    model_schema = get_model_schema()
    if model_schema:
        print(f"   ✅ Found {len(model_schema)} columns in Event model")
    
    # Compare
    print("\n")
    schemas_match = compare_schemas(local_schema, deployed_schema, model_schema)
    
    return 0 if schemas_match else 1

if __name__ == "__main__":
    sys.exit(main())

