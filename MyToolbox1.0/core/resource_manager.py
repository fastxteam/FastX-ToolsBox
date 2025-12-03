import os
from pathlib import Path
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentIcon


class ResourceManager:
    # 动态获取项目根目录
    # 假设结构是 MyToolbox/core/resource_manager.py
    ROOT_DIR = Path(__file__).resolve().parent.parent
    ICON_DIR = ROOT_DIR / "resources" / "icons"

    @classmethod
    def get_icon(cls, name: str):
        """
        全能图标获取方法
        优先级：自定义文件 > Fluent图标 > 系统保底图标
        """
        if not name:
            return cls.get_fallback_icon()

        # 1. 查找本地资源文件 (resources/icons/name.svg/png)
        # 支持传入 "edit" 自动找 "edit.svg"
        if not os.path.exists(cls.ICON_DIR):
            os.makedirs(cls.ICON_DIR, exist_ok=True)

        for ext in ['.svg', '.png', '.ico']:
            icon_path = cls.ICON_DIR / f"{name}{ext}"
            if icon_path.exists():
                return QIcon(str(icon_path))

        # 2. 查找 FluentIcon 枚举 (不区分大小写)
        # 例如传入 "edit", "EDIT" 都能找到 FluentIcon.EDIT
        upper_name = name.upper()
        if hasattr(FluentIcon, upper_name):
            return getattr(FluentIcon, upper_name).icon()

        # 3. 常用别名映射 (兼容旧习惯)
        aliases = {
            "rename": "EDIT",
            "batch": "Copy",
            "tree": "FOLDER",
            "calc": "CALCULATOR",
            "calculator": "CALCULATOR"
        }
        if name.lower() in aliases:
            target = aliases[name.lower()]
            if hasattr(FluentIcon, target):
                return getattr(FluentIcon, target).icon()

        # 4. 没找到，返回保底图标
        print(f"[Icon Warning] 图标 '{name}' 未找到，使用默认图标。")
        return cls.get_fallback_icon()

    @classmethod
    def get_fallback_icon(cls):
        """
        获取绝对存在的保底图标 (问号)
        """
        # QUESTION 是 FluentIcon 中非常基础的图标，通常都存在
        if hasattr(FluentIcon, 'QUESTION'):
            return FluentIcon.QUESTION.icon()

        # 如果连 QUESTION 都没有 (极低概率)，尝试 HELP 或 SEARCH
        for backup in ['HELP', 'SEARCH', 'HOME']:
            if hasattr(FluentIcon, backup):
                return getattr(FluentIcon, backup).icon()

        # 如果系统里一个图标都没有，返回空 QIcon (不会报错，只是不显示)
        return QIcon()


# 便捷入口
def qicon(name: str):
    return ResourceManager.get_icon(name)