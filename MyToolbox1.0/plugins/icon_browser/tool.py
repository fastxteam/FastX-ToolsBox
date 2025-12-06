import os
import shutil
import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                               QApplication, QLabel, QFileDialog, QMenu, QInputDialog,
                               QMessageBox, QHBoxLayout, QFrame)
from PySide6.QtCore import Qt, QSize, QTimer, QPoint  # <--- 确保导入 QPoint
from PySide6.QtGui import QIcon, QAction

from qfluentwidgets import (FluentIcon, SearchLineEdit, CardWidget,
                            StrongBodyLabel, SegmentedWidget,
                            PushButton, ToolButton, InfoBar, TransparentToolButton,
                            CheckBox, LineEdit)

from core.plugin_interface import PluginInterface
from core.resource_manager import ResourceManager, qicon
from core.config import ConfigManager


class AssetManagerPlugin(PluginInterface):
    @property
    def name(self) -> str: return "图标浏览器"

    @property
    def icon(self):
        return qicon("icon_browser")

    @property
    def group(self) -> str: return "开发工具"

    @property
    def theme_color(self) -> str: return "#0078D4"

    @property
    def description(self) -> str: return "多源图标管理、预览、导出与代码生成工具。"

    def create_widget(self) -> QWidget: return AssetBrowserWidget()


class AssetBrowserWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_key = "fluent"
        self.folder_history = []
        self.init_ui()
        QTimer.singleShot(100, lambda: self.load_current_tab("fluent"))

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        top_card = CardWidget(self)
        top_layout = QVBoxLayout(top_card)

        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("fluent", "QFluentWidgets (内置)")
        self.pivot.addItem("local", "本地文件系统")
        self.pivot.setCurrentItem("fluent")
        self.pivot.currentItemChanged.connect(self.on_tab_changed)

        top_layout.addWidget(StrongBodyLabel("资源来源", self))
        top_layout.addWidget(self.pivot)

        # 文件夹栏
        self.folder_bar = QWidget()
        fb_layout = QHBoxLayout(self.folder_bar)
        fb_layout.setContentsMargins(0, 5, 0, 5)

        self.btn_switch_folder = PushButton(FluentIcon.FOLDER, "切换文件夹", self)
        self.btn_switch_folder.clicked.connect(self.show_folder_menu)

        self.path_display = LineEdit(self)
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("当前路径...")

        self.btn_remove_folder = TransparentToolButton(getattr(FluentIcon, 'DELETE', FluentIcon.CLOSE), self)
        self.btn_remove_folder.setToolTip("移除当前文件夹")
        self.btn_remove_folder.clicked.connect(self.remove_current_folder)

        self.chk_recursive = CheckBox("遍历子目录", self)
        self.chk_recursive.stateChanged.connect(lambda: self.load_local_icons(self.path_display.text()))

        fb_layout.addWidget(self.btn_switch_folder)
        fb_layout.addWidget(self.path_display, 1)
        fb_layout.addWidget(self.btn_remove_folder)
        fb_layout.addSpacing(10)
        fb_layout.addWidget(self.chk_recursive)

        top_layout.addWidget(self.folder_bar)
        self.folder_bar.hide()

        search_layout = QHBoxLayout()
        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("搜索图标名称...")
        self.search_edit.textChanged.connect(self.filter_icons)

        self.btn_export_info = TransparentToolButton(getattr(FluentIcon, 'Share', FluentIcon.SHARE), self)
        self.btn_export_info.setToolTip("导出列表")
        self.btn_export_info.clicked.connect(self.export_file_list)

        search_layout.addWidget(self.search_edit, 1)
        search_layout.addWidget(self.btn_export_info)
        top_layout.addLayout(search_layout)
        self.layout.addWidget(top_card)

        self.list_widget = QListWidget(self)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(12)
        self.list_widget.setIconSize(QSize(48, 48))
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAcceptDrops(True)
        self.list_widget.setStyleSheet(
            "QListWidget { background: transparent; border: none; } QListWidget::item { background-color: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 8px; padding: 10px; color: #333; } QListWidget::item:hover { background-color: rgba(0, 120, 212, 0.1); border-color: #0078D4; } QListWidget::item:selected { background-color: #0078D4; color: white; }")
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.layout.addWidget(self.list_widget)
        self.lbl_status = QLabel("就绪", self)
        self.layout.addWidget(self.lbl_status)

        self.refresh_folder_data()

    def refresh_folder_data(self):
        self.folder_history = []
        try:
            default_path = ResourceManager.ICON_DIR.resolve()
            self.folder_history.append({"name": "项目默认资源 (Icons)", "path": str(default_path), "is_default": True})
        except:
            pass

        config = ConfigManager.load()
        saved_paths = config.get("asset_folders", [])
        for p in saved_paths:
            path_obj = Path(p)
            if path_obj.exists():
                self.folder_history.append(
                    {"name": f"{path_obj.name} ({str(path_obj)})", "path": str(path_obj.resolve()),
                     "is_default": False})

    def show_folder_menu(self):
        menu = QMenu(self)

        action_add = QAction(FluentIcon.ADD.icon(), "添加新文件夹...", self)
        action_add.triggered.connect(self.add_custom_folder)
        menu.addAction(action_add)

        menu.addSeparator()

        for item in self.folder_history:
            action = QAction(item['name'], self)
            path = item['path']
            action.triggered.connect(lambda ch=False, p=path: self.load_local_icons(p))
            menu.addAction(action)

        # 【修复点】使用 QPoint(0, height)
        menu.exec(self.btn_switch_folder.mapToGlobal(QPoint(0, self.btn_switch_folder.height())))

    def load_current_tab(self, key):
        self.current_key = key
        self.list_widget.clear()
        if key == "fluent":
            self.folder_bar.hide()
            self.load_fluent_icons()
        elif key == "local":
            self.folder_bar.show()
            if self.folder_history:
                self.load_local_icons(self.folder_history[0]['path'])
            else:
                self.lbl_status.setText("没有可用的文件夹")

    def on_tab_changed(self, key):
        self.search_edit.clear()
        self.load_current_tab(key)

    def load_local_icons(self, path_str):
        self.list_widget.clear()
        self.path_display.setText(path_str)
        self.path_display.setToolTip(path_str)

        target_dir = Path(path_str)
        if not target_dir.exists(): return self.lbl_status.setText(f"目录不存在: {path_str}")

        self.lbl_status.setText(f"正在扫描: {path_str}...")
        QApplication.processEvents()

        count = 0
        extensions = {'.svg', '.png', '.jpg', '.ico', '.bmp'}
        try:
            is_recursive = self.chk_recursive.isChecked()
            iterator = target_dir.rglob('*') if is_recursive else target_dir.iterdir()

            for file in iterator:
                if file.is_file() and file.suffix.lower() in extensions:
                    icon = QIcon(str(file))
                    display_name = file.stem
                    if is_recursive and file.parent != target_dir: display_name = f"{file.parent.name}/{file.stem}"
                    item = QListWidgetItem(icon, display_name)
                    item.setSizeHint(QSize(100, 80))
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setToolTip(str(file))
                    code = f'qicon("{file.stem}")' if target_dir.resolve() == ResourceManager.ICON_DIR.resolve() else str(
                        file)
                    item.setData(Qt.UserRole,
                                 {"type": "local", "code": code, "path": str(file), "dir": str(target_dir)})
                    self.list_widget.addItem(item)
                    count += 1

            if count == 0:
                self.lbl_status.setText(f"未找到图片 | 路径: {target_dir}")
            else:
                self.lbl_status.setText(f"加载成功: {count} 个文件 | 路径: {target_dir}")
        except Exception as e:
            self.lbl_status.setText(f"加载出错: {e}")

    def add_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder: return
        path = str(Path(folder).resolve())

        # 查重
        for item in self.folder_history:
            if item['path'] == path:
                self.load_local_icons(path)
                return

        config = ConfigManager.load()
        customs = config.get("asset_folders", [])
        if path not in customs:
            customs.append(path)
            config["asset_folders"] = customs
            ConfigManager.save(config)

        self.refresh_folder_data()
        self.load_local_icons(path)
        InfoBar.success("添加成功", f"已切换至: {Path(path).name}", parent=self.window())

    def remove_current_folder(self):
        current_path = self.path_display.text()
        if not current_path: return

        if str(ResourceManager.ICON_DIR.resolve()) == str(Path(current_path).resolve()):
            InfoBar.warning("操作禁止", "不能移除项目默认资源库", parent=self.window())
            return

        config = ConfigManager.load()
        customs = config.get("asset_folders", [])
        if current_path in customs:
            customs.remove(current_path)
            config["asset_folders"] = customs
            ConfigManager.save(config)
            self.refresh_folder_data()
            if self.folder_history: self.load_local_icons(self.folder_history[0]['path'])
            InfoBar.success("已移除", "文件夹已移除", parent=self.window())

    # ... (其他通用方法保持不变: load_fluent_icons, filter_icons, on_item_clicked 等) ...
    # 为了节省篇幅，请保留之前代码中这些与 UI 交互相关的方法
    # 务必确保包含: load_fluent_icons, filter_icons, on_item_clicked, show_context_menu,
    # export_fluent_icon, export_file_list, rename_local_file, delete_local_file, reveal_file
    # dragEnterEvent, dropEvent

    def load_fluent_icons(self):
        self.list_widget.clear()
        count = 0
        for name, member in FluentIcon.__members__.items():
            item = QListWidgetItem(member.icon(), name)
            item.setSizeHint(QSize(100, 80))
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, {"type": "fluent", "code": f"FluentIcon.{name}", "obj": member})
            self.list_widget.addItem(item)
            count += 1
        self.lbl_status.setText(f"内置库: 加载 {count} 个图标")

    def filter_icons(self, text):
        text = text.upper().strip()
        count = self.list_widget.count()
        visible = 0
        for i in range(count):
            item = self.list_widget.item(i)
            if text in item.text().upper():
                item.setHidden(False); visible += 1
            else:
                item.setHidden(True)
        self.lbl_status.setText(f"筛选显示: {visible} / {count}")

    def on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        QApplication.clipboard().setText(data["code"])
        from qfluentwidgets import InfoBar
        InfoBar.success("已复制", f"代码: {data['code']}", parent=self.window(), duration=1500)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        data = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("复制引用代码/路径").triggered.connect(lambda: self.on_item_clicked(item))
        if data["type"] == "fluent":
            menu.addAction("导出为文件...").triggered.connect(lambda: self.export_fluent_icon(item))
        elif data["type"] == "local":
            menu.addSeparator()
            menu.addAction("重命名").triggered.connect(lambda: self.rename_local_file(item))
            menu.addAction("删除文件").triggered.connect(lambda: self.delete_local_file(item))
            menu.addAction("打开所在位置").triggered.connect(lambda: self.reveal_file(data["path"]))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def export_fluent_icon(self, item):
        data = item.data(Qt.UserRole)
        name = item.text().lower()
        path, _ = QFileDialog.getSaveFileName(self, "导出", f"{name}.png", "PNG (*.png);;SVG (*.svg)")
        if path:
            data["obj"].icon().pixmap(64, 64).save(path)
            InfoBar.success("导出成功", path, parent=self.window())

    def export_file_list(self):
        count = self.list_widget.count()
        if count == 0: return InfoBar.warning("无数据", "当前列表为空", parent=self.window())
        items_data = [self.list_widget.item(i).text() for i in range(count)]
        json_str = json.dumps(items_data, indent=4, ensure_ascii=False)
        default_name = f"icons_{self.current_key}.json"
        save_path, _ = QFileDialog.getSaveFileName(self, "导出", default_name, "JSON (*.json);;Text (*.txt)")
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.endswith('.json'):
                    f.write(json_str)
                else:
                    f.write("\n".join(items_data))
            InfoBar.success("导出成功", save_path, parent=self.window())

    def rename_local_file(self, item):
        data = item.data(Qt.UserRole);
        old_path = Path(data["path"])
        new_name, ok = QInputDialog.getText(self, "重命名", "新文件名:", text=old_path.stem)
        if ok and new_name:
            try:
                old_path.rename(old_path.with_name(new_name + old_path.suffix)); self.load_local_icons(
                    self.path_display.text())
            except:
                pass

    def delete_local_file(self, item):
        data = item.data(Qt.UserRole);
        path = Path(data["path"])
        if QMessageBox.question(self, "确认", f"删除 {path.name}？") == QMessageBox.Yes:
            try:
                os.remove(path); self.load_local_icons(self.path_display.text())
            except:
                pass

    def reveal_file(self, path):
        import subprocess
        subprocess.run(['explorer', '/select,', os.path.normpath(path)])

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if self.current_key != "local": return
        target_dir_str = self.path_display.text()
        if not target_dir_str: return
        target_dir = Path(target_dir_str)
        urls = event.mimeData().urls()
        count = 0
        for url in urls:
            src = Path(url.toLocalFile())
            if src.suffix.lower() in {'.png', '.svg', '.jpg', '.ico'}:
                try:
                    shutil.copy2(src, target_dir / src.name); count += 1
                except:
                    pass
        if count > 0:
            self.load_local_icons(target_dir_str)
            InfoBar.success("导入成功", f"已复制 {count} 个文件", parent=self.window())