#!/usr/bin/env python3
"""
Generic CRUD Endpoint Generator
Automatically creates PUT/DELETE endpoints for any model
"""

import sys
import os
from flask import request, jsonify
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_generic_crud_endpoints(app, db, City, Venue, Event):
    """Create generic CRUD endpoints for all models"""
    
    # Define models and their configurations
    models_config = {
        'cities': {
            'model': City,
            'route_prefix': '/api/admin/cities',
            'exclude_fields': ['id', 'created_at', 'updated_at'],  # Fields to exclude from updates
            'required_fields': ['name', 'country', 'timezone']  # Required fields for creation
        },
        'venues': {
            'model': Venue,
            'route_prefix': '/api/admin/venues',
            'exclude_fields': ['id', 'created_at', 'updated_at'],
            'required_fields': ['name', 'venue_type', 'city_id']
        },
        'events': {
            'model': Event,
            'route_prefix': '/api/admin/events',
            'exclude_fields': ['id', 'created_at', 'updated_at'],
            'required_fields': ['title', 'event_type', 'start_date']
        }
    }
    
    for model_name, config in models_config.items():
        model_class = config['model']
        route_prefix = config['route_prefix']
        exclude_fields = config['exclude_fields']
        
        # Create PUT endpoint for updating
        def create_update_endpoint(model_class, exclude_fields):
            def update_item(item_id):
                """Generic update endpoint for any model"""
                try:
                    item = model_class.query.get_or_404(item_id)
                    data = request.get_json()
                    
                    if not data:
                        return jsonify({'error': 'No data provided'}), 400
                    
                    # Get all updatable fields from the model
                    updatable_fields = get_model_fields(model_class, exclude_fields)
                    
                    # Update fields dynamically
                    updated_fields = []
                    for field_name in updatable_fields:
                        if field_name in data:
                            setattr(item, field_name, data[field_name])
                            updated_fields.append(field_name)
                    
                    # Always update the updated_at timestamp if the field exists
                    if hasattr(item, 'updated_at'):
                        item.updated_at = datetime.utcnow()
                    
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'message': f'{model_class.__name__} updated successfully',
                        'updated_fields': updated_fields,
                        'item': item.to_dict() if hasattr(item, 'to_dict') else None
                    })
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'error': str(e)}), 500
            
            return update_item
        
        # Create DELETE endpoint for deleting
        def create_delete_endpoint(model_class):
            def delete_item(item_id):
                """Generic delete endpoint for any model"""
                try:
                    item = model_class.query.get_or_404(item_id)
                    
                    # Get item name for response (try common name fields)
                    item_name = getattr(item, 'name', None) or getattr(item, 'title', None) or f'Item {item_id}'
                    
                    db.session.delete(item)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'message': f'{model_class.__name__} "{item_name}" deleted successfully'
                    })
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'error': str(e)}), 500
            
            return delete_item
        
        # Create POST endpoint for creating
        def create_create_endpoint(model_class, required_fields):
            def create_item():
                """Generic create endpoint for any model"""
                try:
                    data = request.get_json()
                    
                    if not data:
                        return jsonify({'error': 'No data provided'}), 400
                    
                    # Check required fields
                    missing_fields = [field for field in required_fields if field not in data or not data[field]]
                    if missing_fields:
                        return jsonify({
                            'error': f'Missing required fields: {", ".join(missing_fields)}'
                        }), 400
                    
                    # Get all fields from the model
                    model_fields = get_model_fields(model_class, ['id', 'created_at', 'updated_at'])
                    
                    # Create new item
                    item_data = {}
                    for field_name in model_fields:
                        if field_name in data:
                            item_data[field_name] = data[field_name]
                    
                    # Create the item
                    item = model_class(**item_data)
                    db.session.add(item)
                    db.session.commit()
                    
                    # Special handling for cities - sync to predefined JSON
                    if model_class.__name__ == 'City':
                        try:
                            from app import sync_cities_to_predefined_json
                            sync_cities_to_predefined_json()
                        except Exception as sync_error:
                            print(f"⚠️ Warning: Could not sync city to predefined JSON: {sync_error}")
                    
                    return jsonify({
                        'success': True,
                        'message': f'{model_class.__name__} created successfully',
                        'item': item.to_dict() if hasattr(item, 'to_dict') else None
                    }), 201
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'error': str(e)}), 500
            
            return create_item
        
        # Register the endpoints with unique names
        update_func = create_update_endpoint(model_class, exclude_fields)
        delete_func = create_delete_endpoint(model_class)
        create_func = create_create_endpoint(model_class, config['required_fields'])
        
        # Register routes with unique endpoint names
        app.add_url_rule(f'{route_prefix}/<int:item_id>', 
                        f'update_{model_name}', 
                        update_func, 
                        methods=['PUT'])
        app.add_url_rule(f'{route_prefix}/<int:item_id>', 
                        f'delete_{model_name}', 
                        delete_func, 
                        methods=['DELETE'])
        app.add_url_rule(f'{route_prefix}', 
                        f'create_{model_name}', 
                        create_func, 
                        methods=['POST'])

def get_model_fields(model_class, exclude_fields=None):
    """Get all field names from a SQLAlchemy model"""
    if exclude_fields is None:
        exclude_fields = []
    
    # Get all column names from the model
    columns = model_class.__table__.columns.keys()
    
    # Filter out excluded fields
    return [col for col in columns if col not in exclude_fields]

def register_generic_crud_endpoints(app, db, City, Venue, Event):
    """Register all generic CRUD endpoints"""
    create_generic_crud_endpoints(app, db, City, Venue, Event)
    print("✅ Generic CRUD endpoints registered for all models")

if __name__ == "__main__":
    # This won't work when run directly due to circular import
    print("This script should be imported by app.py, not run directly")
