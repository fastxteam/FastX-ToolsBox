# 🛠️ Python Fluent Toolbox 开发指南

# 🛠️ Python Fluent Toolbox 开发指南

欢迎加入 **MyToolbox** 开发团队！本项目是一个基于 PySide6 和 Fluent-Widgets 的现代化工具箱平台。

本文档将帮助你快速理解项目架构，并教会你如何开发一个新的插件工具。

## 1. 项目架构概览

你不需要理解所有代码，只需关注 **plugins/** 目录和 **resources/** 目录即可。

`codeText`

`MyToolbox/
├── main.py                  # [勿动] 程序启动入口
├── core/                    # [勿动] 核心框架（插件加载、配置管理、资源管理）
├── ui/                      # [勿动] 主界面逻辑（Tab页管理、卡片渲染）
├── config/                  # [自动生成] 配置文件存储位置
├── resources/               # [资源] 存放图标和静态资源
│   └── icons/               # 🟢 在这里放入你的 .svg 或 .png 图标
└── plugins/                 # 🟢 开发区：在这里创建你的插件
    ├── demo_tool/           # 示例：数据转换工坊
    ├── markdown_editor/     # 示例：Markdown 编辑器
    └── your_new_tool/       # 👉 你的新插件放在这里`

## 2. 插件开发流程 (5步走)

### 第 1 步：创建目录

在 plugins/ 目录下创建一个新文件夹，例如 password_gen。

并在其中创建一个空文件 __init__.py 和核心代码文件 tool.py。

### 第 2 步：准备图标

找一个 .svg 或 .png 图标（例如 lock.svg），放入 resources/icons/ 文件夹。

### 第 3 步：编写插件类

打开 tool.py，定义一个继承自 PluginInterface 的类。这是主程序识别你插件的“身份证”。

`code`

<`Python`>

`from core.plugin_interface import PluginInterface
from core.resource_manager import qicon
from PySide6.QtWidgets import QWidget

class MyPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "密码生成器"  # 工具名称

    @property
    def icon(self):
        return qicon("lock") # 对应 resources/icons/lock.svg

    @property
    def group(self) -> str:
        return "安全工具"    # 分组名称

    @property
    def theme_color(self) -> str:
        return "#009688"    # 主题色 (Hex)

    @property
    def description(self) -> str:
        return "生成高强度随机密码" # 卡片上的描述

    def create_widget(self) -> QWidget:
        return MyToolWidget() # 返回下面定义的界面类`

### 第 4 步：编写界面类

在同一个文件中，编写实际的 QWidget 界面逻辑。推荐使用 qfluentwidgets 提供的控件以保持风格统一。

### 第 5 步：运行测试

直接运行根目录下的 main.py，你的插件会自动出现在首页！无需注册任何配置。

---

## 3. 常用组件与 API 速查

### 图标系统

不要硬编码路径，使用核心库提供的 qicon：

codePython

`from core.resource_manager import qicon
btn = PushButton(qicon("save"), "保存", self)`

*系统会自动查找 resources/icons/save.svg，如果找不到会尝试使用系统默认图标，绝不报错。*

### 配置持久化

如果你的插件需要保存用户设置（如上次选中的选项）：

codePython

`from core.config import ConfigManager

# 读取
config = ConfigManager.load()
my_setting = config.get("my_plugin_setting", True)

# 保存
config["my_plugin_setting"] = False
ConfigManager.save(config)`

### 消息提示

不要使用 QMessageBox，请使用更现代的 InfoBar：

codePython

`from qfluentwidgets import InfoBar, InfoBarPosition

InfoBar.success(
    title="成功",
    content="密码已复制到剪贴板",
    orient=Qt.Horizontal,
    isClosable=True,
    position=InfoBarPosition.TOP,
    parent=self
)`

---

## 4. 标准模板代码 (Template)

**建议将以下代码复制到 plugins/template_tool/tool.py 中作为参考。**

这是一个完整的“密码生成器”插件示例，展示了：

1. 布局管理
2. 常用 Fluent 控件 (Slider, CheckBox, Button)
3. 信号与槽
4. 剪贴板操作

codePython

`import random
import string
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QApplication, 
                               QFrame, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

# 引入 Fluent 控件
from qfluentwidgets import (PrimaryPushButton, PushButton, CheckBox, Slider, 
                            LineEdit, StrongBodyLabel, SubtitleLabel, 
                            InfoBar, InfoBarPosition, CardWidget)

# 引入核心接口
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon

# ==========================================
# 1. 插件定义 (身份证)
# ==========================================
class PasswordGenPlugin(PluginInterface):
    @property
    def name(self) -> str:
        return "密码生成器"

    @property
    def icon(self):
        # 请确保 resources/icons/lock.svg 存在，否则会显示默认问号
        return qicon("lock") 

    @property
    def group(self) -> str:
        return "安全工具"
    
    @property
    def theme_color(self) -> str:
        return "#009688" # 蓝绿色

    @property
    def description(self) -> str:
        return "快速生成包含大小写、数字和符号的高强度随机密码。"

    def create_widget(self) -> QWidget:
        return PasswordWidget()

# ==========================================
# 2. 界面逻辑 (躯体)
# ==========================================
class PasswordWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- 布局初始化 ---
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(30, 30, 30, 30)
        self.v_layout.setSpacing(20)

        # --- 标题区 ---
        title = SubtitleLabel("生成随机密码", self)
        self.v_layout.addWidget(title)

        # --- 设置卡片区 (使用 CardWidget 增加美观度) ---
        settings_card = CardWidget(self)
        card_layout = QVBoxLayout(settings_card)
        
        # 1. 长度滑块
        h_layout_len = QHBoxLayout()
        self.len_label = StrongBodyLabel("长度: 12", self)
        self.slider = Slider(Qt.Horizontal, self)
        self.slider.setRange(4, 64)
        self.slider.setValue(12)
        self.slider.valueChanged.connect(lambda v: self.len_label.setText(f"长度: {v}"))
        
        h_layout_len.addWidget(self.len_label)
        h_layout_len.addWidget(self.slider)
        card_layout.addLayout(h_layout_len)

        # 2. 选项复选框
        self.chk_upper = CheckBox("包含大写字母 (A-Z)", self)
        self.chk_upper.setChecked(True)
        
        self.chk_number = CheckBox("包含数字 (0-9)", self)
        self.chk_number.setChecked(True)
        
        self.chk_symbol = CheckBox("包含特殊符号 (!@#$)", self)
        self.chk_symbol.setChecked(False)

        card_layout.addWidget(self.chk_upper)
        card_layout.addWidget(self.chk_number)
        card_layout.addWidget(self.chk_symbol)
        
        self.v_layout.addWidget(settings_card)

        # --- 结果展示区 ---
        result_layout = QHBoxLayout()
        
        self.result_edit = LineEdit(self)
        self.result_edit.setPlaceholderText("点击生成按钮...")
        self.result_edit.setReadOnly(True) # 只读
        
        self.btn_copy = PushButton(qicon("copy"), "复制", self)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)

        result_layout.addWidget(self.result_edit)
        result_layout.addWidget(self.btn_copy)
        
        self.v_layout.addLayout(result_layout)

        # --- 底部大按钮 ---
        self.btn_gen = PrimaryPushButton(qicon("sync"), "生成新密码", self)
        self.btn_gen.clicked.connect(self.generate_password)
        self.v_layout.addWidget(self.btn_gen)

        self.v_layout.addStretch(1) # 顶上去

        # 初始化生成一次
        self.generate_password()

    def generate_password(self):
        """核心业务逻辑"""
        length = self.slider.value()
        chars = string.ascii_lowercase
        
        if self.chk_upper.isChecked():
            chars += string.ascii_uppercase
        if self.chk_number.isChecked():
            chars += string.digits
        if self.chk_symbol.isChecked():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            self.result_edit.setText("")
            return

        pwd = "".join(random.choice(chars) for _ in range(length))
        self.result_edit.setText(pwd)

    def copy_to_clipboard(self):
        """复制逻辑"""
        text = self.result_edit.text()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            
            # 弹出成功提示
            InfoBar.success(
                title="已复制",
                content="密码已保存到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )`