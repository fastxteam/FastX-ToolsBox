from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon

from core.plugin_manager import PluginManager
from core.config import ConfigManager
from ui.views import CentralTabWidget
from ui.tool_window import ToolWindow


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        self.independent_windows = []  # 独立窗口列表

        # 1. 配置加载
        self.config_data = ConfigManager.load()
        ConfigManager.apply_theme(self.config_data["theme"])

        # 2. 窗口基础设置
        self.setWindowTitle("Python Fluent Toolbox")
        w, h = self.config_data.get("window_size", [1000, 700])
        self.resize(w, h)

        # 3. 插件加载
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

        # 4. 初始化 UI
        self.init_ui()

    def init_ui(self):
        plugins = self.plugin_manager.get_plugins()

        # --- 核心修改：使用统一的 Tab 视图 ---
        self.central_interface = CentralTabWidget(plugins, self)
        self.central_interface.setObjectName("central_interface")

        # 连接独立窗口信号
        self.central_interface.tool_new_window.connect(self.open_tool_independent)

        # 将其添加到 FluentWindow 的主区域
        # 我们使用 addSubInterface 添加它，并给它一个 HOME 图标
        # 注意：这里我们不再需要 "工作台" 这个额外的侧边栏条目了
        self.addSubInterface(
            self.central_interface,
            FluentIcon.HOME,
            "工作台",
            position=NavigationItemPosition.TOP
        )

        # 你可以添加其他全局功能到侧边栏，比如设置
        self.navigationInterface.addSeparator()
        if hasattr(FluentIcon, 'SETTING'):
            # 仅作为演示，这里没写 SettingsInterface
            pass

    def open_tool_independent(self, plugin):
        """打开独立窗口"""
        new_window = ToolWindow(plugin)
        self.independent_windows.append(new_window)
        new_window.destroyed.connect(lambda: self.cleanup_window(new_window))
        new_window.show()

    def cleanup_window(self, window):
        if window in self.independent_windows:
            self.independent_windows.remove(window)

    def closeEvent(self, event):
        """窗口关闭时保存配置"""

        # 1. 【关键修复】重新加载最新配置
        # 防止覆盖掉运行期间（比如排序功能）修改的其他配置项
        current_config = ConfigManager.load()

        # 2. 更新窗口大小
        current_config["window_size"] = [self.width(), self.height()]

        # 3. 保存回文件
        ConfigManager.save(current_config)

        event.accept()