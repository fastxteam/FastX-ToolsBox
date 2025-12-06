from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                               QListWidgetItem, QStackedWidget, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from qfluentwidgets import (FluentIcon, CardWidget, SubtitleLabel, TransparentToolButton)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon

# 绝对导入
from plugins.color_assistant.pages import ColorPickerPage, PaletteGridPage, AiPalettePage


class ColorAssistantPlugin(PluginInterface):
    @property
    def name(self) -> str: return "颜色助手"

    @property
    def icon(self):
        # 优先使用本地图标，没有则回退到 PALETTE 或 EDIT
        return qicon("palette")

    @property
    def group(self) -> str: return "设计工具"

    @property
    def theme_color(self) -> str: return "#FFB900"

    @property
    def description(self) -> str: return "全能取色、UI色卡、传统色与AI配色工具"

    def create_widget(self) -> QWidget: return ColorAssistantWidget()


class ColorAssistantWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # 主布局
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # --- 左侧导航栏 ---
        self.nav_card = QWidget()
        self.nav_card.setFixedWidth(200)
        self.nav_card.setStyleSheet("background-color: transparent; border-right: 1px solid #e5e5e5;")
        nav_layout = QVBoxLayout(self.nav_card)
        nav_layout.setContentsMargins(10, 20, 10, 20)

        # 标题
        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("颜色助手", self.nav_card))
        nav_layout.addLayout(header)
        nav_layout.addSpacing(20)

        # 列表
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; outline: none; }
            QListWidget::item { height: 40px; border-radius: 6px; padding-left: 10px; margin-bottom: 4px; }
            QListWidget::item:hover { background: rgba(0,0,0,0.05); }
            QListWidget::item:selected { background: rgba(0,0,0,0.1); color: #333; }
        """)
        nav_layout.addWidget(self.list_widget)
        nav_layout.addStretch(1)

        # --- 右侧内容区 ---
        self.stack = QStackedWidget()

        # 组装页面
        # 务必确保这里的图标获取是安全的
        icon_palette = getattr(FluentIcon, 'PALETTE', FluentIcon.EDIT)
        icon_robot = getattr(FluentIcon, 'ROBOT', FluentIcon.PEOPLE)  # 很多版本没有 ROBOT
        icon_tiles = getattr(FluentIcon, 'TILES', FluentIcon.FOLDER)
        icon_ink = getattr(FluentIcon, 'PENCIL_INK', FluentIcon.EDIT)

        self.items = [
            ("颜色", icon_palette, ColorPickerPage()),
            ("AI 配色", icon_robot, AiPalettePage()),
            ("UI 色卡", icon_tiles, PaletteGridPage("ui")),
            ("传统色", icon_ink, PaletteGridPage("traditional")),
        ]

        for name, icon_enum, widget in self.items:
            # 【核心修复】将 FluentIcon 枚举转为 QIcon 对象
            if hasattr(icon_enum, 'icon'):
                actual_icon = icon_enum.icon()
            else:
                actual_icon = QIcon()  # 空图标保底

            item = QListWidgetItem(actual_icon, name)
            self.list_widget.addItem(item)
            self.stack.addWidget(widget)

        self.list_widget.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.list_widget.setCurrentRow(0)  # 默认选中第一个

        h_layout.addWidget(self.nav_card)
        h_layout.addWidget(self.stack)