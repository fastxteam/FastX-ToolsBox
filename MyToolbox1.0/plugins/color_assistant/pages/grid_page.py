import sys
import os

# 确保能找到项目根目录
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
# 【核心修复】加上 StrongBodyLabel
from qfluentwidgets import StrongBodyLabel, FlowLayout

from plugins.color_assistant.components.color_block import ColorBlock
from plugins.color_assistant.color_data import TRADITIONAL_COLORS, UI_PALETTES


class PaletteGridPage(QScrollArea):
    def __init__(self, palette_type="ui"):
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.setWidget(self.container)

        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        if palette_type == "ui":
            self.load_ui_palettes()
        else:
            self.load_traditional_colors()

    def load_ui_palettes(self):
        for name, colors in UI_PALETTES.items():
            self.main_layout.addWidget(StrongBodyLabel(name, self.container))

            flow = QWidget()
            flow_layout = FlowLayout(flow, needAni=False)
            flow_layout.setContentsMargins(0, 0, 0, 0)

            for hex_code in colors:
                flow_layout.addWidget(ColorBlock(hex_code, hex_code))

            self.main_layout.addWidget(flow)
            self.main_layout.addSpacing(20)
        self.main_layout.addStretch(1)

    def load_traditional_colors(self):
        flow = QWidget()
        flow_layout = FlowLayout(flow, needAni=False)

        for item in TRADITIONAL_COLORS:
            flow_layout.addWidget(ColorBlock(item["hex"], item["name"]))

        self.main_layout.addWidget(flow)
        self.main_layout.addStretch(1)