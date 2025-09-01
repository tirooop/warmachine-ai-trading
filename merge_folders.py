"""
Merge all folders from warmachine/warmachine/ to outer warmachine/ directory
"""

import os
import shutil
from pathlib import Path

def merge_folders():
    """Merge inner folders to outer folders"""
    inner = Path("warmachine")
    outer = Path(".")
    
    print("Starting merge process...")
    
    # 遍历内层目录下的所有内容
    for item in os.listdir(inner):
        if item == "__pycache__":
            continue  # 跳过 __pycache__ 目录
            
        src = inner / item
        dst = outer / item
        print(f"Processing: {item}")
        
        if os.path.isdir(src):
            # 如果是目录，确保目标目录存在
            os.makedirs(dst, exist_ok=True)
            
            # 移动目录下的所有内容
            for subitem in os.listdir(src):
                src_sub = src / subitem
                dst_sub = dst / subitem
                if os.path.exists(dst_sub):
                    if os.path.isdir(dst_sub):
                        shutil.rmtree(dst_sub)
                    else:
                        os.remove(dst_sub)
                shutil.move(str(src_sub), str(dst_sub))
                print(f"  Moved: {subitem}")
        else:
            # 如果是文件，直接移动
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(str(src), str(dst))
            print(f"  Moved: {item}")
    
    # 删除内层目录
    shutil.rmtree(inner)
    print("\nMerge completed successfully!")
    print("Inner warmachine directory has been removed.")

if __name__ == "__main__":
    merge_folders() 