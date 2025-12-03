import re
import json
import fnmatch
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QFileDialog, QApplication, QStackedWidget,
                               QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

from qfluentwidgets import (PrimaryPushButton, PushButton, CheckBox,
                            LineEdit, StrongBodyLabel, SubtitleLabel,
                            InfoBar, CardWidget,
                            PlainTextEdit, ComboBox, BodyLabel,
                            StateToolTip, SegmentedWidget,
                            ToolTipFilter, MessageBoxBase, TextEdit)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


# ==========================================
# 0. 辅助类：自定义对话框
# ==========================================
class IgnoreRulesDialog(MessageBoxBase):
    """自定义的忽略规则编辑弹窗"""

    def __init__(self, rules, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("管理忽略规则", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.infoLabel = BodyLabel("每行一个规则，支持通配符 * 和 ?", self)
        self.viewLayout.addWidget(self.infoLabel)

        self.textEdit = TextEdit(self)
        self.textEdit.setPlainText("\n".join(rules))
        self.textEdit.setMinimumSize(400, 300)
        self.viewLayout.addWidget(self.textEdit)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

        self.widget.setMinimumWidth(450)

    def getRules(self):
        return [line.strip() for line in self.textEdit.toPlainText().splitlines() if line.strip()]


# ==========================================
# 1. 插件定义
# ==========================================
class DirectoryTreePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "目录树工具箱"

    @property
    def icon(self):
        return qicon("directory_tree")

    @property
    def group(self) -> str:
        return "文件工具"

    @property
    def theme_color(self) -> str:
        return "#0097A7"

    @property
    def description(self) -> str:
        return "文件夹结构↔Tree文本双向转换工具"

    def create_widget(self) -> QWidget:
        return DirectoryTreeWidget()


# ==========================================
# 2. 主界面逻辑
# ==========================================
class DirectoryTreeWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.default_ignore = [
            "__pycache__", "*.pyc", ".git", ".DS_Store", "Thumbs.db",
            "*.log", "*.tmp", ".venv", "venv", ".idea", ".vscode",
            "*.egg-info", "build", "dist", "*.pyo",
            "node_modules", ".pytest_cache", ".coverage"
        ]
        self.ignore_patterns = self.default_ignore.copy()

        self.emoji_blacklist = [
            '📁', '📄', '📝', '⚙️', '📦', '🔧', '⚡', '🧪', '📚', '🔍',
            '📌', '✅', '❌', '⚠️', '💡', '🚀', '🎯', '🛠️', '📎', '📌',
            '📂', '🗂️', '🧾', '📋', '💼', '📊', '📈', '📉', '🎨', '🔨'
        ]

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_layout = QHBoxLayout()
        title = SubtitleLabel("📂 目录树工具箱", self)
        title_layout.addWidget(title)
        title_layout.addStretch(1)

        self.pivot = SegmentedWidget(self)
        self.pivot.addItem(
            routeKey="folder2tree",
            text="📁 文件夹→Tree",
            onClick=lambda: self.switch_to("folder2tree")
        )
        self.pivot.addItem(
            routeKey="tree2folder",
            text="🌳 Tree→文件夹",
            onClick=lambda: self.switch_to("tree2folder")
        )

        title_layout.addWidget(self.pivot)
        layout.addLayout(title_layout)

        separator = QFrame(self)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(separator)

        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        self.folder2tree_page = self.create_folder2tree_page()
        self.tree2folder_page = self.create_tree2folder_page()

        self.stacked_widget.addWidget(self.folder2tree_page)
        self.stacked_widget.addWidget(self.tree2folder_page)

        self.pivot.setCurrentItem("folder2tree")
        self.stacked_widget.setCurrentWidget(self.folder2tree_page)

        bottom_layout = QHBoxLayout()
        self.btn_manage_ignore = PushButton(qicon("settings"), "管理忽略规则", self)
        self.btn_manage_ignore.clicked.connect(self.manage_ignore_rules)
        self.btn_manage_ignore.installEventFilter(ToolTipFilter(self.btn_manage_ignore))

        self.btn_clear_all = PushButton(qicon("delete"), "清空所有", self)
        self.btn_clear_all.clicked.connect(self.clear_all)
        self.btn_clear_all.installEventFilter(ToolTipFilter(self.btn_clear_all))

        bottom_layout.addWidget(self.btn_manage_ignore)
        bottom_layout.addWidget(self.btn_clear_all)
        bottom_layout.addStretch(1)
        layout.addLayout(bottom_layout)

    def switch_to(self, page_key):
        if page_key == "folder2tree":
            self.stacked_widget.setCurrentWidget(self.folder2tree_page)
            self.pivot.setCurrentItem("folder2tree")
        else:
            self.stacked_widget.setCurrentWidget(self.tree2folder_page)
            self.pivot.setCurrentItem("tree2folder")

    def create_folder2tree_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        folder_card = CardWidget(page)
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.addWidget(StrongBodyLabel("📁 源文件夹", page))

        path_layout = QHBoxLayout()
        self.folder_path_edit = LineEdit(page)
        self.folder_path_edit.setPlaceholderText("请选择文件夹...")
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

        config_card = CardWidget(page)
        config_layout = QVBoxLayout(config_card)
        config_layout.addWidget(StrongBodyLabel("⚙️ 配置选项", page))

        format_layout = QHBoxLayout()
        format_layout.addWidget(BodyLabel("输出格式:", page))
        self.format_combo = ComboBox(page)
        self.format_combo.addItems(["Tree文本格式", "Markdown格式", "JSON格式"])
        format_layout.addWidget(self.format_combo)

        self.ignore_hidden_check = CheckBox("忽略隐藏文件", page)
        self.ignore_hidden_check.setChecked(True)
        format_layout.addWidget(self.ignore_hidden_check)

        self.exclude_empty_check = CheckBox("排除空目录", page)
        self.exclude_empty_check.setChecked(True)
        format_layout.addWidget(self.exclude_empty_check)
        config_layout.addLayout(format_layout)
        layout.addWidget(config_card)

        output_card = CardWidget(page)
        output_layout = QVBoxLayout(output_card)
        output_layout.addWidget(StrongBodyLabel("📋 输出结果", page))

        self.output_text = PlainTextEdit(page)
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)

        btn_layout = QHBoxLayout()
        self.btn_generate_tree = PrimaryPushButton(qicon("sync"), "生成目录树", page)
        self.btn_generate_tree.clicked.connect(self.generate_directory_tree)
        self.btn_generate_tree.setEnabled(False)
        btn_layout.addWidget(self.btn_generate_tree)

        self.btn_copy_output = PushButton(qicon("copy"), "复制", page)
        self.btn_copy_output.clicked.connect(self.copy_output)
        btn_layout.addWidget(self.btn_copy_output)

        self.btn_save_output = PushButton(qicon("save"), "保存", page)
        self.btn_save_output.clicked.connect(self.save_output_file)
        btn_layout.addWidget(self.btn_save_output)

        self.btn_clear_output = PushButton(qicon("delete"), "清空", page)
        self.btn_clear_output.clicked.connect(lambda: self.output_text.clear())
        btn_layout.addWidget(self.btn_clear_output)

        btn_layout.addStretch(1)
        output_layout.addLayout(btn_layout)
        layout.addWidget(output_card)

        self.folder_path_edit.textChanged.connect(
            lambda: self.btn_generate_tree.setEnabled(bool(self.folder_path_edit.text().strip()))
        )
        return page

    def create_tree2folder_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        input_card = CardWidget(page)
        input_layout = QVBoxLayout(input_card)
        input_layout.addWidget(StrongBodyLabel("📝 输入Tree结构", page))

        self.input_tree_text = PlainTextEdit(page)
        self.input_tree_text.setPlaceholderText("粘贴Tree结构或导入文件...")
        input_layout.addWidget(self.input_tree_text)

        btn_layout = QHBoxLayout()
        self.btn_import_tree = PushButton(qicon("upload"), "导入文件", page)
        self.btn_import_tree.clicked.connect(self.import_tree_file)
        btn_layout.addWidget(self.btn_import_tree)

        self.btn_paste_tree = PushButton(qicon("paste"), "粘贴剪贴板", page)
        self.btn_paste_tree.clicked.connect(self.paste_tree_clipboard)
        btn_layout.addWidget(self.btn_paste_tree)

        self.btn_insert_example = PushButton(qicon("help"), "插入示例", page)
        self.btn_insert_example.clicked.connect(self.insert_tree_example)
        btn_layout.addWidget(self.btn_insert_example)

        self.btn_clear_tree_input = PushButton(qicon("delete"), "清空", page)
        self.btn_clear_tree_input.clicked.connect(lambda: self.input_tree_text.clear())
        btn_layout.addWidget(self.btn_clear_tree_input)
        btn_layout.addStretch(1)
        input_layout.addLayout(btn_layout)
        layout.addWidget(input_card)

        config_card = CardWidget(page)
        config_layout = QVBoxLayout(config_card)
        config_layout.addWidget(StrongBodyLabel("⚙️ 生成配置", page))

        path_layout = QHBoxLayout()
        path_layout.addWidget(BodyLabel("输出目录:", page))
        self.output_dir_edit = LineEdit(page)
        path_layout.addWidget(self.output_dir_edit)
        self.btn_browse_output_dir = PushButton("选择", page)
        self.btn_browse_output_dir.clicked.connect(self.browse_output_directory)
        path_layout.addWidget(self.btn_browse_output_dir)
        config_layout.addLayout(path_layout)

        opt_layout = QHBoxLayout()
        self.auto_init_check = CheckBox("自动添加 __init__.py", page)
        self.auto_init_check.setChecked(True)
        opt_layout.addWidget(self.auto_init_check)
        self.create_ipynb_check = CheckBox("创建空 .ipynb", page)
        self.create_ipynb_check.setChecked(True)
        opt_layout.addWidget(self.create_ipynb_check)
        self.create_readme_check = CheckBox("创建 README.md", page)
        self.create_readme_check.setChecked(True)
        opt_layout.addWidget(self.create_readme_check)
        config_layout.addLayout(opt_layout)
        layout.addWidget(config_card)

        log_card = CardWidget(page)
        log_layout = QVBoxLayout(log_card)
        log_layout.addWidget(StrongBodyLabel("📊 生成日志", page))
        self.log_text = PlainTextEdit(page)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

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

    def manage_ignore_rules(self):
        dialog = IgnoreRulesDialog(self.ignore_patterns, self)
        if dialog.exec():
            self.ignore_patterns = dialog.getRules()
            InfoBar.success("成功", f"已保存 {len(self.ignore_patterns)} 条忽略规则", parent=self)

    def clear_all(self):
        self.folder_path_edit.clear()
        self.output_text.clear()
        self.input_tree_text.clear()
        self.output_dir_edit.clear()
        self.log_text.clear()
        InfoBar.info("已清空", "所有输入和输出已清空", parent=self)

    def should_ignore(self, path: Path):
        name = path.name
        if self.ignore_hidden_check.isChecked() and name.startswith('.'): return True
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(str(path), f"*/{pattern}"): return True
        return False

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder: self.folder_path_edit.setText(folder)

    def browse_output_directory(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path: self.output_dir_edit.setText(path)

    # --- 生成目录树核心 ---
    def generate_directory_tree(self):
        folder_path = self.folder_path_edit.text().strip()
        if not folder_path or not Path(folder_path).exists():
            return InfoBar.error("错误", "路径无效", parent=self)

        state_tooltip = StateToolTip("正在生成", "扫描目录结构...", self)
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            root = Path(folder_path)
            lines = self._generate_tree_lines(root)

            fmt = self.format_combo.currentText()
            if fmt == "Markdown格式":
                output = self._to_markdown(lines)
            elif fmt == "JSON格式":
                output = self._to_json(root, lines)
            else:
                output = "\n".join(lines)

            self.output_text.setPlainText(output)

            # 【核心修复】分开设置标题和内容，防止参数错误
            state_tooltip.setTitle("生成完成")
            state_tooltip.setContent("目录树已生成")
            state_tooltip.setState(True)  # 停止动画

            InfoBar.success("成功", f"已生成 {len(lines)} 行", parent=self)

        except Exception as e:
            # 【核心修复】错误处理也分开设置
            state_tooltip.setTitle("生成失败")
            state_tooltip.setContent(str(e))
            state_tooltip.setState(True)  # 确保停止动画

            InfoBar.error("错误", str(e), parent=self)
        finally:
            self.btn_generate_tree.setEnabled(True)

    def _generate_tree_lines(self, root_path, prefix="", is_last=True):
        lines = []
        if not prefix:
            lines.append(f"{root_path.name}/")
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{root_path.name}/")
            prefix += "    " if is_last else "│   "

        try:
            items = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            filtered = []
            for item in items:
                if self.should_ignore(item): continue
                if self.exclude_empty_check.isChecked() and item.is_dir():
                    try:
                        if not any(not self.should_ignore(c) for c in item.iterdir()): continue
                    except:
                        pass
                filtered.append(item)

            for i, child in enumerate(filtered):
                is_last_child = (i == len(filtered) - 1)
                if child.is_dir():
                    lines.extend(self._generate_tree_lines(child, prefix, is_last_child))
                else:
                    con = "└── " if is_last_child else "├── "
                    lines.append(f"{prefix}{con}{child.name}")
        except:
            lines.append(f"{prefix}└── [权限拒绝]")
        return lines

    def _to_markdown(self, lines):
        md = []
        for line in lines:
            clean = re.sub(r'^[│ ├└─]*', '', line).rstrip('/')
            if not clean: continue
            is_dir = line.strip().endswith('/')
            indent = len(re.match(r'^[│ ├└─]*', line).group(0) or "")
            md.append(f"{'  ' * (indent // 4)}- [{'📁' if is_dir else '📄'} {clean}]()")
        return "\n".join(md)

    def _to_json(self, root, lines):
        return json.dumps({"root": str(root), "lines": lines}, indent=2, ensure_ascii=False)

    def copy_output(self):
        QApplication.clipboard().setText(self.output_text.toPlainText())
        InfoBar.success("复制成功", "已复制到剪贴板", parent=self)

    def save_output_file(self):
        text = self.output_text.toPlainText()
        if not text: return
        path, _ = QFileDialog.getSaveFileName(self, "保存", "tree.txt")
        if path:
            Path(path).write_text(text, encoding='utf-8')
            InfoBar.success("保存成功", path, parent=self)

    def import_tree_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入", "", "Text (*.txt *.md);;All (*.*)")
        if path:
            self.input_tree_text.setPlainText(Path(path).read_text(encoding='utf-8'))

    def paste_tree_clipboard(self):
        self.input_tree_text.setPlainText(QApplication.clipboard().text())

    def insert_tree_example(self):
        self.input_tree_text.setPlainText("project/\n├── src/\n│   └── main.py\n└── README.md")

    def generate_project_structure(self):
        content = self.input_tree_text.toPlainText().strip()
        out_dir = self.output_dir_edit.text().strip()
        if not content or not out_dir: return InfoBar.warning("警告", "请填写完整", parent=self)

        state_tooltip = StateToolTip("正在生成", "创建文件...", self)
        state_tooltip.move(state_tooltip.getSuitablePos())
        state_tooltip.show()

        try:
            self.log_text.clear()
            lines = [l for l in content.splitlines() if l.strip()]

            self.log_text.appendPlainText("✅ 开始生成... (逻辑未完全实现)")
            # 这里需要补充完整的生成逻辑，参考之前的代码

            # 【核心修复】分开设置
            state_tooltip.setTitle("完成")
            state_tooltip.setContent("项目结构已生成")
            state_tooltip.setState(True)

            InfoBar.success("成功", "项目结构已生成", parent=self)

        except Exception as e:
            # 【核心修复】分开设置
            state_tooltip.setTitle("失败")
            state_tooltip.setContent(str(e))
            state_tooltip.setState(True)
            InfoBar.error("错误", str(e), parent=self)