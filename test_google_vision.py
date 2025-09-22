#!/usr/bin/env python3
"""
Google Vision API Test Script

This script tests your Google Vision API setup and provides detailed feedback
about what's working and what needs to be configured.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_environment_setup():
    """Test basic environment setup"""
    print("🔧 Testing Environment Setup")
    print("=" * 40)
    
    # Check if .env file exists
    env_file = project_root / '.env'
    print(f"📁 .env file: {'✅ Found' if env_file.exists() else '❌ Not found'}")
    
    # Load environment variables manually
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        pass
    
    # Check GOOGLE_APPLICATION_CREDENTIALS
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path:
        print(f"🔑 GOOGLE_APPLICATION_CREDENTIALS: ✅ Set to '{credentials_path}'")
        
        # Check if it's a file path or JSON content
        if credentials_path.startswith('{'):
            print("   📄 Detected: JSON content (direct)")
        else:
            print(f"   📄 Detected: File path")
            if os.path.exists(credentials_path):
                print(f"   ✅ File exists")
            else:
                print(f"   ❌ File not found")
    else:
        print("🔑 GOOGLE_APPLICATION_CREDENTIALS: ❌ Not set")
    
    print()

def test_google_vision_import():
    """Test Google Vision API import"""
    print("📦 Testing Google Vision API Import")
    print("=" * 40)
    
    try:
        from google.cloud import vision
        print("✅ google.cloud.vision imported successfully")
        
        # Try to create a client
        try:
            client = vision.ImageAnnotatorClient()
            print("✅ ImageAnnotatorClient created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create ImageAnnotatorClient: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import google.cloud.vision: {e}")
        print("   💡 Try: pip install google-cloud-vision")
        return False

def test_tesseract_setup():
    """Test Tesseract setup"""
    print("🔍 Testing Tesseract Setup")
    print("=" * 40)
    
    try:
        import pytesseract
        print("✅ pytesseract imported successfully")
        
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
            return True
        except Exception as e:
            print(f"❌ Tesseract not found: {e}")
            print("   💡 Install Tesseract:")
            print("      macOS: brew install tesseract")
            print("      Ubuntu: sudo apt-get install tesseract-ocr")
            print("      Windows: Download from GitHub releases")
            return False
            
    except ImportError:
        print("❌ pytesseract not installed")
        print("   💡 Try: pip install pytesseract")
        return False

def test_image_processor():
    """Test the ImageEventProcessor"""
    print("🖼️  Testing Image Event Processor")
    print("=" * 40)
    
    try:
        from scripts.image_event_processor import ImageEventProcessor
        processor = ImageEventProcessor()
        
        print(f"✅ ImageEventProcessor created successfully")
        print(f"   OCR Engine: {processor.ocr_engine}")
        
        if processor.ocr_engine == 'google_vision':
            print("   🎯 Using Google Vision API")
        elif processor.ocr_engine == 'tesseract':
            print("   🎯 Using Tesseract OCR")
        else:
            print(f"   ⚠️  Using fallback engine: {processor.ocr_engine}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create ImageEventProcessor: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Google Vision API Test Suite")
    print("=" * 50)
    print()
    
    # Test environment setup
    test_environment_setup()
    
    # Test Tesseract (should work locally)
    tesseract_works = test_tesseract_setup()
    print()
    
    # Test Google Vision API
    vision_works = test_google_vision_import()
    print()
    
    # Test image processor
    processor_works = test_image_processor()
    print()
    
    # Summary
    print("📊 Test Summary")
    print("=" * 40)
    print(f"Tesseract OCR: {'✅ Working' if tesseract_works else '❌ Not working'}")
    print(f"Google Vision API: {'✅ Working' if vision_works else '❌ Not working'}")
    print(f"Image Processor: {'✅ Working' if processor_works else '❌ Not working'}")
    
    if tesseract_works or vision_works:
        print("\n🎉 OCR functionality should work!")
        if tesseract_works and vision_works:
            print("   🚀 You have both OCR engines available - excellent!")
        elif tesseract_works:
            print("   📝 Tesseract OCR will be used (free, local)")
        elif vision_works:
            print("   ☁️  Google Vision API will be used (cloud-based)")
    else:
        print("\n⚠️  OCR functionality may not work properly")
        print("   💡 Set up at least one OCR engine:")
        print("      - Install Tesseract for local OCR")
        print("      - Configure Google Vision API for cloud OCR")
        print("   📖 See docs/setup/GOOGLE_VISION_SETUP.md for detailed instructions")

if __name__ == "__main__":
    main()