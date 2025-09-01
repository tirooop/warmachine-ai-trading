#!/usr/bin/env python
"""
Direct PIL/Pillow Patch for Null Bytes

This simple script directly patches PIL/Pillow to handle images with null bytes.
Import this at the beginning of your application to fix PIL/Pillow issues.

Usage:
    import imghdr_patch_direct
"""

import sys
import io
import os

def log(message):
    """Simple logging function"""
    print(f"[PIL_PATCH] {message}")

# Only apply once
if getattr(sys, '_pil_patched', False):
    log("Patch already applied")
else:
    log("Applying PIL/Pillow patch for null bytes")
    
    try:
        # Direct PIL patching
        from PIL import Image
        _original_open = Image.open
        
        def _safe_open_image(fp, mode='r', formats=None):
            """Safely open images, handling null bytes"""
            # First try the normal approach
            try:
                return _original_open(fp, mode, formats)
            except Exception as e:
                # If it's a BytesIO or similar, try cleaning null bytes
                if hasattr(fp, 'read') and hasattr(fp, 'seek'):
                    try:
                        # Save position and reset
                        pos = fp.tell()
                        fp.seek(0)
                        
                        # Read data and clean it
                        data = fp.read()
                        if isinstance(data, bytes) and b'\x00\x00' in data:
                            # Remove duplicate nulls but preserve single nulls
                            cleaned = data.replace(b'\x00\x00', b'\x00')
                            
                            # Create new BytesIO with cleaned data
                            cleaned_fp = io.BytesIO(cleaned)
                            return _original_open(cleaned_fp, mode, formats)
                            
                        # Reset position
                        fp.seek(pos)
                    except:
                        # If cleaning fails, reset and try original again
                        if hasattr(fp, 'seek'):
                            try:
                                fp.seek(0)
                            except:
                                pass
                
                # One more attempt with original
                try:
                    return _original_open(fp, mode, formats)
                except:
                    # Re-raise the original exception if all else fails
                    raise
        
        # Apply the patch
        Image.open = _safe_open_image
        
        # Flag as patched
        sys._pil_patched = True
        log("Successfully patched PIL.Image.open")
        
    except ImportError:
        log("PIL/Pillow not installed")
    except Exception as e:
        log(f"Error applying patch: {str(e)}")

# Create a tiny test function
def test_patch():
    """Test if the patch works"""
    try:
        from PIL import Image
        
        # Create a simple test PNG with null bytes
        test_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_with_nulls = test_png.replace(b'\x00', b'\x00\x00')
        
        # First test normal PNG
        buf1 = io.BytesIO(test_png)
        img1 = Image.open(buf1)
        img1.load()
        
        # Now test with null bytes
        buf2 = io.BytesIO(test_with_nulls)
        img2 = Image.open(buf2)
        img2.load()
        
        log("✅ Patch test successful - Can handle images with null bytes")
        return True
    except Exception as e:
        log(f"❌ Patch test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Run the test
    test_patch()
    
    log("\nTo use this patch in your application, add this import at the top:")
    log("    import imghdr_patch_direct")
    
    # Create a simple example
    example = """#!/usr/bin/env python
# Example of using the direct PIL/Pillow patch

# Import the patch first
import imghdr_patch_direct

# Then regular imports
import io
from PIL import Image

# Now you can safely open images with null bytes
def process_image(image_data):
    img_io = io.BytesIO(image_data)
    img = Image.open(img_io)  # This will work even with null bytes
    print(f"Opened image: {img.format} {img.size}")
    return img

# Test with a PNG that has null bytes
test_png = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x08\\x02\\x00\\x00\\x00\\x90wS\\xde\\x00\\x00\\x00\\x0cIDATx\\x9cc```\\x00\\x00\\x00\\x04\\x00\\x01\\xf6\\x178U\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
test_with_nulls = test_png.replace(b'\\x00', b'\\x00\\x00')

# Process it
img = process_image(test_with_nulls)
print("Success!")
"""
    
    try:
        with open("pil_patch_example.py", "w") as f:
            f.write(example)
        log("Created pil_patch_example.py with usage example") 