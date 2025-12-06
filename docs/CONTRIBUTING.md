📘 MyToolbox 架构与协作指南 (v2.0)

适用对象：后端工程师、UI 设计师、AI 辅助编程助手
核心目标：解耦开发、统一规范、零崩溃架构
1. 项目全景图 (Project Map)
项目采用 核心(Core) - 界面(UI) - 插件(Plugins) 三层分离架构。
code
Text
MyToolbox/
├── main.py                  # [入口] 程序启动，引导环境
├── config/                  # [数据] 用户配置文件 (自动生成，git忽略)
├── resources/               # [资源] 静态资源库
│   └── icons/               # 🟢 存放 .svg/.png，文件名即索引键
├── core/                    # [后端核心] 系统的"大脑"
│   ├── plugin_interface.py  # ⚠️ 插件契约 (所有插件必须继承)
│   ├── plugin_manager.py    # 插件加载器 (反射机制、排序、过滤)
│   ├── config.py            # 配置管理器 (单例模式，持久化)
│   └── resource_manager.py  # 资源管理器 (图标安全获取，防崩溃)
├── ui/                      # [前端核心] 系统的"脸面"
│   ├── main_window.py       # 主窗口框架
│   ├── views.py             # 首页与工作台逻辑 (Tab页管理)
│   ├── settings_interface.py# 设置页 (插件管理、外观)
│   └── gallery_card.py      # 首页卡片组件
└── plugins/                 # [开发区] 功能插件目录
    ├── batch_rename/        # 示例：复杂 UI + 逻辑插件
    ├── calculator/          # 示例：纯 UI 交互插件
    └── ...                  # 🟢 新插件请在此新建文件夹
2. 核心开发规范 (The Rules)
为了防止 AI 产生幻觉代码，或前后端打架，请严格遵守以下铁律：
🛑 铁律 1：资源安全 (Safe Resource)
严禁硬编码图标路径 (如 "./icons/icon.png")。
严禁直接使用 FluentIcon.SomeName (版本差异会导致崩溃)。
必须使用资源管理器：
code
Python
from core.resource_manager import qicon
# 自动查找 resources/icons/edit.svg，找不到则回退到系统图标
icon = qicon("edit")
🛑 铁律 2：配置原子性 (Atomic Config)
严禁在持有 config 对象很久之后直接 save()，这会覆盖期间其他操作产生的变更。
必须在保存前一刻重新加载：
code
Python
# ✅ 正确写法
def save_changes(self):
    cfg = ConfigManager.load()  # 1. 读最新
    cfg["my_key"] = "new_val"   # 2. 改
    ConfigManager.save(cfg)     # 3. 存
🛑 铁律 3：UI 与 逻辑分离
后端开发：只关注 RenameEngine 这种纯逻辑类，输入数据 -> 处理 -> 返回数据。不要在逻辑类里写 QWidget 代码。
前端开发：Widget 只负责布局和信号连接。耗时操作（如遍历大文件夹）必须使用 QThread 或 QApplication.processEvents()，防止界面卡死。
3. 角色分工指南
👨‍💻 后端/逻辑开发 (Backend Dev)
你的任务：编写插件的“大脑”。
工作目录：plugins/your_tool/logic.py (建议将逻辑拆分)
定义接口：继承 PluginInterface。
数据处理：使用 pandas/sqlite/os 等处理数据。
异常处理：所有可能出错的逻辑（文件IO、网络）必须包裹在 try...except 中，并通过 InfoBar.error 反馈给前端，绝对不能让程序闪退。
🎨 前端/UI 开发 (UI Dev)
你的任务：编写插件的“脸面”。
工作目录：plugins/your_tool/tool.py
组件库：全面使用 qfluentwidgets (PushButton, LineEdit, TableWidget)，保持风格统一。
布局：
左侧/顶部：设置区 (CardWidget 包裹)。
右侧/底部：展示区 (QTableWidget 或 PlainTextEdit)。
交互：
使用 Signal 通信。
复杂状态使用 StateToolTip (如：正在生成...)。
🤖 AI 辅助开发 (Prompting Guide)
如何让 AI 快速生成高质量代码？
请在对话开始时，将以下 Context 发送给 AI：
[System Context for MyToolbox]
你是一个 PySide6 + Fluent-Widgets 专家。我们正在开发一个插件化工具箱。
项目规则：
图标必须使用 from core.resource_manager import qicon，调用 qicon("name")。
弹窗必须使用 InfoBar 或 StateToolTip，禁止使用原生 QMessageBox。
插件入口类必须继承 PluginInterface 并实现 create_widget。
读写配置必须使用 ConfigManager.load() 和 save()。
颜色和主题必须适配 isDarkTheme()。
当前任务：
[描述你要开发的功能]
4. 插件标准模板 (Standard Template)
所有新功能请直接复制此模板开始。
plugins/new_tool/tool.py:
code
Python
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import PrimaryPushButton, SubtitleLabel, InfoBar
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon # 资源管理
from core.config import ConfigManager   # 配置管理

class MyNewPlugin(PluginInterface):
    @property
    def name(self) -> str: return "新工具名称"
    @property
    def icon(self): return qicon("rocket") # 对应 resources/icons/rocket.svg
    @property
    def group(self) -> str: return "开发工具"
    def create_widget(self) -> QWidget: return MyWidget()

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. 标题
        layout.addWidget(SubtitleLabel("你好，世界", self))
        
        # 2. 按钮
        self.btn = PrimaryPushButton(qicon("save"), "点击我", self)
        self.btn.clicked.connect(self.on_click)
        layout.addWidget(self.btn)
        
        layout.addStretch(1)

    def on_click(self):
        # 3. 读取配置示例
        cfg = ConfigManager.load()
        count = cfg.get("click_count", 0) + 1
        
        # 4. 保存配置示例
        cfg["click_count"] = count
        ConfigManager.save(cfg)
        
        # 5. 反馈
        InfoBar.success("成功", f"这是第 {count} 次点击", parent=self)
5. 常见问题排查 (Troubleshooting)
现象	可能原因	解决方案
程序启动报错 AttributeError	FluentIcon 枚举版本不匹配	改用 qicon("图标名")，不要直接调枚举。
配置保存后重启失效	发生了“脏数据覆盖”	检查 save() 前是否调用了 load() 获取最新数据。
拖拽排序无效	Item Flags 未设置	确保设置了 Qt.ItemIsDragEnabled 等标志位。
界面卡死	主线程执行了耗时循环	在循环中加入 QApplication.processEvents() 或使用线程。
右键菜单不显示	策略未设置	检查 setContextMenuPolicy(Qt.CustomContextMenu)。
6. Git 协作流
Main 分支：保持稳定，随时可发布。
Dev 分支：日常开发分支。
Feature 分支：开发新插件时，从 Dev 切出 feature/plugin-name。
提交前：确保 plugins/你的插件/ 下的代码可以独立运行，不依赖其他插件。
合并时：检查 resources/icons 是否上传了新图标。
给团队的建议
后端人员：你可以完全不管 ui/ 文件夹，只专注写好 python 脚本逻辑，然后告诉前端：“我给了你一个函数 process_data(input_file)，你调用它就行。”
前端人员：你可以完全不管 process_data 怎么实现的，你只需要画好界面，点击按钮时调用这个函数，并处理返回结果或报错信息。
AI 助手：把上面的 [System Context] 发给它，它生成的代码准确率将从 60% 提升到 95%。