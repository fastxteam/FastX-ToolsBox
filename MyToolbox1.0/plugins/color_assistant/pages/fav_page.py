import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame,
                               QHBoxLayout, QLabel, QGridLayout, QApplication, QInputDialog, QMenu)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QBrush, QCursor, QAction
from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel,
                            TransparentToolButton, FluentIcon, InfoBar, FlowLayout, ToolButton)

from plugins.color_assistant.services import CollectionService


# ==========================================
# 1. 组合色卡组件 (PaletteCard)
# ==========================================
class PaletteCard(QFrame):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.colors = item.get('colors', [])
        self.is_custom = (item.get('type') == 'custom_palette')

        self.setFixedSize(240, 120)
        self.setStyleSheet("""
            PaletteCard { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; }
            PaletteCard:hover { border: 2px solid #009faa; }
        """)

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)

        self.color_strip_container = QWidget()
        self.strip_layout = QHBoxLayout(self.color_strip_container)
        self.strip_layout.setContentsMargins(5, 5, 5, 0)
        self.strip_layout.setSpacing(2)
        self.v_layout.addWidget(self.color_strip_container, 1)

        self.render_colors()

        info_bar = QWidget()
        h_info = QHBoxLayout(info_bar)
        h_info.setContentsMargins(10, 5, 5, 5)

        lbl_name = StrongBodyLabel(item['name'], self)
        lbl_name.setStyleSheet("font-size: 13px;")

        h_info.addWidget(lbl_name)
        h_info.addStretch(1)

        btn_style = "background: transparent; border: none;"

        btn_copy = TransparentToolButton(FluentIcon.COPY, self)
        btn_copy.setFixedSize(28, 28);
        btn_copy.setIconSize(QSize(14, 14))
        btn_copy.setToolTip("复制所有 HEX")
        btn_copy.setStyleSheet(btn_style)
        btn_copy.clicked.connect(self.copy_all)

        btn_del = TransparentToolButton(FluentIcon.DELETE, self)
        btn_del.setFixedSize(28, 28);
        btn_del.setIconSize(QSize(14, 14))
        btn_del.setToolTip("删除此色板")
        btn_del.setStyleSheet(btn_style)
        btn_del.clicked.connect(self.delete_me)

        h_info.addWidget(btn_copy)
        h_info.addWidget(btn_del)

        self.v_layout.addWidget(info_bar)

    def render_colors(self):
        # 清理旧颜色
        while self.strip_layout.count():
            item = self.strip_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        if not self.colors:
            lbl = QLabel("空色板", self)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: gray; font-size: 12px;")
            self.strip_layout.addWidget(lbl)
            return

        for hex_code in self.colors:
            bar = QFrame()
            bar.setStyleSheet(f"background-color: {hex_code}; border-radius: 4px;")
            bar.setCursor(Qt.PointingHandCursor)
            bar.setToolTip(f"{hex_code}")

            if self.is_custom:
                bar.setContextMenuPolicy(Qt.CustomContextMenu)
                bar.customContextMenuRequested.connect(lambda pos, c=hex_code: self.show_color_menu(pos, c))
            self.strip_layout.addWidget(bar)

    def show_color_menu(self, pos, hex_code):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 5px; }
            QMenu::item { padding: 6px 20px; border-radius: 4px; color: #333; }
            QMenu::item:selected { background-color: #f0f0f0; color: black; }
        """)
        menu.addAction(f"复制 {hex_code}").triggered.connect(lambda: QApplication.clipboard().setText(hex_code))
        menu.addAction("从此色板移除").triggered.connect(lambda: self.remove_single_color(hex_code))
        menu.exec(QCursor.pos())

    def remove_single_color(self, hex_code):
        if CollectionService.remove_color_from_palette(self.item['id'], hex_code):
            if hex_code in self.colors: self.colors.remove(hex_code)
            self.render_colors()
            InfoBar.success("已移除", hex_code, parent=self.window())

    def copy_all(self):
        QApplication.clipboard().setText(", ".join(self.colors))
        InfoBar.success("已复制", "色值列表已复制", parent=self.window())

    def delete_me(self):
        # 1. 从数据源删除
        CollectionService.remove_item(self.item['id'])
        # 2. 从界面删除
        self.deleteLater()
        # 3. 通知父级刷新 (可选，但为了保险起见，或者只是显示提示)
        InfoBar.success("已删除", "色板已移除", parent=self.window())


# ==========================================
# 2. 收藏页主逻辑
# ==========================================
class FavPage(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent; border: none;")

        self.container = QWidget()
        self.setWidget(self.container)
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("我的收藏", self.container))
        header.addStretch(1)

        self.btn_add_palette = ToolButton(FluentIcon.ADD, self)
        self.btn_add_palette.setToolTip("新建空白色板")
        self.btn_add_palette.clicked.connect(self.create_new_palette)
        header.addWidget(self.btn_add_palette)

        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.UPDATE)
        btn_refresh = TransparentToolButton(icon_sync, self)
        btn_refresh.setToolTip("刷新列表")
        btn_refresh.clicked.connect(self.load_data)
        header.addWidget(btn_refresh)

        self.main_layout.addLayout(header)

        self.flow_container = QWidget()
        self.flow_container.setStyleSheet("background: transparent;")
        self.content_flow = FlowLayout(self.flow_container, needAni=True)
        self.content_flow.setContentsMargins(0, 0, 0, 0)
        self.content_flow.setVerticalSpacing(20)
        self.content_flow.setHorizontalSpacing(20)

        self.main_layout.addWidget(self.flow_container)
        self.main_layout.addStretch(1)

        self.load_data()

    def create_new_palette(self):
        name, ok = QInputDialog.getText(self.window(), "新建色板", "色板名称:")
        if ok and name:
            CollectionService.create_custom_palette(name)
            self.load_data()

    def load_data(self):
        # =================================================
        # 【核心修复】万能清理逻辑 (v3.0)
        # 兼容不同版本的 FlowLayout 和 PySide6
        # =================================================

        # 方法 A: 尝试使用 FlowLayout.removeAllWidgets() (如果库支持)
        try:
            self.content_flow.removeAllWidgets()
        except:
            # 方法 B: 手动遍历清理
            while self.content_flow.count():
                item = self.content_flow.takeAt(0)
                # 检查 item 是否有效
                if not item: continue

                # 尝试获取 Widget
                widget = None
                if hasattr(item, 'widget'):
                    widget = item.widget()
                elif isinstance(item, QWidget):
                    widget = item

                if widget:
                    widget.hide()
                    widget.deleteLater()

        # 再次确保清空：遍历子控件
        for child in self.flow_container.children():
            if isinstance(child, (PaletteCard, QFrame)) and child.isVisible():
                child.deleteLater()

        # 读取数据
        items = CollectionService.get_all()

        # 移除空提示
        for i in reversed(range(self.main_layout.count())):
            item = self.main_layout.itemAt(i)
            w = item.widget()
            if w and isinstance(w, BodyLabel):
                w.deleteLater()

        if not items:
            lbl = BodyLabel("暂无收藏，快去挑选或生成喜欢的颜色吧！", self.container)
            lbl.setStyleSheet("color: gray; margin-top: 50px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.main_layout.insertWidget(1, lbl)
            return

        for item in items:
            t = item.get('type')
            if t == 'color':
                self.add_color_card(item)
            elif t == 'gradient':
                self.add_gradient_card(item)
            elif t in ['custom_palette', 'palette']:
                self.add_palette_card(item)

    def add_palette_card(self, item):
        card = PaletteCard(item, self.container)
        self.content_flow.addWidget(card)

    def add_color_card(self, item):
        card = self.create_base_card()
        v = QVBoxLayout(card);
        v.setContentsMargins(0, 0, 0, 0);
        v.setSpacing(0)
        color_area = QFrame();
        color_area.setStyleSheet(
            f"background-color: {item['hex']}; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        color_area.setCursor(Qt.PointingHandCursor)
        v.addWidget(color_area, 1)
        info = self.create_info_area(item['name'], item['hex'], card, item['id'])
        v.addWidget(info)
        self.content_flow.addWidget(card)

    def add_gradient_card(self, item):
        card = self.create_base_card()
        v = QVBoxLayout(card);
        v.setContentsMargins(0, 0, 0, 0);
        v.setSpacing(0)
        grad_area = GradientPreview(item['colors'], item['angle'])
        v.addWidget(grad_area, 1)
        info = self.create_info_area(item['name'], "渐变色", card, item['id'])
        v.addWidget(info)
        self.content_flow.addWidget(card)

    def create_base_card(self):
        card = QFrame();
        card.setFixedSize(240, 120)
        card.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; } QFrame:hover { border: 2px solid #009faa; }")
        return card

    def create_info_area(self, title, subtitle, parent_card, item_id):
        widget = QWidget();
        widget.setStyleSheet("background-color: transparent; border: none;")
        h = QHBoxLayout(widget);
        h.setContentsMargins(8, 6, 6, 6)
        text_layout = QVBoxLayout();
        text_layout.setSpacing(2)
        lbl_title = StrongBodyLabel(title, widget);
        lbl_title.setStyleSheet("font-size: 13px; border: none;")
        lbl_sub = BodyLabel(subtitle, widget);
        lbl_sub.setStyleSheet("font-size: 11px; color: gray; border: none;")
        text_layout.addWidget(lbl_title);
        text_layout.addWidget(lbl_sub)
        h.addLayout(text_layout);
        h.addStretch(1)

        btn_style = "background: transparent; border: none;"
        btn_del = TransparentToolButton(FluentIcon.DELETE, widget)
        btn_del.setFixedSize(28, 28);
        btn_del.setIconSize(QSize(14, 14))
        btn_del.setToolTip("删除")
        btn_del.setStyleSheet(btn_style)
        btn_del.clicked.connect(lambda ch, i=item_id, w=parent_card: self.delete_item(i, w))

        h.addWidget(btn_del)
        return widget

    def delete_item(self, item_id, widget):
        CollectionService.remove_item(item_id)
        widget.deleteLater()
        InfoBar.success("已删除", "收藏项已移除", parent=self.window())


class GradientPreview(QFrame):
    def __init__(self, colors, angle, parent=None):
        super().__init__(parent);
        self.colors = colors;
        self.angle = angle
        self.setStyleSheet(
            "border-top-left-radius: 8px; border-top-right-radius: 8px; background: transparent; border: none;")
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self);
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        step = 1.0 / (len(self.colors) - 1)
        for i, c in enumerate(self.colors): grad.setColorAt(i * step, QColor(c))
        painter.setBrush(QBrush(grad));
        painter.setPen(Qt.NoPen);
        painter.drawRoundedRect(self.rect(), 8, 8)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            css = f"background: linear-gradient({self.angle}deg, {', '.join(self.colors)});"
            QApplication.clipboard().setText(css)
            InfoBar.success("CSS 已复制", css, parent=self.window())