import sys
import os

# 1. 修复路径问题（确保能找到 core 和 ui）
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from PySide6.QtWidgets import QApplication
# 2. 【核心修复】这里必须导入 Qt，否则下面代码会报 NameError
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 3. 设置高分屏缩放策略 (现在 Qt 被正确导入了，这行就不会报错了)
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)

    w = MainWindow()
    w.show()

    sys.exit(app.exec())