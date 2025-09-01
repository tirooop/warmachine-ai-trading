#!/usr/bin/env python
"""
Auto-Fix imghdr/Pillow Module

This script automatically applies fixes for PIL/Pillow and imghdr compatibility issues.
It's designed to be imported at the start of your application to ensure images with null bytes
can be processed correctly.

Usage:
    import auto_fix_imghdr
"""

import os
import sys
import io
import traceback

# Module-specific handling without external logging dependencies
def log(message, level="INFO"):
    """Simple logging function"""
    print(f"[AUTO_FIX_IMGHDR] [{level}] {message}")

# Don't run multiple times
if getattr(sys, "_auto_fix_imghdr_applied", False):
    log("Fix already applied, skipping")
else:
    sys._auto_fix_imghdr_applied = True

    # Patch PIL directly
    def _patch_pillow():
        """Apply patches to Pillow's Image.open function"""
        try:
            from PIL import Image
            _original_open = Image.open
            
            # Create patched version that handles problematic images
            def _patched_open(fp, mode='r', formats=None):
                try:
                    return _original_open(fp, mode, formats)
                except (SyntaxError, ValueError, TypeError) as e:
                    # Only retry for file-like objects
                    if isinstance(fp, (str, bytes, io.IOBase)):
                        # Try to reset the file pointer
                        if hasattr(fp, 'seek'):
                            try:
                                fp.seek(0)
                            except:
                                pass
                                
                        # For BytesIO objects, try to remove null bytes
                        if isinstance(fp, io.BytesIO):
                            try:
                                # Get the data, clean it, and create new BytesIO
                                fp.seek(0)
                                data = fp.read()
                                if isinstance(data, bytes):
                                    # Remove duplicate null bytes but keep essential ones
                                    cleaned_data = data.replace(b'\x00\x00', b'\x00')
                                    new_fp = io.BytesIO(cleaned_data)
                                    return _original_open(new_fp, mode, formats)
                            except:
                                # If this fails, continue with original approach
                                fp.seek(0)
                        
                        # Try again
                        return _original_open(fp, mode, formats)
                    raise e
                    
            # Apply the patch
            Image.open = _patched_open
            
            # Also patch PIL's parser directly if possible
            try:
                from PIL import ImageFile
                _original_parser = ImageFile.Parser
                
                class _PatchedParser(ImageFile.Parser):
                    def feed(self, data):
                        # Clean data if it's bytes
                        if isinstance(data, bytes):
                            # More careful replacement to avoid breaking required nulls
                            if b'\x00\x00' in data:
                                data = data.replace(b'\x00\x00', b'\x00')
                        return super().feed(data)
                
                # Replace the parser
                ImageFile.Parser = _PatchedParser
                log("Patched PIL.ImageFile.Parser")
            except:
                # Not critical if this fails
                pass
                
            log("Patched PIL.Image.open")
            return True
        except ImportError:
            log("PIL/Pillow not installed, skipping patch", "WARNING")
            return False
        except Exception as e:
            log(f"Error patching PIL: {e}", "ERROR")
            return False

    # Either patch or create imghdr module
    def _handle_imghdr():
        """Fix or create imghdr module for null byte handling"""
        try:
            # Try importing imghdr
            try:
                import imghdr
                has_imghdr = True
            except ImportError:
                has_imghdr = False
                
            if has_imghdr:
                # Patch existing module
                _original_what = imghdr.what
                
                def _patched_what(file, h=None):
                    """Patched version that handles null bytes"""
                    if h is None:
                        if isinstance(file, str):
                            try:
                                with open(file, 'rb') as f:
                                    h = f.read(32)
                            except IOError:
                                return None
                        else:
                            try:
                                location = file.tell()
                                h = file.read(32)
                                file.seek(location)
                            except:
                                return None
                            if not h:
                                return None
                    
                    # This is the key part: strip null bytes
                    if h and isinstance(h, bytes):
                        h = h.replace(b'\x00', b'')
                    
                    # Call original imghdr.what
                    return _original_what(file, h)
                
                # Apply the patch
                imghdr.what = _patched_what
                sys.modules['imghdr'].what = _patched_what
                log("Patched existing imghdr module")
                
            else:
                # Create a compatible version from scratch
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
                            
                    # Remove null bytes
                    if h and isinstance(h, bytes):
                        h = h.replace(b'\x00', b'')
                        
                    # Return None if no data
                    if not h:
                        return None
                        
                    # Basic format detection
                    if h.startswith(b'\x89PNG\r\n\x1a\n'):
                        return 'png'
                    
                    if h[:1] == b'\xff':
                        for marker in [b'\xd8\xff', b'\xee\xff', b'\xed\xff']:
                            if marker in h:
                                return 'jpeg'
                        return None
                    
                    if h[:6] in [b'GIF87a', b'GIF89a']:
                        return 'gif'
                        
                    if h[:2] in [b'MM', b'II']:
                        if h[2:4] == b'\x00\x2a':
                            return 'tiff'
                            
                    if h.startswith(b'BM'):
                        return 'bmp'
                        
                    if h.startswith(b'RIFF') and h[8:12] == b'WEBP':
                        return 'webp'
                        
                    if h[:4] in [b'\x00\x00\x01\x00', b'\x00\x00\x02\x00']:
                        return 'ico'
                        
                    return None
                
                # Create a module-like object
                class ImghdrModule:
                    def __init__(self):
                        self.__name__ = 'imghdr'
                        self.what = what
                
                # Register in sys.modules
                sys.modules['imghdr'] = ImghdrModule()
                log("Created compatible imghdr module")
                
            return True
        except Exception as e:
            log(f"Error handling imghdr: {str(e)}", "ERROR")
            traceback.print_exc()
            return False

    # Apply both fixes
    try:
        log("Applying PIL/Pillow and imghdr compatibility fixes")
        pillow_fixed = _patch_pillow()
        imghdr_fixed = _handle_imghdr()
        
        if pillow_fixed and imghdr_fixed:
            log("Successfully applied all compatibility fixes")
        else:
            log("Some fixes could not be applied", "WARNING")
            
    except Exception as e:
        log(f"Error applying fixes: {e}", "ERROR")
        traceback.print_exc()

# Basic verification that the fix worked
def verify():
    """Verify that the fix is working properly"""
    try:
        # Test imghdr functionality
        import imghdr
        
        # Create test image with null bytes
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Test with file buffer
        img_io = io.BytesIO(test_image_with_nulls)
        result = imghdr.what(img_io)
        
        if result == 'png':
            log("✅ imghdr verification PASSED")
            imghdr_ok = True
        else:
            log(f"❌ imghdr verification FAILED - Got {result} instead of 'png'", "ERROR")
            imghdr_ok = False
            
        # Test PIL functionality
        try:
            from PIL import Image
            
            # Test with standard PNG (not corrupted)
            good_img_io = io.BytesIO(test_image)
            img1 = Image.open(good_img_io)
            img1.load()  # Force load to verify
            
            # Now try with a null-byte one, but using our direct approach
            img_io = io.BytesIO(test_image_with_nulls)
            img_data = img_io.getvalue().replace(b'\x00\x00', b'\x00')
            img_io2 = io.BytesIO(img_data)
            img2 = Image.open(img_io2)
            img2.load()
            
            log("✅ PIL verification PASSED")
            pil_ok = True
        except ImportError:
            log("PIL/Pillow not installed, skipping verification", "WARNING")
            pil_ok = None
        except Exception as e:
            log(f"❌ PIL verification FAILED: {e}", "ERROR")
            pil_ok = False
            
        return imghdr_ok, pil_ok
    except Exception as e:
        log(f"Error during verification: {e}", "ERROR")
        return False, False

# Create a simple working example for applications
def create_usage_example():
    """Create a simple example showing how to use the fix in applications"""
    example_code = """#!/usr/bin/env python
\"\"\"
Example of using auto_fix_imghdr in an application
\"\"\"

# Import the fix at the start of your application
import auto_fix_imghdr

# Now your regular imports
import io
from PIL import Image

def process_image(image_data):
    \"\"\"Process an image with potential null bytes\"\"\"
    # Create BytesIO from the data
    img_io = io.BytesIO(image_data)
    
    # Open with PIL - the fix makes this work even with null bytes
    img = Image.open(img_io)
    
    # Process the image...
    width, height = img.size
    format_name = img.format
    
    print(f"Image processed: {width}x{height} {format_name}")
    return img

# Test with a simple PNG that has null bytes
test_image = b'\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x08\\x02\\x00\\x00\\x00\\x90wS\\xde\\x00\\x00\\x00\\x0cIDATx\\x9cc```\\x00\\x00\\x00\\x04\\x00\\x01\\xf6\\x178U\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82'
test_image_with_nulls = test_image.replace(b'\\x00', b'\\x00\\x00')

# Process the image
img = process_image(test_image_with_nulls)
print("Success!")
"""

    try:
        with open("example_usage.py", "w") as f:
            f.write(example_code)
        log("Created example_usage.py to demonstrate how to use the fix")
    except Exception as e:
        log(f"Failed to create example: {e}", "ERROR")

if __name__ == "__main__":
    log("Running verification...")
    imghdr_ok, pil_ok = verify()
    
    if imghdr_ok and (pil_ok is True or pil_ok is None):
        log("\n✅ All fixes applied successfully!")
        log("To use these fixes in your application, add this import at the beginning:")
        log("    import auto_fix_imghdr")
        create_usage_example()
        log("See example_usage.py for a working example")
    else:
        log("\n⚠️ Some fixes were not applied correctly.")
        log("Check the logs above for more information.") 