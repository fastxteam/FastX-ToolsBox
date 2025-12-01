import re
import json
import fnmatch
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QFileDialog, QApplication, QStackedWidget,
                               QLabel, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

from qfluentwidgets import (PrimaryPushButton, PushButton, CheckBox,
                            LineEdit, StrongBodyLabel, SubtitleLabel,
                            InfoBar, InfoBarPosition, CardWidget,
                            PlainTextEdit, ComboBox, BodyLabel,
                            StateToolTip, SegmentedWidget,
                            ScrollArea, ExpandLayout, ToolTipFilter,
                            MessageBox, TextEdit)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


class DirectoryTreePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "目录树工具箱"

    @property
    def icon(self):
        return qicon("directory_tree")  # 需要 icons/directory_tree.svg

    @property
    def group(self) -> str:
        return "文件工具"

    @property
    def theme_color(self) -> str:
        return "#0097A7"  # 青色

    @property
    def description(self) -> str:
        return "文件夹结构↔Tree文本双向转换工具"

    def create_widget(self) -> QWidget:
        return DirectoryTreeWidget()


class DirectoryTreeWidget(QWidget):
    def __init__(self):
        super().__init__()

        # ========== 共享数据 ==========
        self.default_ignore = [
            "__pycache__", "*.pyc", ".git", ".DS_Store", "Thumbs.db",
            "*.log", "*.tmp", ".venv", "venv", ".idea", ".vscode",
            "*.egg-info", "build", "dist", "__pycache__", "*.pyo",
            "node_modules", ".pytest_cache", ".coverage"
        ]
        self.ignore_patterns = self.default_ignore.copy()

        # Emoji 黑名单
        self.emoji_blacklist = [
            '📁', '📄', '📝', '⚙️', '📦', '🔧', '⚡', '🧪', '📚', '🔍',
            '📌', '✅', '❌', '⚠️', '💡', '🚀', '🎯', '🛠️', '📎', '📌',
            '📂', '🗂️', '🧾', '📋', '💼', '📊', '📈', '📉', '🎨', '🔨'
        ]

        # 空 Jupyter Notebook 模板
        self.empty_notebook = {
            "cells": [],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }

        self.init_ui()

    def init_ui(self):
        """初始化界面 - 使用选项卡设计"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # ========== 标题区 ==========
        title_layout = QHBoxLayout()
        title = SubtitleLabel("📂 目录树工具箱", self)
        title.setStyleSheet("font-weight: bold;")

        title_layout.addWidget(title)
        title_layout.addStretch(1)

        # 功能切换标签
        self.pivot = SegmentedWidget(self)
        self.folder2tree_item = self.pivot.addItem(
            routeKey="folder2tree",
            text="📁 文件夹→Tree",
            onClick=lambda: self.switch_to("folder2tree")
        )
        self.tree2folder_item = self.pivot.addItem(
            routeKey="tree2folder",
            text="🌳 Tree→文件夹",
            onClick=lambda: self.switch_to("tree2folder")
        )

        title_layout.addWidget(self.pivot)
        layout.addLayout(title_layout)

        # 分隔线
        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(separator)

        # ========== 内容堆栈 ==========
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        # ========== 创建两个功能页面 ==========
        self.folder2tree_page = self.create_folder2tree_page()
        self.tree2folder_page = self.create_tree2folder_page()

        self.stacked_widget.addWidget(self.folder2tree_page)
        self.stacked_widget.addWidget(self.tree2folder_page)

        # 默认显示第一个页面
        self.pivot.setCurrentItem(self.folder2tree_item)
        self.stacked_widget.setCurrentWidget(self.folder2tree_page)

        # ========== 全局操作按钮 ==========
        bottom_layout = QHBoxLayout()

        # 共享的配置管理
        self.btn_manage_ignore = PushButton(qicon("settings"), "管理忽略规则", self)
        self.btn_manage_ignore.clicked.connect(self.manage_ignore_rules)
        self.btn_manage_ignore.setToolTip("管理两个功能共享的忽略规则")
        self.btn_manage_ignore.installEventFilter(ToolTipFilter(self.btn_manage_ignore))

        self.btn_clear_all = PushButton(qicon("delete"), "清空所有", self)
        self.btn_clear_all.clicked.connect(self.clear_all)
        self.btn_clear_all.setToolTip("清空所有输入和输出")
        self.btn_clear_all.installEventFilter(ToolTipFilter(self.btn_clear_all))

        bottom_layout.addWidget(self.btn_manage_ignore)
        bottom_layout.addWidget(self.btn_clear_all)
        bottom_layout.addStretch(1)

        layout.addLayout(bottom_layout)

    def switch_to(self, page_key):
        """切换页面"""
        if page_key == "folder2tree":
            self.stacked_widget.setCurrentWidget(self.folder2tree_page)
            self.pivot.setCurrentItem(self.folder2tree_item)
        else:
            self.stacked_widget.setCurrentWidget(self.tree2folder_page)
            self.pivot.setCurrentItem(self.tree2folder_item)

    # ========== Page 1: 文件夹→Tree ==========
    def create_folder2tree_page(self):
        """创建文件夹到Tree页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 文件夹选择区域
        folder_card = CardWidget(page)
        folder_layout = QVBoxLayout(folder_card)

        # 卡片标题
        folder_title = StrongBodyLabel("📁 源文件夹")
        folder_layout.addWidget(folder_title)

        # 路径显示和选择
        path_layout = QHBoxLayout()
        self.folder_path_edit = LineEdit(page)
        self.folder_path_edit.setPlaceholderText("请选择文件夹或拖拽到此处...")
        self.folder_path_edit.setReadOnly(True)
        path_layout.addWidget(self.folder_path_edit)

        self.btn_browse_folder = PushButton(qicon("folder"), "选择", page)
        self.btn_browse_folder.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.btn_browse_folder)

        self.btn_clear_folder = PushButton(qicon("delete"), "清空", page)
        self.btn_clear_folder.clicked.connect(lambda: self.folder_path_edit.clear())
        path_layout.addWidget(self.btn_clear_folder)

        folder_layout.addLayout(path_layout)
        layout.addWidget(folder_card)

        # 配置区域
        config_card = CardWidget(page)
        config_layout = QVBoxLayout(config_card)

        # 卡片标题
        config_title = StrongBodyLabel("⚙️ 配置选项")
        config_layout.addWidget(config_title)

        # 输出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(BodyLabel("输出格式:"))
        self.format_combo = ComboBox(page)
        self.format_combo.addItems(["Tree文本格式", "Markdown格式", "JSON格式"])
        format_layout.addWidget(self.format_combo)

        # 选项
        self.ignore_hidden_check = CheckBox("忽略隐藏文件和目录", page)
        self.ignore_hidden_check.setChecked(True)
        format_layout.addWidget(self.ignore_hidden_check)

        self.exclude_empty_check = CheckBox("排除空目录", page)
        self.exclude_empty_check.setChecked(True)
        format_layout.addWidget(self.exclude_empty_check)

        config_layout.addLayout(format_layout)
        layout.addWidget(config_card)

        # 输出区域
        output_card = CardWidget(page)
        output_layout = QVBoxLayout(output_card)

        # 卡片标题
        output_title = StrongBodyLabel("📋 输出结果")
        output_layout.addWidget(output_title)

        self.output_text = PlainTextEdit(page)
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        # 输出操作按钮
        output_btn_layout = QHBoxLayout()

        self.btn_generate_tree = PrimaryPushButton(qicon("sync"), "生成目录树", page)
        self.btn_generate_tree.clicked.connect(self.generate_directory_tree)
        self.btn_generate_tree.setEnabled(False)
        output_btn_layout.addWidget(self.btn_generate_tree)

        self.btn_copy_output = PushButton(qicon("copy"), "复制", page)
        self.btn_copy_output.clicked.connect(self.copy_output)
        output_btn_layout.addWidget(self.btn_copy_output)

        self.btn_save_output = PushButton(qicon("save"), "保存", page)
        self.btn_save_output.clicked.connect(self.save_output_file)
        output_btn_layout.addWidget(self.btn_save_output)

        self.btn_clear_output = PushButton(qicon("delete"), "清空", page)
        self.btn_clear_output.clicked.connect(lambda: self.output_text.clear())
        output_btn_layout.addWidget(self.btn_clear_output)

        output_btn_layout.addStretch(1)
        output_layout.addLayout(output_btn_layout)
        layout.addWidget(output_card)

        # 连接信号
        self.folder_path_edit.textChanged.connect(
            lambda: self.btn_generate_tree.setEnabled(bool(self.folder_path_edit.text().strip()))
        )

        return page

    # ========== Page 2: Tree→文件夹 ==========
    def create_tree2folder_page(self):
        """创建Tree到文件夹页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 输入区域
        input_card = CardWidget(page)
        input_layout = QVBoxLayout(input_card)

        # 卡片标题
        input_title = StrongBodyLabel("📝 输入Tree结构")
        input_layout.addWidget(input_title)

        self.input_tree_text = PlainTextEdit(page)
        self.input_tree_text.setPlaceholderText(
            "粘贴Tree结构或导入文件...\n\n示例：\n"
            "project/\n"
            "├── src/\n"
            "│   ├── __init__.py\n"
            "│   └── main.py\n"
            "├── tests/\n"
            "│   └── test_main.py\n"
            "└── README.md"
        )
        input_layout.addWidget(self.input_tree_text)

        # 输入操作按钮
        input_btn_layout = QHBoxLayout()

        self.btn_import_tree = PushButton(qicon("upload"), "导入文件", page)
        self.btn_import_tree.clicked.connect(self.import_tree_file)
        input_btn_layout.addWidget(self.btn_import_tree)

        self.btn_paste_tree = PushButton(qicon("paste"), "粘贴剪贴板", page)
        self.btn_paste_tree.clicked.connect(self.paste_tree_clipboard)
        input_btn_layout.addWidget(self.btn_paste_tree)

        self.btn_insert_example = PushButton(qicon("help"), "插入示例", page)
        self.btn_insert_example.clicked.connect(self.insert_tree_example)
        input_btn_layout.addWidget(self.btn_insert_example)

        self.btn_clear_tree_input = PushButton(qicon("delete"), "清空", page)
        self.btn_clear_tree_input.clicked.connect(lambda: self.input_tree_text.clear())
        input_btn_layout.addWidget(self.btn_clear_tree_input)

        input_btn_layout.addStretch(1)
        input_layout.addLayout(input_btn_layout)
        layout.addWidget(input_card)

        # 配置区域
        config_card = CardWidget(page)
        config_layout = QVBoxLayout(config_card)

        # 卡片标题
        config_title = StrongBodyLabel("⚙️ 生成配置")
        config_layout.addWidget(config_title)

        # 输出目录
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(BodyLabel("输出目录:"))
        self.output_dir_edit = LineEdit(page)
        self.output_dir_edit.setPlaceholderText("选择生成目录...")
        output_dir_layout.addWidget(self.output_dir_edit)

        self.btn_browse_output_dir = PushButton("选择", page)
        self.btn_browse_output_dir.clicked.connect(self.browse_output_directory)
        output_dir_layout.addWidget(self.btn_browse_output_dir)
        config_layout.addLayout(output_dir_layout)

        # 生成选项
        options_layout = QHBoxLayout()

        self.auto_init_check = CheckBox("自动添加 __init__.py", page)
        self.auto_init_check.setChecked(True)
        options_layout.addWidget(self.auto_init_check)

        self.create_ipynb_check = CheckBox("创建空 .ipynb 文件", page)
        self.create_ipynb_check.setChecked(True)
        options_layout.addWidget(self.create_ipynb_check)

        self.create_readme_check = CheckBox("创建 README.md", page)
        self.create_readme_check.setChecked(True)
        options_layout.addWidget(self.create_readme_check)

        config_layout.addLayout(options_layout)
        layout.addWidget(config_card)

        # 日志区域
        log_card = CardWidget(page)
        log_layout = QVBoxLayout(log_card)

        # 卡片标题
        log_title = StrongBodyLabel("📊 生成日志")
        log_layout.addWidget(log_title)

        self.log_text = PlainTextEdit(page)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        # 日志操作按钮
        log_btn_layout = QHBoxLayout()

        self.btn_generate_project = PrimaryPushButton(qicon("rocket"), "生成项目结构", page)
        self.btn_generate_project.clicked.connect(self.generate_project_structure)
        log_btn_layout.addWidget(self.btn_generate_project)

        self.btn_clear_log = PushButton(qicon("delete"), "清空日志", page)
        self.btn_clear_log.clicked.connect(lambda: self.log_text.clear())
        log_btn_layout.addWidget(self.btn_clear_log)

        log_btn_layout.addStretch(1)
        log_layout.addLayout(log_btn_layout)
        layout.addWidget(log_card)

        return page

    # ========== 共享功能方法 ==========
    def manage_ignore_rules(self):
        """管理忽略规则对话框"""
        dialog = MessageBox(
            "管理忽略规则",
            "设置两个功能共享的文件/目录忽略规则\n（每行一个规则，支持通配符 * 和 ?）",
            self
        )

        text_edit = TextEdit()
        text_edit.setPlainText("\n".join(self.ignore_patterns))
        text_edit.setMinimumSize(400, 300)

        dialog.yesButton.setText("保存")
        dialog.cancelButton.setText("取消")

        # 添加文本编辑框到对话框
        dialog.contentLayout.addWidget(text_edit, 1, 0, 1, 2)

        if dialog.exec():
            rules = [line.strip() for line in text_edit.toPlainText().splitlines() if line.strip()]
            self.ignore_patterns = rules

            InfoBar.success(
                title="成功",
                content=f"已保存 {len(rules)} 条忽略规则",
                parent=self
            )

    def clear_all(self):
        """清空所有内容"""
        self.folder_path_edit.clear()
        self.output_text.clear()
        self.input_tree_text.clear()
        self.output_dir_edit.clear()
        self.log_text.clear()

        InfoBar.info(
            title="已清空",
            content="所有输入和输出已清空",
            parent=self
        )

    def should_ignore(self, path: Path):
        """检查是否应该忽略（共享方法）"""
        name = path.name

        # 检查隐藏文件
        if self.ignore_hidden_check.isChecked() and name.startswith('.'):
            return True

        # 检查忽略规则
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), f"*/{pattern}"):
                return True

        return False

    # ========== 文件夹→Tree 功能方法 ==========
    def browse_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.folder_path_edit.setText(folder)

    def generate_directory_tree(self):
        """生成目录树"""
        folder_path = self.folder_path_edit.text().strip()
        if not folder_path:
            InfoBar.warning(title="警告", content="请选择文件夹", parent=self)
            return

        root = Path(folder_path)
        if not root.exists():
            InfoBar.error(title="错误", content="文件夹不存在", parent=self)
            return

        try:
            # 显示进度
            state_tooltip = StateToolTip("正在生成", "扫描目录结构...", self)
            state_tooltip.move(state_tooltip.getSuitablePos())
            state_tooltip.show()

            # 生成结构
            lines = self._generate_tree_lines(root)
            format_type = self.format_combo.currentText()

            if format_type == "Markdown格式":
                output = self._to_markdown(lines)
            elif format_type == "JSON格式":
                output = self._to_json(root, lines)
            else:
                output = "\n".join(lines)

            self.output_text.setPlainText(output)

            state_tooltip.setContent("生成完成!")
            state_tooltip.setState(StateToolTip.SUCCESS)

            # 3秒后自动关闭
            self.btn_generate_tree.setEnabled(False)
            QApplication.processEvents()

            InfoBar.success(
                title="成功",
                content=f"已生成 {len(lines)} 行目录结构",
                parent=self
            )

        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"生成失败: {str(e)}",
                parent=self
            )
        finally:
            self.btn_generate_tree.setEnabled(True)

    def _generate_tree_lines(self, root_path: Path, prefix="", is_last=True):
        """生成目录树文本行"""
        lines = []

        # 根目录
        if prefix == "":
            lines.append(f"{root_path.name}/")
            prefix = ""
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{root_path.name}/")
            prefix = prefix + ("    " if is_last else "│   ")

        try:
            # 获取子项
            children = []
            for item in root_path.iterdir():
                if not self.should_ignore(item):
                    # 检查空目录
                    if self.exclude_empty_check.isChecked() and item.is_dir():
                        try:
                            has_visible = any(not self.should_ignore(child) for child in item.iterdir())
                            if not has_visible:
                                continue
                        except PermissionError:
                            pass
                    children.append(item)

            # 排序：目录在前，文件在后，按名称排序
            children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        except PermissionError:
            lines.append(f"{prefix}└── [权限拒绝]")
            return lines

        # 递归处理子项
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            if child.is_dir():
                lines.extend(self._generate_tree_lines(child, prefix, is_last_child))
            else:
                connector = "└── " if is_last_child else "├── "
                lines.append(f"{prefix}{connector}{child.name}")

        return lines

    def _to_markdown(self, lines):
        """转换为Markdown格式"""
        md_lines = []
        for line in lines:
            clean = re.sub(r'^[│ ├└─]*', '', line).rstrip('/')
            if not clean:
                continue

            is_dir = line.strip().endswith('/')
            name = clean.rstrip('/')

            # 计算缩进层级
            indent_match = re.match(r'^[│ ├└─]*', line)
            indent = len(indent_match.group(0)) if indent_match else 0
            level = indent // 4

            indent_str = "  " * level
            icon = "📁" if is_dir else "📄"
            md_lines.append(f"{indent_str}- [{icon} {name}]()")

        return "\n".join(md_lines)

    def _to_json(self, root_path, lines):
        """转换为JSON格式"""

        def build_tree(path):
            """递归构建树形结构"""
            item = {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "path": str(path.relative_to(root_path))
            }

            if path.is_dir():
                try:
                    children = []
                    for child in path.iterdir():
                        if not self.should_ignore(child):
                            if self.exclude_empty_check.isChecked():
                                if child.is_dir():
                                    has_visible = any(not self.should_ignore(c) for c in child.iterdir())
                                    if not has_visible:
                                        continue
                            children.append(build_tree(child))

                    # 排序
                    children.sort(key=lambda x: (x["type"] == "file", x["name"].lower()))
                    if children:
                        item["children"] = children
                except PermissionError:
                    item["error"] = "Permission denied"

            return item

        try:
            tree = build_tree(root_path)
            return json.dumps(tree, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False)

    def copy_output(self):
        """复制输出到剪贴板"""
        content = self.output_text.toPlainText().strip()
        if not content:
            InfoBar.warning(title="警告", content="输出为空", parent=self)
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(content)

        InfoBar.success(
            title="成功",
            content="已复制到剪贴板",
            duration=2000,
            parent=self
        )

    def save_output_file(self):
        """保存输出到文件"""
        content = self.output_text.toPlainText().strip()
        if not content:
            InfoBar.warning(title="警告", content="输出为空", parent=self)
            return

        folder_path = self.folder_path_edit.text().strip()
        default_name = f"tree_{Path(folder_path).name if folder_path else 'output'}"
        format_type = self.format_combo.currentText()

        if format_type == "Markdown格式":
            default_name += ".md"
            file_filter = "Markdown文件 (*.md);;所有文件 (*.*)"
        elif format_type == "JSON格式":
            default_name += ".json"
            file_filter = "JSON文件 (*.json);;所有文件 (*.*)"
        else:
            default_name += ".txt"
            file_filter = "文本文件 (*.txt);;所有文件 (*.*)"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存文件",
            default_name,
            file_filter
        )

        if file_path:
            try:
                Path(file_path).write_text(content, encoding='utf-8')
                InfoBar.success(
                    title="成功",
                    content=f"已保存到: {Path(file_path).name}",
                    parent=self
                )
            except Exception as e:
                InfoBar.error(
                    title="错误",
                    content=f"保存失败: {str(e)}",
                    parent=self
                )

    # ========== Tree→文件夹 功能方法 ==========
    def import_tree_file(self):
        """导入Tree文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入Tree文件",
            "",
            "文本文件 (*.txt *.md *.json);;所有文件 (*.*)"
        )

        if file_path:
            try:
                content = Path(file_path).read_text(encoding='utf-8')
                self.input_tree_text.setPlainText(content)
                self.add_log(f"✅ 已导入文件: {Path(file_path).name}")
            except Exception as e:
                self.add_log(f"❌ 导入失败: {str(e)}", "error")

    def paste_tree_clipboard(self):
        """粘贴剪贴板内容"""
        clipboard = QApplication.clipboard()
        content = clipboard.text()
        if content.strip():
            self.input_tree_text.setPlainText(content)
            self.add_log("✅ 已粘贴剪贴板内容")
        else:
            self.add_log("⚠️ 剪贴板为空", "warning")

    def insert_tree_example(self):
        """插入示例"""
        example = """my-project/
├── src/
│   ├── __init__.py
│   ├── main.py
│   └── utils/
│       ├── __init__.py
│       ├── file_utils.py
│       └── log_utils.py
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_utils.py
├── docs/
│   └── README.md
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
│   └── analysis.ipynb
├── requirements.txt
├── setup.py
└── .gitignore"""

        self.input_tree_text.setPlainText(example)
        self.add_log("📝 已插入示例结构")

    def browse_output_directory(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir_edit.setText(directory)
            self.add_log(f"📁 输出目录: {directory}")

    def clean_tree_line(self, line):
        """清理Tree行中的emoji和注释"""
        text = line
        for e in self.emoji_blacklist:
            text = text.replace(e, '')

        # 移除注释
        text = re.split(r'\s*#', text)[0]  # Python风格
        text = re.split(r'\s*//', text)[0]  # C风格
        text = re.sub(r'[├└┬─│` ]+', '', text).strip()
        return text

    def parse_tree_structure(self, content):
        """解析Tree结构"""
        lines = [line.rstrip() for line in content.splitlines() if line.strip()]
        if not lines:
            raise ValueError("内容为空")

        paths = []
        stack = []

        for i, line in enumerate(lines):
            clean = self.clean_tree_line(line)
            if not clean:
                continue

            # 计算缩进层级
            indent_match = re.match(r'^[│ ├└┬─]*', line)
            indent_str = indent_match.group(0) if indent_match else ""
            level = max(0, (len(indent_str) + 1) // 4)

            # 第一行是根目录
            if i == 0:
                level = 0

            # 调整堆栈
            while len(stack) > level:
                stack.pop()

            # 判断类型
            is_dir = clean.endswith('/')
            name = clean.rstrip('/')

            # 构建完整路径
            full_path = '/'.join(stack + [name]) + ('/' if is_dir else '')
            paths.append(full_path)

            # 如果是目录，加入堆栈
            if is_dir:
                stack.append(name)

        return sorted(set(paths))

    def normalize_project_paths(self, raw_paths):
        """规范化项目路径"""
        path_set = set(p for p in raw_paths if p)

        # 自动为Python目录添加 __init__.py
        if self.auto_init_check.isChecked():
            py_dirs = set()
            for p in path_set:
                if p.endswith('.py'):
                    parent = str(Path(p).parent)
                    if parent and parent != '.':
                        py_dirs.add(parent + '/')

            for d in py_dirs:
                init_path = d.rstrip('/') + '/__init__.py'
                path_set.add(init_path)

        # 自动添加 README.md
        if self.create_readme_check.isChecked():
            # 找到根目录
            root_dirs = {p.split('/')[0] + '/' for p in path_set if '/' in p}
            for root_dir in root_dirs:
                readme_path = root_dir.rstrip('/') + '/README.md'
                path_set.add(readme_path)

        return sorted(path_set)

    def create_project_structure(self, paths, out_dir):
        """创建项目结构"""
        root = Path(out_dir)
        created = []

        for p in paths:
            full_path = root / p

            try:
                if p.endswith('/'):  # 目录
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.add_log(f"📁 创建目录: {p}")

                    # 为Python包添加 __init__.py（如果配置了）
                    if self.auto_init_check.isChecked() and ('src/' in p or 'utils/' in p or 'tests/' in p):
                        init_file = full_path / "__init__.py"
                        if not init_file.exists():
                            init_file.write_text("# Package initialization\n", encoding='utf-8')
                            self.add_log(f"  ↪ 添加: {p.rstrip('/')}/__init__.py")

                else:  # 文件
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    # 根据文件类型创建内容
                    if p.endswith('.py'):
                        if p.endswith('__init__.py'):
                            content = "# Package initialization\n"
                        else:
                            class_name = Path(p).stem.replace('_', ' ').title().replace(' ', '')
                            content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
{Path(p).stem} - 模块说明
"""

class {class_name}:
    """类说明"""

    def __init__(self):
        pass

def main():
    """主函数"""
    pass

if __name__ == "__main__":
    main()
'''
                        full_path.write_text(content, encoding='utf-8')
                        self.add_log(f"🐍 创建Python文件: {p}")

                    elif p.endswith('.ipynb') and self.create_ipynb_check.isChecked():
                        with open(full_path, 'w', encoding='utf-8') as f:
                            json.dump(self.empty_notebook, f, indent=2, ensure_ascii=False)
                        self.add_log(f"📓 创建Jupyter Notebook: {p}")

                    elif p.endswith('.md'):
                        if 'README' in p.upper():
                            title = Path(p).parent.name.title()
                            content = f"""# {title}

## 项目简介

这是一个通过目录树工具箱生成的项目结构。

## 目录结构

## 使用说明

1. 安装依赖：`pip install -r requirements.txt`
2. 运行主程序：`python src/main.py`
3. 运行测试：`pytest tests/`

## 许可证

MIT License
"""
                        else:
                            content = f"# {Path(p).stem}\n\n文档内容待补充。\n"
                        full_path.write_text(content, encoding='utf-8')
                        self.add_log(f"📝 创建文档: {p}")

                    elif p.endswith('.txt'):
                        if p.endswith('requirements.txt'):
                            content = """# 项目依赖
# 请在此处添加项目依赖
# 例如：
# numpy>=1.21.0
# pandas>=1.3.0
# matplotlib>=3.4.0
"""
                        else:
                            content = f"# {Path(p).name}\n\n文件内容\n"
                        full_path.write_text(content, encoding='utf-8')
                        self.add_log(f"📄 创建文本文件: {p}")

                    else:
                        full_path.touch()
                        self.add_log(f"📄 创建文件: {p}")

                    created.append(p)

            except Exception as e:
                self.add_log(f"❌ 创建失败 {p}: {str(e)}", "error")
                raise

        return created

    def generate_project_structure(self):
        """生成项目结构"""
        content = self.input_tree_text.toPlainText().strip()
        output_dir = self.output_dir_edit.text().strip()

        if not content:
            InfoBar.warning(title="警告", content="请输入Tree结构", parent=self)
            return

        if not output_dir:
            InfoBar.warning(title="警告", content="请选择输出目录", parent=self)
            return

        # 显示进度
        state_tooltip = StateToolTip("正在生成", "解析Tree结构...", self)
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            self.log_text.clear()
            self.add_log("🔍 开始解析Tree结构...")

            # 解析
            raw_paths = self.parse_tree_structure(content)
            self.add_log(f"✅ 解析完成，找到 {len(raw_paths)} 个路径")

            # 规范化
            all_paths = self.normalize_project_paths(raw_paths)
            self.add_log(f"📊 规范化后: {len(all_paths)} 个路径")

            # 创建
            state_tooltip.setContent("正在生成项目结构...")
            self.add_log("🏗️  开始生成项目结构...")

            created = self.create_project_structure(all_paths, output_dir)

            # 获取项目根目录
            if all_paths:
                root_name = all_paths[0].split('/')[0]
                project_path = Path(output_dir) / root_name

                state_tooltip.setContent("项目生成完成!")
                state_tooltip.setState(StateToolTip.SUCCESS)

                self.add_log(f"🎉 项目生成完成！共创建 {len(created)} 个项目项", "success")
                self.add_log(f"📂 项目路径: {project_path.resolve()}")

                # 问是否打开文件夹
                msg = MessageBox(
                    "项目生成成功",
                    f"项目已成功生成到：\n{project_path}\n\n是否打开所在文件夹？",
                    self
                )
                msg.yesButton.setText("打开文件夹")
                msg.cancelButton.setText("关闭")

                if msg.exec():
                    import os
                    import platform

                    try:
                        if platform.system() == "Windows":
                            os.startfile(project_path)
                        elif platform.system() == "Darwin":  # macOS
                            os.system(f'open "{project_path}"')
                        else:  # Linux
                            os.system(f'xdg-open "{project_path}"')
                    except Exception as e:
                        self.add_log(f"⚠️ 无法打开文件夹: {str(e)}", "warning")

        except Exception as e:
            state_tooltip.setContent("生成失败!")
            state_tooltip.setState(StateToolTip.ERROR)

            self.add_log(f"❌ 生成失败: {str(e)}", "error")

            InfoBar.error(
                title="错误",
                content=f"生成失败: {str(e)}",
                parent=self
            )

    def add_log(self, message, level="info"):
        """添加日志"""
        icons = {
            "info": "📄",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icons.get(level, "📄")
        self.log_text.appendPlainText(f"{icon} {message}")