# core/plugin_manager.py 完整代码

import os
import importlib.util
import inspect
import re
from .plugin_interface import PluginInterface
from .config import ConfigManager


class PluginManager:
    def __init__(self, plugin_dir="plugins"):
        self.plugin_dir = plugin_dir
        self.plugins = []

    def load_plugins(self):
        """扫描并加载插件"""
        self.plugins = []
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

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

                    plugin_instance = obj()

                    # --- 自动关键词提取 ---
                    auto_keywords = set()

                    # 1. 提取插件描述
                    if hasattr(plugin_instance, 'description'):
                        auto_keywords.update(plugin_instance.description.split())

                    # 2. 提取相关类的名字和方法名
                    for sub_name, sub_obj in inspect.getmembers(module):
                        if inspect.isclass(sub_obj) and sub_obj.__module__ == module.__name__:
                            # 拆分驼峰命名 (JsonPage -> json, page)
                            words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', sub_name)
                            auto_keywords.update([w.lower() for w in words])

                            # 提取方法名
                            for method_name, _ in inspect.getmembers(sub_obj, predicate=inspect.isfunction):
                                if not method_name.startswith('_'):
                                    auto_keywords.update(method_name.split('_'))

                    # 3. 过滤并存储到 dynamic_tags 属性
                    valid_tags = [k.lower() for k in auto_keywords if len(k) > 1]

                    # 【关键】挂载到一个新属性上，不与 @property 冲突
                    plugin_instance.dynamic_tags = list(set(valid_tags))

                    # print(f"插件 {plugin_instance.name} 索引: {plugin_instance.dynamic_tags}")

                    self.plugins.append(plugin_instance)

        except Exception as e:
            print(f"加载插件 {path} 失败: {e}")

    def get_plugins(self, include_disabled=False):
        """返回排序后的插件列表"""
        config = ConfigManager.load()
        saved_order = config.get("plugin_order", [])
        disabled_list = set(config.get("disabled_plugins", []))

        sorted_list = []
        plugin_map = {p.name: p for p in self.plugins}

        for name in saved_order:
            if name in plugin_map:
                sorted_list.append(plugin_map[name])
                del plugin_map[name]

        for p in plugin_map.values():
            sorted_list.append(p)

        if not include_disabled:
            return [p for p in sorted_list if p.name not in disabled_list]
        else:
            return sorted_list