"""
Windows-specific Pillow/imghdr Fix Script

This script provides a Windows-focused fix for the imghdr module and PIL/Pillow compatibility issues.
It addresses the "unexpected indent" error in imghdr and PIL/Pillow compatibility with null bytes.

Usage:
    python fix_imghdr_windows.py
"""

import os
import sys
import importlib
import importlib.util
import site
import platform
import subprocess
import logging
import tempfile
import io
import shutil
import ctypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("windows_imghdr_fixer")

# Check if running as administrator
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

# Patched imghdr module content
IMGHDR_PATCH = """
# Patched imghdr module that handles null bytes correctly
# This addresses compatibility issues with PIL/Pillow

__all__ = ["what"]

import os
import struct

def what(file, h=None):
    \"\"\"Recognize image file formats based on their first few bytes.\"\"\"
    if h is None:
        if isinstance(file, str):
            try:
                with open(file, 'rb') as f:
                    h = f.read(32)
            except IOError:
                return None
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
            if not h:
                return None

    # Strip null bytes that might appear in image data
    if h and isinstance(h, bytes):
        h = h.replace(b'\\x00', b'')

    if not h:
        return None

    if h[:1] == b'\\377':
        # JPEG (jpeg_factory can handle SOI + EOI + JFIF/Exif APP1)
        for marker in [b'\\330\\377', b'\\356\\377', b'\\355\\377']:
            if marker in h:
                return 'jpeg'
        return None

    # All PNG files start with the same 8 bytes
    if h.startswith(b'\\211PNG\\r\\n\\032\\n'):
        return 'png'

    # GIF ('87a' or '89a')
    if h[:6] in [b'GIF87a', b'GIF89a']:
        return 'gif'

    # TIFF (can be in Motorola or Intel byte order)
    if h[:2] in [b'MM', b'II']:
        if h[2:4] == b'\\x00\\x2a':
            return 'tiff'

    # BMP files start with BM
    if h.startswith(b'BM'):
        return 'bmp'

    # WEBP has a 12-byte header
    if h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'

    # ICO files
    if h[:4] in [b'\\x00\\x00\\x01\\x00', b'\\x00\\x00\\x02\\x00']:
        return 'ico'

    # Additional formats
    if h.startswith(b'P6') or h.startswith(b'P5') or h.startswith(b'P4'):
        return 'ppm'

    if b'#define' in h:
        return 'xbm'

    # SVG detection
    if b'<?xml' in h and b'<svg' in h:
        return 'svg'
    if h.startswith(b'<svg'):
        return 'svg'

    return None
"""

# PIL compatibility patch
PIL_PATCH = """
# PIL/Pillow compatibility patch

import io
import sys

# Patch PIL.Image.open
try:
    from PIL import Image
    _original_open = Image.open
    
    def _patched_open(fp, mode='r', formats=None):
        try:
            return _original_open(fp, mode, formats)
        except (SyntaxError, ValueError) as e:
            if isinstance(fp, (str, bytes, io.IOBase)):
                # Retry with a more robust approach
                if hasattr(fp, 'seek'):
                    try:
                        fp.seek(0)
                    except:
                        pass
                return _original_open(fp, mode, formats)
            raise e
            
    Image.open = _patched_open
except ImportError:
    pass

# Patch imghdr
try:
    import imghdr
    _original_what = imghdr.what
    
    def _patched_what(file, h=None):
        if h is None:
            if isinstance(file, str):
                try:
                    with open(file, 'rb') as f:
                        h = f.read(32)
                except IOError:
                    return None
            else:
                location = file.tell()
                h = file.read(32)
                file.seek(location)
                if not h:
                    return None
    
        # Strip null bytes that might appear in image data
        if h and isinstance(h, bytes):
            h = h.replace(b'\\x00', b'')
    
        # Call the original logic but with our preprocessed h
        return _original_what(file, h)
    
    # Apply the patch
    imghdr.what = _patched_what
    sys.modules['imghdr'].what = _patched_what
except ImportError:
    pass
"""

def find_imghdr_path():
    """Find the path to the imghdr module"""
    try:
        # Try to find the module using importlib
        spec = importlib.util.find_spec("imghdr")
        if spec is not None and spec.origin is not None and spec.origin != "built-in":
            return spec.origin
        
        # Fallback method: import and check __file__
        if importlib.util.find_spec("imghdr") is not None:
            import imghdr
            if hasattr(imghdr, "__file__"):
                return imghdr.__file__
    except:
        logger.warning("Could not find imghdr module path using importlib")
    
    # Second fallback: Look in standard library directories
    for path in sys.path:
        imghdr_path = os.path.join(path, "imghdr.py")
        if os.path.exists(imghdr_path):
            return imghdr_path
    
    return None

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.bak"
    if not os.path.exists(backup_path):
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    return True

def patch_system_imghdr():
    """Patch the system imghdr module"""
    imghdr_path = find_imghdr_path()
    if not imghdr_path:
        logger.error("Could not find imghdr module path")
        return False
    
    logger.info(f"Found imghdr module at: {imghdr_path}")
    
    # Create backup
    if not create_backup(imghdr_path):
        logger.error("Failed to create backup, aborting patch")
        return False
    
    # Write patched file
    try:
        with open(imghdr_path, 'w') as f:
            f.write(IMGHDR_PATCH)
        logger.info(f"Successfully patched imghdr module")
        return True
    except Exception as e:
        logger.error(f"Failed to patch imghdr module: {e}")
        return False

def create_local_patch():
    """Create a local patch file that can be imported in scripts"""
    try:
        with open("imghdr_patch.py", "w") as f:
            f.write(PIL_PATCH)
        logger.info("Created local patch file: imghdr_patch.py")
        
        # Create README with instructions
        with open("IMGHDR_PATCH_README.txt", "w") as f:
            f.write("PIL/Pillow and imghdr Patch\n")
            f.write("==========================\n\n")
            f.write("To use this patch, add the following line at the beginning of your scripts:\n\n")
            f.write("    import imghdr_patch\n\n")
            f.write("This will fix compatibility issues between PIL/Pillow and the imghdr module.\n")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create local patch: {e}")
        return False

def reinstall_pillow():
    """Reinstall Pillow to fix potential issues"""
    try:
        logger.info("Reinstalling Pillow...")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "Pillow", "PIL"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "Pillow"])
        
        try:
            import PIL
            logger.info(f"Successfully reinstalled Pillow version {PIL.__version__}")
            return True
        except ImportError:
            logger.error("Failed to import PIL after reinstallation")
            return False
    except Exception as e:
        logger.error(f"Failed to reinstall Pillow: {e}")
        return False

def test_patch():
    """Test if the patch is working correctly"""
    # Create a simple test image with null bytes
    test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
    
    # Add some null bytes to simulate the problem
    test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
    
    try:
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.write(fd, test_image_with_nulls)
        os.close(fd)
        
        # Import imghdr and test
        import imghdr
        importlib.reload(imghdr)  # Reload to get our changes
        
        result = imghdr.what(temp_path)
        result2 = imghdr.what(io.BytesIO(test_image_with_nulls))
        
        # Clean up
        os.unlink(temp_path)
        
        if result == 'png' and result2 == 'png':
            logger.info("Patch test PASSED - imghdr correctly identifies PNG with null bytes")
            return True
        else:
            logger.error(f"Patch test FAILED - file: {result}, buffer: {result2}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing patch: {e}")
        return False

def test_pillow():
    """Test PIL/Pillow with patched imghdr"""
    try:
        from PIL import Image
        import io
        
        # Create a simple test image with null bytes
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'
        test_image_with_nulls = test_image.replace(b'\x00', b'\x00\x00')
        
        # Test opening image from buffer
        img_io = io.BytesIO(test_image_with_nulls)
        img = Image.open(img_io)
        img.load()  # Force load to check for errors
        
        logger.info("Pillow test PASSED - PIL can open images with null bytes")
        return True
    except ImportError:
        logger.warning("PIL/Pillow not installed, skipping test")
        return None
    except Exception as e:
        logger.error(f"Pillow test FAILED: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Windows Pillow/imghdr Fix Script")
    logger.info("=" * 60)
    
    # Check Python version
    python_version = platform.python_version()
    logger.info(f"Python version: {python_version}")
    logger.info(f"Platform: {platform.platform()}")
    
    # Check for PIL
    try:
        import PIL
        logger.info(f"PIL/Pillow version: {PIL.__version__}")
    except ImportError:
        logger.info("PIL/Pillow not installed")
    
    # Check admin rights
    admin = is_admin()
    logger.info(f"Running as administrator: {'Yes' if admin else 'No'}")
    
    if not admin:
        logger.warning("Some operations may fail without administrator privileges")
        logger.warning("Consider rerunning this script as administrator")
    
    # Step 1: Patch system imghdr if possible
    logger.info("\nStep 1: Patching system imghdr module...")
    system_patched = patch_system_imghdr()
    
    # Step 2: Create local patch
    logger.info("\nStep 2: Creating local patch...")
    local_patched = create_local_patch()
    
    # Step 3: Reinstall Pillow
    logger.info("\nStep 3: Reinstalling Pillow...")
    pillow_reinstalled = reinstall_pillow()
    
    # Step 4: Test the patch
    logger.info("\nStep 4: Testing patch...")
    patch_works = test_patch()
    
    # Step 5: Test Pillow
    logger.info("\nStep 5: Testing Pillow...")
    pillow_works = test_pillow()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary of Results")
    logger.info("=" * 60)
    logger.info(f"System imghdr patched: {'✅ Success' if system_patched else '❌ Failed'}")
    logger.info(f"Local patch created: {'✅ Success' if local_patched else '❌ Failed'}")
    logger.info(f"Pillow reinstalled: {'✅ Success' if pillow_reinstalled else '❌ Failed'}")
    logger.info(f"Patch test: {'✅ Success' if patch_works else '❌ Failed'}")
    
    if pillow_works is not None:
        logger.info(f"Pillow test: {'✅ Success' if pillow_works else '❌ Failed'}")
    else:
        logger.info("Pillow test: ⚠️ Skipped (PIL not installed)")
    
    # Instructions
    logger.info("\n" + "-" * 60)
    logger.info("Instructions for Use")
    logger.info("-" * 60)
    
    if system_patched and patch_works:
        logger.info("✅ The system-wide patch has been successfully applied.")
        logger.info("   You shouldn't need to do anything else.")
    
    if local_patched:
        logger.info("To use the local patch in your scripts, add this import statement at the top:")
        logger.info("    import imghdr_patch")
    
    if not (system_patched or local_patched) or not patch_works:
        logger.info("The patch could not be applied or failed testing.")
        logger.info("Try running this script as administrator.")
    
    logger.info("\nFix process complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 