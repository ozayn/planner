#!/usr/bin/env python3
"""Simple test to debug the hanging issue"""

import os
import sys
import requests
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_simple_groq():
    """Test Groq API directly without the complex fallback system"""
    print("🔍 Testing Groq API directly...")
    
    # Load environment
    from scripts.env_config import ensure_env_loaded, get_api_keys
    ensure_env_loaded()
    api_keys = get_api_keys()
    
    groq_key = api_keys.get('GROQ_API_KEY')
    if not groq_key:
        print("❌ No Groq API key found")
        return False
    
    print(f"✅ Found Groq API key: {groq_key[:10]}...")
    
    # Simple prompt
    prompt = 'Find information about "Phillips Collection" in Washington, United States. Return ONLY a JSON object with name, address, venue_type, description, website_url. Return ONLY valid JSON, no other text.'
    
    headers = {
        'Authorization': f'Bearer {groq_key}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'llama-3.3-70b-versatile',
        'messages': [
            {'role': 'system', 'content': 'You are a helpful cultural tourism expert. Always respond with valid JSON.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 1000
    }
    
    try:
        print("📡 Sending request to Groq...")
        response = requests.post('https://api.groq.com/openai/v1/chat/completions', 
                               headers=headers, json=data, timeout=10)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("✅ Success!")
            print(f"Response: {content[:200]}...")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    test_simple_groq()


