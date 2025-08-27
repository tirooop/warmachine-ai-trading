
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
            h = h.replace(b'\x00', b'')
    
        # Call the original logic but with our preprocessed h
        return _original_what(file, h)
    
    # Apply the patch
    imghdr.what = _patched_what
    sys.modules['imghdr'].what = _patched_what
except ImportError:
    pass
