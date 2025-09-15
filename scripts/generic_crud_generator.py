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

def register_generic_crud_endpoints(app, db, City, Venue, Event):
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
                        return jsonify({'error': 'No JSON data provided'}), 400
                    
                    # Update fields (excluding protected fields)
                    for key, value in data.items():
                        if hasattr(item, key) and key not in exclude_fields:
                            setattr(item, key, value)
                    
                    # Set updated timestamp
                    if hasattr(item, 'updated_at'):
                        item.updated_at = datetime.utcnow()
                    
                    db.session.commit()
                    return jsonify({'message': 'Item updated successfully', 'id': item.id})
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'error': f'Update failed: {str(e)}'}), 500
            
            return update_item
        
        # Create DELETE endpoint
        def create_delete_endpoint(model_class):
            def delete_item(item_id):
                """Generic delete endpoint for any model"""
                try:
                    item = model_class.query.get_or_404(item_id)
                    db.session.delete(item)
                    db.session.commit()
                    return jsonify({'message': 'Item deleted successfully', 'id': item_id})
                    
                except Exception as e:
                    db.session.rollback()
                    return jsonify({'error': f'Delete failed: {str(e)}'}), 500
            
            return delete_item
        
        # Register endpoints
        update_func = create_update_endpoint(model_class, exclude_fields)
        delete_func = create_delete_endpoint(model_class)
        
        app.add_url_rule(f'{route_prefix}/<int:item_id>', 
                        f'update_{model_name}', 
                        update_func, 
                        methods=['PUT'])
        
        app.add_url_rule(f'{route_prefix}/<int:item_id>', 
                        f'delete_{model_name}', 
                        delete_func, 
                        methods=['DELETE'])
    
    print("✅ Generic CRUD endpoints registered successfully")

if __name__ == "__main__":
    print("Generic CRUD Generator module loaded")

