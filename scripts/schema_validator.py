#!/usr/bin/env python3
"""
Database Schema Validator
Ensures schema consistency between local and deployed environments
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db, Event, Venue, City, Source
import sqlite3

class SchemaValidator:
    """Validates database schema consistency"""
    
    def __init__(self):
        self.is_railway = self._detect_environment()
        
    def _detect_environment(self) -> bool:
        """Detect if running in Railway/deployed environment"""
        return (
            os.getenv('RAILWAY_ENVIRONMENT') is not None or
            os.getenv('DATABASE_URL', '').startswith('postgresql://') or
            'railway.app' in os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
        )
    
    def get_schema_info(self) -> Dict:
        """Get current database schema information"""
        with app.app_context():
            schema_info = {
                'environment': 'Railway/PostgreSQL' if self.is_railway else 'Local/SQLite',
                'tables': {},
                'constraints': {},
                'indexes': {}
            }
            
            if not self.is_railway:
                # SQLite schema inspection
                db_path = 'instance/events.db'
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for table_name, in tables:
                    # Get table schema
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    schema_info['tables'][table_name] = {
                        'columns': [
                            {
                                'name': col[1],
                                'type': col[2],
                                'nullable': not col[3],
                                'default': col[4],
                                'primary_key': bool(col[5])
                            }
                            for col in columns
                        ]
                    }
                    
                    # Get foreign keys
                    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
                    foreign_keys = cursor.fetchall()
                    
                    schema_info['constraints'][table_name] = {
                        'foreign_keys': [
                            {
                                'column': fk[3],
                                'references_table': fk[2],
                                'references_column': fk[4]
                            }
                            for fk in foreign_keys
                        ]
                    }
                
                conn.close()
            else:
                # PostgreSQL schema inspection (simplified)
                # In production, you'd use psycopg2 to inspect PostgreSQL schema
                schema_info['tables'] = {
                    'cities': {'note': 'PostgreSQL schema inspection not implemented'},
                    'venues': {'note': 'PostgreSQL schema inspection not implemented'},
                    'sources': {'note': 'PostgreSQL schema inspection not implemented'},
                    'events': {'note': 'PostgreSQL schema inspection not implemented'}
                }
            
            return schema_info
    
    def validate_table_structure(self, table_name: str) -> Dict:
        """Validate specific table structure"""
        with app.app_context():
            validation = {
                'table': table_name,
                'valid': True,
                'issues': [],
                'stats': {}
            }
            
            if table_name == 'cities':
                cities = City.query.all()
                validation['stats'] = {
                    'count': len(cities),
                    'sample_ids': [c.id for c in cities[:5]],
                    'sample_names': [c.name for c in cities[:5]]
                }
                
                # Check for required fields
                for city in cities:
                    if not city.name:
                        validation['issues'].append(f"City ID {city.id} missing name")
                    if not city.country:
                        validation['issues'].append(f"City ID {city.id} missing country")
                    if not city.timezone:
                        validation['issues'].append(f"City ID {city.id} missing timezone")
            
            elif table_name == 'sources':
                sources = Source.query.all()
                validation['stats'] = {
                    'count': len(sources),
                    'sample_names': [s.name for s in sources[:5]],
                    'source_types': list(set(s.source_type for s in sources))
                }
                
                # Check for orphaned sources
                city_ids = set(City.query.with_entities(City.id).all())
                city_ids = {cid[0] for cid in city_ids}
                
                orphaned_count = 0
                for source in sources:
                    if source.city_id not in city_ids:
                        validation['issues'].append(f"Source '{source.name}' has invalid city_id: {source.city_id}")
                        orphaned_count += 1
                
                if orphaned_count > 0:
                    validation['issues'].append(f"{orphaned_count} sources have invalid city_id references")
            
            elif table_name == 'venues':
                venues = Venue.query.all()
                validation['stats'] = {
                    'count': len(venues),
                    'sample_names': [v.name for v in venues[:5]],
                    'venue_types': list(set(v.venue_type for v in venues))
                }
                
                # Check for orphaned venues
                city_ids = set(City.query.with_entities(City.id).all())
                city_ids = {cid[0] for cid in city_ids}
                
                orphaned_count = 0
                for venue in venues:
                    if venue.city_id not in city_ids:
                        validation['issues'].append(f"Venue '{venue.name}' has invalid city_id: {venue.city_id}")
                        orphaned_count += 1
                
                if orphaned_count > 0:
                    validation['issues'].append(f"{orphaned_count} venues have invalid city_id references")
            
            elif table_name == 'events':
                events = Event.query.all()
                validation['stats'] = {
                    'count': len(events),
                    'sample_titles': [e.title for e in events[:5]],
                    'event_types': list(set(e.event_type for e in events))
                }
                
                # Check for orphaned events
                city_ids = set(City.query.with_entities(City.id).all())
                city_ids = {cid[0] for cid in city_ids}
                
                orphaned_count = 0
                for event in events:
                    if event.city_id not in city_ids:
                        validation['issues'].append(f"Event '{event.title}' has invalid city_id: {event.city_id}")
                        orphaned_count += 1
                
                if orphaned_count > 0:
                    validation['issues'].append(f"{orphaned_count} events have invalid city_id references")
            
            validation['valid'] = len(validation['issues']) == 0
            return validation
    
    def compare_with_expected_schema(self) -> Dict:
        """Compare current schema with expected schema"""
        expected_schema = {
            'cities': {
                'required_columns': ['id', 'name', 'country', 'timezone', 'created_at', 'updated_at'],
                'min_count': 20,
                'max_count': 50
            },
            'sources': {
                'required_columns': ['id', 'name', 'source_type', 'city_id', 'created_at', 'updated_at'],
                'min_count': 30,
                'max_count': 100
            },
            'venues': {
                'required_columns': ['id', 'name', 'venue_type', 'city_id', 'created_at', 'updated_at'],
                'min_count': 100,
                'max_count': 500
            },
            'events': {
                'required_columns': ['id', 'title', 'event_type', 'city_id', 'created_at', 'updated_at'],
                'min_count': 0,
                'max_count': 10000
            }
        }
        
        comparison = {
            'valid': True,
            'issues': [],
            'tables': {}
        }
        
        with app.app_context():
            for table_name, requirements in expected_schema.items():
                table_validation = self.validate_table_structure(table_name)
                comparison['tables'][table_name] = table_validation
                
                # Check count requirements
                count = table_validation['stats'].get('count', 0)
                if count < requirements['min_count']:
                    comparison['issues'].append(f"{table_name}: Only {count} records, expected at least {requirements['min_count']}")
                    comparison['valid'] = False
                elif count > requirements['max_count']:
                    comparison['issues'].append(f"{table_name}: {count} records, expected at most {requirements['max_count']}")
                    comparison['valid'] = False
                
                # Add table-specific issues
                if not table_validation['valid']:
                    comparison['issues'].extend(table_validation['issues'])
                    comparison['valid'] = False
        
        return comparison
    
    def generate_schema_report(self) -> str:
        """Generate a comprehensive schema report"""
        schema_info = self.get_schema_info()
        comparison = self.compare_with_expected_schema()
        
        report = []
        report.append("🔍 DATABASE SCHEMA VALIDATION REPORT")
        report.append("=" * 50)
        report.append(f"Environment: {schema_info['environment']}")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        report.append("📊 TABLE VALIDATION:")
        report.append("-" * 30)
        for table_name, validation in comparison['tables'].items():
            status = "✅" if validation['valid'] else "❌"
            report.append(f"{status} {table_name}: {validation['stats'].get('count', 0)} records")
            
            if not validation['valid']:
                for issue in validation['issues']:
                    report.append(f"   ⚠️ {issue}")
        
        report.append("")
        report.append("🔗 OVERALL VALIDATION:")
        report.append("-" * 25)
        overall_status = "✅ VALID" if comparison['valid'] else "❌ INVALID"
        report.append(f"Status: {overall_status}")
        
        if comparison['issues']:
            report.append("Issues:")
            for issue in comparison['issues']:
                report.append(f"  - {issue}")
        
        return "\n".join(report)

def main():
    """Main function for schema validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Schema Validator')
    parser.add_argument('--table', help='Validate specific table only')
    parser.add_argument('--report', action='store_true', help='Generate full schema report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    validator = SchemaValidator()
    
    if args.table:
        validation = validator.validate_table_structure(args.table)
        if args.json:
            print(json.dumps(validation, indent=2))
        else:
            print(f"🔍 Validation for {args.table}:")
            print(f"Valid: {validation['valid']}")
            print(f"Stats: {validation['stats']}")
            if validation['issues']:
                print("Issues:")
                for issue in validation['issues']:
                    print(f"  - {issue}")
    elif args.report:
        report = validator.generate_schema_report()
        print(report)
    else:
        # Default: full validation
        comparison = validator.compare_with_expected_schema()
        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print("🔍 Schema Validation Results:")
            print(f"Overall Valid: {comparison['valid']}")
            if comparison['issues']:
                print("Issues:")
                for issue in comparison['issues']:
                    print(f"  - {issue}")
    
    # Get comparison for return value
    if 'comparison' not in locals():
        comparison = validator.compare_with_expected_schema()
    
    return 0 if comparison['valid'] else 1

if __name__ == '__main__':
    sys.exit(main())
