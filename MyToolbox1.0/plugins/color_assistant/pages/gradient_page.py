import random
import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
                               QFrame, QGridLayout, QApplication, QDial)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QPen

from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel,
                            PrimaryPushButton, PushButton, TransparentToolButton,
                            FluentIcon, Slider, ColorPickerButton, InfoBar, FlowLayout)

from plugins.color_assistant.services import CollectionService
from core.resource_manager import qicon


# ==========================================
# 1. 渐变小卡片 (用于列表)
# ==========================================
class GradientBlock(QFrame):
    def __init__(self, colors, angle=135, name="渐变", parent=None):
        super().__init__(parent)
        self.colors = colors
        self.angle = angle
        self.name = name
        self.setFixedSize(160, 120)
        self.setCursor(Qt.PointingHandCursor)

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addStretch(1)

        info_bar = QWidget()
        info_bar.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.95); border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        h = QHBoxLayout(info_bar)
        h.setContentsMargins(8, 4, 4, 4)

        lbl = BodyLabel(name, info_bar)
        lbl.setStyleSheet("font-size: 12px; color: #333; background: transparent; border: none;")

        self.btn_fav = TransparentToolButton(FluentIcon.HEART, info_bar)
        self.btn_fav.setFixedSize(24, 24)
        self.btn_fav.setIconSize(QSize(14, 14))
        self.btn_fav.setCheckable(True)
        self.btn_fav.setStyleSheet("background: transparent; border: none;")
        self.btn_fav.clicked.connect(self.toggle_fav)

        h.addWidget(lbl)
        h.addStretch(1)
        h.addWidget(self.btn_fav)

        self.v_layout.addWidget(info_bar)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, self.width(), self.height())
        step = 1.0 / (len(self.colors) - 1)
        for i, c in enumerate(self.colors):
            grad.setColorAt(i * step, QColor(c))

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 发送信号给主界面更新顶部预览，而不是直接复制
            # 这里简单起见，还是直接复制
            css = f"background: linear-gradient({self.angle}deg, {', '.join(self.colors)});"
            QApplication.clipboard().setText(css)
            InfoBar.success("CSS 已复制", css, parent=self.window())
        super().mouseReleaseEvent(e)

    def toggle_fav(self, checked):
        if checked:
            CollectionService.add_gradient(self.colors, self.angle, self.name)
            InfoBar.success("已收藏", self.name, parent=self.window())


# ==========================================
# 2. 顶部超级预览器
# ==========================================
# ==========================================
# 2. 顶部超级预览器 (UI 修复版)
# ==========================================
class GradientGenerator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(220)
        self.colors = ["#4facfe", "#00f2fe"]
        self.angle = 135

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # 悬浮控制条
        self.control_bar = CardWidget(self)
        self.control_bar.setFixedHeight(60)
        self.control_bar.setStyleSheet("""
            CardWidget { 
                background-color: rgba(255, 255, 255, 0.95); 
                border-radius: 30px; 
                border: 1px solid rgba(0,0,0,0.1);
            }
        """)

        h_layout = QHBoxLayout(self.control_bar)
        h_layout.setContentsMargins(15, 5, 15, 5)
        h_layout.setSpacing(10)  # 控件间距

        # 1. 颜色选择区
        self.btn_col1 = ColorPickerButton(QColor(self.colors[0]), "Start", self.control_bar)
        self.btn_col1.setFixedSize(36, 36)
        self.btn_col1.setStyleSheet("border-radius: 18px; border: 2px solid #e0e0e0;")

        # 交换按钮
        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.SYNC)
        self.btn_swap = TransparentToolButton(icon_sync, self.control_bar)
        self.btn_swap.setToolTip("交换颜色")
        self.btn_swap.clicked.connect(self.swap_colors)

        self.btn_col2 = ColorPickerButton(QColor(self.colors[1]), "End", self.control_bar)
        self.btn_col2.setFixedSize(36, 36)
        self.btn_col2.setStyleSheet("border-radius: 18px; border: 2px solid #e0e0e0;")

        h_layout.addWidget(self.btn_col1)
        h_layout.addWidget(self.btn_swap)
        h_layout.addWidget(self.btn_col2)

        # 分隔线
        line1 = QFrame();
        line1.setFrameShape(QFrame.VLine);
        line1.setStyleSheet("color: #ddd;")
        h_layout.addWidget(line1)

        # 2. 角度控制区
        self.slider_angle = Slider(Qt.Horizontal, self.control_bar)
        self.slider_angle.setRange(0, 360)
        self.slider_angle.setValue(135)
        self.slider_angle.setFixedWidth(100)
        self.slider_angle.valueChanged.connect(self.on_angle_changed)

        self.lbl_angle = BodyLabel("135°", self.control_bar)
        self.lbl_angle.setFixedWidth(40)

        h_layout.addWidget(self.slider_angle)
        h_layout.addWidget(self.lbl_angle)

        # 分隔线
        line2 = QFrame();
        line2.setFrameShape(QFrame.VLine);
        line2.setStyleSheet("color: #ddd;")
        h_layout.addWidget(line2)

        # 3. 操作区
        # 随机按钮 (使用骰子图标，如果没有就用默认)
        icon_random = qicon("dice")
        if icon_random.isNull(): icon_random = getattr(FluentIcon, 'RINGER', FluentIcon.refresh).icon()

        self.btn_random = TransparentToolButton(icon_random, self.control_bar)
        self.btn_random.setToolTip("随机生成")
        self.btn_random.clicked.connect(self.random_gen)

        # 复制按钮
        self.btn_copy = PrimaryPushButton("复制 CSS", self.control_bar)
        self.btn_copy.setFixedWidth(90)
        self.btn_copy.clicked.connect(self.copy_css)

        h_layout.addStretch(1)  # 弹簧，把操作按钮推到最右边
        h_layout.addWidget(self.btn_random)
        h_layout.addWidget(self.btn_copy)

        # 布局组装
        self.layout.addStretch(1)
        self.layout.addWidget(self.control_bar, 0, Qt.AlignCenter)
        self.layout.addStretch(1)

        # 连接信号
        self.btn_col1.colorChanged.connect(self.update_colors)
        self.btn_col2.colorChanged.connect(self.update_colors)

    def update_colors(self):
        self.colors = [self.btn_col1.color.name(), self.btn_col2.color.name()]
        self.update()  # 重绘背景

    def on_angle_changed(self, val):
        self.angle = val
        self.lbl_angle.setText(f"{val}°")
        self.update()

    def swap_colors(self):
        c1 = self.btn_col1.color
        c2 = self.btn_col2.color
        # 阻断信号防止递归刷新
        self.btn_col1.blockSignals(True);
        self.btn_col2.blockSignals(True)
        self.btn_col1.setColor(c2)
        self.btn_col2.setColor(c1)
        self.btn_col1.blockSignals(False);
        self.btn_col2.blockSignals(False)
        self.update_colors()

    def random_gen(self):
        c1 = QColor.fromRgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        c2 = QColor.fromRgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        angle = random.randint(0, 360)

        self.btn_col1.setColor(c1)
        self.btn_col2.setColor(c2)
        self.slider_angle.setValue(angle)
        # 信号会自动触发 update

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制全背景渐变
        # 计算角度 (简单映射：0度=下到上, 90度=左到右)
        # 精确计算需要三角函数，这里简化处理，能看效果就行
        w, h = self.width(), self.height()

        # 简易角度映射
        if 45 <= self.angle < 135:
            x1, y1, x2, y2 = 0, 0, w, 0  # 左->右
        elif 135 <= self.angle < 225:
            x1, y1, x2, y2 = 0, 0, 0, h  # 上->下
        elif 225 <= self.angle < 315:
            x1, y1, x2, y2 = w, 0, 0, 0  # 右->左
        else:
            x1, y1, x2, y2 = 0, h, 0, 0  # 下->上

        grad = QLinearGradient(x1, y1, x2, y2)
        grad.setColorAt(0, QColor(self.colors[0]))
        grad.setColorAt(1, QColor(self.colors[1]))

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def copy_css(self):
        css = f"background: linear-gradient({self.angle}deg, {', '.join(self.colors)});"
        QApplication.clipboard().setText(css)
        InfoBar.success("CSS 已复制", css, parent=self.window())

# ==========================================
# 3. 主页面 (上下布局)
# ==========================================
class GradientPage(QWidget):
    def __init__(self):
        super().__init__()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")

        self.container = QWidget()
        self.scroll.setWidget(self.container)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(30)

        # --- 顶部：生成器 ---
        # 移除了所有多余的 Layout，只保留 Title 和 Generator
        self.layout.addWidget(StrongBodyLabel("渐变工坊", self))
        self.generator = GradientGenerator()
        self.layout.addWidget(self.generator)

        # --- 底部：灵感库 ---
        self.layout.addWidget(StrongBodyLabel("热门灵感", self))

        self.flow_layout = FlowLayout(needAni=True)
        self.flow_layout.setContentsMargins(0, 0, 0, 0)
        self.flow_layout.setVerticalSpacing(15)
        self.flow_layout.setHorizontalSpacing(15)

        self.layout.addLayout(self.flow_layout)

        self.main_layout.addWidget(self.scroll)

        self.load_presets()

    def load_presets(self):
        presets = [
            (["#a18cd1", "#fbc2eb"], "莫兰迪紫"),
            (["#fad0c4", "#ffd1ff"], "樱花粉"),
            (["#ff9a9e", "#fecfef"], "甜蜜之吻"),
            (["#fbc2eb", "#a6c1ee"], "梦幻蓝紫"),
            (["#84fab0", "#8fd3f4"], "清凉薄荷"),
            (["#a1c4fd", "#c2e9fb"], "天空之境"),
            (["#cfd9df", "#e2ebf0"], "云雾白"),
            (["#43e97b", "#38f9d7"], "极光绿"),
            (["#fa709a", "#fee140"], "日落橙"),
            (["#667eea", "#764ba2"], "深邃夜空"),
            (["#2af598", "#009efd"], "电子蓝绿"),
            (["#b721ff", "#21d4fd"], "赛博朋克"),
            (["#4facfe", "#00f2fe"], "马尔代夫"),
            (["#43e97b", "#38f9d7"], "清新自然"),
        ]

        for colors, name in presets:
            card = GradientBlock(colors, 135, name)
            self.flow_layout.addWidget(card)