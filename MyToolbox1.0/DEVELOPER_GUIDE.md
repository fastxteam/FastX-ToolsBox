<h1 id="e80c6791"></h1>
**<font style="color:rgb(26, 28, 30);">欢迎加入 MyToolbox 开发团队！</font>**<font style="color:rgb(26, 28, 30);">  
</font><font style="color:rgb(26, 28, 30);">这是一个基于 Python + PySide6 + Fluent-Widgets 的现代化桌面工具箱平台。本项目旨在提供一个高颜值、可扩展、插件化的生产力工具集合。</font>

**<font style="color:rgb(26, 28, 30);">⚠️</font>****<font style="color:rgb(26, 28, 30);"> v2.0 核心变更</font>**<font style="color:rgb(26, 28, 30);">：移除 QtWebEngine 依赖，采用纯原生渲染；规范了绝对导入路径；明确了全屏与面板类插件的布局差异。</font>

---

<h2 id="986e9df6"><font style="color:rgb(26, 28, 30);">📑</font><font style="color:rgb(26, 28, 30);"> 目录</font></h2>
+ [<font style="color:rgb(36, 131, 226);">快速开始 (Quick Start)</font>](https://www.google.com/url?sa=E&q=#1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
+ [<font style="color:rgb(36, 131, 226);">项目架构 (Architecture)</font>](https://www.google.com/url?sa=E&q=#2-%E9%A1%B9%E7%9B%AE%E6%9E%B6%E6%9E%84)
+ [<font style="color:rgb(36, 131, 226);">核心规范 (Core Rules)</font>](https://www.google.com/url?sa=E&q=#3-%E6%A0%B8%E5%BF%83%E8%A7%84%E8%8C%83-%E2%9A%A0%EF%B8%8F-%E9%87%8D%E8%A6%81)
+ [<font style="color:rgb(36, 131, 226);">UI 布局策略 (Layout Strategies)</font>](https://www.google.com/url?sa=E&q=#4-ui-%E5%B8%83%E5%B1%80%E7%AD%96%E7%95%A5-%F0%9F%8E%A8-%E6%A0%B8%E5%BF%83)
+ [<font style="color:rgb(36, 131, 226);">插件开发指南 (Plugin Guide)</font>](https://www.google.com/url?sa=E&q=#5-%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91%E6%8C%87%E5%8D%97)
+ [<font style="color:rgb(36, 131, 226);">Git 协作规范 (Collaboration)</font>](https://www.google.com/url?sa=E&q=#6-git-%E5%8D%8F%E4%BD%9C%E8%A7%84%E8%8C%83)

---

<h2 id="8050b8ac"><font style="color:rgb(26, 28, 30);">1. 快速开始</font></h2>
<h3 id="64808b1c"><font style="color:rgb(26, 28, 30);">1.1 环境要求</font></h3>
+ **<font style="color:rgb(26, 28, 30);">Python</font>**<font style="color:rgb(26, 28, 30);">: 3.8 ~ 3.11</font>
+ **<font style="color:rgb(26, 28, 30);">OS</font>**<font style="color:rgb(26, 28, 30);">: Windows 10/11 (推荐), macOS, Linux</font>

<h3 id="10582237"><font style="color:rgb(26, 28, 30);">1.2 安装依赖</font></h3>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
# 克隆项目
git clone https://github.com/your-repo/MyToolbox.git
cd MyToolbox

# 1. 安装核心 UI 库
pip install PySide6 "PyQt-Fluent-Widgets[pyside6]"

# 2. 安装通用工具库
pip install pandas openpyxl keyring requests

# 3. 安装渲染与计算库 (Markdown/AI/Color)
pip install markdown pygments matplotlib numpy scikit-learn pillow openai google-genai
```

_<font style="color:rgb(26, 28, 30);">(注：本项目不再依赖</font>__<font style="color:rgb(26, 28, 30);"> </font>__<font style="color:rgb(50, 48, 44);">PySide6-WebEngine</font>__<font style="color:rgb(26, 28, 30);">，以确保界面特效的稳定性)</font>_

<h3 id="5257bffd"><font style="color:rgb(26, 28, 30);">1.3 运行</font></h3>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
python main.py
```

---

<h2 id="6c498eec"><font style="color:rgb(26, 28, 30);">2. 项目架构</font></h2>
<font style="color:rgb(26, 28, 30);">本项目采用</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">微内核 + 插件化</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">架构。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Text</font>**

```plain
MyToolbox/
├── main.py                  # [入口] 程序启动，样式初始化
├── config/                  # [数据] settings.json (自动生成)
├── core/                    # [核心]
│   ├── plugin_interface.py  # 接口契约：所有插件的基类
│   ├── plugin_manager.py    # 加载器：负责反射读取、关键词索引提取
│   ├── resource_manager.py  # 资源管理：qicon() 统一入口
│   └── config.py            # 配置管理：单例模式，防脏写
├── ui/                      # [界面]
│   ├── main_window.py       # 主窗口：Mica 特效容器
│   ├── views.py             # 首页/工作台逻辑
│   ├── settings_interface.py# 设置页
│   └── gallery_card.py      # 卡片组件
└── plugins/                 # [业务] 插件开发区 (独立沙箱)
    ├── color_assistant/     # 范例：复杂 MVC 结构，多页面
    ├── markdown_editor/     # 范例：纯代码控制，自定义绘制
    └── ...
```

---

<h2 id="2e5e8b61"><font style="color:rgb(26, 28, 30);">3. 核心规范 (</font><font style="color:rgb(26, 28, 30);">⚠️</font><font style="color:rgb(26, 28, 30);"> 重要)</font></h2>
<h3 id="7b594111"><font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则一：绝对导入路径</font></h3>
<font style="color:rgb(26, 28, 30);">由于</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">PluginManager</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">动态加载机制的限制，插件内部</font>**<font style="color:rgb(26, 28, 30);">严禁使用相对导入</font>**<font style="color:rgb(26, 28, 30);">（如</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">from . import xxx</font><font style="color:rgb(26, 28, 30);">）。</font><font style="color:rgb(26, 28, 30);">  
</font>**<font style="color:rgb(26, 28, 30);">✅</font>****<font style="color:rgb(26, 28, 30);"> 正确</font>**<font style="color:rgb(26, 28, 30);">：</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
# 必须从根目录 plugins 开始写
from plugins.color_assistant.components.color_wheel import ColorWheel
```

<h3 id="f3d5d8b0"><font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则二：资源安全加载</font></h3>
**<font style="color:rgb(26, 28, 30);">❌</font>****<font style="color:rgb(26, 28, 30);"> 错误</font>**<font style="color:rgb(26, 28, 30);">：直接使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">FluentIcon.SOME_ICON</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(可能因版本差异报错)。</font><font style="color:rgb(26, 28, 30);">  
</font>**<font style="color:rgb(26, 28, 30);">✅</font>****<font style="color:rgb(26, 28, 30);"> 正确</font>**<font style="color:rgb(26, 28, 30);">：使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">qicon</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">或</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">getattr</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">降级保护。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from core.resource_manager import qicon
# 优先找本地 svg -> 找库图标 -> 回退到默认
icon = qicon("edit") 

# 或者
icon = getattr(FluentIcon, 'ROBOT', FluentIcon.PEOPLE)
```

<h3 id="7dcd2c82"><font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则三：禁止 WebEngine</font></h3>
<font style="color:rgb(26, 28, 30);">为了保留主窗口的</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">亚克力/透明 (Mica)</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">特效，项目</font>**<font style="color:rgb(26, 28, 30);">禁止使用</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(50, 48, 44);">QWebEngineView</font>**<font style="color:rgb(26, 28, 30);">。</font><font style="color:rgb(26, 28, 30);">  
</font><font style="color:rgb(26, 28, 30);">WebEngine 会强制接管 OpenGL 上下文，导致其他半透明控件变黑。</font>

+ **<font style="color:rgb(26, 28, 30);">替代方案</font>**<font style="color:rgb(26, 28, 30);">：使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">QTextBrowser</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">+</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">Matplotlib</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(生成图片) +</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">Pygments</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(代码高亮) 实现富文本渲染。</font>

---

<h2 id="1f97e1ef"><font style="color:rgb(26, 28, 30);">4. UI 布局策略 (</font><font style="color:rgb(26, 28, 30);">🎨</font><font style="color:rgb(26, 28, 30);"> 核心)</font></h2>
<font style="color:rgb(26, 28, 30);">为了避免界面出现“黑边”、“背景透黑”等渲染 Bug，针对不同类型的插件，必须采用不同的容器策略：</font>

<h3 id="57027123"><font style="color:rgb(26, 28, 30);">4.1 类型 A：工具面板型 (Dashboard)</font></h3>
**<font style="color:rgb(26, 28, 30);">适用</font>**<font style="color:rgb(26, 28, 30);">：计算器、颜色助手、格式转换。</font><font style="color:rgb(26, 28, 30);">  
</font>**<font style="color:rgb(26, 28, 30);">规范</font>**<font style="color:rgb(26, 28, 30);">：</font>

+ <font style="color:rgb(26, 28, 30);">使用</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(50, 48, 44);">CardWidget</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">作为容器。</font>
+ <font style="color:rgb(26, 28, 30);">利用 CardWidget 自带的圆角、阴影和背景色适配。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
class MyToolWidget(QWidget):
    def init_ui(self):
        # 左侧控制面板使用 CardWidget
        self.left_panel = CardWidget(self) 
        # 右侧展示区使用 CardWidget
        self.right_panel = CardWidget(self)
```

<h3 id="5179a219"><font style="color:rgb(26, 28, 30);">4.2 类型 B：全屏编辑器型 (Full Editor)</font></h3>
**<font style="color:rgb(26, 28, 30);">适用</font>**<font style="color:rgb(26, 28, 30);">：Markdown 笔记、代码编辑器。</font><font style="color:rgb(26, 28, 30);">  
</font>**<font style="color:rgb(26, 28, 30);">规范</font>**<font style="color:rgb(26, 28, 30);">：</font>

+ **<font style="color:rgb(26, 28, 30);">严禁使用</font>****<font style="color:rgb(26, 28, 30);"> </font>****<font style="color:rgb(50, 48, 44);">CardWidget</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(会导致双重边框和边距问题)。</font>
+ <font style="color:rgb(26, 28, 30);">直接继承</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">QWidget</font><font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">必须显式硬编码背景色</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(适配深/浅模式)，不能依赖</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">transparent</font><font style="color:rgb(26, 28, 30);">，否则会透出主窗口底色导致变黑。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from qfluentwidgets import isDarkTheme

class MyEditor(QWidget):
    def __init__(self):
        super().__init__()
        # 必须手动处理背景，确保无黑边
        bg = "#1e1e1e" if isDarkTheme() else "#ffffff"
        self.setStyleSheet(f"background-color: {bg};")
```

---

<h2 id="2e76871e"><font style="color:rgb(26, 28, 30);">5. 插件开发指南</font></h2>
<h3 id="3eb7f4e5"><font style="color:rgb(26, 28, 30);">5.1 标准目录结构</font></h3>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Text</font>**

```plain
plugins/my_tool/
├── __init__.py          # 必须有
├── tool.py              # 入口：定义 Plugin 类和 主 Widget
├── services.py          # 逻辑：数据处理、API 请求
├── components/          # 组件：自定义 UI 控件
└── pages/               # 页面：如果插件很复杂，拆分多页
```

<h3 id="fdd86e77"><font style="color:rgb(26, 28, 30);">5.2 插件定义 (</font><font style="color:rgb(50, 48, 44);">tool.py</font><font style="color:rgb(26, 28, 30);">)</font></h3>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon
from PySide6.QtWidgets import QWidget

class MyPlugin(PluginInterface):
    @property
    def name(self) -> str: return "工具名称"
    @property
    def icon(self): return qicon("tool_icon") 
    @property
    def group(self) -> str: return "开发工具"
    @property
    def description(self) -> str: return "一句话描述功能"
    
    # 【可选】定义搜索关键词，方便用户在首页搜索
    @property
    def keywords(self) -> list: return ["转换", "格式", "json"]

    def create_widget(self) -> QWidget:
        return MyWidget()
```

<h3 id="76aaf19f"><font style="color:rgb(26, 28, 30);">5.3 数据持久化</font></h3>
<font style="color:rgb(26, 28, 30);">使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">ConfigManager</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">进行配置读写，支持</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">keyring</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">存储敏感信息（如 API Key）。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from core.config import ConfigManager
import keyring

# 普通配置
config = ConfigManager.load()
config["last_tab"] = 1
ConfigManager.save(config)

# 敏感信息 (API Key)
keyring.set_password("PythonFluentToolbox", "my_api_key", "sk-xxx")
```

---

<h2 id="ec886056"><font style="color:rgb(26, 28, 30);">6. Git 协作规范</font></h2>
+ **<font style="color:rgb(26, 28, 30);">不要提交</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(50, 48, 44);">config/settings.json</font>
    - <font style="color:rgb(50, 48, 44);">config/color_favorites.json</font>
    - <font style="color:rgb(50, 48, 44);">__pycache__/</font>
+ **<font style="color:rgb(26, 28, 30);">提交前检查</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(26, 28, 30);">运行</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">main.py</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">确保无报错。</font>
    - <font style="color:rgb(26, 28, 30);">确认</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">import</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">路径已改为绝对路径。</font>
    - <font style="color:rgb(26, 28, 30);">如果是新插件，确保图标已放入</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">resources/icons</font><font style="color:rgb(26, 28, 30);">。</font>

---

**<font style="color:rgb(26, 28, 30);">Design for Performance</font>**<font style="color:rgb(26, 28, 30);">: 我们的目标是启动速度 < 1s。请避免在插件 </font><font style="color:rgb(50, 48, 44);">__init__</font><font style="color:rgb(26, 28, 30);"> 中进行耗时操作（如加载大文件、网络请求），请使用 </font><font style="color:rgb(50, 48, 44);">QTimer.singleShot(0, self.init_heavy_task)</font><font style="color:rgb(26, 28, 30);"> 延迟加载。</font>

