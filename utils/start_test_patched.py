#!/usr/bin/env python
"""
Test Script for Pillow/imghdr Patch

This script tests if the local patch is working correctly
by attempting to load and process image data with null bytes.
"""

import os
import sys
import io
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("patch_tester")

# Import the local patch
try:
    import imghdr_patch
    logger.info("Successfully imported imghdr_patch")
except ImportError:
    logger.error("Failed to import imghdr_patch - file may be missing")
    logger.info("Run fix_imghdr_windows.py first to create the patch")
    sys.exit(1)

# Test PIL/Pillow functionality
def test_pillow():
    try:
        from PIL import Image
        logger.info(f"PIL/Pillow is installed")
        
        # Create a simple test PNG image with null bytes
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Try to open the image with null bytes
        img_io = io.BytesIO(test_image_with_nulls)
        img = Image.open(img_io)
        img.load()  # Force load to check for errors
        
        logger.info("✅ PIL/Pillow test PASSED - Can open images with null bytes")
        return True
    except ImportError:
        logger.error("❌ PIL/Pillow is not installed")
        return False
    except Exception as e:
        logger.error(f"❌ PIL/Pillow test FAILED: {e}")
        return False

# Try to manually create imghdr functionality if not available
def create_imghdr_fallback():
    logger.info("Creating imghdr fallback functionality")
    
    # Define a minimal imghdr.what function
    def what(file, h=None):
        """Simple implementation of imghdr.what that handles null bytes"""
        if h is None:
            if isinstance(file, str):
                try:
                    with open(file, 'rb') as f:
                        h = f.read(32)
                except:
                    return None
            else:
                try:
                    pos = file.tell()
                    h = file.read(32)
                    file.seek(pos)
                except:
                    return None
                
        # Remove null bytes that might be problematic
        if h and isinstance(h, bytes):
            h = h.replace(b'\x00', b'')
            
        # Check PNG signature
        if h.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        
        # Check JPEG signature
        if h[:2] == b'\xff\xd8':
            return 'jpeg'
            
        # Check GIF signature
        if h[:6] in [b'GIF87a', b'GIF89a']:
            return 'gif'
            
        return None
    
    # Create a module-like object
    class ImghdrModule:
        def __init__(self):
            self.what = what
    
    # Register in sys.modules if not there
    if 'imghdr' not in sys.modules:
        sys.modules['imghdr'] = ImghdrModule()
        
    return sys.modules['imghdr']

# Test if imghdr works
def test_imghdr():
    try:
        # Try to import imghdr
        try:
            import imghdr
            logger.info("imghdr module is available")
        except ImportError:
            logger.warning("imghdr module not found, creating fallback")
            imghdr = create_imghdr_fallback()
        
        # Test PNG identification with null bytes
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Test with BytesIO
        img_io = io.BytesIO(test_image_with_nulls)
        result = imghdr.what(img_io)
        
        if result == 'png':
            logger.info("✅ imghdr test PASSED - Can identify PNG with null bytes")
            return True
        else:
            logger.error(f"❌ imghdr test FAILED - Got {result} instead of 'png'")
            return False
    except Exception as e:
        logger.error(f"❌ imghdr test FAILED: {e}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("Pillow/imghdr Patch Test")
    logger.info("=" * 60)
    
    # Test if PIL/Pillow works
    pillow_works = test_pillow()
    
    # Test if imghdr works
    imghdr_works = test_imghdr()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Results")
    logger.info("=" * 60)
    logger.info(f"PIL/Pillow test: {'✅ Success' if pillow_works else '❌ Failed'}")
    logger.info(f"imghdr test: {'✅ Success' if imghdr_works else '❌ Failed'}")
    
    if pillow_works and imghdr_works:
        logger.info("\n✅ All tests PASSED - Your system is ready to run")
        return 0
    else:
        logger.info("\n⚠️ Some tests FAILED - Check the logs for details")
        
        # Suggestions
        logger.info("\nTroubleshooting suggestions:")
        if not pillow_works:
            logger.info("1. Try reinstalling Pillow: pip install --upgrade Pillow")
        
        if not imghdr_works:
            logger.info("2. Try running fix_imghdr_windows.py as administrator")
            logger.info("3. Make sure imghdr_patch.py exists in the current directory")
        
        return 1

if __name__ == "__main__":
    sys.exit(main()) 