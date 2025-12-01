import json
from pathlib import Path
from qfluentwidgets import Theme, setTheme


class ConfigManager:
    """管理应用配置"""
    CONFIG_DIR = Path("config")
    CONFIG_FILE = CONFIG_DIR / "settings.json"

    DEFAULT_CONFIG = {
        "theme": "Light",  # Light, Dark, Auto
        "window_size": [1000, 700],
        "custom_colors": {}  # 【新增】存储用户自定义颜色 {plugin_name: hex_code}
    }

    @classmethod
    def load(cls):
        """加载配置"""
        if not cls.CONFIG_FILE.exists():
            return cls.DEFAULT_CONFIG

        try:
            with open(cls.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                # 深度合并，防止旧配置文件缺少新字段
                merged = cls.DEFAULT_CONFIG.copy()
                merged.update(config)
                if "custom_colors" not in merged:
                    merged["custom_colors"] = {}
                return merged
        except Exception:
            return cls.DEFAULT_CONFIG

    @classmethod
    def save(cls, config_data):
        """保存配置"""
        if not cls.CONFIG_DIR.exists():
            cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        with open(cls.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

    # =========================================================
    # 【重点检查】请确保你的文件中包含下面这个 get_color 方法
    # =========================================================
    @classmethod
    def get_color(cls, plugin):
        """
        获取插件颜色
        优先读取配置文件中的自定义颜色，如果没有，则使用插件自带的默认颜色
        """
        config = cls.load()
        user_colors = config.get("custom_colors", {})

        # 获取插件默认颜色，如果插件没定义 theme_color，则给一个默认青色
        default_color = getattr(plugin, 'theme_color', '#009faa')

        return user_colors.get(plugin.name, default_color)

    @staticmethod
    def apply_theme(theme_str):
        """应用主题"""
        t = Theme.LIGHT if theme_str == "Light" else Theme.DARK
        if theme_str == "Auto":
            t = Theme.AUTO
        setTheme(t)