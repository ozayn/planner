#!/usr/bin/env python3
"""
CENTRALIZED ENVIRONMENT CONFIGURATION
Ensures environment variables are loaded consistently across all scripts
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (where .env file is located)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
ENV_FILE = PROJECT_ROOT / '.env'

# Global flag to track if environment has been loaded
_ENV_LOADED = False

def ensure_env_loaded():
    """Ensure environment variables are loaded exactly once"""
    global _ENV_LOADED
    
    if not _ENV_LOADED:
        # Load .env file from project root
        if ENV_FILE.exists():
            load_dotenv(ENV_FILE)
            print(f"✅ Environment loaded from {ENV_FILE}")
        else:
            print(f"⚠️  No .env file found at {ENV_FILE}")
        
        _ENV_LOADED = True
    
    return _ENV_LOADED

def get_env_var(key: str, default: str = None) -> str:
    """Get environment variable with automatic loading"""
    ensure_env_loaded()
    return os.getenv(key, default)

def get_app_config() -> dict:
    """Get application configuration settings"""
    ensure_env_loaded()
    return {
        'max_venues_per_city': int(os.getenv('MAX_VENUES_PER_CITY', '2')),
        'max_events_per_venue': int(os.getenv('MAX_EVENTS_PER_VENUE', '10')),
        'default_event_type': os.getenv('DEFAULT_EVENT_TYPE', 'tours'),
        'api_timeout': int(os.getenv('API_TIMEOUT', '30')),
        'debug_mode': os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    }

def get_api_keys() -> dict:
    """Get all API keys with automatic loading"""
    ensure_env_loaded()
    
    return {
        'GROQ_API_KEY': os.getenv('GROQ_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'COHERE_API_KEY': os.getenv('COHERE_API_KEY'),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
        'MISTRAL_API_KEY': os.getenv('MISTRAL_API_KEY'),
        'HUGGINGFACE_API_KEY': os.getenv('HUGGINGFACE_API_KEY'),
        'GOOGLE_MAPS_API_KEY': os.getenv('GOOGLE_MAPS_API_KEY'),
        'INSTAGRAM_API_KEY': os.getenv('INSTAGRAM_API_KEY'),
    }

def get_available_llm_providers() -> list:
    """Get list of available LLM providers"""
    api_keys = get_api_keys()
    
    available = []
    if api_keys['GROQ_API_KEY']:
        available.append('groq')
    if api_keys['OPENAI_API_KEY']:
        available.append('openai')
    if api_keys['ANTHROPIC_API_KEY']:
        available.append('anthropic')
    if api_keys['COHERE_API_KEY']:
        available.append('cohere')
    if api_keys['GOOGLE_API_KEY']:
        available.append('google')
    if api_keys['MISTRAL_API_KEY']:
        available.append('mistral')
    if api_keys['HUGGINGFACE_API_KEY']:
        available.append('huggingface')
    
    return available

def check_env_status() -> dict:
    """Check environment configuration status"""
    ensure_env_loaded()
    
    api_keys = get_api_keys()
    available_providers = get_available_llm_providers()
    
    return {
        'env_file_exists': ENV_FILE.exists(),
        'env_file_path': str(ENV_FILE),
        'env_loaded': _ENV_LOADED,
        'available_providers': available_providers,
        'total_providers': len(available_providers),
        'has_llm_setup': len(available_providers) > 0,
        'api_keys_status': {key: bool(value) for key, value in api_keys.items()}
    }

# Auto-load environment when this module is imported
ensure_env_loaded()

if __name__ == "__main__":
    # Test the environment configuration
    print("🧪 Testing Environment Configuration")
    print("=" * 50)
    
    status = check_env_status()
    print(f"Environment File: {status['env_file_path']}")
    print(f"File Exists: {status['env_file_exists']}")
    print(f"Environment Loaded: {status['env_loaded']}")
    print(f"Available LLM Providers: {status['available_providers']}")
    print(f"Total Providers: {status['total_providers']}")
    print(f"Has LLM Setup: {status['has_llm_setup']}")
    
    print("\nAPI Keys Status:")
    for key, has_key in status['api_keys_status'].items():
        status_icon = "✅" if has_key else "❌"
        print(f"  {status_icon} {key}")
    
    print("\n✅ Environment configuration test complete!")

