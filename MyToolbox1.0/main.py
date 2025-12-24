import sys
import os

# 1. 修复路径问题（确保能找到 core 和 ui）
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 2. 导入必要的模块
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

if __name__ == "__main__":
    # 3. 首先设置高分屏缩放策略，必须在创建 QApplication 之前调用
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # 4. 然后创建 QApplication
    app = QApplication(sys.argv)
    
    # 5. 导入并创建 MainWindow
    from ui.main_window import MainWindow
    w = MainWindow()
    w.show()
    
    # 6. 运行应用
    sys.exit(app.exec())