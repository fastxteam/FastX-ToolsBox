import os
from PySide6.QtWidgets import QPlainTextEdit, QFrame
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QImage, QTextCursor


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_path = ""

        # 1. 基础外观设置
        self.setFrameShape(QFrame.NoFrame)  # 无边框
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(0)

        # 2. 交互设置
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)  # Tab=4空格

        # 3. 初始样式 (透明背景，依靠父级)
        self.setStyleSheet("background: transparent; border: none; outline: none;")

    def set_base_path(self, path):
        self.base_path = path

    # ==========================
    # 图片粘贴逻辑
    # ==========================
    def canInsertFromMimeData(self, source):
        return source.hasImage() or source.hasUrls() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        # 1. 截图粘贴
        if source.hasImage():
            self._save_and_insert(source.imageData())
            return

        # 2. 文件复制粘贴
        if source.hasUrls():
            for url in source.urls():
                local = url.toLocalFile()
                if local.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    self._save_and_insert(QImage(local))
                    return  # 只处理第一张图片

        # 3. 普通文本
        super().insertFromMimeData(source)

    def _save_and_insert(self, image):
        # 确定保存路径
        if self.base_path:
            doc_dir = os.path.dirname(self.base_path)
        else:
            doc_dir = os.path.abspath("temp_assets")

        assets_dir = os.path.join(doc_dir, "assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)

        timestamp = QDateTime.currentDateTime().toString("yyyyMMdd_HHmmss_zzz")
        filename = f"img_{timestamp}.png"
        filepath = os.path.join(assets_dir, filename)

        if isinstance(image, QImage):
            image.save(filepath, "PNG")
        else:
            image.toImage().save(filepath, "PNG")

        # 插入相对路径
        self.insertPlainText(f"![image](assets/{filename})")

    # ==========================
    # 智能输入辅助
    # ==========================
    def keyPressEvent(self, e):
        # 回车自动缩进
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            block_text = cursor.block().text()

            # 计算缩进
            indent = ""
            for char in block_text:
                if char in (' ', '\t'):
                    indent += char
                else:
                    break

            # 列表补全 (- item)
            stripped = block_text.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                if len(stripped) == 1 or stripped == "-":
                    # 如果只有标记，删除标记结束列表
                    # (逻辑略复杂，简单起见只做延续)
                    pass
                else:
                    indent += stripped[0] + " "

            super().keyPressEvent(e)
            self.insertPlainText(indent)
            return

        # 符号成对补全
        pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'", '`': '`'}
        text = e.text()
        if text in pairs:
            cursor = self.textCursor()
            if cursor.hasSelection():
                sel = cursor.selectedText()
                cursor.insertText(f"{text}{sel}{pairs[text]}")
            else:
                super().keyPressEvent(e)
                self.insertPlainText(pairs[text])
                self.moveCursor(QTextCursor.Left)
            return

        super().keyPressEvent(e)