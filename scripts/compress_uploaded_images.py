#!/usr/bin/env python3
"""
Compress all uploaded images to low quality and delete originals
"""

import os
import sys
from PIL import Image

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def compress_uploaded_images():
    """Compress all images in uploads directory to low quality JPEG"""
    uploads_dir = os.path.join(project_root, 'uploads')
    
    if not os.path.exists(uploads_dir):
        print(f"❌ Uploads directory not found: {uploads_dir}")
        return
    
    # Get all image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    image_files = []
    
    for filename in os.listdir(uploads_dir):
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                image_files.append(file_path)
    
    if not image_files:
        print("✅ No images found in uploads directory")
        return
    
    print(f"📸 Found {len(image_files)} images to compress")
    
    total_original_size = 0
    total_compressed_size = 0
    
    for image_path in image_files:
        try:
            # Get original file size
            original_size = os.path.getsize(image_path)
            total_original_size += original_size
            
            print(f"\n🔄 Processing: {os.path.basename(image_path)} ({original_size / 1024:.1f} KB)")
            
            # Open image
            image = Image.open(image_path)
            original_format = image.format
            print(f"   Original format: {original_format}, size: {image.width}x{image.height}")
            
            # Resize if too large (max width 1200px)
            max_width = 1200
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                print(f"   Resized to: {image.width}x{image.height}")
            
            # Convert to RGB if necessary (for JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = rgb_image
                print(f"   Converted to RGB")
            
            # Create new filename (replace extension with .jpg)
            base_name = os.path.splitext(image_path)[0]
            new_path = base_name + '.jpg'
            
            # Save as low quality JPEG
            image.save(new_path, format='JPEG', quality=60, optimize=True)
            
            # Get compressed file size
            compressed_size = os.path.getsize(new_path)
            total_compressed_size += compressed_size
            
            # Delete original if it's different from the new file
            if image_path != new_path:
                os.remove(image_path)
                print(f"   ✅ Deleted original: {os.path.basename(image_path)}")
            
            print(f"   ✅ Saved compressed: {os.path.basename(new_path)} ({compressed_size / 1024:.1f} KB)")
            print(f"   📉 Compression: {original_size / 1024:.1f} KB → {compressed_size / 1024:.1f} KB ({100 * (1 - compressed_size/original_size):.1f}% reduction)")
            
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(image_path)}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Summary:")
    print(f"   Original total size: {total_original_size / 1024:.1f} KB ({total_original_size / (1024*1024):.2f} MB)")
    print(f"   Compressed total size: {total_compressed_size / 1024:.1f} KB ({total_compressed_size / (1024*1024):.2f} MB)")
    print(f"   Total space saved: {(total_original_size - total_compressed_size) / 1024:.1f} KB ({100 * (1 - total_compressed_size/total_original_size):.1f}% reduction)")

if __name__ == '__main__':
    print("🔄 Compressing uploaded images to low quality...")
    compress_uploaded_images()
    print("✅ Done!")

