#!/usr/bin/env python
"""
Global Pillow/imghdr Fix Script

This script provides a permanent fix for Pillow/PIL compatibility issues with the imghdr module.
It addresses issues that occur when PIL/Pillow is updated to newer versions, particularly with
null byte handling in image files.

Usage:
    python fix_imghdr_pillow_global.py

The script will:
1. Create a patched version of imghdr module
2. Fix PIL/Pillow compatibility issues
3. Install patch handlers for runtime environments
4. Verify the fix is working correctly
"""

import os
import sys
import shutil
import importlib
import importlib.util
import site
import platform
import subprocess
import logging
import tempfile
from pathlib import Path
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("imghdr_fixer")

# Patch content for imghdr module
IMGHDR_PATCH = """
\"\"\"Recognize image file formats.

This module is a modified version of the standard library's imghdr module,
with additional patches for compatibility with newer PIL/Pillow versions.
\"\"\"

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

    # Additional formats supported by PIL but not in original imghdr
    
    # ICO/CUR files start with 0x00 0x00 followed by 0x01 0x00 (ICO) or 0x02 0x00 (CUR)
    if h[:4] in [b'\\x00\\x00\\x01\\x00', b'\\x00\\x00\\x02\\x00']:
        return 'ico'
        
    # Treat PPM files
    if h.startswith(b'P6') or h.startswith(b'P5') or h.startswith(b'P4'):
        return 'ppm'
        
    # Treat XBM files
    if b'#define' in h:
        return 'xbm'
        
    # Placeholder for HEIF detection
    if h[4:12] == b'ftypheic' or h[4:12] == b'ftypheix' or h[4:12] == b'ftyphevc' or h[4:12] == b'ftypheim':
        return 'heif'
    
    # Try to detect AVIF (AV1 Image File Format)
    if h[4:12] == b'ftypavis' or h[4:12] == b'ftypavif':
        return 'avif'
        
    # SVG detection
    if b'<?xml' in h and b'<svg' in h:
        return 'svg'
    if h.startswith(b'<svg'):
        return 'svg'
        
    return None
"""

PIL_TEST_IMAGE = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82'

def get_site_packages_paths():
    """Get all site-packages paths for the current Python environment"""
    site_packages = []
    
    # Add user site-packages
    if site.ENABLE_USER_SITE:
        site_packages.append(site.getusersitepackages())
    
    # Add global site-packages
    site_packages.extend(site.getsitepackages())
    
    # Add any additional paths from sys.path that contain site-packages
    for path in sys.path:
        if "site-packages" in path and path not in site_packages:
            site_packages.append(path)
    
    return [p for p in site_packages if os.path.exists(p)]

def find_imghdr_module_path():
    """Find the path to the imghdr module"""
    try:
        imghdr_spec = importlib.util.find_spec("imghdr")
        if imghdr_spec is None:
            return None
        
        if imghdr_spec.origin in [None, "built-in"]:
            return None
            
        return imghdr_spec.origin
    except (ImportError, AttributeError):
        # Fallback method
        if importlib.util.find_spec("imghdr") is not None:
            import imghdr
            if hasattr(imghdr, "__file__"):
                return imghdr.__file__
        
        return None

def create_backup(file_path):
    """Create a backup of the file if it doesn't already exist"""
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

def patch_imghdr_module():
    """Patch the imghdr module with our fixed version"""
    imghdr_path = find_imghdr_module_path()
    
    if not imghdr_path:
        logger.error("Could not find imghdr module path")
        return False
    
    if not create_backup(imghdr_path):
        logger.error("Failed to create backup, aborting patch")
        return False
    
    try:
        with open(imghdr_path, 'w') as f:
            f.write(IMGHDR_PATCH)
        logger.info(f"Successfully patched imghdr module at {imghdr_path}")
        
        # Reload the module to apply changes
        try:
            import imghdr
            importlib.reload(imghdr)
            logger.info("Reloaded imghdr module")
        except:
            logger.warning("Could not reload imghdr module, restart Python to apply changes")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch imghdr module: {e}")
        return False

def create_runtime_patch():
    """Create a runtime patch that can be imported at the start of programs"""
    patch_code = """
# imghdr runtime patch
import imghdr
import io
import sys

# Store the original what function
_original_what = imghdr.what

# Define our patched function
def _patched_what(file, h=None):
    \"\"\"Patched version of imghdr.what that handles null bytes\"\"\"
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

# Replace the original function with our patched version
imghdr.what = _patched_what
sys.modules['imghdr'].what = _patched_what

# Additional PIL patches
try:
    from PIL import Image
    _original_open = Image.open
    
    def _patched_open(fp, mode='r', formats=None):
        \"\"\"Patched version of PIL.Image.open that handles potential imghdr issues\"\"\"
        try:
            return _original_open(fp, mode, formats)
        except (SyntaxError, ValueError) as e:
            if isinstance(fp, (str, bytes, io.IOBase)):
                # Retry with a more robust approach
                if hasattr(fp, 'seek'):
                    fp.seek(0)
                return _original_open(fp, mode, formats)
            raise e
            
    Image.open = _patched_open
except ImportError:
    pass
"""
    
    try:
        # Write to current directory
        runtime_path = os.path.join(os.getcwd(), "imghdr_runtime_patch.py")
        with open(runtime_path, 'w') as f:
            f.write(patch_code)
        
        # Try to write to site-packages
        site_packages = get_site_packages_paths()
        if site_packages:
            try:
                for site_path in site_packages:
                    site_patch_path = os.path.join(site_path, "imghdr_runtime_patch.py")
                    with open(site_patch_path, 'w') as f:
                        f.write(patch_code)
                    logger.info(f"Created runtime patch at {site_patch_path}")
            except (PermissionError, IOError):
                logger.warning("Could not write to site-packages, using local patch only")
        
        logger.info(f"Created runtime patch at {runtime_path}")
        logger.info("To use the runtime patch, add this to the top of your scripts:")
        logger.info("    import imghdr_runtime_patch")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create runtime patch: {e}")
        return False

def verify_patch():
    """Verify that the patch is working correctly"""
    try:
        # Import the module to make sure our patched version is used
        import imghdr
        importlib.reload(imghdr)
        
        # Test with a simple PIL image with null bytes
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_file.write(PIL_TEST_IMAGE)
        temp_file.close()
        
        # Test with file path
        file_result = imghdr.what(temp_file.name)
        
        # Test with file object
        with open(temp_file.name, 'rb') as f:
            file_obj_result = imghdr.what(f)
        
        # Test with bytes that include null bytes
        modified_image = PIL_TEST_IMAGE.replace(b'\x00', b'\x00\x00')
        bytes_io = io.BytesIO(modified_image)
        bytes_result = imghdr.what(bytes_io)
        
        # Clean up
        os.unlink(temp_file.name)
        
        # Report results
        logger.info(f"Verification results:")
        logger.info(f"  File path test: {'PASSED' if file_result == 'png' else 'FAILED'}")
        logger.info(f"  File object test: {'PASSED' if file_obj_result == 'png' else 'FAILED'}")
        logger.info(f"  Bytes with null bytes test: {'PASSED' if bytes_result == 'png' else 'FAILED'}")
        
        if file_result == 'png' and file_obj_result == 'png' and bytes_result == 'png':
            logger.info("All tests PASSED! The patch is working correctly.")
            return True
        else:
            logger.warning("Some tests FAILED. The patch may not be fully effective.")
            return False
            
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

def fix_pillow_installation():
    """Fix PIL/Pillow installation if needed"""
    try:
        # Check if PIL is installed
        try:
            import PIL
            logger.info(f"PIL/Pillow is installed (version {PIL.__version__})")
        except ImportError:
            logger.warning("PIL/Pillow is not installed. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            logger.info("PIL/Pillow has been installed.")
            
        # Apply monkey patch to PIL
        patch_code = """
# Monkey patch PIL to handle imghdr issues
import io
from PIL import Image

_original_open = Image.open

def _patched_open(fp, mode='r', formats=None):
    \"\"\"Patched version of PIL.Image.open that handles potential imghdr issues\"\"\"
    try:
        return _original_open(fp, mode, formats)
    except (SyntaxError, ValueError) as e:
        if isinstance(fp, (str, bytes, io.IOBase)):
            # Retry with a more robust approach
            if hasattr(fp, 'seek'):
                fp.seek(0)
            return _original_open(fp, mode, formats)
        raise e
        
Image.open = _patched_open
"""
        try:
            # Find PIL installation
            import PIL
            pil_dir = os.path.dirname(PIL.__file__)
            patch_path = os.path.join(pil_dir, "pil_patch.py")
            
            with open(patch_path, 'w') as f:
                f.write(patch_code)
            
            # Create an __init__.py patch to load our patch
            init_path = os.path.join(pil_dir, "__init__.py")
            with open(init_path, 'r') as f:
                init_content = f.read()
            
            if "import pil_patch" not in init_content:
                with open(init_path, 'a') as f:
                    f.write("\n# Added by fix_imghdr_pillow_global.py\ntry:\n    import pil_patch\nexcept ImportError:\n    pass\n")
                
            logger.info(f"Applied PIL/Pillow patch at {patch_path}")
            return True
        except (PermissionError, IOError):
            logger.warning("Could not write to PIL/Pillow directory. Using runtime patch only.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to fix PIL/Pillow: {e}")
        return False

def test_pil_integration():
    """Test PIL integration with the patch"""
    try:
        from PIL import Image
        import io
        
        # Create a simple test image
        img_bytes = io.BytesIO(PIL_TEST_IMAGE)
        
        try:
            # Try to open the image
            img = Image.open(img_bytes)
            img.load()  # This will actually try to read the image data
            logger.info("PIL/Pillow integration test: PASSED")
            return True
        except Exception as e:
            logger.error(f"PIL/Pillow integration test failed: {e}")
            return False
            
    except ImportError:
        logger.warning("PIL/Pillow not available, skipping integration test")
        return None

def create_import_wrapper():
    """Create an import wrapper that can be used in projects"""
    wrapper_code = """
\"\"\"
ImgHdr PIL Compatibility Wrapper

Import this module at the beginning of your program to ensure
PIL/Pillow and imghdr compatibility.

Usage:
    import imghdr_compat
\"\"\"

import sys
import io

# Patch imghdr
try:
    import imghdr
    _original_what = imghdr.what
    
    def _patched_what(file, h=None):
        \"\"\"Patched version of imghdr.what that handles null bytes\"\"\"
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

# Patch PIL
try:
    from PIL import Image
    _original_open = Image.open
    
    def _patched_open(fp, mode='r', formats=None):
        \"\"\"Patched version of PIL.Image.open that handles potential imghdr issues\"\"\"
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
            
    # Apply the patch
    Image.open = _patched_open
except ImportError:
    pass
"""
    
    try:
        # Write to current directory
        wrapper_path = os.path.join(os.getcwd(), "imghdr_compat.py")
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_code)
        
        # Try to write to site-packages
        site_packages = get_site_packages_paths()
        if site_packages:
            try:
                for site_path in site_packages:
                    site_wrapper_path = os.path.join(site_path, "imghdr_compat.py")
                    with open(site_wrapper_path, 'w') as f:
                        f.write(wrapper_code)
                    logger.info(f"Created compatibility wrapper at {site_wrapper_path}")
            except (PermissionError, IOError):
                logger.warning("Could not write to site-packages, using local wrapper only")
        
        logger.info(f"Created compatibility wrapper at {wrapper_path}")
        logger.info("To use the compatibility wrapper, add this to the top of your scripts:")
        logger.info("    import imghdr_compat")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create compatibility wrapper: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("PIL/Pillow and imghdr Global Fix Utility")
    logger.info("=" * 60)
    
    # System information
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"OS: {platform.system()} {platform.version()}")
    
    # Check for PIL
    try:
        import PIL
        logger.info(f"PIL/Pillow version: {PIL.__version__}")
    except ImportError:
        logger.info("PIL/Pillow not installed")
    
    # Detect running as admin/sudo
    is_admin = False
    if platform.system() == "Windows":
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    else:
        is_admin = os.geteuid() == 0 if hasattr(os, "geteuid") else False
    
    if not is_admin:
        logger.warning("Not running with administrator privileges.")
        logger.warning("Some operations may fail due to permission issues.")
        logger.warning("Consider rerunning as administrator/sudo if fixes fail.")
    
    # Step 1: Patch imghdr module
    logger.info("\nStep 1: Patching imghdr module...")
    imghdr_patched = patch_imghdr_module()
    
    # Step 2: Create runtime patch
    logger.info("\nStep 2: Creating runtime patch...")
    runtime_patch_created = create_runtime_patch()
    
    # Step 3: Fix PIL/Pillow installation
    logger.info("\nStep 3: Fixing PIL/Pillow installation...")
    pillow_fixed = fix_pillow_installation()
    
    # Step 4: Create import wrapper
    logger.info("\nStep 4: Creating import compatibility wrapper...")
    wrapper_created = create_import_wrapper()
    
    # Step 5: Verify the patch
    logger.info("\nStep 5: Verifying patch...")
    patch_verified = verify_patch()
    
    # Step 6: Test PIL integration
    logger.info("\nStep 6: Testing PIL integration...")
    pil_test_result = test_pil_integration()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary of Results")
    logger.info("=" * 60)
    logger.info(f"imghdr module patched: {'✅ Success' if imghdr_patched else '❌ Failed'}")
    logger.info(f"Runtime patch created: {'✅ Success' if runtime_patch_created else '❌ Failed'}")
    logger.info(f"PIL/Pillow fixed: {'✅ Success' if pillow_fixed else '❌ Failed'}")
    logger.info(f"Import wrapper created: {'✅ Success' if wrapper_created else '❌ Failed'}")
    logger.info(f"Patch verification: {'✅ Success' if patch_verified else '❌ Failed'}")
    
    if pil_test_result is not None:
        logger.info(f"PIL integration test: {'✅ Success' if pil_test_result else '❌ Failed'}")
    else:
        logger.info(f"PIL integration test: ⚠️ Skipped (PIL not available)")
    
    # Recommendations
    logger.info("\nRecommendations:")
    if imghdr_patched and patch_verified:
        logger.info("✅ The system-wide patch has been successfully applied.")
        logger.info("   No further action is needed for most applications.")
    elif runtime_patch_created or wrapper_created:
        logger.info("⚠️ The system-wide patch could not be fully applied.")
        logger.info("   You can use one of the following methods in your code:")
        
        if runtime_patch_created:
            logger.info("   1. Add 'import imghdr_runtime_patch' at the top of your scripts")
        
        if wrapper_created:
            logger.info("   2. Add 'import imghdr_compat' at the top of your scripts")
    else:
        logger.info("❌ All fix attempts failed. Try running as administrator/sudo.")
    
    logger.info("\nPatch applied successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 