"""
兼容性模块 - 替代imghdr
使用PIL/Pillow库提供与imghdr模块相同的功能
"""

import os
import sys
from PIL import Image

def what(file, h=None):
    """
    测试图像文件的类型，与imghdr.what兼容
    
    Args:
        file: 文件路径或已打开的文件对象
        h: 可选的文件头数据（未使用，仅为兼容性保留）
        
    Returns:
        图像类型字符串（小写）如'jpeg', 'png'等，如果无法识别则返回None
    """
    try:
        if isinstance(file, str):
            # 如果是文件路径
            with Image.open(file) as img:
                format = img.format
        else:
            # 如果是文件对象
            pos = file.tell()
            file.seek(0)
            with Image.open(file) as img:
                format = img.format
            file.seek(pos)  # 恢复文件指针位置
            
        # 转换为imghdr风格的输出（小写）
        if format:
            return format.lower()
        return None
    except Exception:
        return None

# 格式映射表，用于特定格式的检测
tests = {
    'jpeg': lambda f: what(f) == 'jpeg',
    'png': lambda f: what(f) == 'png',
    'gif': lambda f: what(f) == 'gif',
    'bmp': lambda f: what(f) == 'bmp',
    'tiff': lambda f: what(f) in ('tiff', 'tif'),
}

# 为了支持系统级导入，我们在模块加载时执行这段代码
# 这允许系统使用PIL_image_check替代imghdr
# 当其他模块尝试导入imghdr时，将导入这个模块
sys.modules['imghdr'] = sys.modules[__name__]

if __name__ == '__main__':
    # 测试代码
    import sys
    
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            print(f"{filename}: {what(filename)}")
    else:
        print("用法: python PIL_image_check.py 图片文件1 [图片文件2 ...]") 