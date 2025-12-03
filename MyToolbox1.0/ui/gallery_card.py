from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QVBoxLayout, QFrame
from qfluentwidgets import (CardWidget, IconWidget, BodyLabel, CaptionLabel,
                            RoundMenu, Action, FluentIcon)
from core.config import ConfigManager
from core.resource_manager import qicon


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

        # 获取颜色 (增加容错)
        try:
            self.color = ConfigManager.get_color(plugin)
        except:
            self.color = "#009faa"

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)

        # 1. 顶部彩色装饰条
        self.color_strip = QFrame(self)
        self.color_strip.setFixedHeight(4)
        self.color_strip.setStyleSheet(
            f"background-color: {self.color}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        self.v_layout.addWidget(self.color_strip)

        # 内容容器
        self.content_widget = QFrame(self)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 16, 20, 20)
        self.content_layout.setSpacing(10)

        # 2. 图标 (支持 FluentIcon 或 QIcon)
        icon_obj = plugin.icon
        # 如果 icon 是字符串，尝试转换
        if isinstance(icon_obj, str):
            icon_obj = qicon(icon_obj)

        self.icon_widget = IconWidget(icon_obj, self)
        self.icon_widget.setFixedSize(40, 40)

        # 3. 标题
        name_text = getattr(plugin, 'name', '未知工具')
        self.title_label = BodyLabel(name_text, self)
        font = self.title_label.font()
        font.setBold(True)
        font.setPixelSize(16)
        self.title_label.setFont(font)

        # 4. 描述 (【核心修复】防御性获取)
        desc_text = "暂无描述"
        try:
            # 优先尝试直接获取 description
            if hasattr(plugin, 'description'):
                desc_text = plugin.description

            # 如果为空或默认值，尝试用 group 拼接
            if not desc_text or desc_text == "暂无描述":
                if hasattr(plugin, 'group'):
                    desc_text = f"属于 {plugin.group} 分组"
        except Exception as e:
            print(f"[Warn] 获取描述失败: {e}")
            desc_text = "加载失败"

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

        # 安全获取图标
        icon_add = getattr(FluentIcon, 'ADD', FluentIcon.EDIT)
        action_tab = Action(icon_add, "在新标签页打开", parent=self)
        action_tab.triggered.connect(lambda: self.open_new_tab.emit(self.plugin))
        menu.addAction(action_tab)

        icon_win = getattr(FluentIcon, 'SHARE', getattr(FluentIcon, 'SEND', FluentIcon.FOLDER))
        action_win = Action(icon_win, "在新窗口打开", parent=self)
        action_win.triggered.connect(lambda: self.open_new_window.emit(self.plugin))
        menu.addAction(action_win)

        menu.exec(self.mapToGlobal(pos))