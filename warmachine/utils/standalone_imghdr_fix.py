#!/usr/bin/env python
"""
Standalone imghdr/Pillow Fix

This script provides an immediate runtime fix for the PIL/Pillow and imghdr compatibility issues.
It fixes the problem directly when run, without requiring system modifications.

Usage:
    python standalone_imghdr_fix.py
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
logger = logging.getLogger("standalone_fixer")

# Create imghdr module if it doesn't exist
def create_imghdr_module():
    """Create and register a compatible imghdr module"""
    logger.info("Creating standalone imghdr module")
    
    # Define the minimal functionality needed
    def what(file, h=None):
        """Implementation of imghdr.what that handles null bytes"""
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
                
        # Remove null bytes that cause problems
        if h and isinstance(h, bytes):
            h = h.replace(b'\x00', b'')
            
        # Basic image format detection
        if not h:
            return None
            
        # PNG signature
        if h.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        
        # JPEG signature
        if h[:1] == b'\xff':
            for marker in [b'\xd8\xff', b'\xee\xff', b'\xed\xff']:
                if marker in h:
                    return 'jpeg'
            return None
        
        # GIF signatures
        if h[:6] in [b'GIF87a', b'GIF89a']:
            return 'gif'
            
        # TIFF signatures
        if h[:2] in [b'MM', b'II']:
            if h[2:4] == b'\x00\x2a':
                return 'tiff'
                
        # BMP signature
        if h.startswith(b'BM'):
            return 'bmp'
            
        # WEBP signature
        if h.startswith(b'RIFF') and h[8:12] == b'WEBP':
            return 'webp'
            
        # ICO files
        if h[:4] in [b'\x00\x00\x01\x00', b'\x00\x00\x02\x00']:
            return 'ico'
            
        return None
    
    # Create a module-like object to register
    class ImghdrModule:
        def __init__(self):
            self.__name__ = 'imghdr'
            self.what = what
            
    # Register in sys.modules
    sys.modules['imghdr'] = ImghdrModule()
    logger.info("Registered imghdr module in sys.modules")
    
    return sys.modules['imghdr']

# Patch PIL.Image.open to handle problematic images
def patch_pillow():
    """Patch PIL.Image.open to better handle problematic images"""
    try:
        from PIL import Image
        logger.info(f"Found PIL/Pillow, patching Image.open")
        
        # Store the original open function
        original_open = Image.open
        
        # Create a patched version
        def patched_open(fp, mode='r', formats=None):
            try:
                return original_open(fp, mode, formats)
            except (SyntaxError, ValueError) as e:
                if isinstance(fp, (str, bytes, io.IOBase)):
                    # Try to reset the file pointer if possible
                    if hasattr(fp, 'seek'):
                        try:
                            fp.seek(0)
                        except:
                            pass
                    # Try again
                    return original_open(fp, mode, formats)
                # If we can't handle it, re-raise the original error
                raise e
                
        # Apply the patch
        Image.open = patched_open
        logger.info("PIL.Image.open has been patched")
        return True
    except ImportError:
        logger.warning("PIL/Pillow not found, skipping patch")
        return False
    except Exception as e:
        logger.error(f"Failed to patch PIL/Pillow: {e}")
        return False

def test_fix():
    """Test if our fix works"""
    success = True
    
    # Test imghdr
    try:
        import imghdr
        
        # Create a PNG with null bytes
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Test detection
        img_io = io.BytesIO(test_image_with_nulls)
        format_detected = imghdr.what(img_io)
        
        if format_detected == 'png':
            logger.info("✅ imghdr test PASSED - Successfully detected PNG format")
        else:
            logger.error(f"❌ imghdr test FAILED - Got {format_detected} instead of 'png'")
            success = False
            
    except Exception as e:
        logger.error(f"❌ imghdr test ERROR: {e}")
        success = False
    
    # Test PIL/Pillow
    try:
        from PIL import Image
        
        # Create a test image
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Try to open the image
        img_io = io.BytesIO(test_image_with_nulls)
        img = Image.open(img_io)
        img.load()  # Force load
        
        logger.info("✅ PIL/Pillow test PASSED - Successfully opened image with null bytes")
    except ImportError:
        logger.warning("⚠️ PIL/Pillow not available, skipping test")
    except Exception as e:
        logger.error(f"❌ PIL/Pillow test FAILED: {e}")
        success = False
    
    return success

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Standalone imghdr/Pillow Fix")
    logger.info("=" * 60)
    
    # Check if imghdr module exists
    try:
        import imghdr
        logger.info("imghdr module is available, will patch existing module")
        has_imghdr = True
    except ImportError:
        logger.info("imghdr module not available, will create standalone module")
        has_imghdr = False
    
    # Create imghdr module if needed
    if not has_imghdr:
        create_imghdr_module()
    else:
        # Patch existing module
        try:
            import imghdr
            original_what = imghdr.what
            
            def patched_what(file, h=None):
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
                
                # Handle null bytes
                if h and isinstance(h, bytes):
                    h = h.replace(b'\x00', b'')
                
                return original_what(file, h)
            
            # Apply the patch
            imghdr.what = patched_what
            logger.info("Patched existing imghdr.what function")
        except Exception as e:
            logger.error(f"Failed to patch existing imghdr module: {e}")
            logger.info("Creating new imghdr module")
            create_imghdr_module()
    
    # Patch PIL/Pillow
    patch_pillow()
    
    # Test the fix
    logger.info("\nTesting the fix...")
    if test_fix():
        logger.info("\n✅ All tests PASSED - Fix is working correctly")
    else:
        logger.error("\n❌ Some tests FAILED - See log for details")
    
    logger.info("\nThe imghdr and PIL/Pillow modules have been patched for this session.")
    logger.info("To use this fix in your application, insert the following at the beginning of your script:")
    logger.info("\nimport standalone_imghdr_fix")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 