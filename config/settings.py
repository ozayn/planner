import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///events.db')
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Google Calendar API
    GOOGLE_CALENDAR_CREDENTIALS_PATH = os.getenv('GOOGLE_CALENDAR_CREDENTIALS_PATH', 'credentials.json')
    GOOGLE_CALENDAR_TOKEN_PATH = os.getenv('GOOGLE_CALENDAR_TOKEN_PATH', 'token.json')
    
    # Scraping
    SCRAPING_HEADLESS = os.getenv('SCRAPING_HEADLESS', 'True').lower() == 'true'
    SCRAPING_TIMEOUT = int(os.getenv('SCRAPING_TIMEOUT', '10'))
    
    # App
    APP_PORT = int(os.getenv('APP_PORT', '5001'))
    APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
    
    # External APIs
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    INSTAGRAM_API_KEY = os.getenv('INSTAGRAM_API_KEY')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
