import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
                               QListWidgetItem, QStackedWidget, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon

from qfluentwidgets import (FluentIcon, CardWidget, SubtitleLabel, TransparentToolButton)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon

from plugins.color_assistant.pages.picker_page import ColorPickerPage
from plugins.color_assistant.pages.grid_page import PaletteGridPage
from plugins.color_assistant.pages.ai_page import AiPalettePage
from plugins.color_assistant.pages.fav_page import FavPage
from plugins.color_assistant.pages.gradient_page import GradientPage
from plugins.color_assistant.pages.image_page import ImagePalettePage # 新增

class ColorAssistantPlugin(PluginInterface):
    @property
    def name(self) -> str: return "颜色助手"

    @property
    def icon(self): return qicon("palette")

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
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        self.nav_card = QWidget()
        self.nav_card.setFixedWidth(200)
        self.nav_card.setStyleSheet("background-color: transparent; border-right: 1px solid #e5e5e5;")
        nav_layout = QVBoxLayout(self.nav_card)
        nav_layout.setContentsMargins(10, 20, 10, 20)

        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("颜色助手", self.nav_card))
        nav_layout.addLayout(header)
        nav_layout.addSpacing(20)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; outline: none; border: none; }
            QListWidget::item { 
                height: 40px; 
                border-radius: 6px; 
                padding-left: 10px; 
                margin-bottom: 4px; 
                color: #333;
            }
            QListWidget::item:hover { background: rgba(0,0,0,0.05); }
            QListWidget::item:selected { background: rgba(0,0,0,0.1); color: #000; font-weight: bold; }
        """)

        nav_layout.addWidget(self.list_widget)

        self.stack = QStackedWidget()

        # 准备图标
        # 优先使用 qicon 加载自定义 SVG，如果没有文件，qicon 会自动回退到默认
        # 所以你可以放心地写 qicon("ai"), qicon("gradient") 等

        # 如果你想混用 FluentIcon 枚举和自定义 QIcon，逻辑如下：
        icon_image = getattr(FluentIcon, 'PHOTO', FluentIcon.CAMERA)
        self.items = [
            ("颜色", getattr(FluentIcon, 'PALETTE', FluentIcon.PALETTE), ColorPickerPage()),  # 尝试加载 color_wheel.svg
            ("AI 配色", qicon("colorai"), AiPalettePage()),
            ("图片色卡", qicon("image"), ImagePalettePage()),  # 新增
            ("渐变色", qicon("gradient"), GradientPage()),  # 加载 gradient.svg
            ("UI 色卡", qicon("colorui"), PaletteGridPage("ui")),
            ("传统色", getattr(FluentIcon, 'PENCIL_INK', FluentIcon.IOT), PaletteGridPage("traditional")),
            ("收藏夹", qicon("favorite"), FavPage()),
        ]

        for name, icon_obj, widget in self.items:
            # 【核心修复】智能判断图标类型
            if isinstance(icon_obj, QIcon):
                actual_icon = icon_obj
            elif hasattr(icon_obj, 'icon'):
                # 处理 FluentIcon 枚举
                actual_icon = icon_obj.icon()
            else:
                # 如果是个字符串路径
                actual_icon = QIcon(str(icon_obj))

            item = QListWidgetItem(actual_icon, name)
            self.list_widget.addItem(item)
            self.stack.addWidget(widget)

        total_height = len(self.items) * 44 + 10
        self.list_widget.setFixedHeight(total_height)

        nav_layout.addStretch(1)

        self.list_widget.currentRowChanged.connect(self.on_tab_changed)
        self.list_widget.setCurrentRow(0)

        h_layout.addWidget(self.nav_card)
        h_layout.addWidget(self.stack)

    def on_tab_changed(self, index):
        self.stack.setCurrentIndex(index)
        current_widget = self.stack.widget(index)
        if isinstance(current_widget, FavPage):
            if hasattr(current_widget, 'load_data'):
                current_widget.load_data()