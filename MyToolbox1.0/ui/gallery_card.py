from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QVBoxLayout, QFrame # 引入 QFrame
from qfluentwidgets import (CardWidget, IconWidget, BodyLabel, CaptionLabel,
                            RoundMenu, Action, FluentIcon)
from core.config import ConfigManager # 引入配置


class ToolCard(CardWidget):
    """首页展示的工具卡片"""
    tool_clicked = Signal(object)
    open_new_tab = Signal(object)
    open_new_window = Signal(object)

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(200, 160)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # 获取颜色
        self.color = ConfigManager.get_color(plugin)

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)  # 清空默认边距，为了让色条贴顶
        self.v_layout.setSpacing(0)

        # 1. 顶部彩色装饰条
        self.color_strip = QFrame(self)
        self.color_strip.setFixedHeight(4)
        self.color_strip.setStyleSheet(
            f"background-color: {self.color}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        self.v_layout.addWidget(self.color_strip)

        # 内容容器（为了恢复内边距）
        self.content_widget = QFrame(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 16, 20, 20)
        self.content_layout.setSpacing(10)

        # 2. 图标 (我们给图标强制上色，或者你可以保留原色)
        # 这里演示如何给 icon_widget 的图标着色不太容易，
        # 我们用更简单的方法：直接用 IconWidget，它会自动适配黑白，
        # 如果你想图标也有颜色，需要重写 IconWidget 的 paintEvent，这里我们先只做装饰条。
        self.icon_widget = IconWidget(plugin.icon, self)
        self.icon_widget.setFixedSize(40, 40)

        # 3. 标题
        self.title_label = BodyLabel(plugin.name, self)
        font = self.title_label.font()
        font.setBold(True)
        font.setPixelSize(16)
        self.title_label.setFont(font)

        # 4. 描述
        desc_text = getattr(plugin, 'description', f"属于 {plugin.group} 分组")
        self.desc_label = CaptionLabel(desc_text, self)
        self.desc_label.setTextColor(Qt.gray, Qt.gray)
        self.desc_label.setWordWrap(True)

        self.content_layout.addWidget(self.icon_widget)
        self.content_layout.addWidget(self.title_label)
        self.content_layout.addWidget(self.desc_label)
        self.content_layout.addStretch(1)

        self.v_layout.addWidget(self.content_widget)
    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.LeftButton:
            self.tool_clicked.emit(self.plugin)

    def on_context_menu(self, pos: QPoint):
        menu = RoundMenu(parent=self)

        # 1. 在新标签页打开 (强制多开)
        # 使用 ADD 图标
        if hasattr(FluentIcon, 'ADD'):
            icon_add = FluentIcon.ADD
        else:
            icon_add = FluentIcon.edit  # 保底

        action_tab = Action(icon_add, "在新标签页打开", parent=self)
        action_tab.triggered.connect(lambda: self.open_new_tab.emit(self.plugin))
        menu.addAction(action_tab)

        # 2. 在新窗口打开
        if hasattr(FluentIcon, 'SHARE'):
            icon_win = FluentIcon.SHARE
        elif hasattr(FluentIcon, 'SEND'):
            icon_win = FluentIcon.SEND
        else:
            icon_win = FluentIcon.FOLDER

        action_win = Action(icon_win, "在新窗口打开", parent=self)
        action_win.triggered.connect(lambda: self.open_new_window.emit(self.plugin))
        menu.addAction(action_win)

        menu.exec(self.mapToGlobal(pos))