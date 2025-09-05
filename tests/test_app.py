"""
Test suite for Event Planner App
"""

import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, db, City, Venue, Tour

class TestEventPlannerApp(unittest.TestCase):
    """Test cases for the Event Planner application"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.drop_all()
    
    def test_cities_endpoint(self):
        """Test cities API endpoint"""
        response = self.client.get('/api/cities')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
    
    def test_events_endpoint_without_city(self):
        """Test events endpoint without city_id"""
        response = self.client.get('/api/events')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_events_endpoint_with_city(self):
        """Test events endpoint with city_id"""
        # First create a city
        with self.app.app_context():
            city = City(name='Test City', country='Test Country', timezone='UTC')
            db.session.add(city)
            db.session.commit()
            
            response = self.client.get(f'/api/events?city_id={city.id}')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIsInstance(data, list)
    
    def test_calendar_add_endpoint(self):
        """Test calendar add endpoint"""
        response = self.client.post('/api/calendar/add', 
                                  json={'event_id': 1, 'event_type': 'tour', 'city_id': 1})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('message', data)

if __name__ == '__main__':
    unittest.main()
