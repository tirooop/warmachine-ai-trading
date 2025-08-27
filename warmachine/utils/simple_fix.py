#!/usr/bin/env python
"""
Simple PIL/Pillow Fix

Minimal patch for fixing Pillow/PIL compatibility with null bytes in images.
"""

from PIL import Image
import io

# Store original open function
original_open = Image.open

# Create patched version
def patched_open(fp, mode='r', formats=None):
    """Patched version of PIL.Image.open that handles null bytes"""
    try:
        # Try normal open first
        return original_open(fp, mode, formats)
    except Exception as e:
        # If it failed and it's a file-like object, try clean approach
        if hasattr(fp, 'read') and hasattr(fp, 'seek'):
            try:
                # Get current position
                fp.seek(0)
                data = fp.read()
                
                # Clean data if it's bytes with null bytes
                if isinstance(data, bytes) and b'\x00\x00' in data:
                    # Replace consecutive null bytes with single ones
                    data = data.replace(b'\x00\x00', b'\x00')
                    # Create new BytesIO with cleaned data
                    cleaned_fp = io.BytesIO(data)
                    # Try again with cleaned data
                    return original_open(cleaned_fp, mode, formats)
            except:
                # If this fails, just continue
                pass
                
            # Reset position in case we need to retry
            try:
                fp.seek(0)
            except:
                pass
                
        # Try again with original function
        return original_open(fp, mode, formats)

# Apply the patch
Image.open = patched_open
print("[SIMPLE_FIX] Applied PIL/Pillow patch for null bytes")

# Simple test function
def test():
    """Test if patch works"""
    test_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
    test_with_nulls = test_png.replace(b'\x00', b'\x00\x00')
    
    try:
        # Test with null bytes
        fp = io.BytesIO(test_with_nulls)
        img = Image.open(fp)
        img.load()  # Force load
        print("[SIMPLE_FIX] Test successful - can handle images with null bytes")
        return True
    except Exception as e:
        print(f"[SIMPLE_FIX] Test failed: {e}")
        return False

if __name__ == "__main__":
    # Run test when executed directly
    test() 