from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication, QMenu, QInputDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction
from qfluentwidgets import InfoBar, FluentIcon

from plugins.color_assistant.services import CollectionService


class ColorBlock(QFrame):
    """基础色块组件"""

    def __init__(self, hex_code, name, parent=None):
        super().__init__(parent)
        self.hex_code = hex_code
        self.name = name
        self.setFixedSize(110, 90)
        self.setCursor(Qt.PointingHandCursor)

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)
        self.v_layout.addStretch(1)

        # 底部文字标签
        self.lbl_name = QLabel(f"{name}\n{hex_code}", self)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.95);
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            color: #333; font-size: 11px; padding: 4px;
        """)
        self.v_layout.addWidget(self.lbl_name)

        self.update_style(hover=False)

    def update_style(self, hover=False):
        border = "2px solid #009faa" if hover else "1px solid #e0e0e0"
        self.setStyleSheet(f"""
            ColorBlock {{ 
                background-color: {self.hex_code}; 
                border-radius: 8px; 
                border: {border}; 
            }}
        """)

    def enterEvent(self, e):
        self.update_style(hover=True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update_style(hover=False)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        # 左键点击复制
        if e.button() == Qt.LeftButton:
            self.copy_hex()
        super().mouseReleaseEvent(e)

    # =========================================================
    # 【核心功能】右键菜单 (包含收藏)
    # =========================================================
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #333;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
                color: black;
            }
            QMenu::separator {
                height: 1px;
                background: #eee;
                margin: 4px 0;
            }
        """)
        # 1. 复制
        action_copy_hex = QAction(f"复制 HEX: {self.hex_code}", self)
        action_copy_hex.triggered.connect(self.copy_hex)
        menu.addAction(action_copy_hex)

        menu.addSeparator()

        # 2. 收藏单色
        if CollectionService.is_collected(self.hex_code):
            action_fav = QAction("♥ 已在收藏夹", self)
            action_fav.setEnabled(False)
            menu.addAction(action_fav)
        else:
            action_add = QAction("♡ 收藏此颜色", self)
            action_add.triggered.connect(self.add_to_favorite)
            menu.addAction(action_add)

        # 3. 【新增】添加到色板
        palettes = CollectionService.get_custom_palettes()
        if palettes:
            submenu = menu.addMenu("添加到色板...")
            for p in palettes:
                # 使用闭包捕获 p['id']
                action = QAction(p['name'], self)
                action.triggered.connect(lambda ch=False, pid=p['id'], name=p['name']: self.add_to_palette(pid, name))
                submenu.addAction(action)

        # 4. 快速新建色板并添加
        action_new = QAction("新建色板并添加...", self)
        action_new.triggered.connect(self.create_and_add)
        menu.addAction(action_new)

        menu.exec(event.globalPos())

    def add_to_favorite(self):
        CollectionService.add_color(self.hex_code, self.name)
        InfoBar.success("收藏成功", "已加入收藏夹", parent=self.window())

    def add_to_palette(self, pid, pname):
        if CollectionService.add_color_to_palette(pid, self.hex_code):
            InfoBar.success("添加成功", f"已加入色板 '{pname}'", parent=self.window())
        else:
            InfoBar.warning("重复", f"色板 '{pname}' 中已存在此颜色", parent=self.window())

    def create_and_add(self):
        name, ok = QInputDialog.getText(self.window(), "新建色板", "请输入色板名称:")
        if ok and name:
            new_p = CollectionService.create_custom_palette(name)
            CollectionService.add_color_to_palette(new_p['id'], self.hex_code)
            InfoBar.success("成功", f"已创建色板 '{name}' 并添加颜色", parent=self.window())

    def copy_hex(self):
        self.copy_text(self.hex_code)

    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        InfoBar.success("已复制", f"{self.name} {text}", parent=self.window(), duration=1500)