import sys
import os
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import PrimaryPushButton, SubtitleLabel, FluentIcon, InfoBar
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


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
    def description(self) -> str: return "高性能独立进程编辑器 (支持Mermaid/公式)"

    def create_widget(self) -> QWidget: return LauncherWidget()


class LauncherWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        layout.addWidget(SubtitleLabel("Markdown 专业版", self))

        info = QLabel("为了获得最佳的渲染性能（WebEngine）并避免UI冲突，\n编辑器将在独立窗口中运行。", self)
        info.setStyleSheet("color: gray; font-size: 14px;")
        layout.addWidget(info)

        btn = PrimaryPushButton(qicon("rocket"), "启动编辑器", self)
        btn.setFixedWidth(200)
        btn.clicked.connect(self.launch_process)
        layout.addWidget(btn)

        layout.addStretch(1)

    def launch_process(self):
        try:
            # 定位到 main_editor.py
            script_path = os.path.join(os.path.dirname(__file__), 'editor_app.py')

            # 启动子进程
            # 使用 Popen 而不是 run，这样主程序不会卡住
            subprocess.Popen([sys.executable, script_path])

            InfoBar.success("已启动", "编辑器正在后台加载...", parent=self)
        except Exception as e:
            InfoBar.error("启动失败", str(e), parent=self)