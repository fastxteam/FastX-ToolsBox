import os
import shutil
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                               QAbstractItemView, QHBoxLayout, QFrame, QLabel,
                               QFileDialog, QScrollArea)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from qfluentwidgets import (StrongBodyLabel, SubtitleLabel, CaptionLabel,
                            CardWidget, SwitchButton, PrimaryPushButton, InfoBar,
                            ComboBox, setTheme, Theme, PushButton, LineEdit, FluentIcon)

from core.plugin_manager import PluginManager
from core.config import ConfigManager
from core.resource_manager import qicon


# ==========================================
# 1. 外观设置卡片 (包含背景图设置)
# ==========================================
class AppearanceCard(CardWidget):
    """外观设置"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # 标题
        self.layout.addWidget(SubtitleLabel("外观", self))

        # --- 主题选择 ---
        h_layout_theme = QHBoxLayout()
        h_layout_theme.addWidget(StrongBodyLabel("应用主题", self))
        h_layout_theme.addStretch(1)

        self.theme_combo = ComboBox(self)
        self.theme_combo.addItems(["浅色", "深色", "跟随系统"])
        self.theme_combo.setFixedWidth(150)

        config = ConfigManager.load()
        current_theme = config.get("theme", "Light")
        theme_idx = {"Light": 0, "Dark": 1, "Auto": 2}.get(current_theme, 0)
        self.theme_combo.setCurrentIndex(theme_idx)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)

        h_layout_theme.addWidget(self.theme_combo)
        self.layout.addLayout(h_layout_theme)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        self.layout.addWidget(line)

        # --- 首页背景图设置 ---
        self.layout.addWidget(StrongBodyLabel("首页背景", self))

        bg_layout = QHBoxLayout()
        self.bg_path = LineEdit(self)
        self.bg_path.setPlaceholderText("未设置背景图片...")
        self.bg_path.setReadOnly(True)

        # 加载当前背景配置
        current_bg = config.get("background_image", "")
        self.bg_path.setText(current_bg)

        # 安全获取图标
        icon_folder = getattr(FluentIcon, 'FOLDER', FluentIcon.EDIT)
        icon_del = getattr(FluentIcon, 'DELETE', FluentIcon.CLOSE)

        self.btn_bg_select = PushButton(icon_folder, "选择图片", self)
        self.btn_bg_clear = PushButton(icon_del, "清除", self)

        bg_layout.addWidget(self.bg_path)
        bg_layout.addWidget(self.btn_bg_select)
        bg_layout.addWidget(self.btn_bg_clear)
        self.layout.addLayout(bg_layout)

        self.layout.addWidget(CaptionLabel("图片将自动保存到本地资源目录。", self))

        # 连接信号
        self.btn_bg_select.clicked.connect(self.select_background)
        self.btn_bg_clear.clicked.connect(self.clear_background)

    def on_theme_changed(self, index):
        theme_map = {0: "Light", 1: "Dark", 2: "Auto"}
        theme_str = theme_map[index]

        config = ConfigManager.load()
        config["theme"] = theme_str
        ConfigManager.save(config)

        t = getattr(Theme, theme_str.upper(), Theme.AUTO)
        setTheme(t)

        InfoBar.success("主题已切换", f"当前主题: {self.theme_combo.currentText()}", parent=self.window())

    def select_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.update_config(file_path)

    def clear_background(self):
        self.bg_path.clear()
        self.update_config("")

    def update_config(self, path):
        """保存配置并复制图片"""
        try:
            target_path = path  # 默认为原路径

            # 如果是新选择的图片（非空），复制到 resources/backgrounds
            if path and os.path.exists(path):
                # 1. 确保目录存在
                # 使用 core/resource_manager.py 的同级目录逻辑，或者直接基于当前运行目录
                # 这里假设 resources 在项目根目录下
                bg_dir = Path("resources/backgrounds")
                if not bg_dir.exists():
                    bg_dir.mkdir(parents=True, exist_ok=True)

                # 2. 构建目标路径
                file_name = os.path.basename(path)
                target_file = bg_dir / file_name

                # 3. 复制文件 (如果源文件和目标不一样)
                if Path(path).resolve() != target_file.resolve():
                    shutil.copy2(path, target_file)

                # 4. 使用相对路径保存 (这样移动整个软件文件夹后背景依然有效)
                # target_path = str(target_file) # 绝对路径
                target_path = f"resources/backgrounds/{file_name}"  # 相对路径

            # 更新 UI 显示
            self.bg_path.setText(target_path)

            config = ConfigManager.load()
            config["background_image"] = target_path
            ConfigManager.save(config)

            # 通知主窗口刷新背景
            if hasattr(self.window(), 'update_background'):
                self.window().update_background(target_path)

            if path:
                InfoBar.success("背景已更新", "图片已保存到本地资源库", parent=self.window())
            else:
                InfoBar.success("已清除", "背景图片已移除", parent=self.window())

        except Exception as e:
            InfoBar.error("错误", str(e), parent=self.window())


# ==========================================
# 2. 插件管理卡片
# ==========================================
class PluginManageCard(CardWidget):
    """插件管理卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # 标题栏
        header = QHBoxLayout()
        header.addWidget(SubtitleLabel("插件管理", self))
        header.addStretch(1)

        self.btn_save = PrimaryPushButton("保存更改", self)
        self.btn_save.clicked.connect(self.save_changes)
        header.addWidget(self.btn_save)
        self.layout.addLayout(header)

        self.layout.addWidget(CaptionLabel("拖拽调整顺序，切换开关控制显示/隐藏（保存后需重启生效）", self))

        # 列表
        self.list_widget = QListWidget(self)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setStyleSheet(
            "QListWidget { border: 1px solid #e0e0e0; border-radius: 6px; background: transparent; }")

        self.layout.addWidget(self.list_widget)

        self.load_data()

    def load_data(self):
        self.list_widget.clear()

        manager = PluginManager()
        manager.load_plugins()
        plugins = manager.get_plugins(include_disabled=True)

        config = ConfigManager.load()
        disabled = set(config.get("disabled_plugins", []))

        row_height = 50

        for plugin in plugins:
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(0, row_height))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

            widget = QWidget()
            h_layout = QHBoxLayout(widget)
            h_layout.setContentsMargins(15, 5, 15, 5)

            icon_drag = QLabel()
            icon_pixmap = qicon("menu")
            if not icon_pixmap.isNull():
                icon_drag.setPixmap(icon_pixmap.pixmap(16, 16))
            else:
                icon_drag.setText("☰")
            icon_drag.setFixedWidth(24)
            h_layout.addWidget(icon_drag)

            name_lbl = StrongBodyLabel(plugin.name, widget)
            h_layout.addWidget(name_lbl)

            h_layout.addStretch(1)

            switch = SwitchButton(widget)
            switch.setOnText("显示")
            switch.setOffText("隐藏")
            is_enabled = plugin.name not in disabled
            switch.setChecked(is_enabled)

            item.setData(Qt.UserRole, plugin.name)
            h_layout.addWidget(switch)

            self.list_widget.setItemWidget(item, widget)

        total_height = len(plugins) * row_height + 10
        self.list_widget.setFixedHeight(total_height)

    def save_changes(self):
        new_order = []
        new_disabled = []

        count = self.list_widget.count()
        for i in range(count):
            item = self.list_widget.item(i)
            name = item.data(Qt.UserRole)

            widget = self.list_widget.itemWidget(item)
            switch = widget.findChild(SwitchButton)

            if name:
                new_order.append(name)
                if switch and not switch.isChecked():
                    new_disabled.append(name)

        try:
            config = ConfigManager.load()
            config["plugin_order"] = new_order
            config["disabled_plugins"] = new_disabled
            ConfigManager.save(config)
            InfoBar.success("保存成功", "设置已更新，请重启软件以生效。", parent=self.window())
        except Exception as e:
            InfoBar.error("保存失败", str(e), parent=self.window())


# ==========================================
# 3. 设置页面主容器
# ==========================================
class SettingsInterface(QScrollArea):  # 使用 QScrollArea 而不是 ScrollArea
    """设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsInterface")

        self.scrollWidget = QWidget()
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.v_layout = QVBoxLayout(self.scrollWidget)
        self.v_layout.setContentsMargins(30, 30, 30, 30)
        self.v_layout.setSpacing(20)

        self.v_layout.addWidget(SubtitleLabel("设置", self))

        # 1. 外观卡片 (背景图设置就在这里)
        self.appearance_card = AppearanceCard(self)
        self.v_layout.addWidget(self.appearance_card)

        # 2. 插件管理卡片
        self.plugin_card = PluginManageCard(self)
        self.v_layout.addWidget(self.plugin_card)

        self.v_layout.addStretch(1)