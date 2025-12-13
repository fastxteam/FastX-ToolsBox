import json
import os
from pathlib import Path
from qfluentwidgets import Theme, setTheme


class ConfigManager:
    """管理应用配置"""
    # 1. 确定配置存储目录 (例如: C:\Users\User\AppData\Local\MyToolbox)
    # 这样无论 EXE 在哪里运行，配置都能保存
    APP_DATA_DIR = Path(os.getenv('LOCALAPPDATA')) / "MyToolbox"

    # 确保目录存在
    if not APP_DATA_DIR.exists():
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    CONFIG_FILE = APP_DATA_DIR / "settings.json"
    # =========================================================
    # 【核心修复】使用绝对路径定位项目根目录
    # =========================================================
    # __file__ 是当前文件 (core/config.py) 的路径
    # .parent 是 core 目录
    # .parent.parent 是项目根目录 (MyToolbox1.0)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    CONFIG_DIR = PROJECT_ROOT / "config"


    DEFAULT_CONFIG = {
        "theme": "Light",  # Light, Dark, Auto
        "window_size": [1000, 700],
        "custom_colors": {},
        "plugin_order": []
    }

    @classmethod
    def load(cls):
        """加载配置"""
        # 调试打印：确认读取路径
        # print(f"[Config] Reading from: {cls.CONFIG_FILE}")

        if not cls.CONFIG_FILE.exists():
            return cls.DEFAULT_CONFIG.copy()

        try:
            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():  # 防止文件为空导致报错
                    return cls.DEFAULT_CONFIG.copy()

                config = json.loads(content)

                # 深度合并默认配置
                merged = cls.DEFAULT_CONFIG.copy()
                merged.update(config)

                # 确保关键字段存在
                if "custom_colors" not in merged: merged["custom_colors"] = {}
                if "plugin_order" not in merged: merged["plugin_order"] = []

                return merged
        except Exception as e:
            print(f"[Config] Load Error: {e}")
            return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save(cls, config_data):
        """保存配置"""
        try:
            # 调试打印：确认写入路径
            print(f"[Config] Saving to: {cls.CONFIG_FILE}")

            if not cls.CONFIG_DIR.exists():
                cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
                # ensure_ascii=False 确保中文插件名正常显示，indent=4 美化格式
                json.dump(config_data, f, indent=4, ensure_ascii=False)

        except Exception as e:
            print(f"[Config] Save Error: {e}")

    @classmethod
    def get_color(cls, plugin):
        """获取插件颜色"""
        config = cls.load()
        user_colors = config.get("custom_colors", {})
        default_color = getattr(plugin, 'theme_color', '#009faa')
        return user_colors.get(plugin.name, default_color)

    @staticmethod
    def apply_theme(theme_str):
        """应用主题"""
        t = Theme.LIGHT if theme_str == "Light" else Theme.DARK
        if theme_str == "Auto":
            t = Theme.AUTO
        setTheme(t)