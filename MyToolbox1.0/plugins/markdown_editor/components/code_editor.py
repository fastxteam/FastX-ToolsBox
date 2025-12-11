import os
from PySide6.QtWidgets import QWidget, QPlainTextEdit, QTextEdit, QFrame
from PySide6.QtCore import Qt, QRect, QSize, Signal, QDateTime
from PySide6.QtGui import QColor, QPainter, QTextFormat, QFont, QTextCursor, QImage

from qfluentwidgets import isDarkTheme


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor
        # 行号区也要透明背景
        self.setAttribute(Qt.WA_TranslucentBackground)

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.base_path = ""

        # 1. 强制去边框属性
        self.setFrameShape(QFrame.NoFrame)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(0)
        self.setMidLineWidth(0)

        # 2. 视口透明
        self.viewport().setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 3. 初始硬编码样式（去边框，背景透明）
        # 这一行非常重要，作为保底
        self.setStyleSheet("QPlainTextEdit { border: none; background: transparent; }")

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)

    def set_base_path(self, path):
        self.base_path = path

    def canInsertFromMimeData(self, source):
        if source.hasImage() or source.hasUrls(): return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            self.save_and_insert_image(image)
            return

        if source.hasUrls():
            has_handled = False
            for url in source.urls():
                local_path = url.toLocalFile()
                if local_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                    image = QImage(local_path)
                    if not image.isNull():
                        self.save_and_insert_image(image)
                        has_handled = True

            if has_handled: return

        super().insertFromMimeData(source)

    def save_and_insert_image(self, image):
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

        rel_path = f"assets/{filename}"
        self.insertPlainText(f"![image]({rel_path})")

    def lineNumberAreaWidth(self):
        digits = 1;
        max_num = max(1, self.blockCount())
        while max_num >= 10: max_num //= 10; digits += 1
        return 20 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()): self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)

        # 【关键修复】确保行号区背景与主题一致，或者透明
        if isDarkTheme():
            bg_color = QColor("#1e1e1e")  # 与 tool.py 中的 bg 一致
            text_color = QColor("#858585")
            current_text_color = QColor("#c6c6c6")
        else:
            bg_color = QColor("#ffffff")
            text_color = QColor("#237893")
            current_text_color = QColor("#000000")

        painter.fillRect(event.rect(), bg_color)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        current_line = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                is_current = (blockNumber == current_line)
                painter.setPen(current_text_color if is_current else text_color)
                font = painter.font()
                font.setBold(is_current)
                painter.setFont(font)
                painter.drawText(0, int(top), self.lineNumberArea.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            # 【关键修复】高亮色必须半透明，否则会遮住背景图或产生色块
            if isDarkTheme():
                line_color = QColor(255, 255, 255, 10)
            else:
                line_color = QColor(0, 0, 0, 10)

            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
        self.lineNumberArea.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            cursor = self.textCursor()
            block_text = cursor.block().text()
            indentation = ""
            for char in block_text:
                if char == ' ':
                    indentation += " "
                elif char == '\t':
                    indentation += "\t"
                else:
                    break

            if block_text.strip().startswith("- "):
                if block_text.strip() == "-":
                    cursor.select(QTextCursor.BlockUnderCursor)
                    cursor.removeSelectedText()
                    return
                else:
                    indentation += "- "

            super().keyPressEvent(event)
            self.insertPlainText(indentation)
            return

        pairs = {'(': ')', '[': ']', '{': '}', '"': '"', "'": "'", '`': '`'}
        if event.text() in pairs:
            char = event.text()
            cursor = self.textCursor()
            if cursor.hasSelection():
                text = cursor.selectedText()
                cursor.insertText(f"{char}{text}{pairs[char]}")
                return
            super().keyPressEvent(event)
            self.insertPlainText(pairs[char])
            self.moveCursor(QTextCursor.Left)
            return

        super().keyPressEvent(event)