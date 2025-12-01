import os
import subprocess
import sys
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QApplication, QFileDialog, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from qfluentwidgets import (PrimaryPushButton, PushButton, CheckBox,
                            LineEdit, StrongBodyLabel, SubtitleLabel,
                            InfoBar, InfoBarPosition, CardWidget,
                            ComboBox, SpinBox, BodyLabel,
                            ScrollArea, PlainTextEdit, StateToolTip)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


# ==========================================
# 1. 插件定义类
# ==========================================
class PyToExePlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "Python打包工具"

    @property
    def icon(self):
        return qicon("package")  # 需要 resources/icons/package.svg

    @property
    def group(self) -> str:
        return "开发工具"

    @property
    def theme_color(self) -> str:
        return "#2FD076"  # 绿色

    @property
    def description(self) -> str:
        return "将Python脚本打包成独立的可执行文件"

    def create_widget(self) -> QWidget:
        return PyToExeWidget()


# ==========================================
# 2. 打包线程类 (避免界面卡顿)
# ==========================================
class PackagerThread(QThread):
    """打包执行线程"""
    progress_signal = Signal(str)
    finished_signal = Signal(bool, str)
    output_signal = Signal(str)

    def __init__(self, python_file, output_dir, options):
        super().__init__()
        self.python_file = python_file
        self.output_dir = output_dir
        self.options = options
        self.is_running = True

    def run(self):
        try:
            self.progress_signal.emit("正在检查PyInstaller安装...")

            # 检查PyInstaller是否安装
            try:
                import PyInstaller
            except ImportError:
                self.progress_signal.emit("正在安装PyInstaller...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

            # 构建PyInstaller命令
            cmd = self._build_command()

            self.progress_signal.emit("开始打包过程...")
            self.output_signal.emit(f"执行命令: {' '.join(cmd)}\n")

            # 执行打包命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=os.path.dirname(self.python_file) if self.python_file else None
            )

            # 实时输出
            for line in process.stdout:
                if self.is_running:
                    self.output_signal.emit(line.strip())
                else:
                    process.terminate()
                    break

            process.wait()

            if process.returncode == 0:
                self.finished_signal.emit(True, "打包成功完成！")
            else:
                self.finished_signal.emit(False, f"打包失败，返回码: {process.returncode}")

        except Exception as e:
            self.finished_signal.emit(False, f"打包过程中发生错误: {str(e)}")

    def _build_command(self):
        """构建PyInstaller命令"""
        cmd = [sys.executable, "-m", "PyInstaller"]

        # 输入文件
        cmd.append(self.python_file)

        # 输出目录
        if self.options.get("output_dir"):
            cmd.extend(["--distpath", self.options["output_dir"]])

        # 工作目录
        if self.options.get("work_dir"):
            cmd.extend(["--workpath", self.options["work_dir"]])

        # 规格文件目录
        if self.options.get("spec_dir"):
            cmd.extend(["--specpath", self.options["spec_dir"]])

        # 单文件模式
        if self.options.get("onefile", True):
            cmd.append("--onefile")
        else:
            cmd.append("--onedir")

        # 控制台窗口
        if not self.options.get("console", True):
            cmd.append("--windowed")

        # 图标
        if self.options.get("icon_file"):
            cmd.extend(["--icon", self.options["icon_file"]])

        # 名称
        if self.options.get("name"):
            cmd.extend(["--name", self.options["name"]])

        # 附加文件
        if self.options.get("add_files"):
            for file in self.options["add_files"].split(";"):
                if file.strip():
                    cmd.extend(["--add-data", f"{file.strip()}"])

        # 隐藏导入
        if self.options.get("hidden_imports"):
            for imp in self.options["hidden_imports"].split(";"):
                if imp.strip():
                    cmd.extend(["--hidden-import", imp.strip()])

        # 清理临时文件
        if self.options.get("clean", True):
            cmd.append("--clean")

        # 调试模式
        if self.options.get("debug"):
            cmd.append("--debug")

        return cmd

    def stop(self):
        """停止打包过程"""
        self.is_running = False


# ==========================================
# 3. 主界面类
# ==========================================
class PyToExeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.packager_thread = None
        self.state_tooltip = None
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        title = SubtitleLabel("Python文件打包工具", self)
        layout.addWidget(title)

        # 文件选择卡片
        file_card = CardWidget(self)
        file_layout = QVBoxLayout(file_card)
        file_layout.setSpacing(15)

        # Python文件选择
        python_file_layout = QHBoxLayout()
        self.python_file_edit = LineEdit(self)
        self.python_file_edit.setPlaceholderText("选择要打包的Python文件...")
        self.btn_browse_python = PushButton("选择文件", self)
        self.btn_browse_python.clicked.connect(self.browse_python_file)

        python_file_layout.addWidget(self.python_file_edit)
        python_file_layout.addWidget(self.btn_browse_python)
        file_layout.addLayout(python_file_layout)

        # 输出目录选择
        output_layout = QHBoxLayout()
        self.output_dir_edit = LineEdit(self)
        self.output_dir_edit.setPlaceholderText("选择输出目录（可选）...")
        self.btn_browse_output = PushButton("选择目录", self)
        self.btn_browse_output.clicked.connect(self.browse_output_dir)

        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.btn_browse_output)
        file_layout.addLayout(output_layout)

        layout.addWidget(file_card)

        # 打包选项卡片
        options_card = CardWidget(self)
        options_layout = QVBoxLayout(options_card)
        options_layout.setSpacing(15)

        # 基本选项
        basic_options_layout = QHBoxLayout()

        self.onefile_check = CheckBox("单文件模式", self)
        self.onefile_check.setChecked(True)
        basic_options_layout.addWidget(self.onefile_check)

        self.console_check = CheckBox("控制台窗口", self)
        self.console_check.setChecked(True)
        basic_options_layout.addWidget(self.console_check)

        self.clean_check = CheckBox("清理临时文件", self)
        self.clean_check.setChecked(True)
        basic_options_layout.addWidget(self.clean_check)

        options_layout.addLayout(basic_options_layout)

        # 名称和图标
        name_icon_layout = QHBoxLayout()

        name_icon_layout.addWidget(BodyLabel("输出名称:"))
        self.name_edit = LineEdit(self)
        self.name_edit.setPlaceholderText("自动从文件名获取")
        name_icon_layout.addWidget(self.name_edit)

        name_icon_layout.addWidget(BodyLabel("图标文件:"))
        self.icon_edit = LineEdit(self)
        self.icon_edit.setPlaceholderText("选择.ico图标文件（可选）")
        name_icon_layout.addWidget(self.icon_edit)

        self.btn_browse_icon = PushButton("...", self)
        self.btn_browse_icon.setFixedWidth(40)
        self.btn_browse_icon.clicked.connect(self.browse_icon_file)
        name_icon_layout.addWidget(self.btn_browse_icon)

        options_layout.addLayout(name_icon_layout)

        # 高级选项
        advanced_options_layout = QVBoxLayout()

        # 附加文件
        add_files_layout = QHBoxLayout()
        add_files_layout.addWidget(BodyLabel("附加文件:"))
        self.add_files_edit = LineEdit(self)
        self.add_files_edit.setPlaceholderText("用分号;分隔多个文件")
        add_files_layout.addWidget(self.add_files_edit)
        advanced_options_layout.addLayout(add_files_layout)

        # 隐藏导入
        hidden_imports_layout = QHBoxLayout()
        hidden_imports_layout.addWidget(BodyLabel("隐藏导入:"))
        self.hidden_imports_edit = LineEdit(self)
        self.hidden_imports_edit.setPlaceholderText("用分号;分隔多个模块")
        hidden_imports_layout.addWidget(self.hidden_imports_edit)
        advanced_options_layout.addLayout(hidden_imports_layout)

        options_layout.addLayout(advanced_options_layout)
        layout.addWidget(options_card)

        # 输出区域
        output_card = CardWidget(self)
        output_layout = QVBoxLayout(output_card)

        output_layout.addWidget(StrongBodyLabel("打包输出:"))
        self.output_text = PlainTextEdit(self)
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(200)
        output_layout.addWidget(self.output_text)

        layout.addWidget(output_card)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.btn_package = PrimaryPushButton(qicon("rocket"), "开始打包", self)
        self.btn_package.clicked.connect(self.start_packaging)
        button_layout.addWidget(self.btn_package)

        self.btn_stop = PushButton(qicon("stop"), "停止打包", self)
        self.btn_stop.clicked.connect(self.stop_packaging)
        self.btn_stop.setEnabled(False)
        button_layout.addWidget(self.btn_stop)

        self.btn_clear = PushButton(qicon("delete"), "清空输出", self)
        self.btn_clear.clicked.connect(self.clear_output)
        button_layout.addWidget(self.btn_clear)

        layout.addLayout(button_layout)

        layout.addStretch(1)

    def browse_python_file(self):
        """选择Python文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Python文件",
            "",
            "Python Files (*.py);;All Files (*)"
        )
        if file_path:
            self.python_file_edit.setText(file_path)
            # 自动设置输出名称
            if not self.name_edit.text():
                name = Path(file_path).stem
                self.name_edit.setText(name)

    def browse_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录"
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def browse_icon_file(self):
        """选择图标文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图标文件",
            "",
            "Icon Files (*.ico);;All Files (*)"
        )
        if file_path:
            self.icon_edit.setText(file_path)

    def start_packaging(self):
        """开始打包过程"""
        python_file = self.python_file_edit.text().strip()

        if not python_file:
            InfoBar.warning(
                title="警告",
                content="请选择要打包的Python文件",
                parent=self
            )
            return

        if not os.path.exists(python_file):
            InfoBar.error(
                title="错误",
                content="选择的Python文件不存在",
                parent=self
            )
            return

        # 收集选项
        options = {
            "onefile": self.onefile_check.isChecked(),
            "console": self.console_check.isChecked(),
            "clean": self.clean_check.isChecked(),
            "output_dir": self.output_dir_edit.text().strip() or None,
            "icon_file": self.icon_edit.text().strip() or None,
            "name": self.name_edit.text().strip() or None,
            "add_files": self.add_files_edit.text().strip() or None,
            "hidden_imports": self.hidden_imports_edit.text().strip() or None,
        }

        # 设置工作目录和规格文件目录
        python_dir = os.path.dirname(python_file)
        if options["output_dir"]:
            options["work_dir"] = os.path.join(options["output_dir"], "build")
            options["spec_dir"] = python_dir
        else:
            options["work_dir"] = os.path.join(python_dir, "build")
            options["spec_dir"] = python_dir

        # 清空输出
        self.output_text.clear()

        # 显示进度提示
        self.state_tooltip = StateToolTip("正在打包", "请稍候...", self)
        self.state_tooltip.move(self.state_tooltip.getSuitablePos())
        self.state_tooltip.show()

        # 更新按钮状态
        self.btn_package.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 启动打包线程
        self.packager_thread = PackagerThread(python_file, options["output_dir"], options)
        self.packager_thread.progress_signal.connect(self.update_progress)
        self.packager_thread.finished_signal.connect(self.packaging_finished)
        self.packager_thread.output_signal.connect(self.update_output)
        self.packager_thread.start()

    def stop_packaging(self):
        """停止打包过程"""
        if self.packager_thread and self.packager_thread.isRunning():
            self.packager_thread.stop()
            self.packager_thread.wait()
            self.update_output("打包过程已被用户中止")
            self.packaging_finished(False, "打包过程被中止")

    def clear_output(self):
        """清空输出区域"""
        self.output_text.clear()

    def update_progress(self, message):
        """更新进度信息"""
        if self.state_tooltip:
            self.state_tooltip.setContent(message)

    def update_output(self, text):
        """更新输出文本"""
        self.output_text.appendPlainText(text)
        # 自动滚动到底部
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def packaging_finished(self, success, message):
        """打包完成处理"""
        # 隐藏进度提示
        if self.state_tooltip:
            self.state_tooltip.setContent(message)
            self.state_tooltip.setState(StateToolTip.SUCCESS if success else StateToolTip.ERROR)
            self.state_tooltip.close()
            self.state_tooltip = None

        # 更新按钮状态
        self.btn_package.setEnabled(True)
        self.btn_stop.setEnabled(False)

        # 显示结果消息
        if success:
            InfoBar.success(
                title="完成",
                content=message,
                parent=self
            )
        else:
            InfoBar.error(
                title="错误",
                content=message,
                parent=self
            )