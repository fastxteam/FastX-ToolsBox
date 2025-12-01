import os
import re
import markdown
from core.resource_manager import qicon
# 引入打印支持，用于导出 PDF
from PySide6.QtPrintSupport import QPrinter

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QFileDialog, QFrame, QTextBrowser)
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
                           QShortcut, QKeySequence, QTextCursor)
from PySide6.QtCore import Qt, QUrl, QTimer

from qfluentwidgets import (PlainTextEdit, FluentIcon, TransparentToolButton,
                            ToolTipFilter, ToolTipPosition, isDarkTheme,
                            InfoBar)
from core.plugin_interface import PluginInterface


# ==========================================
# 1. 语法高亮 (保持不变，用于左侧编辑器)
# ==========================================
class MdHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        # 根据主题适配颜色
        base_color = QColor("#dcdcdc") if isDarkTheme() else QColor("#333333")
        header_color = QColor("#4EC9B0") if isDarkTheme() else QColor("#005cc5")
        link_color = QColor("#9cdcfe") if isDarkTheme() else QColor("#005cc5")

        # 正则规则
        self.rules.append((re.compile(r"^#+.*"), self.fmt(header_color, True)))
        self.rules.append((re.compile(r"\*\*.*?\*\*"), self.fmt(QColor("#e91e63"), True)))
        self.rules.append((re.compile(r"`.*?`"), self.fmt(QColor("#22863a"))))
        self.rules.append((re.compile(r"!\[.*?\]\(.*?\)"), self.fmt(QColor("#d32f2f"))))
        self.rules.append((re.compile(r"\[.*?\]\(.*?\)"), self.fmt(link_color, False, True)))

    def fmt(self, color, bold=False, underline=False):
        f = QTextCharFormat()
        f.setForeground(color)
        if bold: f.setFontWeight(QFont.Bold)
        if underline: f.setFontUnderline(True)
        return f

    def highlightBlock(self, text):
        for pattern, format in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)


# ==========================================
# 2. 插件入口
# ==========================================
class MarkdownPlugin(PluginInterface):
    @property
    def name(self) -> str: return "Markdown 笔记"

    @property
    def icon(self): return qicon("markdown")

    @property
    def group(self) -> str: return "办公工具"

    @property
    def theme_color(self) -> str: return "#0078D4"

    @property
    def description(self) -> str: return "轻量级 Markdown 编辑器，支持导出 HTML/PDF"

    def create_widget(self) -> QWidget: return MarkdownWidget()


# ==========================================
# 3. 核心 Widget (最终增强版)
# ==========================================
class MarkdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_file = None

        # 允许拖拽文件
        self.setAcceptDrops(True)

        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)

        self.init_toolbar()

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        split_col = "#333" if isDarkTheme() else "#e0e0e0"
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {split_col}; }}")

        self.v_layout.addWidget(self.splitter)

        # --- 左侧：编辑器 ---
        self.editor = PlainTextEdit(self)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.editor.setFont(font)
        self.highlighter = MdHighlighter(self.editor.document())

        # --- 右侧：预览区 ---
        self.preview = QTextBrowser(self)
        self.preview.setOpenExternalLinks(True)
        preview_bg = "#202020" if isDarkTheme() else "#ffffff"
        self.preview.setStyleSheet(f"border: none; background-color: {preview_bg};")

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        # --- 底部状态栏 ---
        self.init_statusbar()

        # 防抖渲染
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.interval = 300
        self.render_timer.timeout.connect(self.render_markdown)

        # 信号连接
        self.editor.textChanged.connect(lambda: self.render_timer.start())
        self.editor.cursorPositionChanged.connect(self.update_status_bar)  # 光标移动更新状态栏

        # 【优化1】同步滚动连接
        self.editor.verticalScrollBar().valueChanged.connect(self.sync_scroll_editor_to_preview)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.save_file)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_file)

        # 初始内容
        init_text = """# 欢迎使用

试试 **滚动** 左侧的编辑区，右侧会跟随滚动哦！

也可以直接把 `.md` 文件 **拖拽** 到这里打开。
"""
        self.editor.setPlainText(init_text)
        self.render_markdown()

    def init_toolbar(self):
        toolbar_container = QWidget()
        toolbar_container.setFixedHeight(46)
        border_col = "#252525" if isDarkTheme() else "#e5e5e5"
        toolbar_container.setStyleSheet(f"border-bottom: 1px solid {border_col}; background: transparent;")

        layout = QHBoxLayout(toolbar_container)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(5)

        def add_btn(icon_obj, tooltip, slot):
            # 注意：TransparentToolButton 既接受 FluentIcon 也接受 QIcon
            btn = TransparentToolButton(icon_obj, self)
            btn.setToolTip(tooltip)
            btn.installEventFilter(ToolTipFilter(btn, showDelay=300, position=ToolTipPosition.BOTTOM))
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        # === 现在你可以随心所欲地定义图标了 ===

        # 1. 优先去 resources/icons 找 'folder.svg'，找不到则用 FluentIcon.FOLDER
        add_btn(qicon("folder"), "打开", self.open_file)
        add_btn(qicon("save"), "保存", self.save_file)

        # 2. 导出按钮
        add_btn(qicon("export"), "导出", self.export_file)

        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedHeight(20)
        line.setStyleSheet(f"color: {border_col};")
        layout.addWidget(line)

        # 3. 格式按钮
        # 你可以去下个 bold.svg 扔进 resources/icons，这里就会自动变成你的图标
        add_btn(qicon("bold"), "粗体", lambda: self.insert_syntax("**", "**"))
        add_btn(qicon("italic"), "斜体", lambda: self.insert_syntax("*", "*"))
        add_btn(qicon("header"), "标题", lambda: self.insert_line_prefix("# "))

        # 4. 高级功能
        add_btn(qicon("chart"), "插入图表", lambda: self.insert_syntax("```mermaid\ngraph TD;\n    A-->B;\n", "```"))
        add_btn(qicon("image"), "插入图片", lambda: self.insert_syntax("![描述](", ")"))

        layout.addStretch(1)
        self.v_layout.addWidget(toolbar_container)

    def init_statusbar(self):
        """【优化3】初始化底部状态栏"""
        from PySide6.QtWidgets import QLabel
        self.status_bar = QWidget()
        self.status_bar.setFixedHeight(24)
        bg_col = "#252525" if isDarkTheme() else "#f3f3f3"
        self.status_bar.setStyleSheet(f"background: {bg_col}; border-top: 1px solid #e0e0e0;")

        layout = QHBoxLayout(self.status_bar)
        layout.setContentsMargins(10, 0, 10, 0)

        # 信息标签
        self.status_label = QLabel("Ln 1, Col 1")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")

        self.word_count_label = QLabel("0 字")
        self.word_count_label.setStyleSheet("color: gray; font-size: 11px;")

        layout.addWidget(self.status_label)
        layout.addWidget(self.word_count_label)
        layout.addStretch(1)

        self.v_layout.addWidget(self.status_bar)

    def update_status_bar(self):
        """更新状态栏信息"""
        cursor = self.editor.textCursor()
        block_num = cursor.blockNumber() + 1
        col_num = cursor.columnNumber() + 1

        # 统计字数
        text = self.editor.toPlainText()
        word_count = len(text)

        self.status_label.setText(f"Ln {block_num}, Col {col_num}")
        self.word_count_label.setText(f"{word_count} 字")

    def sync_scroll_editor_to_preview(self):
        """【优化1】同步滚动：编辑器 -> 预览"""
        # 计算编辑器滚动的百分比
        editor_bar = self.editor.verticalScrollBar()
        preview_bar = self.preview.verticalScrollBar()

        if editor_bar.maximum() <= 0: return

        percent = editor_bar.value() / editor_bar.maximum()

        # 设置预览区滚动到相同百分比的位置
        target_val = int(percent * preview_bar.maximum())
        preview_bar.setValue(target_val)

    # ==========================
    # 【优化2】拖拽事件处理
    # ==========================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.endswith('.md') or file_path.endswith('.txt'):
                self.load_file_from_path(file_path)

    def load_file_from_path(self, path):
        """加载文件的辅助函数"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self.current_file = path
            self.render_markdown()
            InfoBar.success("打开成功", os.path.basename(path), parent=self)
        except Exception as e:
            InfoBar.error("打开失败", str(e), parent=self)

    # ... (insert_syntax, insert_line_prefix, open_file, save_file, export_file, render_markdown) ...
    # 为了完整性，请保留这些方法，逻辑与之前完全一致
    def insert_syntax(self, prefix, suffix):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.insertText(f"{prefix}{text}{suffix}")
        else:
            cursor.insertText(f"{prefix}{suffix}")
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, len(suffix))
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def insert_line_prefix(self, prefix):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(prefix)
        self.editor.setFocus()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "打开 Markdown", "", "Markdown Files (*.md);;All Files (*)")
        if path:
            self.load_file_from_path(path)

    def save_file(self):
        if not self.current_file:
            path, _ = QFileDialog.getSaveFileName(self, "保存文件", "note.md", "Markdown Files (*.md)")
            if not path: return
            self.current_file = path
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            InfoBar.success("成功", "文件已保存", parent=self)
        except Exception as e:
            InfoBar.error("错误", str(e), parent=self)

    def export_file(self):
        path, filt = QFileDialog.getSaveFileName(self, "导出文件", "export.pdf",
                                                 "PDF Document (*.pdf);;HTML Page (*.html)")
        if not path: return
        try:
            if path.endswith(".pdf"):
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(path)
                self.preview.print_(printer)
                InfoBar.success("导出成功", f"已保存为 PDF", parent=self)
            elif path.endswith(".html"):
                html_content = self.preview.toHtml()
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                InfoBar.success("导出成功", f"已保存为 HTML", parent=self)
        except Exception as e:
            InfoBar.error("导出失败", str(e), parent=self)

    def render_markdown(self):
        raw_text = self.editor.toPlainText()
        try:
            body_html = markdown.markdown(raw_text, extensions=['extra', 'codehilite', 'tables', 'fenced_code'])
        except Exception as e:
            body_html = f"<p style='color:red'>{e}</p>"

        if isDarkTheme():
            text_col = "#e0e0e0"
            bg_col = "#202020"
            link_col = "#4cc2ff"
            code_bg = "#2d2d2d"
            quote_col = "#a0a0a0"
        else:
            text_col = "#333333"
            bg_col = "#ffffff"
            link_col = "#0969da"
            code_bg = "#f6f8fa"
            quote_col = "#6a737d"

        final_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: "Microsoft YaHei", sans-serif; font-size: 14pt; color: {text_col}; background-color: {bg_col}; }}
                a {{ color: {link_col}; text-decoration: none; }}
                h1 {{ font-size: 24pt; font-weight: bold; border-bottom: 2px solid {text_col}; padding-bottom: 10px; margin-top: 20px; }}
                h2 {{ font-size: 20pt; font-weight: bold; border-bottom: 1px solid {text_col}; padding-bottom: 5px; margin-top: 15px; }}
                blockquote {{ border-left: 5px solid {quote_col}; padding: 5px 15px; color: {quote_col}; background-color: {code_bg}; margin: 10px 0; }}
                pre {{ background-color: {code_bg}; padding: 15px; border-radius: 5px; }}
                code {{ font-family: "Consolas", monospace; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid {text_col}; padding: 8px; }}
            </style>
        </head>
        <body>{body_html}</body>
        </html>
        """
        self.preview.setHtml(final_html)