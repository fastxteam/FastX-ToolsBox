from qfluentwidgets import FluentWindow
from PySide6.QtGui import QIcon


class ToolWindow(FluentWindow):
    """用于独立显示工具的窗口"""

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

        # 1. 设置基础属性
        self.setWindowTitle(f"{plugin.name} - 独立窗口")
        self.resize(800, 600)

        # 2. 设置图标
        if isinstance(plugin.icon, str):
            self.setWindowIcon(QIcon(plugin.icon))
        # 如果是 FluentIcon 枚举，FluentWindow 会自动处理，这里暂略

        # 3. 加载插件内容
        # 注意：这里我们只用addSubInterface把插件加进去，并隐藏导航栏
        self.widget = plugin.create_widget()
        self.widget.setObjectName(f"tool_{plugin.name}")

        # 将插件设为中心部件（或者作为一个全屏的子界面）
        # 这里为了保持 Fluent 风格，我们还是通过 addSubInterface 添加，但隐藏左侧栏
        self.addSubInterface(self.widget, plugin.icon, plugin.name)

        # 隐藏左侧导航栏，只留内容区
        self.navigationInterface.hide()