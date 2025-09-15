#!/usr/bin/env python3
"""Minimal test to isolate the hanging issue"""

print("Starting minimal test...")

try:
    print("1. Testing basic imports...")
    import os
    import sys
    print("✅ Basic imports work")
    
    print("2. Testing dotenv...")
    from dotenv import load_dotenv
    print("✅ Dotenv import works")
    
    print("3. Testing environment loading...")
    load_dotenv()
    print("✅ Environment loading works")
    
    print("4. Testing API key access...")
    groq_key = os.getenv('GROQ_API_KEY')
    print(f"✅ Groq key found: {groq_key[:10] if groq_key else 'None'}...")
    
    print("5. Testing requests...")
    import requests
    print("✅ Requests import works")
    
    print("6. Testing simple API call...")
    headers = {'Authorization': f'Bearer {groq_key}'}
    data = {
        'model': 'llama-3.3-70b-versatile',
        'messages': [{'role': 'user', 'content': 'Say hello'}],
        'max_tokens': 10
    }
    
    response = requests.post('https://api.groq.com/openai/v1/chat/completions', 
                           headers=headers, json=data, timeout=5)
    print(f"✅ API call works: {response.status_code}")
    
    print("🎉 All tests passed!")
    
except Exception as e:
    print(f"❌ Error at step: {e}")
    import traceback
    traceback.print_exc()


