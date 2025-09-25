#!/usr/bin/env python3
"""
Google Vision API Test Suite
Comprehensive testing of Google Vision API improvements
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.image_event_processor import ImageEventProcessor
from google.cloud import vision

class VisionAPITester:
    """Comprehensive Google Vision API testing"""
    
    def __init__(self):
        self.processor = ImageEventProcessor()
        self.test_results = []
        
    def test_basic_functionality(self):
        """Test basic Google Vision API functionality"""
        print("🔍 Testing Basic Google Vision API Functionality")
        print("=" * 50)
        
        try:
            # Test client creation
            client = vision.ImageAnnotatorClient()
            print("✅ Google Vision client created successfully")
            
            # Test OCR engine detection
            print(f"✅ OCR Engine: {self.processor.ocr_engine}")
            
            if self.processor.ocr_engine == 'google_vision':
                print("✅ Using Google Vision API (preferred)")
            else:
                print("⚠️ Using fallback OCR engine")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_image_processing(self, image_path: str):
        """Test image processing with a specific image"""
        print(f"\n🖼️ Testing Image Processing: {image_path}")
        print("-" * 40)
        
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return None
        
        try:
            # Process the image
            result = self.processor.process_image(image_path)
            
            # Display results
            print("📊 Processing Results:")
            print(f"  Title: {result.title}")
            print(f"  Description: {result.description}")
            print(f"  Start Date: {result.start_date}")
            print(f"  Start Time: {result.start_time}")
            print(f"  Location: {result.location}")
            print(f"  Event Type: {result.event_type}")
            print(f"  City: {result.city}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Source: {result.source}")
            
            # Test raw text extraction
            print("\n📝 Raw Text Extraction:")
            raw_text = self.processor.extract_text_from_image(image_path)
            print(f"  Text Length: {len(raw_text)} characters")
            print(f"  Preview: {raw_text[:200]}...")
            
            # Test text cleaning
            cleaned_text = self.processor._clean_text_for_extraction(raw_text)
            print(f"\n🧹 Cleaned Text:")
            print(f"  Length: {len(cleaned_text)} characters")
            print(f"  Preview: {cleaned_text[:200]}...")
            
            # Test garbled detection
            is_garbled = self.processor._is_garbled_text(cleaned_text)
            print(f"\n🔍 Garbled Text Detection: {'Yes' if is_garbled else 'No'}")
            
            return {
                'success': True,
                'result': result,
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'is_garbled': is_garbled
            }
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_ocr_engine_comparison(self, image_path: str):
        """Compare Google Vision vs Tesseract performance"""
        print(f"\n⚖️ OCR Engine Comparison: {image_path}")
        print("-" * 40)
        
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return None
        
        try:
            # Test Google Vision directly
            print("🔍 Testing Google Vision API directly...")
            client = vision.ImageAnnotatorClient()
            
            with open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.text_detection(image=image)
            texts = response.text_annotations
            
            if texts:
                google_vision_text = texts[0].description
                print(f"✅ Google Vision extracted {len(google_vision_text)} characters")
                print(f"Preview: {google_vision_text[:200]}...")
            else:
                print("❌ Google Vision found no text")
                google_vision_text = ""
            
            # Test Tesseract (if available)
            print("\n🔍 Testing Tesseract OCR...")
            try:
                import pytesseract
                from PIL import Image as PILImage
                
                image_pil = PILImage.open(image_path)
                tesseract_text = pytesseract.image_to_string(image_pil)
                print(f"✅ Tesseract extracted {len(tesseract_text)} characters")
                print(f"Preview: {tesseract_text[:200]}...")
                
            except Exception as e:
                print(f"⚠️ Tesseract not available: {e}")
                tesseract_text = ""
            
            # Compare results
            print("\n📊 Comparison:")
            print(f"  Google Vision: {len(google_vision_text)} chars")
            print(f"  Tesseract: {len(tesseract_text)} chars")
            
            if google_vision_text and tesseract_text:
                # Simple similarity check
                google_words = set(google_vision_text.lower().split())
                tesseract_words = set(tesseract_text.lower().split())
                common_words = google_words.intersection(tesseract_words)
                similarity = len(common_words) / max(len(google_words), len(tesseract_words))
                print(f"  Word similarity: {similarity:.2%}")
            
            return {
                'google_vision_text': google_vision_text,
                'tesseract_text': tesseract_text,
                'google_vision_length': len(google_vision_text),
                'tesseract_length': len(tesseract_text)
            }
            
        except Exception as e:
            print(f"❌ Error in comparison: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_multiple_images(self):
        """Test with multiple images from uploads folder"""
        print("\n🖼️ Testing Multiple Images")
        print("=" * 30)
        
        uploads_dir = Path("uploads")
        if not uploads_dir.exists():
            print("❌ Uploads directory not found")
            return
        
        image_files = list(uploads_dir.glob("*.jpg")) + list(uploads_dir.glob("*.png"))
        
        if not image_files:
            print("❌ No images found in uploads directory")
            return
        
        print(f"Found {len(image_files)} images to test:")
        for img_file in image_files:
            print(f"  - {img_file.name}")
        
        results = []
        for img_file in image_files:
            print(f"\n{'='*50}")
            result = self.test_image_processing(str(img_file))
            if result:
                results.append({
                    'file': img_file.name,
                    'success': result['success'],
                    'title': result['result'].title,
                    'event_type': result['result'].event_type,
                    'confidence': result['result'].confidence
                })
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"  Images tested: {len(image_files)}")
        print(f"  Successful: {len(results)}")
        print(f"  Failed: {len(image_files) - len(results)}")
        
        if results:
            print("\nResults:")
            for result in results:
                print(f"  {result['file']}: {result['title']} ({result['event_type']}) - Confidence: {result['confidence']}")
        
        return results
    
    def run_comprehensive_test(self):
        """Run comprehensive Google Vision API test suite"""
        print("🧪 GOOGLE VISION API COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Test 1: Basic functionality
        basic_test = self.test_basic_functionality()
        if not basic_test:
            print("❌ Basic functionality test failed. Stopping.")
            return False
        
        # Test 2: Single image processing
        test_image = "uploads/event_image_20250922_133250_2025-09-22 12.19.38.jpg"
        if os.path.exists(test_image):
            single_test = self.test_image_processing(test_image)
            if single_test:
                self.test_results.append(single_test)
        
        # Test 3: OCR engine comparison
        if os.path.exists(test_image):
            comparison_test = self.test_ocr_engine_comparison(test_image)
            if comparison_test:
                self.test_results.append(comparison_test)
        
        # Test 4: Multiple images
        multiple_test = self.test_multiple_images()
        if multiple_test:
            self.test_results.extend(multiple_test)
        
        # Final summary
        print(f"\n🎉 TEST SUITE COMPLETED")
        print("=" * 30)
        print(f"Total tests run: {len(self.test_results)}")
        print(f"Successful: {sum(1 for r in self.test_results if r.get('success', False))}")
        
        return True

def main():
    """Main function for Google Vision API testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Vision API Test Suite')
    parser.add_argument('--image', help='Test specific image file')
    parser.add_argument('--compare', action='store_true', help='Compare OCR engines')
    parser.add_argument('--comprehensive', action='store_true', help='Run comprehensive test suite')
    
    args = parser.parse_args()
    
    tester = VisionAPITester()
    
    if args.image:
        # Test specific image
        result = tester.test_image_processing(args.image)
        if args.compare:
            tester.test_ocr_engine_comparison(args.image)
    elif args.comprehensive:
        # Run comprehensive test suite
        tester.run_comprehensive_test()
    else:
        # Default: basic test
        tester.test_basic_functionality()
        if os.path.exists("uploads/event_image_20250922_133250_2025-09-22 12.19.38.jpg"):
            tester.test_image_processing("uploads/event_image_20250922_133250_2025-09-22 12.19.38.jpg")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
