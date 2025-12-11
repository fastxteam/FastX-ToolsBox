import os
import re
import markdown
from pathlib import Path
from string import Template  # 引入模板引擎
from PySide6.QtPrintSupport import QPrinter

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QFileDialog, QFrame, QTextBrowser, QLabel,
                               QTreeWidget, QTreeWidgetItem)
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
                           QShortcut, QKeySequence, QTextCursor, QPalette)
from PySide6.QtCore import Qt, QUrl, QTimer

from qfluentwidgets import (PlainTextEdit, FluentIcon, TransparentToolButton,
                            ToolTipFilter, ToolTipPosition, isDarkTheme,
                            InfoBar)
from core.plugin_interface import PluginInterface
from plugins.markdown_editor.components.code_editor import CodeEditor

HAS_WEBENGINE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings

    HAS_WEBENGINE = True
except ImportError:
    pass


# ... (MdHighlighter, MarkdownPlugin 保持不变，略去以节省篇幅，请保留原有的类定义) ...
# 为了确保代码完整，这里保留 MdHighlighter 和 Plugin 定义
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

        # 1. 确定配色方案
        if isDarkTheme():
            self.bg_col = "#1e1e1e"
            self.fg_col = "#d4d4d4"
            self.border_col = "#333333"
            self.tool_bg = "#252526"
            self.tree_bg = "#181818"
        else:
            self.bg_col = "#ffffff"
            self.fg_col = "#333333"
            self.border_col = "#e5e5e5"
            self.tool_bg = "#f3f3f3"
            self.tree_bg = "#f8f8f8"

        self.setStyleSheet(f"background-color: {self.bg_col};")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 2. 工具栏
        self.init_toolbar()

        # 3. 分割器
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"""
            QSplitter {{ background-color: {self.bg_col}; border: none; }}
            QSplitter::handle {{ background-color: {self.border_col}; }}
        """)
        self.main_layout.addWidget(self.splitter)

        # 4. 左侧大纲
        self.outline = QTreeWidget()
        self.outline.setHeaderHidden(True)
        self.outline.setIndentation(15)
        self.outline.itemClicked.connect(self.on_outline_clicked)
        self.outline.setStyleSheet(f"""
            QTreeWidget {{ 
                background-color: {self.tree_bg}; 
                color: {self.fg_col}; 
                border: none; 
                border-right: 1px solid {self.border_col};
                outline: none;
            }}
            QTreeWidget::item:hover {{ background: rgba(128,128,128,0.1); }}
            QTreeWidget::item:selected {{ background: rgba(128,128,128,0.2); color: {self.fg_col}; }}
        """)
        self.splitter.addWidget(self.outline)

        # 5. 中间编辑器
        self.editor = CodeEditor(self)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.editor.setFont(font)
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.bg_col}; 
                color: {self.fg_col}; 
                border: none; 
                padding: 10px;
                outline: none;
            }}
        """)
        self.highlighter = MdHighlighter(self.editor.document())
        self.splitter.addWidget(self.editor)

        # 6. 右侧预览
        if HAS_WEBENGINE:
            self.preview = QWebEngineView(self)
            self.preview.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
            self.preview.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            self.preview.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            self.preview.page().setBackgroundColor(QColor(self.bg_col))
        else:
            self.preview = QTextBrowser(self)
            self.preview.setOpenExternalLinks(True)
            self.preview.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {self.bg_col}; 
                    border: none; 
                    padding: 10px; 
                    border-left: 1px solid {self.border_col};
                }}
            """)
        self.splitter.addWidget(self.preview)

        self.splitter.setSizes([150, 425, 425])

        # 7. 状态栏
        self.init_statusbar()

        # 8. 逻辑
        self.render_timer = QTimer();
        self.render_timer.setSingleShot(True);
        self.render_timer.interval = 500
        self.render_timer.timeout.connect(self.render_markdown)

        self.parse_timer = QTimer();
        self.parse_timer.setSingleShot(True);
        self.parse_timer.interval = 800
        self.parse_timer.timeout.connect(self.parse_outline)

        self.editor.textChanged.connect(lambda: (self.render_timer.start(), self.parse_timer.start()))
        self.editor.cursorPositionChanged.connect(self.update_status_bar)

        if hasattr(self.editor, 'verticalScrollBar'):
            self.editor.verticalScrollBar().valueChanged.connect(self.sync_scroll)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_file)

        # 加载模板
        self.template_content = ""
        try:
            tpl_path = Path(__file__).parent / "template.html"
            if tpl_path.exists():
                self.template_content = tpl_path.read_text(encoding='utf-8')
        except:
            pass

        self.editor.setPlainText("# 欢迎使用\n\n按 `Ctrl+V` 粘贴图片试试。")
        self.render_markdown()
        self.parse_outline()

    # ... (init_toolbar, init_statusbar, insert... 保持不变) ...
    # 为节省篇幅，这里复用
    def init_toolbar(self):
        self.toolbar = QWidget();
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet(f"background-color: {self.tool_bg}; border-bottom: 1px solid {self.border_col};")
        layout = QHBoxLayout(self.toolbar);
        layout.setContentsMargins(10, 0, 10, 0);
        layout.setSpacing(5)

        def add(icon, tip, slot):
            btn = TransparentToolButton(icon, self);
            btn.setToolTip(tip);
            btn.clicked.connect(slot);
            layout.addWidget(btn)

        add(FluentIcon.FOLDER, "打开", self.open_file)
        add(FluentIcon.SAVE, "保存", self.save_file)
        add(getattr(FluentIcon, 'DOWNLOAD', FluentIcon.SHARE), "导出", self.export_file)
        line = QFrame();
        line.setFrameShape(QFrame.VLine);
        line.setFixedHeight(20);
        line.setStyleSheet(f"color: {self.border_col};");
        layout.addWidget(line)
        add(getattr(FluentIcon, 'BOLD', FluentIcon.EDIT), "粗体", lambda: self.insert("**", "**"))
        add(getattr(FluentIcon, 'ITALIC', FluentIcon.DOCUMENT), "斜体", lambda: self.insert("*", "*"))
        add(FluentIcon.MENU, "标题", lambda: self.insert_line_prefix("# "))
        icon_img = getattr(FluentIcon, 'PHOTO', getattr(FluentIcon, 'CAMERA', FluentIcon.FOLDER))
        add_btn = TransparentToolButton(icon_img, self);
        add_btn.clicked.connect(lambda: self.insert("![描述](", ")"));
        layout.addWidget(add_btn)
        layout.addStretch(1);
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

    def insert(self, p, s):
        c = self.editor.textCursor()
        if c.hasSelection():
            c.insertText(f"{p}{c.selectedText()}{s}")
        else:
            c.insertText(f"{p}{s}"); c.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor,
                                                    len(s)); self.editor.setTextCursor(c)
        self.editor.setFocus()

    def insert_line_prefix(self, p):
        c = self.editor.textCursor(); c.movePosition(QTextCursor.StartOfLine); c.insertText(p); self.editor.setFocus()

    def update_status_bar(self):
        c = self.editor.textCursor(); self.status_label.setText(
            f"Ln {c.blockNumber() + 1}, Col {c.columnNumber() + 1}"); self.word_count_label.setText(
            f"{len(self.editor.toPlainText())} 字")

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
            InfoBar.success("打开成功", os.path.basename(path), parent=self)
        except Exception as e:
            InfoBar.error("打开失败", str(e), parent=self)

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
            html = self.preview.toHtml() if hasattr(self.preview, 'toHtml') else ""
            with open(p, 'w', encoding='utf-8') as f:
                f.write(html)
            InfoBar.success("Exported", str(p), parent=self)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self)

    # ==========================
    # 核心：使用模板渲染
    # ==========================
    def render_markdown(self):
        raw_text = self.editor.toPlainText()

        mermaid_pattern = re.compile(r'```mermaid(.*?)```', re.DOTALL)
        raw_text = mermaid_pattern.sub(r'<div class="mermaid">\1</div>', raw_text)

        try:
            extensions = ['extra', 'codehilite', 'tables', 'fenced_code']
            try:
                import mdx_math; extensions.append('mdx_math')
            except:
                pass
            body_html = markdown.markdown(raw_text, extensions=extensions)
        except Exception as e:
            body_html = f"<p style='color:red'>{e}</p>"

        # 准备模板变量
        context = {
            'text_col': "#e0e0e0" if isDarkTheme() else "#333333",
            'bg_col': self.bg_col,
            'link_col': "#4cc2ff" if isDarkTheme() else "#0969da",
            'code_bg': "#2d2d2d" if isDarkTheme() else "#f6f8fa",
            'quote_col': "#a0a0a0" if isDarkTheme() else "#6a737d",
            'mermaid_theme': "dark" if isDarkTheme() else "default",
            'content': body_html
        }

        # 替换模板
        if self.template_content:
            final_html = Template(self.template_content).safe_substitute(context)
        else:
            # 备用硬编码模板 (防止文件丢失报错)
            final_html = f"<html><body>{body_html}</body></html>"

        # 路径修复
        if self.current_file:
            base_dir = os.path.dirname(self.current_file)
        else:
            base_dir = os.path.abspath("temp_assets")
            if not os.path.exists(base_dir): os.makedirs(base_dir, exist_ok=True)

        base_dir_str = base_dir.replace("\\", "/")
        if not base_dir_str.endswith("/"): base_dir_str += "/"

        def img_replacer(m):
            rel = m.group(1)
            if rel.startswith("http") or rel.startswith("file:"): return m.group(0)
            return f'src="file:///{base_dir_str}{rel}"'

        html_fixed = re.sub(r'src="([^"]+)"', img_replacer, final_html)

        if HAS_WEBENGINE:
            self.preview.setHtml(html_fixed, QUrl.fromLocalFile(base_dir_str))
        else:
            self.preview.setSearchPaths([base_dir_str])
            self.preview.setHtml(html_fixed)

    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        u = e.mimeData().urls()
        if u:
            p = u[0].toLocalFile()
            if p.lower().endswith(('.md', '.txt')): self.load_file_from_path(p)