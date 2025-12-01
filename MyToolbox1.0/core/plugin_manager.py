import os
import importlib.util
import inspect
from .plugin_interface import PluginInterface

class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    def load_plugins(self):
        """扫描并加载插件"""
        self.plugins = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

        # 遍历 plugins 目录下的所有文件夹
        for folder_name in os.listdir(self.plugin_dir):
            folder_path = os.path.join(self.plugin_dir, folder_name)
            if os.path.isdir(folder_path):
                # 假设插件入口文件名为 tool.py 或与文件夹同名
                # 这里简化处理：查找文件夹内的 .py 文件
                for file in os.listdir(folder_path):
                    if file.endswith(".py") and file != "__init__.py":
                        self._load_plugin_from_file(os.path.join(folder_path, file))

    def _load_plugin_from_file(self, path):
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("dynamic_plugin", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 检查模块中的类
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, PluginInterface) and obj is not PluginInterface:
                    # 实例化插件
                    plugin_instance = obj()
                    self.plugins.append(plugin_instance)
                    print(f"已加载插件: {plugin_instance.name}")
        except Exception as e:
            print(f"加载插件 {path} 失败: {e}")

    def get_plugins(self):
        return self.plugins