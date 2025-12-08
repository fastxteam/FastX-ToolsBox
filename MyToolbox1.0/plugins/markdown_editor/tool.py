import os
import re
import markdown
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                               QFileDialog, QFrame, QTextBrowser, QLabel)
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
                           QShortcut, QKeySequence)
from PySide6.QtCore import Qt, QUrl, QTimer

from qfluentwidgets import (FluentIcon, TransparentToolButton, ToolTipFilter,
                            ToolTipPosition, isDarkTheme, InfoBar)
from core.plugin_interface import PluginInterface
from plugins.markdown_editor.components.code_editor import CodeEditor


class MarkdownPlugin(PluginInterface):
    @property
    def name(self): return "Markdown 笔记"

    @property
    def icon(self): return FluentIcon.DOCUMENT

    @property
    def group(self): return "办公工具"

    @property
    def theme_color(self): return "#0078D4"

    @property
    def description(self): return "极简风格 Markdown 编辑器"

    def create_widget(self): return MarkdownWidget()


class MdHighlighter(QSyntaxHighlighter):
    def __init__(self, doc):
        super().__init__(doc)
        self.rules = []
        # VS Code Dark 风格
        if isDarkTheme():
            h_col = "#569cd6";
            code_col = "#ce9178";
            link_col = "#9cdcfe"
        else:
            h_col = "#0000ff";
            code_col = "#a31515";
            link_col = "#0000ff"

        self.rules = [
            (r"^#+.*", h_col, True),
            (r"\*\*.*?\*\*", code_col, True),
            (r"`.*?`", "#6a9955", False),
            (r"!\[.*?\]\(.*?\)", link_col, False)
        ]

    def highlightBlock(self, text):
        for pattern, col, bold in self.rules:
            for m in re.finditer(pattern, text):
                fmt = QTextCharFormat()
                fmt.setForeground(QColor(col))
                if bold: fmt.setFontWeight(QFont.Bold)
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class MarkdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_file = None

        # 布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. 工具栏
        self.init_toolbar()

        # 2. 分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.main_layout.addWidget(self.splitter)

        # 3. 编辑器
        self.editor = CodeEditor()
        self.editor.setFont(QFont("Consolas", 11))
        self.highlighter = MdHighlighter(self.editor.document())

        # 4. 预览区
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 1);
        self.splitter.setStretchFactor(1, 1)

        # 5. 状态栏
        self.init_statusbar()

        # --- 核心：应用样式 ---
        self.apply_theme_style()

        # 逻辑
        self.timer = QTimer();
        self.timer.setSingleShot(True);
        self.timer.interval = 300
        self.timer.timeout.connect(self.render)
        self.editor.textChanged.connect(self.timer.start)
        self.editor.cursorPositionChanged.connect(self.update_status)

        QShortcut("Ctrl+S", self).activated.connect(self.save)
        QShortcut("Ctrl+O", self).activated.connect(self.open)

        self.editor.setPlainText("# Hello\nWrite something...")

    def apply_theme_style(self):
        """一次性设置所有样式，确保统一"""
        if isDarkTheme():
            bg = "#1e1e1e";
            fg = "#d4d4d4";
            border = "#333333"
            preview_bg = "#1e1e1e";
            tool_bg = "#252526"
        else:
            bg = "#ffffff";
            fg = "#333333";
            border = "#e5e5e5"
            preview_bg = "#ffffff";
            tool_bg = "#f3f3f3"

        # 设置 Splitter 样式 (去黑边)
        self.splitter.setStyleSheet(f"""
            QSplitter {{ background-color: {bg}; border: none; }}
            QSplitter::handle {{ background-color: {border}; }}
        """)

        # 设置编辑器样式
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg}; color: {fg}; 
                border: none; padding: 15px;
            }}
        """)

        # 设置预览区样式
        self.preview.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {preview_bg}; color: {fg};
                border: none; padding: 15px; border-left: 1px solid {border};
            }}
        """)

        # 设置工具栏样式
        self.toolbar.setStyleSheet(f"background-color: {tool_bg}; border-bottom: 1px solid {border};")
        self.status_bar.setStyleSheet(f"background-color: #007acc; color: white;")

    def init_toolbar(self):
        self.toolbar = QWidget();
        self.toolbar.setFixedHeight(40)
        h = QHBoxLayout(self.toolbar);
        h.setContentsMargins(10, 0, 10, 0);
        h.setSpacing(5)

        def btn(icon, func):
            b = TransparentToolButton(icon, self);
            b.clicked.connect(func)
            h.addWidget(b)

        btn(FluentIcon.FOLDER, self.open)
        btn(FluentIcon.SAVE, self.save)
        h.addStretch(1)
        self.main_layout.addWidget(self.toolbar)

    def init_statusbar(self):
        self.status_bar = QWidget();
        self.status_bar.setFixedHeight(22)
        h = QHBoxLayout(self.status_bar);
        h.setContentsMargins(10, 0, 10, 0)
        self.lbl_info = QLabel("Ready")
        h.addWidget(self.lbl_info);
        h.addStretch(1)
        self.main_layout.addWidget(self.status_bar)

    def update_status(self):
        c = self.editor.textCursor()
        self.lbl_info.setText(f"Ln {c.blockNumber() + 1}, Col {c.columnNumber() + 1}")

    def render(self):
        raw = self.editor.toPlainText()
        html = markdown.markdown(raw, extensions=['extra', 'codehilite'])

        # CSS 注入
        if isDarkTheme():
            css = "body { color: #d4d4d4; } code { background: #2d2d2d; padding: 2px; } img { max-width: 100%; }"
        else:
            css = "body { color: #333; } code { background: #f0f0f0; padding: 2px; } img { max-width: 100%; }"

        final = f"<html><head><style>{css}</style></head><body>{html}</body></html>"

        # 路径处理
        if self.current_file:
            base = os.path.dirname(self.current_file)
        else:
            base = os.path.abspath("temp_assets")

        if not os.path.exists(base): os.makedirs(base, exist_ok=True)
        # 强制转为 file:/// URL
        self.preview.setSearchPaths([base.replace("\\", "/")])
        self.preview.setHtml(final)

    def open(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open", "", "MD (*.md)")
        if p:
            self.current_file = p;
            self.editor.set_base_path(p)
            with open(p, 'r', encoding='utf-8') as f: self.editor.setPlainText(f.read())

    def save(self):
        if not self.current_file:
            p, _ = QFileDialog.getSaveFileName(self, "Save", "note.md", "MD (*.md)")
            if not p: return
            self.current_file = p;
            self.editor.set_base_path(p)
        with open(self.current_file, 'w', encoding='utf-8') as f:
            f.write(self.editor.toPlainText())
        InfoBar.success("Saved", self.current_file, parent=self)