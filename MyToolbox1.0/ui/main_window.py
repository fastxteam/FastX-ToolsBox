from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon

from core.plugin_manager import PluginManager
from core.config import ConfigManager
from core.resource_manager import qicon
from ui.views import CentralTabWidget
from ui.tool_window import ToolWindow
from ui.settings_interface import SettingsInterface


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()

        self.independent_windows = []

        # 1. 加载配置
        self.config_data = ConfigManager.load()
        ConfigManager.apply_theme(self.config_data["theme"])

        self.setWindowTitle("Python Fluent Toolbox")

        app_icon = qicon("app")
        if app_icon.isNull():
            self.setWindowIcon(FluentIcon.TILES.icon())
        else:
            self.setWindowIcon(app_icon)

        w, h = self.config_data.get("window_size", [1000, 700])
        self.resize(w, h)

        # 【核心修复】强制窗口背景透明 (依赖操作系统的亚克力效果，或者退化为纯色)
        # 这行代码能解决很多背景变黑的问题
        self.setStyleSheet("MainWindow { background: transparent; }")

        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

        self.init_ui()

    def init_ui(self):
        plugins = self.plugin_manager.get_plugins(include_disabled=False)

        self.central_interface = CentralTabWidget(plugins, self)
        self.central_interface.setObjectName("central_interface")
        self.central_interface.tool_new_window.connect(self.open_tool_independent)

        icon_home = getattr(FluentIcon, 'HOME', None)
        if not icon_home: icon_home = getattr(FluentIcon, 'TILES', FluentIcon.EDIT)

        self.addSubInterface(
            self.central_interface,
            icon_home,
            "工作台",
            position=NavigationItemPosition.TOP
        )

        self.navigationInterface.addSeparator()

        self.settings_interface = SettingsInterface(self)

        icon_setting = getattr(FluentIcon, 'SETTING', getattr(FluentIcon, 'SETTINGS', FluentIcon.EDIT))

        self.addSubInterface(
            self.settings_interface,
            icon_setting,
            "设置",
            position=NavigationItemPosition.BOTTOM
        )
        
        # 连接导航栏显示模式变化信号，用于同步调整中央界面
        self.navigationInterface.displayModeChanged.connect(self.update_central_layout)

    def open_tool_independent(self, plugin):
        new_window = ToolWindow(plugin)
        self.independent_windows.append(new_window)
        new_window.destroyed.connect(lambda: self.cleanup_window(new_window))
        new_window.show()

    def cleanup_window(self, window):
        if window in self.independent_windows:
            self.independent_windows.remove(window)

    def update_central_layout(self):
        """当导航栏显示模式变化时，更新中央界面布局"""
        # 确保中央界面正确响应导航栏宽度变化
        self.central_interface.updateGeometry()
        # 调用父类的update方法，确保整个窗口重新布局
        self.update()
    
    def update_background(self, path):
        if hasattr(self, 'central_interface') and hasattr(self.central_interface, 'home_view'):
            self.central_interface.home_view.load_background()

    def closeEvent(self, event):
        try:
            current_config = ConfigManager.load()
            current_config["window_size"] = [self.width(), self.height()]
            ConfigManager.save(current_config)
        except Exception as e:
            print(f"关闭保存失败: {e}")

        for w in self.independent_windows:
            w.close()

        event.accept()