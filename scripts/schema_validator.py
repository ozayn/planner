#!/usr/bin/env python3
"""
Schema Validation System
Automatically detects and fixes schema inconsistencies
"""

import sys
import os
import inspect
from typing import List, Dict, Set, Tuple
import sqlite3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Venue, City, Event

class SchemaValidator:
    """Comprehensive schema validation and synchronization system"""
    
    def __init__(self):
        self.db_path = os.path.expanduser('~/.local/share/planner/events.db')
        self.models = [Venue, City, Event]
    
    def get_model_fields(self, model) -> Set[str]:
        """Get all fields from a SQLAlchemy model"""
        return {column.name for column in model.__table__.columns}
    
    def get_database_fields(self, table_name: str) -> Set[str]:
        """Get all fields from the actual database table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            conn.close()
            return {col[1] for col in columns}  # col[1] is the column name
        except Exception as e:
            print(f"❌ Error reading database schema for {table_name}: {e}")
            return set()
    
    def validate_model_database_sync(self) -> Dict[str, List[str]]:
        """Validate that model fields match database fields"""
        issues = {}
        
        for model in self.models:
            table_name = model.__tablename__
            model_fields = self.get_model_fields(model)
            db_fields = self.get_database_fields(table_name)
            
            # Check for missing fields in database
            missing_in_db = model_fields - db_fields
            if missing_in_db:
                issues[f"{table_name}_missing_in_db"] = list(missing_in_db)
            
            # Check for extra fields in database
            extra_in_db = db_fields - model_fields
            if extra_in_db:
                issues[f"{table_name}_extra_in_db"] = list(extra_in_db)
        
        return issues
    
    def validate_object_creation(self) -> Dict[str, List[str]]:
        """Validate that object creation includes all model fields"""
        issues = {}
        
        # Check Venue creation in discover_venues.py
        try:
            with open('scripts/discover_venues.py', 'r') as f:
                content = f.read()
            
            # Find Venue() creation
            if 'Venue(' in content:
                # Get all Venue model fields
                venue_fields = self.get_model_fields(Venue)
                
                # Check which fields are missing from Venue() creation
                missing_fields = []
                for field in venue_fields:
                    if field not in ['id', 'created_at']:  # Skip auto-generated fields
                        # Look for field assignment patterns
                        field_patterns = [
                            f'{field}=',  # field=value
                            f'{field}:',  # field: value (in dict)
                        ]
                        if not any(pattern in content for pattern in field_patterns):
                            missing_fields.append(field)
                
                if missing_fields:
                    issues['venue_creation_missing_fields'] = missing_fields
        
        except Exception as e:
            issues['venue_creation_error'] = [str(e)]
        
        return issues
    
    def validate_to_dict_methods(self) -> Dict[str, List[str]]:
        """Validate that to_dict() methods include all fields"""
        issues = {}
        
        for model in self.models:
            if hasattr(model, 'to_dict'):
                try:
                    # Get the to_dict method source
                    source = inspect.getsource(model.to_dict)
                    model_fields = self.get_model_fields(model)
                    
                    # Check which fields are missing from to_dict
                    missing_fields = []
                    for field in model_fields:
                        if field not in ['id', 'created_at']:  # Skip auto-generated fields
                            if f"'{field}'" not in source and f'"{field}"' not in source:
                                missing_fields.append(field)
                    
                    if missing_fields:
                        issues[f"{model.__tablename__}_to_dict_missing"] = missing_fields
                
                except Exception as e:
                    issues[f"{model.__tablename__}_to_dict_error"] = [str(e)]
        
        return issues
    
    def validate_admin_endpoints(self) -> Dict[str, List[str]]:
        """Validate that admin endpoints include all fields"""
        issues = {}
        
        try:
            with open('app.py', 'r') as f:
                content = f.read()
            
            # Check admin venues endpoint
            if 'get_admin_venues' in content:
                venue_fields = self.get_model_fields(Venue)
                missing_fields = []
                
                for field in venue_fields:
                    if field not in ['id', 'created_at']:
                        if f"'{field}': venue.{field}" not in content:
                            missing_fields.append(field)
                
                if missing_fields:
                    issues['admin_venues_missing_fields'] = missing_fields
        
        except Exception as e:
            issues['admin_endpoints_error'] = [str(e)]
        
        return issues
    
    def generate_fix_suggestions(self, issues: Dict[str, List[str]]) -> List[str]:
        """Generate specific fix suggestions for detected issues"""
        suggestions = []
        
        for issue_type, fields in issues.items():
            if 'missing_in_db' in issue_type:
                table_name = issue_type.split('_')[0]
                suggestions.append(f"🔧 Add missing columns to {table_name} table:")
                for field in fields:
                    suggestions.append(f"   ALTER TABLE {table_name} ADD COLUMN {field} TEXT;")
            
            elif 'venue_creation_missing_fields' in issue_type:
                suggestions.append("🔧 Update Venue() creation in scripts/discover_venues.py:")
                for field in fields:
                    suggestions.append(f"   {field}=details.get('{field}', ''),")
            
            elif 'to_dict_missing' in issue_type:
                table_name = issue_type.split('_')[0]
                suggestions.append(f"🔧 Update {table_name}.to_dict() method:")
                for field in fields:
                    suggestions.append(f"   '{field}': self.{field},")
            
            elif 'admin_venues_missing_fields' in issue_type:
                suggestions.append("🔧 Update get_admin_venues endpoint:")
                for field in fields:
                    suggestions.append(f"   '{field}': venue.{field},")
        
        return suggestions
    
    def run_comprehensive_validation(self) -> Dict:
        """Run all validation checks and return comprehensive report"""
        print("🔍 Running comprehensive schema validation...")
        
        results = {
            'model_db_sync': self.validate_model_database_sync(),
            'object_creation': self.validate_object_creation(),
            'to_dict_methods': self.validate_to_dict_methods(),
            'admin_endpoints': self.validate_admin_endpoints()
        }
        
        # Generate fix suggestions
        all_issues = {}
        for category, issues in results.items():
            all_issues.update(issues)
        
        suggestions = self.generate_fix_suggestions(all_issues)
        
        return {
            'results': results,
            'suggestions': suggestions,
            'has_issues': len(all_issues) > 0
        }
    
    def print_validation_report(self, validation_result: Dict):
        """Print a comprehensive validation report"""
        print("\n" + "="*60)
        print("📊 SCHEMA VALIDATION REPORT")
        print("="*60)
        
        if not validation_result['has_issues']:
            print("✅ All schema validations passed!")
            return
        
        print("❌ Schema issues detected:")
        
        for category, issues in validation_result['results'].items():
            if issues:
                print(f"\n📋 {category.upper().replace('_', ' ')}:")
                for issue_type, fields in issues.items():
                    print(f"   • {issue_type}: {', '.join(fields)}")
        
        if validation_result['suggestions']:
            print(f"\n🔧 FIX SUGGESTIONS:")
            for suggestion in validation_result['suggestions']:
                print(f"   {suggestion}")
        
        print("\n" + "="*60)

def main():
    """Main validation function"""
    validator = SchemaValidator()
    result = validator.run_comprehensive_validation()
    validator.print_validation_report(result)
    
    if result['has_issues']:
        print("\n🚨 Schema issues detected! Please fix before proceeding.")
        return 1
    else:
        print("\n✅ Schema validation passed!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
