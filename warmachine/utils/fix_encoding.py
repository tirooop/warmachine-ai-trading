#!/usr/bin/env python

"""
Fix script: Resolve imghdr import and file encoding issues
"""

import os
import re
import sys
import chardet
from pathlib import Path

def fix_encoding(filepath):
    """Fix file encoding, remove BOM markers"""
    try:
        # Read file content
        with open(filepath, 'rb') as f:
            content = f.read()
        
        # Detect encoding
        encoding_info = chardet.detect(content)
        encoding = encoding_info['encoding']
        
        # Handle BOM header
        if content.startswith(b'\xfe\xff') or content.startswith(b'\xff\xfe') or content.startswith(b'\xef\xbb\xbf'):
            print(f"Fixing BOM header: {filepath}")
            if content.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                content = content[3:]
            elif content.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                content = content[2:]
            elif content.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                content = content[2:]
        
        # Decode content
        try:
            if encoding is None:
                encoding = 'utf-8'
            text = content.decode(encoding)
        except UnicodeDecodeError:
            # If decoding fails, try UTF-8
            text = content.decode('utf-8', errors='replace')
        
        # Write back file, using UTF-8 without BOM encoding
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        
        return True
    except Exception as e:
        print(f"Fixing encoding error: {filepath} - {str(e)}")
        return False

def fix_imghdr_imports(filepath):
    """Fix imghdr import issues"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Find direct imghdr import cases
        pattern1 = r'^import\s+imghdr\s*$'
        pattern2 = r'^from\s+imghdr\s+import\s+'
        
        if re.search(pattern1, content, re.MULTILINE) or re.search(pattern2, content, re.MULTILINE):
            print(f"Fixing imghdr import: {filepath}")
            
            # Add imghdr_compatibility import
            new_content = "# 添加PIL-based imghdr替代品\nimport utils.imghdr_compatibility\n\n" + content
            
            # Write back file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        return False
    except Exception as e:
        print(f"Fixing imghdr import error: {filepath} - {str(e)}")
        return False

def should_process_file(filepath):
    """Determine whether to process the file"""
    # Skip files in venv directory
    if 'venv' in filepath.parts:
        return False
    # Skip files in .git directory
    if '.git' in filepath.parts:
        return False
    # Only process .py files
    return filepath.suffix.lower() == '.py'

def main():
    """Main function"""
    # Get current working directory
    workspace_dir = Path.cwd()
    print(f"Starting to fix: {workspace_dir}")
    
    # Counter
    encoding_fixed = 0
    imghdr_fixed = 0
    
    # Iterate over all Python files
    for filepath in workspace_dir.glob("**/*.py"):
        # Skip venv and .git directories
        if not should_process_file(filepath):
            continue
        
        # Fix encoding issues
        if fix_encoding(filepath):
            encoding_fixed += 1
        
        # Fix imghdr import issues
        if fix_imghdr_imports(filepath):
            imghdr_fixed += 1
    
    print(f"\nFixing completed! Fixed {encoding_fixed} file encoding issues, {imghdr_fixed} imghdr import issues")
    print("Please restart the application, Telegram and Discord bots should be working normally now")

if __name__ == "__main__":
    main() 