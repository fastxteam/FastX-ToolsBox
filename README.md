🧰 Python Fluent Toolbox
=======================
一款基于 PySide6 & Fluent-Widgets 的现代化、模块化桌面工具箱，支持多标签页多开、插件热插拔、自定义主题色。

<p align="center">
<img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python Version">
<img src="https://img.shields.io/badge/UI-WinUI%203-0078D4.svg" alt="UI Style">
<img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

📖 简介
-------
Python Fluent Toolbox 是一个高度可扩展的个人工具箱框架。它采用了类似 Edge/Chrome 浏览器的多标签页架构，无论你是开发者、数据分析师还是文字工作者，都可以通过编写简单的 Python 脚本，将自己的脚本转化为带有精美 UI 的原生桌面应用。

✨ 核心特性
------------
- **🎨 极致 UI 体验**: 采用最新的 Fluent Design 设计语言，支持浅色/深色主题自动切换，亚克力磨砂效果
- **📑 浏览器式交互**: 支持多标签页、动态添加、独立窗口
- **🧩 插件化架构**: 新增功能无需修改主程序
- **🛠️ 开发者友好**: 提供标准 PluginInterface 接口和 ResourceManager

🚀 安装指南
-----------
### 前置要求
- Python 3.12 或更高版本

### 步骤
```bash
# 克隆仓库
git clone https://gitee.com/lostsing/MyToolbox.git
cd MyToolbox

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

📦 内置插件
-----------
项目内置了多个高质量的生产力工具：
- **📝 Markdown 笔记**: 支持双栏预览、语法高亮、文件导出
- **🔄 数据转换工坊**: JSON 格式化、Excel 转换、数据库操作
- **📘 软件打包工具**: Python 脚本打包为可执行文件
- **🎨 颜色助手**: 颜色选取、渐变生成、调色板管理
- **📖 批量重命名**: 支持多种重命名规则
- **📏 目录树工具**: 目录结构转换
- **🖼️ 图标浏览器**: 查看和管理图标资源

🔌 插件开发
-----------
想要添加自己的工具？只需 3 步即可集成一个新插件：
```python
# 示例：plugins/my_tool/tool.py
from core.plugin_interface import PluginInterface
from PySide6.QtWidgets import QLabel

class MyPlugin(PluginInterface):
    @property
    def name(self): return "我的新工具"
    @property
    def icon(self): return "rocket" # 自动读取 resources/icons/rocket.svg
    
    def create_widget(self):
        return QLabel("Hello World!")
```

📂 项目结构
-----------
```
MyToolbox/
├── main.py                  # 程序入口
├── core/                    # 核心框架
│   ├── config.py            # 配置管理
│   ├── plugin_interface.py  # 插件接口定义
│   └── resource_manager.py  # 图标资源管理
├── ui/                      # 界面逻辑
│   ├── main_window.py       # 主窗口
│   └── views.py             # 视图与标签页逻辑
├── resources/               # 静态资源
│   └── icons/               # 图标存放处 (.svg/.png)
├── plugins/                 # 插件目录
│   ├── markdown_editor/     # [内置] Markdown 插件
│   └── demo_tool/           # [内置] 数据转换插件
└── config/                  # 用户配置文件 (自动生成)
```

🤝 贡献
-------
欢迎提交 Pull Request 或 Issue！如果你发现 Bug，请提交 Issue。

📄 许可证
---------
本项目采用 MIT 许可证。

🙏 致谢
---------
- UI 框架基于 PyQt-Fluent-Widgets
- 图标资源来自 Fluent System Icons

<div align="center">
Created with ❤️ by YourTeam
</div>