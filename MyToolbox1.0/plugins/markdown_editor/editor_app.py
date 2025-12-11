import sys
import os

# 1. 强制启用 OpenGL 共享 (解决 WebEngine 黑屏的关键)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# 添加项目根目录到路径，以便引用 core
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.append(project_root)

# 引入之前的 Widget 代码
# 注意：这里我们不能直接引用 tool.py 了，因为 tool.py 现在是启动器
# 我们需要把之前的 MarkdownWidget 代码移动到一个新文件，比如 widget.py
from plugins.markdown_editor.widget import MarkdownWidget

if __name__ == "__main__":
    # 设置高分屏
    os.environ["QT_API"] = "pyside6"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)  # 关键！

    app = QApplication(sys.argv)

    # 设置应用图标
    # app.setWindowIcon(...)

    w = MarkdownWidget()
    w.setWindowTitle("Markdown Pro - 独立编辑器")
    w.resize(1200, 800)

    # 可以在这里设置独立的主题样式

    w.show()
    sys.exit(app.exec())