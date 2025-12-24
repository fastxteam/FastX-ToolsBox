from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFrame
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
        self.setFixedSize(300, 120)  # 调整卡片大小，更适合新布局
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # 统一卡片样式，简约大气
        self.setStyleSheet("""
            CardWidget {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 8px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
        """)

        # 主布局 - 垂直布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # 第一行：图标 + 标题区域
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(12)

        # 1. 图标 (支持 FluentIcon 或 QIcon)
        icon_obj = plugin.icon
        # 如果 icon 是字符串，尝试转换
        if isinstance(icon_obj, str):
            icon_obj = qicon(icon_obj)

        self.icon_widget = IconWidget(icon_obj, self)
        self.icon_widget.setFixedSize(48, 48)
        self.top_layout.addWidget(self.icon_widget)

        # 标题区域：垂直布局，包含标题和子标题
        self.title_area = QVBoxLayout()
        self.title_area.setSpacing(4)
        self.title_area.setAlignment(Qt.AlignTop)

        # 2. 标题
        name_text = getattr(plugin, 'name', '未知工具')
        self.title_label = BodyLabel(name_text, self)
        font = self.title_label.font()
        font.setBold(True)
        font.setPixelSize(16)
        self.title_label.setFont(font)
        self.title_area.addWidget(self.title_label)

        # 3. 子标题（使用分组信息）
        group_text = ""
        try:
            if hasattr(plugin, 'group'):
                group_text = plugin.group
        except Exception as e:
            print(f"[Warn] 获取分组失败: {e}")
            group_text = ""
        
        self.subtitle_label = CaptionLabel(group_text, self)
        self.subtitle_label.setTextColor(Qt.gray, Qt.gray)
        self.subtitle_label.setWordWrap(True)
        self.title_area.addWidget(self.subtitle_label)

        # 填充空白，将标题区域推到顶部
        self.title_area.addStretch(1)
        self.top_layout.addLayout(self.title_area)
        self.top_layout.addStretch(1)

        # 4. 描述（放在整个下面区域）
        desc_text = "暂无描述"
        try:
            # 优先尝试直接获取 description
            if hasattr(plugin, 'description'):
                desc_text = plugin.description
        except Exception as e:
            print(f"[Warn] 获取描述失败: {e}")
            desc_text = "加载失败"

        self.desc_label = CaptionLabel(desc_text, self)
        self.desc_label.setTextColor(Qt.gray, Qt.gray)
        self.desc_label.setWordWrap(True)

        # 添加到主布局
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.desc_label)
        self.main_layout.addStretch(1)

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