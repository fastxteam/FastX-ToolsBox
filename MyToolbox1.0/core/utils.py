import sys
import os
from pathlib import Path


def get_base_path():
    """获取项目根路径"""
    # 1. 优先检查冻结状态 (打包环境)
    if getattr(sys, 'frozen', False):
        # 在文件夹模式下，资源就在 exe 的同级目录下
        # sys.executable 指向 MyToolbox.exe
        return Path(sys.executable).parent

    # 2. 开发环境
    return Path(__file__).resolve().parent.parent