import os
from pathlib import Path
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentIcon, getIconColor, Theme, isDarkTheme


class ResourceManager:
    # 定义资源根目录
    ROOT_DIR = Path(__file__).parent.parent
    ICON_DIR = ROOT_DIR / "resources" / "icons"

    @classmethod
    def get_icon(cls, name: str):
        """
        获取图标的通用接口
        :param name: 图标名称 (例如 "save", "edit", "my_custom_icon")
        :return: QIcon 对象
        """
        if not name:
            return QIcon()

        # 1. 优先查找自定义文件 (resources/icons/name.svg 或 .png)
        # 支持不带后缀的自动查找
        for ext in ['.svg', '.png', '.ico']:
            icon_path = cls.ICON_DIR / f"{name}{ext}"
            if icon_path.exists():
                return QIcon(str(icon_path))

            # 也支持直接传文件名带后缀的情况
            icon_path_direct = cls.ICON_DIR / name
            if icon_path_direct.exists():
                return QIcon(str(icon_path_direct))

        # 2. 如果文件不存在，尝试从 FluentIcon 枚举中查找同名图标 (作为回退)
        # 比如传入 "SAVE"，尝试获取 FluentIcon.SAVE
        if hasattr(FluentIcon, name.upper()):
            return getattr(FluentIcon, name.upper()).icon()

        # 3. 还是没找到，尝试模糊匹配 (比如传入 "bold"，映射到 FluentIcon.BOLD 或 EDIT)
        # 这里可以维护一个映射表，处理旧版本兼容问题
        fallback_map = {
            "bold": "EDIT",
            "italic": "DOCUMENT",
            "chart": "TILES",
            "image": "FOLDER"
        }
        if name.lower() in fallback_map:
            fallback_name = fallback_map[name.lower()]
            if hasattr(FluentIcon, fallback_name):
                return getattr(FluentIcon, fallback_name).icon()

        # 4. 彻底没招了，返回一个保底图标 (比如 QUESTION 或 MENU)
        # 这样保证程序永远不会因为缺图标而崩溃
        if hasattr(FluentIcon, 'QUESTION'):
            return FluentIcon.QUESTION.icon()

        return QIcon()  # 空图标


# 为了方便调用，提供一个简短的别名函数
def qicon(name: str):
    return ResourceManager.get_icon(name)