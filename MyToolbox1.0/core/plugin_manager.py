import os
import importlib.util
import inspect
from .plugin_interface import PluginInterface
from .config import ConfigManager  # <--- 【关键】必须导入配置管理器


class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    def load_plugins(self):
        """扫描并加载插件 (物理加载，不排序)"""
        self.plugins = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

        # 遍历 plugins 目录下的所有文件夹
        for folder_name in os.listdir(self.plugin_dir):
            folder_path = os.path.join(self.plugin_dir, folder_name)
            if os.path.isdir(folder_path):
                for file in os.listdir(folder_path):
                    if file.endswith(".py") and file != "__init__.py":
                        self._load_plugin_from_file(os.path.join(folder_path, file))

    def _load_plugin_from_file(self, path):
        try:
            spec = importlib.util.spec_from_file_location("dynamic_plugin", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj is not PluginInterface:
                    self.plugins.append(obj())
                    print(f"已加载插件: {self.plugins[-1].name}")
        except Exception as e:
            print(f"加载插件 {path} 失败: {e}")

    # =========================================================
    # 【核心修复】获取插件时，应用配置文件中的排序
    # =========================================================
    def get_plugins(self):
        """返回排序后的插件列表"""
        loaded_plugins = self.plugins

        # 1. 尝试读取
        config = ConfigManager.load()
        saved_order = config.get("plugin_order", [])

        print(f"[DEBUG] 启动加载顺序: {saved_order}")  # 调试信息

        if not saved_order:
            return loaded_plugins

        sorted_list = []
        plugin_map = {p.name: p for p in loaded_plugins}

        for name in saved_order:
            if name in plugin_map:
                sorted_list.append(plugin_map[name])
                del plugin_map[name]

        for p in plugin_map.values():
            sorted_list.append(p)

        return sorted_list