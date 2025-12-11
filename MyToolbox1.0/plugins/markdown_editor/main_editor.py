import sys
import os

# 添加路径以便引用 core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from PySide6.QtWidgets import QApplication
from plugins.markdown_editor.tool import MarkdownWidget  # 复用之前的 Widget 代码

if __name__ == "__main__":
    # 在这里启用 WebEngine，不会影响主程序
    os.environ["QT_API"] = "pyside6"

    app = QApplication(sys.argv)

    w = MarkdownWidget()
    w.setWindowTitle("Markdown Pro (独立进程)")
    w.resize(1200, 800)
    w.show()

    sys.exit(app.exec())