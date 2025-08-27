#!/usr/bin/env python
"""
WarMachine Bot 修复工具 - 修复 Telegram 和 Discord 机器人

这个脚本专门用于修复:
1. 文件编码问题 (去除BOM头)
2. 替换imghdr依赖为PIL/Pillow
"""
import os
import sys
import re
from pathlib import Path

def create_imghdr_compatibility():
    """创建imghdr兼容模块"""
    
    # 确保utils目录存在
    os.makedirs("utils", exist_ok=True)
    
    # 写入兼容模块
    content = """\"\"\"
A compatibility module to replace the deprecated imghdr module with PIL-based functionality.
\"\"\"
from PIL import Image
import io
import sys
import os

# Dictionary mapping PIL formats to file extensions
FORMAT_TO_EXTENSION = {
    'JPEG': 'jpeg',
    'PNG': 'png',
    'GIF': 'gif',
    'BMP': 'bmp',
    'TIFF': 'tiff',
    'WEBP': 'webp',
    'ICO': 'ico'
}

def what(file, h=None):
    \"\"\"
    Determine the type of image contained in a file or memory buffer.
    
    Args:
        file: A filename (string), pathlib.Path object, or a file object open in binary mode.
        h: A bytes object containing the header of the file (ignored, for compatibility).
        
    Returns:
        A string describing the image type (e.g., 'png', 'jpeg', etc.) or None if the type cannot be determined.
    \"\"\"
    try:
        if isinstance(file, (str, os.PathLike)):
            with Image.open(file) as img:
                format = img.format
        elif hasattr(file, 'read'):
            # If it's a file-like object
            position = file.tell()
            try:
                with Image.open(file) as img:
                    format = img.format
            finally:
                file.seek(position)  # Reset file position
        elif isinstance(file, bytes):
            # If it's bytes data
            with Image.open(io.BytesIO(file)) as img:
                format = img.format
        else:
            return None
            
        # Convert PIL format to imghdr-style extension
        return FORMAT_TO_EXTENSION.get(format, None)
    except Exception:
        return None

# Make the module appear as if it were imghdr
sys.modules['imghdr'] = sys.modules[__name__]

# For testing/debugging
if __name__ == \"__main__\":
    import os
    for filename in os.listdir(\".\"):
        if os.path.isfile(filename):
            img_type = what(filename)
            if img_type:
                print(f\"{filename}: {img_type}\")
"""
    
    with open("utils/imghdr_compatibility.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("✅ 已创建 imghdr 兼容模块: utils/imghdr_compatibility.py")

def fix_encoding(file_path):
    """Fix file encoding, remove BOM markers"""
    try:
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
        
        fixed = False
        # Handle BOM header
        if content.startswith(b'\xfe\xff') or content.startswith(b'\xff\xfe') or content.startswith(b'\xef\xbb\xbf'):
            print(f"Fixing BOM header: {file_path}")
            if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                content = content[3:]
            elif content.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                content = content[2:]
            elif content.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                content = content[2:]
            fixed = True
        
        # Try to decode content
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Replace undecodable bytes
            text = content.decode('utf-8', errors='replace')
            fixed = True
            
        # Write back to file using UTF-8 without BOM
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return fixed
    except Exception as e:
        print(f"❌ Error fixing encoding: {file_path} - {str(e)}")
        return False

def add_imghdr_compatibility(file_path):
    """在文件中添加imghdr兼容模块导入"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # 查找imghdr导入
        has_imghdr_import = re.search(r'import\s+imghdr', content) or re.search(r'from\s+imghdr\s+import', content)
        
        if has_imghdr_import:
            print(f"添加imghdr兼容导入: {file_path}")
            
            # 添加兼容模块导入
            import_statement = "# PIL-based imghdr compatibility\nimport utils.imghdr_compatibility\n\n"
            
            # 查找导入区域结束位置
            imports_end = 0
            found_imports = False
            
            for match in re.finditer(r'^import\s+|^from\s+\w+\s+import', content, re.MULTILINE):
                found_imports = True
                end_pos = match.start() + content[match.start():].find('\n')
                if end_pos > imports_end:
                    imports_end = end_pos
            
            if found_imports:
                # 在所有导入之后添加
                new_content = content[:imports_end+1] + "\n" + import_statement + content[imports_end+1:]
            else:
                # 在文件开头添加
                new_content = import_statement + content
            
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        return False
    except Exception as e:
        print(f"❌ 添加兼容导入错误: {file_path} - {str(e)}")
        return False

def fix_bots():
    """修复Telegram和Discord机器人"""
    # 创建imghdr兼容模块
    create_imghdr_compatibility()
    
    # 机器人文件列表
    bot_files = []
    
    # 查找所有可能的机器人文件
    for pattern in ["**/telegram_bot.py", "**/discord_bot.py"]:
        bot_files.extend(list(Path(".").glob(pattern)))
    
    # 修复每个文件
    for file_path in bot_files:
        print(f"\n开始修复: {file_path}")
        
        # 修复编码
        encoding_fixed = fix_encoding(file_path)
        
        # 添加imghdr兼容导入
        imghdr_fixed = add_imghdr_compatibility(file_path)
        
        if encoding_fixed or imghdr_fixed:
            print(f"✅ 成功修复: {file_path}")
        else:
            print(f"ℹ️ 无需修复: {file_path}")
    
    print("\n🎉 所有机器人文件修复完成!")
    print("📋 请重新启动WarMachine，Telegram和Discord机器人应该能正常工作了")
    print("   运行命令: python run_warmachine.py")

if __name__ == "__main__":
    fix_bots() 