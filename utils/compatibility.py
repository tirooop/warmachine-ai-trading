#!/usr/bin/env python


"""


Python 3.13+ 兼容性预加载模块





此模块解决Python 3.13中已移除的模块（如imghdr）的兼容性问题。


使用方法：


    python -m preload_compatibility run_ai_strategy_with_telegram.py [args]





这将确保所有必要的兼容性层在任何其他模块导入前加载。


"""





import os
import sys
import logging
from pathlib import Path

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

# 配置基本日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/compatibility.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ imghdr 兼容性处理 ============


try:


    # 先尝试导入原始的imghdr


    try:


        import imghdr


        logger.info("成功导入原始imghdr模块")


    except ImportError:


        logger.info("原始imghdr模块不可用，创建PIL替代品")


        


        from PIL import Image


        import io


        


        # 定义格式到扩展名的映射


        FORMAT_TO_EXTENSION = {


            'JPEG': 'jpeg',


            'PNG': 'png',


            'GIF': 'gif',


            'BMP': 'bmp',


            'TIFF': 'tiff',


            'WEBP': 'webp',


            'ICO': 'ico'


        }


        


        # 创建what函数


        def what(file, h=None):


            """


            确定文件或内存缓冲区中包含的图像类型。


            Args:


                file: 文件名（字符串）、pathlib.Path对象或以二进制模式打开的文件对象。


                h: 包含文件头部的字节对象（为兼容性而保留，被忽略）。


                


            Returns:


                描述图像类型的字符串（例如'png'、'jpeg'等），如果无法确定类型则返回None。


            """


            try:


                if isinstance(file, (str, os.PathLike)):


                    with Image.open(file) as img:


                        format = img.format


                elif hasattr(file, 'read'):


                    # 如果是类文件对象


                    position = file.tell()


                    try:


                        with Image.open(file) as img:


                            format = img.format


                    finally:


                        file.seek(position)  # 重置文件位置


                elif isinstance(file, bytes):


                    # 如果是字节数据


                    with Image.open(io.BytesIO(file)) as img:


                        format = img.format


                else:


                    return None


                    


                # 将PIL格式转换为imghdr样式的扩展名


                return FORMAT_TO_EXTENSION.get(format, None)


            except Exception:


                return None


            


        # 创建模块


        class ImghdrModule:


            def __init__(self):


                self.what = what


                self.__name__ = "imghdr"


        


        # 替换sys.modules中的imghdr


        imghdr_module = ImghdrModule()


        sys.modules['imghdr'] = imghdr_module


        logger.info("使用PIL成功创建imghdr兼容层")


    # 安装PIL扩展包


    try:


        import pip


        try:


            import PIL


            logger.info("PIL已安装")


        except ImportError:


            logger.info("安装PIL...")


            pip.main(['install', 'pillow'])


            logger.info("PIL安装完成")


    except Exception as e:


        logger.error(f"安装PIL失败: {str(e)}")


    


except Exception as e:


    logger.error(f"创建兼容层时出错: {str(e)}")





logger.info("兼容性预加载完成")


# 测试imghdr是否可用


try:


    import imghdr


    logger.info(f"imghdr.what函数可用: {hasattr(imghdr, 'what')}")


except Exception as e:


    logger.error(f"导入imghdr失败: {str(e)}")





# ============ 运行目标脚本 ============


def run_script(script_path, script_args):


    """


    运行指定的Python脚本，保持所有已加载的兼容性层


    """


    if not os.path.exists(script_path):


        print(f"错误: 找不到脚本 {script_path}")


        sys.exit(1)


    


    # 添加脚本所在目录到path


    script_dir = os.path.dirname(os.path.abspath(script_path))


    if script_dir not in sys.path:


        sys.path.insert(0, script_dir)


    


    # 设置命令行参数


    sys.argv = [script_path] + script_args


    


    # 执行脚本


    try:


        with open(script_path, 'rb') as script_file:


            # 运行脚本


            runpy.run_path(script_path, run_name='__main__')


    except Exception as e:


        print(f"运行脚本时出错: {e}")


        sys.exit(1)





if __name__ == "__main__":


    print("兼容性预加载完成，所有功能应该可以正常使用了")


    print(f"imghdr可用状态: {'imghdr' in sys.modules}")


    if 'imghdr' in sys.modules:


        print(f"imghdr.what函数可用: {hasattr(sys.modules['imghdr'], 'what')}")


    if len(sys.argv) < 2:


        print("用法: python -m preload_compatibility 脚本路径 [参数...]")


        sys.exit(1)


    


    script_path = sys.argv[1]


    script_args = sys.argv[2:]


    


    run_script(script_path, script_args) 