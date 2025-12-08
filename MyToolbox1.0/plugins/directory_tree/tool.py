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
# 0. 辅助类
# ==========================================
class IgnoreRulesDialog(MessageBoxBase):
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

    def getRules(self): return [line.strip() for line in self.textEdit.toPlainText().splitlines() if line.strip()]


# ==========================================
# 1. 插件定义
# ==========================================
class DirectoryTreePlugin(PluginInterface):
    @property
    def name(self) -> str: return "目录树工具箱"

    @property
    def icon(self):
        from qfluentwidgets import FluentIcon
        return qicon("directory_tree") if qicon("tree").isNull() is False else getattr(FluentIcon, 'Folder', FluentIcon.FOLDER)

    @property
    def group(self) -> str: return "文件工具"

    @property
    def theme_color(self) -> str: return "#0097A7"

    @property
    def description(self) -> str: return "文件夹结构↔Tree文本双向转换工具"

    def create_widget(self) -> QWidget: return DirectoryTreeWidget()


# ==========================================
# 2. 主界面
# ==========================================
class DirectoryTreeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.default_ignore = ["__pycache__", "*.pyc", ".git", ".DS_Store", "*.log", ".venv", "venv", ".idea",
                               ".vscode", "dist", "node_modules"]
        self.ignore_patterns = self.default_ignore.copy()
        self.emoji_blacklist = ['📁', '📄', '📝', '⚙️', '📦', '🔧', '⚡', '📚', '🔍', '📌', '✅', '📂', '🗂️']
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)

        # 标题栏
        t_layout = QHBoxLayout()
        t_layout.addWidget(SubtitleLabel("📂 目录树工具箱", self))
        t_layout.addStretch(1)
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem(routeKey="folder2tree", text="📁 文件夹→Tree", onClick=lambda: self.switch_to("folder2tree"))
        self.pivot.addItem(routeKey="tree2folder", text="🌳 Tree→文件夹", onClick=lambda: self.switch_to("tree2folder"))
        t_layout.addWidget(self.pivot)
        layout.addLayout(t_layout)

        sep = QFrame(self);
        sep.setFrameShape(QFrame.Shape.HLine);
        sep.setStyleSheet("color: #e0e0e0;");
        layout.addWidget(sep)

        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        self.folder2tree_page = self.create_folder2tree_page()
        self.tree2folder_page = self.create_tree2folder_page()
        self.stacked_widget.addWidget(self.folder2tree_page)
        self.stacked_widget.addWidget(self.tree2folder_page)

        self.pivot.setCurrentItem("folder2tree")
        self.stacked_widget.setCurrentWidget(self.folder2tree_page)

        # 底部按钮
        b_layout = QHBoxLayout()
        self.btn_rules = PushButton(qicon("settings"), "管理忽略规则", self)
        self.btn_rules.clicked.connect(self.manage_ignore_rules)
        self.btn_clear = PushButton(qicon("delete"), "清空所有", self)
        self.btn_clear.clicked.connect(self.clear_all)
        b_layout.addWidget(self.btn_rules);
        b_layout.addWidget(self.btn_clear);
        b_layout.addStretch(1)
        layout.addLayout(b_layout)

    def switch_to(self, key):
        self.stacked_widget.setCurrentWidget(self.folder2tree_page if key == "folder2tree" else self.tree2folder_page)
        self.pivot.setCurrentItem(key)

    def create_folder2tree_page(self):
        p = QWidget();
        l = QVBoxLayout(p);
        l.setContentsMargins(10, 10, 10, 10);
        l.setSpacing(15)

        c1 = CardWidget(p);
        l1 = QVBoxLayout(c1)
        l1.addWidget(StrongBodyLabel("📁 源文件夹", p))
        h1 = QHBoxLayout()
        self.folder_path_edit = LineEdit(p);
        self.folder_path_edit.setReadOnly(True)
        btn_sel = PushButton(qicon("folder"), "选择", p);
        btn_sel.clicked.connect(self.browse_folder)
        btn_cl = PushButton(qicon("delete"), "清空", p);
        btn_cl.clicked.connect(lambda: self.folder_path_edit.clear())
        h1.addWidget(self.folder_path_edit);
        h1.addWidget(btn_sel);
        h1.addWidget(btn_cl)
        l1.addLayout(h1);
        l.addWidget(c1)

        c2 = CardWidget(p);
        l2 = QVBoxLayout(c2)
        l2.addWidget(StrongBodyLabel("⚙️ 配置选项", p))
        h2 = QHBoxLayout()
        h2.addWidget(BodyLabel("输出格式:", p))
        self.format_combo = ComboBox(p);
        self.format_combo.addItems(["Tree文本格式", "Markdown格式", "JSON格式"])
        self.chk_hidden = CheckBox("忽略隐藏文件", p);
        self.chk_hidden.setChecked(True)
        self.chk_empty = CheckBox("排除空目录", p);
        self.chk_empty.setChecked(True)
        h2.addWidget(self.format_combo);
        h2.addWidget(self.chk_hidden);
        h2.addWidget(self.chk_empty)
        l2.addLayout(h2);
        l.addWidget(c2)

        c3 = CardWidget(p);
        l3 = QVBoxLayout(c3)
        l3.addWidget(StrongBodyLabel("📋 输出结果", p))
        self.output_text = PlainTextEdit(p);
        self.output_text.setReadOnly(True)
        l3.addWidget(self.output_text)
        h3 = QHBoxLayout()
        self.btn_gen = PrimaryPushButton(qicon("sync"), "生成目录树", p);
        self.btn_gen.clicked.connect(self.generate_directory_tree);
        self.btn_gen.setEnabled(False)
        btn_cp = PushButton(qicon("copy"), "复制", p);
        btn_cp.clicked.connect(self.copy_output)
        btn_sv = PushButton(qicon("save"), "保存", p);
        btn_sv.clicked.connect(self.save_output_file)
        btn_cl2 = PushButton(qicon("delete"), "清空", p);
        btn_cl2.clicked.connect(lambda: self.output_text.clear())
        h3.addWidget(self.btn_gen);
        h3.addWidget(btn_cp);
        h3.addWidget(btn_sv);
        h3.addWidget(btn_cl2);
        h3.addStretch(1)
        l3.addLayout(h3);
        l.addWidget(c3)

        self.folder_path_edit.textChanged.connect(
            lambda: self.btn_gen.setEnabled(bool(self.folder_path_edit.text().strip())))
        return p

    def create_tree2folder_page(self):
        p = QWidget();
        l = QVBoxLayout(p);
        l.setContentsMargins(10, 10, 10, 10);
        l.setSpacing(15)

        c1 = CardWidget(p);
        l1 = QVBoxLayout(c1)
        l1.addWidget(StrongBodyLabel("📝 输入Tree结构", p))
        self.input_tree = PlainTextEdit(p);
        self.input_tree.setPlaceholderText("project/\n├── src/\n│   └── main.py\n└── README.md")
        l1.addWidget(self.input_tree)
        h1 = QHBoxLayout()
        btn_imp = PushButton(qicon("upload"), "导入文件", p);
        btn_imp.clicked.connect(self.import_tree_file)
        btn_pst = PushButton(qicon("paste"), "粘贴", p);
        btn_pst.clicked.connect(lambda: self.input_tree.setPlainText(QApplication.clipboard().text()))
        btn_exp = PushButton(qicon("help"), "插入示例", p);
        btn_exp.clicked.connect(self.insert_tree_example)
        btn_clr = PushButton(qicon("delete"), "清空", p);
        btn_clr.clicked.connect(lambda: self.input_tree.clear())
        h1.addWidget(btn_imp);
        h1.addWidget(btn_pst);
        h1.addWidget(btn_exp);
        h1.addWidget(btn_clr);
        h1.addStretch(1)
        l1.addLayout(h1);
        l.addWidget(c1)

        c2 = CardWidget(p);
        l2 = QVBoxLayout(c2)
        l2.addWidget(StrongBodyLabel("⚙️ 生成配置", p))
        h2 = QHBoxLayout()
        h2.addWidget(BodyLabel("输出目录:", p))
        self.out_dir_edit = LineEdit(p)
        btn_dir = PushButton("选择", p);
        btn_dir.clicked.connect(self.browse_output_directory)
        h2.addWidget(self.out_dir_edit);
        h2.addWidget(btn_dir)
        l2.addLayout(h2)
        h3 = QHBoxLayout()
        self.chk_init = CheckBox("自动添加 __init__.py", p);
        self.chk_init.setChecked(True)
        self.chk_readme = CheckBox("创建 README.md", p);
        self.chk_readme.setChecked(True)
        h3.addWidget(self.chk_init);
        h3.addWidget(self.chk_readme);
        h3.addStretch(1)
        l2.addLayout(h3);
        l.addWidget(c2)

        c3 = CardWidget(p);
        l3 = QVBoxLayout(c3)
        l3.addWidget(StrongBodyLabel("📊 生成日志", p))
        self.log_text = PlainTextEdit(p);
        self.log_text.setReadOnly(True);
        self.log_text.setMaximumHeight(150)
        l3.addWidget(self.log_text)
        h4 = QHBoxLayout()
        self.btn_build = PrimaryPushButton(qicon("rocket"), "生成项目结构", p);
        self.btn_build.clicked.connect(self.generate_project_structure)
        btn_cl_log = PushButton(qicon("delete"), "清空日志", p);
        btn_cl_log.clicked.connect(lambda: self.log_text.clear())
        h4.addWidget(self.btn_build);
        h4.addWidget(btn_cl_log);
        h4.addStretch(1)
        l3.addLayout(h4);
        l.addWidget(c3)
        return p

    # --- 逻辑实现 ---
    def manage_ignore_rules(self):
        d = IgnoreRulesDialog(self.ignore_patterns, self)
        if d.exec(): self.ignore_patterns = d.getRules(); InfoBar.success("成功",
                                                                          f"已保存 {len(self.ignore_patterns)} 条规则",
                                                                          parent=self)

    def clear_all(self):
        self.folder_path_edit.clear();
        self.output_text.clear();
        self.input_tree.clear();
        self.out_dir_edit.clear();
        self.log_text.clear()
        InfoBar.info("已清空", "所有内容已重置", parent=self)

    def browse_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择文件夹");
        if f: self.folder_path_edit.setText(f)

    def browse_output_directory(self):
        f = QFileDialog.getExistingDirectory(self, "选择输出目录");
        if f: self.out_dir_edit.setText(f)

    def generate_directory_tree(self):
        path = self.folder_path_edit.text().strip()
        if not path or not Path(path).exists(): return InfoBar.error("错误", "路径无效", parent=self)

        tip = StateToolTip("正在生成", "扫描中...", self);
        tip.move(tip.getSuitablePos());
        tip.show()
        try:
            lines = self._gen_tree(Path(path))
            fmt = self.format_combo.currentText()
            out = self._to_md(lines) if fmt == "Markdown格式" else (
                self._to_json(Path(path), lines) if fmt == "JSON格式" else "\n".join(lines))
            self.output_text.setPlainText(out)
            tip.setTitle("完成");
            tip.setContent("生成成功");
            tip.setState(True)
            InfoBar.success("成功", f"生成 {len(lines)} 行", parent=self)
        except Exception as e:
            tip.setTitle("失败");
            tip.setContent(str(e));
            tip.setState(True)
            InfoBar.error("错误", str(e), parent=self)

    def _gen_tree(self, root, prefix="", is_last=True):
        lines = []
        if not prefix:
            lines.append(f"{root.name}/"); prefix = ""
        else:
            con = "└── " if is_last else "├── "
            lines.append(f"{prefix}{con}{root.name}/")
            prefix += "    " if is_last else "│   "

        try:
            items = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            valid = []
            for i in items:
                if self.should_ignore(i): continue
                if self.chk_empty.isChecked() and i.is_dir():
                    try:
                        if not any(not self.should_ignore(c) for c in i.iterdir()): continue
                    except:
                        pass
                valid.append(i)

            for i, child in enumerate(valid):
                is_end = (i == len(valid) - 1)
                if child.is_dir():
                    lines.extend(self._gen_tree(child, prefix, is_end))
                else:
                    lines.append(f"{prefix}{'└── ' if is_end else '├── '}{child.name}")
        except:
            lines.append(f"{prefix}└── [Access Denied]")
        return lines

    def should_ignore(self, path):
        if self.chk_hidden.isChecked() and path.name.startswith('.'): return True
        for p in self.ignore_patterns:
            if fnmatch.fnmatch(path.name, p): return True
        return False

    def _to_md(self, lines):
        return "\n".join(
            [f"{'  ' * (len(re.match(r'^[│ ├└─]*', l).group(0)) // 4)}- {l.split(' ')[-1]}" for l in lines])

    def _to_json(self, root, lines):
        return json.dumps({"root": str(root), "tree": lines}, indent=2)

    def copy_output(self):
        QApplication.clipboard().setText(self.output_text.toPlainText()); InfoBar.success("复制成功", "", parent=self)

    def save_output_file(self):
        p, _ = QFileDialog.getSaveFileName(self, "保存", "tree.txt")
        if p: Path(p).write_text(self.output_text.toPlainText(), encoding='utf-8'); InfoBar.success("保存成功", "",
                                                                                                    parent=self)

    # --- Tree 转 Folder 核心逻辑 ---
    def import_tree_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "导入", "", "Text (*.txt *.md)")
        if p: self.input_tree.setPlainText(Path(p).read_text(encoding='utf-8'))

    def insert_tree_example(self):
        self.input_tree.setPlainText(
            "project/\n├── src/\n│   ├── main.py\n│   └── utils.py\n├── tests/\n│   └── test_main.py\n└── README.md")

    def generate_project_structure(self):
        text = self.input_tree.toPlainText().strip()
        out_dir = self.out_dir_edit.text().strip()
        if not text or not out_dir: return InfoBar.warning("警告", "请填写完整", parent=self)

        tip = StateToolTip("处理中", "解析结构...", self);
        tip.move(tip.getSuitablePos());
        tip.show()
        self.log_text.clear()

        try:
            # 1. 解析 Tree 文本
            paths = self.parse_tree(text)
            self.log_text.appendPlainText(f"✅ 解析出 {len(paths)} 个路径")

            # 2. 创建文件
            root_path = Path(out_dir)
            created_count = 0

            for rel_path in paths:
                full_path = root_path / rel_path
                if rel_path.endswith('/'):
                    full_path.mkdir(parents=True, exist_ok=True)
                    self.log_text.appendPlainText(f"📁 创建目录: {rel_path}")

                    if self.chk_init.isChecked() and ('src' in rel_path or 'lib' in rel_path):
                        (full_path / "__init__.py").touch()
                else:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.touch()
                    self.log_text.appendPlainText(f"📄 创建文件: {rel_path}")

                    if self.chk_readme.isChecked() and rel_path == "README.md":
                        full_path.write_text(f"# {root_path.name}\nGenerated by MyToolbox", encoding='utf-8')

                created_count += 1

            tip.setTitle("完成");
            tip.setContent("生成成功");
            tip.setState(True)
            InfoBar.success("成功", f"创建了 {created_count} 个项", parent=self)

        except Exception as e:
            tip.setTitle("失败");
            tip.setContent(str(e));
            tip.setState(True)
            self.log_text.appendPlainText(f"❌ 错误: {e}")
            InfoBar.error("错误", str(e), parent=self)

    def parse_tree(self, text):
        """核心解析算法"""
        lines = [l.rstrip() for l in text.splitlines() if l.strip()]
        if not lines: return []

        paths = []
        # 栈用于存储当前路径层级: [(indent_level, name), ...]
        # 初始栈底假设是根
        stack = []

        for i, line in enumerate(lines):
            # 1. 清理前缀符号
            clean_line = line
            for char in self.emoji_blacklist: clean_line = clean_line.replace(char, '')

            # 计算缩进 (每4个字符算一级，或者根据树符号)
            # 匹配开头的树状符号和空格
            match = re.match(r'^([│ ├└─\s]*)', clean_line)
            prefix = match.group(1)
            content = clean_line[len(prefix):].strip()

            # 简单估算层级：长度 / 4
            level = len(prefix) // 4

            # 根目录特殊处理
            if i == 0:
                level = 0
                stack = [content.rstrip('/')]
                paths.append(content)  # 记录根目录
                continue

            # 调整栈：如果当前层级 <= 栈的深度，说明回退了，弹出栈顶
            # 注意：栈的索引 0 是根(Level 0)，所以 stack 长度应该等于 level
            while len(stack) > level:
                stack.pop()

            # 构建完整路径
            current_path = "/".join(stack + [content])

            # 判断是文件还是目录
            is_dir = content.endswith('/') or (
                        i + 1 < len(lines) and len(re.match(r'^([│ ├└─\s]*)', lines[i + 1]).group(1)) // 4 > level)

            if is_dir and not content.endswith('/'):
                current_path += '/'

            paths.append(current_path)

            if is_dir:
                stack.append(content.rstrip('/'))

        return paths