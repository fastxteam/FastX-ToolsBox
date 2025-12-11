import os
import re
import markdown
import textwrap
from string import Template
from pathlib import Path
from PySide6.QtPrintSupport import QPrinter

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QFileDialog, QFrame, QTextBrowser, QLabel,
                               QTreeWidget, QTreeWidgetItem, QInputDialog)
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
                           QShortcut, QKeySequence, QTextCursor)
from PySide6.QtCore import Qt, QUrl, QTimer

from qfluentwidgets import (PlainTextEdit, FluentIcon, TransparentToolButton,
                            ToolTipFilter, ToolTipPosition, isDarkTheme,
                            InfoBar, CardWidget)
from core.plugin_interface import PluginInterface
from plugins.markdown_editor.components.code_editor import CodeEditor

# 尝试导入 matplotlib
try:
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

HAS_WEBENGINE = False

# HTML 模板 (保持不变)
HTML_TEMPLATE = Template(textwrap.dedent("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 14pt; color: $text_col; background-color: $bg_col; margin: 30px; line-height: 1.6; }
        a { color: $link_col; text-decoration: none; border-bottom: 1px dashed $link_col; }
        h1 { border-bottom: 2px solid $text_col; padding-bottom: 10px; margin-top: 30px; font-size: 2em; }
        h2 { border-bottom: 1px solid $text_col; padding-bottom: 5px; margin-top: 25px; font-size: 1.5em; }
        h3 { margin-top: 20px; font-size: 1.2em; font-weight: bold; }
        blockquote { border-left: 5px solid $quote_col; padding: 10px 20px; background-color: $code_bg; margin: 15px 0; color: $quote_col; border-radius: 4px; }
        pre { background-color: $code_bg; padding: 15px; border-radius: 8px; overflow-x: auto; border: 1px solid rgba(128,128,128,0.1); font-family: "Consolas", "Monaco", monospace; }
        code { font-family: "Consolas", "Monaco", monospace; background-color: rgba(128,128,128,0.1); padding: 2px 5px; border-radius: 4px; }
        pre code { background-color: transparent; padding: 0; border-radius: 0; }
        img { max-width: 100%; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin: 10px 0; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; border-radius: 8px; overflow: hidden; }
        th { background-color: $code_bg; font-weight: bold; }
        th, td { border: 1px solid rgba(128,128,128,0.2); padding: 10px; text-align: left; }
    </style>
</head>
<body>
    $content
</body>
</html>
"""))


class MdHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        if isDarkTheme():
            h_col = "#569cd6";
            code_col = "#ce9178";
            link_col = "#9cdcfe";
            img_col = "#d16969"
        else:
            h_col = "#005cc5";
            code_col = "#e91e63";
            link_col = "#005cc5";
            img_col = "#d32f2f"
        self.rules = [
            (re.compile(r"^#+.*"), self.fmt(h_col, True)),
            (re.compile(r"\*\*.*?\*\*"), self.fmt(code_col, True)),
            (re.compile(r"`.*?`"), self.fmt(QColor("#6a9955"))),
            (re.compile(r"!\[.*?\]\(.*?\)"), self.fmt(img_col)),
            (re.compile(r"\[.*?\]\(.*?\)"), self.fmt(link_col, False, True))
        ]

    def fmt(self, color, bold=False, underline=False):
        f = QTextCharFormat();
        f.setForeground(QColor(color) if isinstance(color, str) else color)
        if bold: f.setFontWeight(QFont.Bold)
        if underline: f.setFontUnderline(True)
        return f

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text): self.setFormat(m.start(), m.end() - m.start(), fmt)


class MarkdownPlugin(PluginInterface):
    @property
    def name(self) -> str: return "Markdown 笔记"

    @property
    def icon(self): return FluentIcon.DOCUMENT

    @property
    def group(self) -> str: return "办公工具"

    @property
    def theme_color(self) -> str: return "#0078D4"

    @property
    def description(self) -> str: return "支持大纲、公式、图片粘贴的专业编辑器"

    def create_widget(self) -> QWidget: return MarkdownWidget()


class MarkdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.setAcceptDrops(True)

        if isDarkTheme():
            self.bg_col = "#1e1e1e";
            self.fg_col = "#d4d4d4";
            self.border_col = "#333333";
            self.tool_bg = "#252526";
            self.tree_bg = "#181818"
        else:
            self.bg_col = "#ffffff";
            self.fg_col = "#333333";
            self.border_col = "#e5e5e5";
            self.tool_bg = "#f3f3f3";
            self.tree_bg = "#f8f8f8"

        self.setStyleSheet(f"background-color: {self.bg_col}; color: {self.fg_col};")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.init_toolbar()

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(
            f"QSplitter {{ background-color: {self.bg_col}; border: none; }} QSplitter::handle {{ background-color: {self.border_col}; }}")
        self.main_layout.addWidget(self.splitter)

        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.setIndentation(15)
        self.outline.itemClicked.connect(self.on_outline_clicked)
        self.outline.setStyleSheet(
            f"QTreeWidget {{ background-color: {self.tree_bg}; color: {self.fg_col}; border: none; border-right: 1px solid {self.border_col}; outline: none; }} QTreeWidget::item:hover {{ background: rgba(128,128,128,0.1); }} QTreeWidget::item:selected {{ background: rgba(128,128,128,0.2); color: {self.fg_col}; }}")
        self.splitter.addWidget(self.outline)

        self.editor = CodeEditor(self)
        font = QFont("Consolas", 11);
        font.setStyleHint(QFont.Monospace);
        self.editor.setFont(font)
        self.editor.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {self.bg_col}; color: {self.fg_col}; border: none; padding: 10px; outline: none; }}")
        self.highlighter = MdHighlighter(self.editor.document())
        self.splitter.addWidget(self.editor)

        self.preview = QTextBrowser(self)
        self.preview.setOpenExternalLinks(True)
        self.preview.setStyleSheet(
            f"QTextBrowser {{ background-color: {self.bg_col}; border: none; padding: 10px; border-left: 1px solid {self.border_col}; }}")
        self.splitter.addWidget(self.preview)

        self.splitter.setSizes([150, 425, 425])

        self.init_statusbar()

        self.render_timer = QTimer();
        self.render_timer.setSingleShot(True);
        self.render_timer.interval = 500;
        self.render_timer.timeout.connect(self.render_markdown)
        self.parse_timer = QTimer();
        self.parse_timer.setSingleShot(True);
        self.parse_timer.interval = 800;
        self.parse_timer.timeout.connect(self.parse_outline)

        self.editor.textChanged.connect(lambda: (self.render_timer.start(), self.parse_timer.start()))
        self.editor.cursorPositionChanged.connect(self.update_status_bar)
        if hasattr(self.editor, 'verticalScrollBar'): self.editor.verticalScrollBar().valueChanged.connect(
            self.sync_scroll)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_file)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+B"), self).activated.connect(lambda: self.wrap_text("**"))
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(lambda: self.wrap_text("*"))
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(lambda: self.wrap_text("[", "](url)"))

        self.editor.setPlainText("# 欢迎使用\n\n- 尝试 `Ctrl+B` 加粗\n- 尝试插入表格")
        self.render_markdown()
        self.parse_outline()

    def init_toolbar(self):
        self.toolbar = QWidget();
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet(f"background-color: {self.tool_bg}; border-bottom: 1px solid {self.border_col};")
        layout = QHBoxLayout(self.toolbar);
        layout.setContentsMargins(10, 0, 10, 0);
        layout.setSpacing(5)

        def add(icon, tip, slot):
            btn = TransparentToolButton(icon, self)
            btn.setToolTip(tip)
            # 使用 connect 而不是 lambda，除非 slot 需要参数
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        add(FluentIcon.FOLDER, "打开", self.open_file)
        add(FluentIcon.SAVE, "保存", self.save_file)
        add(getattr(FluentIcon, 'DOWNLOAD', FluentIcon.SHARE), "导出", self.export_file)

        line = QFrame();
        line.setFrameShape(QFrame.VLine);
        line.setFixedHeight(20);
        line.setStyleSheet(f"color: {self.border_col};");
        layout.addWidget(line)

        # 【核心修复】绑定 wrap_text
        add(getattr(FluentIcon, 'BOLD', FluentIcon.EDIT), "粗体 (Ctrl+B)", lambda: self.wrap_text("**"))
        add(getattr(FluentIcon, 'ITALIC', FluentIcon.DOCUMENT), "斜体 (Ctrl+I)", lambda: self.wrap_text("*"))
        add(FluentIcon.CODE, "代码块", lambda: self.wrap_text("\n```\n", "\n```\n"))
        add(getattr(FluentIcon, 'LINK', FluentIcon.SEARCH), "链接 (Ctrl+K)", lambda: self.wrap_text("[", "](url)"))

        # 表格
        add(getattr(FluentIcon, 'TILES', FluentIcon.MENU), "插入表格", self.insert_table)

        # 标题和图片
        add(FluentIcon.MENU, "标题", lambda: self.insert_line_prefix("# "))

        btn_img = TransparentToolButton(getattr(FluentIcon, 'PHOTO', getattr(FluentIcon, 'CAMERA', FluentIcon.FOLDER)),
                                        self)
        btn_img.setToolTip("插入图片语法")
        btn_img.clicked.connect(lambda: self.wrap_text("![Desc](", ")"))
        layout.addWidget(btn_img)

        layout.addStretch(1)
        self.main_layout.addWidget(self.toolbar)

    def init_statusbar(self):
        from PySide6.QtWidgets import QLabel
        self.status_bar = QWidget();
        self.status_bar.setFixedHeight(22)
        self.status_bar.setStyleSheet("background-color: #007acc; color: white;")
        layout = QHBoxLayout(self.status_bar);
        layout.setContentsMargins(10, 0, 10, 0)
        self.status_label = QLabel("Ln 1, Col 1");
        self.status_label.setStyleSheet("color: white; font-size: 11px; background: transparent; border: none;")
        self.word_count_label = QLabel("0 字");
        self.word_count_label.setStyleSheet("color: white; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(self.status_label);
        layout.addWidget(self.word_count_label);
        layout.addStretch(1);
        self.main_layout.addWidget(self.status_bar)

    # 【核心修复】智能包裹与Toggle
    def wrap_text(self, prefix, suffix=""):
        if not suffix: suffix = prefix
        cursor = self.editor.textCursor()

        if cursor.hasSelection():
            text = cursor.selectedText()
            # 简单的 Toggle 检查 (仅检查选中内容本身)
            if text.startswith(prefix) and text.endswith(suffix) and len(text) >= len(prefix) + len(suffix):
                # 取消
                new_text = text[len(prefix): -len(suffix)]
                cursor.insertText(new_text)
                # 恢复选中
                pos = cursor.position()
                cursor.setPosition(pos - len(new_text), QTextCursor.KeepAnchor)
                self.editor.setTextCursor(cursor)
            else:
                # 应用
                cursor.insertText(f"{prefix}{text}{suffix}")
                pos = cursor.position()
                cursor.setPosition(pos - len(suffix), QTextCursor.KeepAnchor)
                cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(text))
                self.editor.setTextCursor(cursor)
        else:
            # 插入
            cursor.insertText(f"{prefix}{suffix}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
            self.editor.setTextCursor(cursor)

        self.editor.setFocus()

    def insert_table(self):
        cols, ok = QInputDialog.getInt(self, "插入表格", "列数:", 3, 1, 10)
        if not ok: return
        header = "| " + " | ".join([f"Header {i + 1}" for i in range(cols)]) + " |"
        sep = "| " + " | ".join(["---"] * cols) + " |"
        row = "| " + " | ".join(["Content"] * cols) + " |"
        self.editor.insertPlainText(f"\n{header}\n{sep}\n{row}\n{row}\n")
        self.editor.setFocus()

    def insert_line_prefix(self, p):
        c = self.editor.textCursor();
        c.movePosition(QTextCursor.StartOfLine);
        c.insertText(p);
        self.editor.setFocus()

    def update_status_bar(self):
        c = self.editor.textCursor()
        self.status_label.setText(f"Ln {c.blockNumber() + 1}, Col {c.columnNumber() + 1}")
        self.word_count_label.setText(f"{len(self.editor.toPlainText())} 字")

    def parse_outline(self):
        self.outline.clear();
        doc = self.editor.document();
        stack = [(0, self.outline.invisibleRootItem())]
        for i in range(doc.blockCount()):
            text = doc.findBlockByNumber(i).text().strip();
            match = re.match(r'^(#+)\s+(.*)', text)
            if match:
                level = len(match.group(1));
                title = match.group(2);
                item = QTreeWidgetItem([title]);
                item.setData(0, Qt.UserRole, i)
                while stack and stack[-1][0] >= level: stack.pop()
                stack[-1][1].addChild(item);
                item.setExpanded(True);
                stack.append((level, item))

    def on_outline_clicked(self, item, col):
        line = item.data(0, Qt.UserRole); self.editor.setTextCursor(QTextCursor(
            self.editor.document().findBlockByNumber(line))) if line is not None else None; self.editor.setFocus()

    def sync_scroll(self):
        if hasattr(self.preview, 'verticalScrollBar'):
            v = self.editor.verticalScrollBar().value();
            m = self.editor.verticalScrollBar().maximum()
            if m > 0: self.preview.verticalScrollBar().setValue(int(v / m * self.preview.verticalScrollBar().maximum()))

    def open_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open", "", "MD (*.md)"); self.load_file_from_path(p) if p else None

    def load_file_from_path(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.current_file = path;
            self.editor.set_base_path(path);
            self.render_markdown();
            InfoBar.success("Open", os.path.basename(path), parent=self)
        except Exception as e:
            InfoBar.error("Fail", str(e), parent=self)

    def save_file(self):
        if not self.current_file: p, _ = QFileDialog.getSaveFileName(self, "Save", "note.md",
                                                                     "MD (*.md)"); self.current_file = p; self.editor.set_base_path(
            p) if p else None
        if self.current_file:
            with open(self.current_file, 'w', encoding='utf-8') as f: f.write(
                self.editor.toPlainText()); InfoBar.success("Saved", str(self.current_file), parent=self)

    def export_file(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export", "out.html", "HTML (*.html)")
        if not p: return
        try:
            # 重新生成 HTML
            html_content = self._generate_full_html()
            with open(p, 'w', encoding='utf-8') as f:
                f.write(html_content)
            InfoBar.success("Exported HTML", str(p), parent=self)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self)

    def _generate_full_html(self):
        raw_text = self.editor.toPlainText()
        # 公式渲染
        if HAS_MATPLOTLIB:
            def latex_sub(m):
                path = self.render_latex_to_image(m.group(1))
                return f"![eq]({path})" if path else m.group(0)

            raw_text = re.sub(r'\$\$([\s\S]*?)\$\$', latex_sub, raw_text)
            raw_text = re.sub(r'(?<!\\)\$([^\$]+?)\$', latex_sub, raw_text)

        try:
            html = markdown.markdown(raw_text, extensions=['extra', 'codehilite', 'tables'])
        except:
            html = ""

        context = {
            'text_col': "#d4d4d4" if isDarkTheme() else "#333333",
            'bg_col': "#1e1e1e" if isDarkTheme() else "#ffffff",
            'link_col': "#4cc2ff" if isDarkTheme() else "#0969da",
            'code_bg': "#2d2d2d" if isDarkTheme() else "#f6f8fa",
            'quote_col': "#a0a0a0" if isDarkTheme() else "#6a737d",
            'mermaid_theme': "dark" if isDarkTheme() else "default",
            'content': html
        }
        return HTML_TEMPLATE.safe_substitute(context)

    def render_latex_to_image(self, latex):
        if not HAS_MATPLOTLIB: return None
        try:
            h = hashlib.md5(latex.encode()).hexdigest()
            filename = f"eq_{h}.svg"
            if self.current_file:
                base_dir = os.path.dirname(self.current_file)
            else:
                base_dir = os.path.abspath("temp_assets")

            assets_dir = os.path.join(base_dir, "assets")
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir, exist_ok=True)

            filepath = os.path.join(assets_dir, filename)

            if not os.path.exists(filepath):
                fig = plt.figure(figsize=(0.1, 0.1))
                text = f"${latex}$"
                color = "#d4d4d4" if isDarkTheme() else "#333333"
                plt.text(0, 0, text, fontsize=14, color=color)
                plt.axis('off')
                plt.savefig(filepath, format='svg', bbox_inches='tight', transparent=True, pad_inches=0.05)
                plt.close(fig)
            return f"assets/{filename}"
        except:
            return None

    def render_markdown(self):
        # 预览使用透明背景
        raw_text = self.editor.toPlainText()
        # ... (Latex 处理同上) ...
        # 为预览生成的 HTML，bg_col 设为 transparent
        try:
            html = markdown.markdown(raw_text, extensions=['extra', 'codehilite', 'tables'])
        except:
            html = ""
        context = {
            'text_col': self.fg_col, 'bg_col': 'transparent',
            'link_col': "#4cc2ff" if isDarkTheme() else "#0969da",
            'code_bg': "#2d2d2d" if isDarkTheme() else "#f6f8fa",
            'quote_col': "#a0a0a0" if isDarkTheme() else "#6a737d",
            'mermaid_theme': "dark" if isDarkTheme() else "default",
            'content': html
        }
        final_html = HTML_TEMPLATE.safe_substitute(context)

        if self.current_file:
            base_dir = os.path.dirname(self.current_file)
        else:
            base_dir = os.path.abspath("temp_assets"); os.makedirs(base_dir, exist_ok=True)
        base_dir_str = base_dir.replace("\\", "/") + "/"

        def img_replacer(m):
            rel = m.group(1)
            if rel.startswith("http") or rel.startswith("file:"): return m.group(0)
            return f'src="file:///{base_dir_str}{rel}"'

        html_fixed = re.sub(r'src="([^"]+)"', img_replacer, final_html)

        self.preview.setSearchPaths([base_dir_str])
        self.preview.setHtml(html_fixed)

    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        u = e.mimeData().urls()
        if u:
            p = u[0].toLocalFile()
            if p.lower().endswith(('.md', '.txt')): self.load_file_from_path(p)