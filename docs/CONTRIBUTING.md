**<font style="color:rgb(26, 28, 30);">欢迎加入 MyToolbox 开发团队！</font>**<font style="color:rgb(26, 28, 30);">  
这是一个基于 Python + PySide6 + Fluent-Widgets 的现代化桌面工具箱平台。本项目旨在提供一个高颜值、可扩展、插件化的生产力工具集合。</font>

---

## <font style="color:rgb(26, 28, 30);">📑</font><font style="color:rgb(26, 28, 30);"> 目录</font>
+ [<font style="color:rgb(36, 131, 226);">快速开始 (Quick Start)</font>](https://www.google.com/url?sa=E&q=#1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B)
+ [<font style="color:rgb(36, 131, 226);">项目架构 (Architecture)</font>](https://www.google.com/url?sa=E&q=#2-%E9%A1%B9%E7%9B%AE%E6%9E%B6%E6%9E%84)
+ [<font style="color:rgb(36, 131, 226);">核心规范 (Core Rules)</font>](https://www.google.com/url?sa=E&q=#3-%E6%A0%B8%E5%BF%83%E8%A7%84%E8%8C%83-%E2%9A%A0%EF%B8%8F-%E9%87%8D%E8%A6%81)
+ [<font style="color:rgb(36, 131, 226);">插件开发指南 (Plugin Guide)</font>](https://www.google.com/url?sa=E&q=#4-%E6%8F%92%E4%BB%B6%E5%BC%80%E5%8F%91%E6%8C%87%E5%8D%97)
+ [<font style="color:rgb(36, 131, 226);">UI 开发最佳实践 (UI Best Practices)</font>](https://www.google.com/url?sa=E&q=#5-ui-%E5%BC%80%E5%8F%91%E6%9C%80%E4%BD%B3%E5%AE%9E%E8%B7%B5)
+ [<font style="color:rgb(36, 131, 226);">Git 协作规范 (Collaboration)</font>](https://www.google.com/url?sa=E&q=#6-git-%E5%8D%8F%E4%BD%9C%E8%A7%84%E8%8C%83)

---

## <font style="color:rgb(26, 28, 30);">1. 快速开始</font>
### <font style="color:rgb(26, 28, 30);">1.1 环境要求</font>
+ **<font style="color:rgb(26, 28, 30);">Python</font>**<font style="color:rgb(26, 28, 30);">: 3.8 ~ 3.11 (推荐 3.10)</font>
+ **<font style="color:rgb(26, 28, 30);">OS</font>**<font style="color:rgb(26, 28, 30);">: Windows 10/11 (macOS/Linux 可运行但部分 Fluent 特效可能降级)</font>

### <font style="color:rgb(26, 28, 30);">1.2 安装依赖</font>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
# 克隆项目
git clone https://github.com/your-repo/MyToolbox.git
cd MyToolbox

# 安装核心依赖
pip install PySide6 "PyQt-Fluent-Widgets[pyside6]"

# 安装插件依赖 (按需)
pip install pandas openpyxl markdown pygments numpy scikit-learn pillow openai google-genai keyring
```

### <font style="color:rgb(26, 28, 30);">1.3 运行</font>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Bash</font>**

```plain
python main.py
```

---

## <font style="color:rgb(26, 28, 30);">2. 项目架构</font>
<font style="color:rgb(26, 28, 30);">本项目采用</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">微内核 + 插件化</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">架构，核心层与业务层完全解耦。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Text</font>**

```plain
MyToolbox/
├── main.py                  # [入口] 程序启动引导
├── config/                  # [数据] 用户配置文件 (自动生成，勿提交到Git)
├── resources/               # [资源] 静态资源库
│   └── icons/               # 🟢 存放图标 (.svg/.png)
├── core/                    # [核心] 系统底层逻辑
│   ├── plugin_interface.py  # 接口契约：所有插件必须继承此类
│   ├── plugin_manager.py    # 插件加载器：负责扫描、排序、加载插件
│   ├── config.py            # 配置管理：单例模式，负责读写 settings.json
│   └── resource_manager.py  # 资源管理：负责安全加载图标，防止崩坏
├── ui/                      # [界面] 主框架逻辑
│   ├── main_window.py       # 主窗口容器
│   ├── views.py             # 首页与工作台逻辑
│   ├── settings_interface.py# 设置中心
│   └── gallery_card.py      # 首页卡片组件
└── plugins/                 # [业务] 插件开发区
    ├── color_assistant/     # 示例：复杂多页面插件 (MVC结构)
    ├── calculator/          # 示例：单页面插件
    └── ...                  # 👉 你的新插件放在这里
```

---

## <font style="color:rgb(26, 28, 30);">3. 核心规范 (</font><font style="color:rgb(26, 28, 30);">⚠️</font><font style="color:rgb(26, 28, 30);"> 重要)</font>
<font style="color:rgb(26, 28, 30);">为了保证系统的稳定性，所有开发者必须遵守以下铁律：</font>

### <font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则一：严禁硬编码资源路径</font>
<font style="color:rgb(26, 28, 30);">❌</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">错误</font>**<font style="color:rgb(26, 28, 30);">：</font><font style="color:rgb(50, 48, 44);">QIcon("./icons/my_icon.png")</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">(打包后绝对报错)</font><font style="color:rgb(26, 28, 30);">  
</font><font style="color:rgb(26, 28, 30);">✅</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">正确</font>**<font style="color:rgb(26, 28, 30);">：使用资源管理器，支持自动回退和查找。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from core.resource_manager import qicon
icon = qicon("my_icon") # 自动查找 my_icon.svg/.png，找不到则返回默认图标
```

### <font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则二：严禁阻塞主线程</font>
<font style="color:rgb(26, 28, 30);">任何耗时操作（网络请求、大文件 IO、复杂计算）</font>**<font style="color:rgb(26, 28, 30);">必须</font>**<font style="color:rgb(26, 28, 30);">放到子线程中。</font>

+ **<font style="color:rgb(26, 28, 30);">网络请求</font>**<font style="color:rgb(26, 28, 30);">：使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">threading</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">或</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">QThread</font><font style="color:rgb(26, 28, 30);">。</font>
+ **<font style="color:rgb(26, 28, 30);">UI 反馈</font>**<font style="color:rgb(26, 28, 30);">：使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">Signal</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">将结果传回主线程更新 UI。</font>

### <font style="color:rgb(26, 28, 30);">🛑</font><font style="color:rgb(26, 28, 30);"> 规则三：配置读写原子性</font>
<font style="color:rgb(26, 28, 30);">❌</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">错误</font>**<font style="color:rgb(26, 28, 30);">：持有</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">config</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">对象太久，最后</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">save()</font><font style="color:rgb(26, 28, 30);">。这会覆盖期间其他插件的修改。</font><font style="color:rgb(26, 28, 30);">  
</font><font style="color:rgb(26, 28, 30);">✅</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">正确</font>**<font style="color:rgb(26, 28, 30);">：在保存的前一刻</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">load()</font><font style="color:rgb(26, 28, 30);">，修改后立即</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">save()</font><font style="color:rgb(26, 28, 30);">。</font>

**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
def save_setting(self):
    cfg = ConfigManager.load() # 1. 读最新
    cfg["my_key"] = "new_val"  # 2. 改
    ConfigManager.save(cfg)    # 3. 存
```

---

## <font style="color:rgb(26, 28, 30);">4. 插件开发指南</font>
### <font style="color:rgb(26, 28, 30);">4.1 创建插件结构</font>
<font style="color:rgb(26, 28, 30);">在</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">plugins/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">下新建文件夹（如</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">my_tool</font><font style="color:rgb(26, 28, 30);">），必须包含</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">__init__.py</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">和</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">tool.py</font><font style="color:rgb(26, 28, 30);">。</font>

### <font style="color:rgb(26, 28, 30);">4.2 实现接口 (</font><font style="color:rgb(50, 48, 44);">tool.py</font><font style="color:rgb(26, 28, 30);">)</font>
**<font style="color:rgb(93, 93, 95);">code</font>****<font style="color:rgb(28, 27, 27);">Python</font>**

```plain
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import PrimaryPushButton, SubtitleLabel
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon

class MyPlugin(PluginInterface):
    @property
    def name(self) -> str: return "我的工具"
    @property
    def icon(self): return qicon("rocket") 
    @property
    def group(self) -> str: return "办公工具"
    @property
    def description(self) -> str: return "这是我的第一个插件"
    
    def create_widget(self) -> QWidget:
        return MyWidget()

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(SubtitleLabel("Hello World", self))
        layout.addWidget(PrimaryPushButton("点击", self))
```

### <font style="color:rgb(26, 28, 30);">4.3 复杂插件建议 (MVC)</font>
<font style="color:rgb(26, 28, 30);">如果插件逻辑复杂，请拆分文件：</font>

+ <font style="color:rgb(50, 48, 44);">tool.py</font><font style="color:rgb(26, 28, 30);">: 只负责插件定义和入口。</font>
+ <font style="color:rgb(50, 48, 44);">pages.py</font><font style="color:rgb(26, 28, 30);">: 存放 UI 界面代码。</font>
+ <font style="color:rgb(50, 48, 44);">logic.py</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">services.py</font><font style="color:rgb(26, 28, 30);">: 存放纯 Python 业务逻辑（无 UI）。</font>
+ <font style="color:rgb(50, 48, 44);">components/</font><font style="color:rgb(26, 28, 30);">: 存放自定义的小组件。</font>

---

## <font style="color:rgb(26, 28, 30);">5. UI 开发最佳实践</font>
<font style="color:rgb(26, 28, 30);">本项目全面使用</font><font style="color:rgb(26, 28, 30);"> </font>**<font style="color:rgb(26, 28, 30);">PyQt-Fluent-Widgets</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">库，请勿混用原生 Qt 丑陋控件。</font>

| **<font style="color:rgb(26, 28, 30);">原生控件</font>** | **<font style="color:rgb(26, 28, 30);">推荐替代品</font>** | **<font style="color:rgb(26, 28, 30);">优势</font>** |
| --- | --- | --- |
| <font style="color:rgb(50, 48, 44);">QPushButton</font> | <font style="color:rgb(50, 48, 44);">PrimaryPushButton</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">PushButton</font> | <font style="color:rgb(26, 28, 30);">自带圆角、动画、主题适配</font> |
| <font style="color:rgb(50, 48, 44);">QLineEdit</font> | <font style="color:rgb(50, 48, 44);">LineEdit</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">SearchLineEdit</font> | <font style="color:rgb(26, 28, 30);">下划线动效、圆角</font> |
| <font style="color:rgb(50, 48, 44);">QLabel</font> | <font style="color:rgb(50, 48, 44);">TitleLabel</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">BodyLabel</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">CaptionLabel</font> | <font style="color:rgb(26, 28, 30);">统一的字体规范和层级</font> |
| <font style="color:rgb(50, 48, 44);">QComboBox</font> | <font style="color:rgb(50, 48, 44);">ComboBox</font> | <font style="color:rgb(26, 28, 30);">现代化的下拉菜单样式</font> |
| <font style="color:rgb(50, 48, 44);">QMessageBox</font> | <font style="color:rgb(50, 48, 44);">MessageBox</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">/</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">InfoBar</font> | <font style="color:rgb(50, 48, 44);">InfoBar</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">是非模态通知，体验更好</font> |
| <font style="color:rgb(50, 48, 44);">QFrame</font> | <font style="color:rgb(50, 48, 44);">CardWidget</font> | <font style="color:rgb(26, 28, 30);">自带阴影和圆角的卡片容器</font> |


### <font style="color:rgb(26, 28, 30);">布局技巧</font>
+ **<font style="color:rgb(26, 28, 30);">卡片式布局</font>**<font style="color:rgb(26, 28, 30);">：将相关功能包裹在</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">CardWidget</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">中，提升层级感。</font>
+ **<font style="color:rgb(26, 28, 30);">流式布局</font>**<font style="color:rgb(26, 28, 30);">：使用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">FlowLayout</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">来排列不固定数量的卡片或标签。</font>
+ **<font style="color:rgb(26, 28, 30);">弹簧占位</font>**<font style="color:rgb(26, 28, 30);">：善用</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">addStretch(1)</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">把控件顶到顶部或左侧，防止分散。</font>

---

## <font style="color:rgb(26, 28, 30);">6. Git 协作规范</font>
+ **<font style="color:rgb(26, 28, 30);">分支管理</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(50, 48, 44);">main</font><font style="color:rgb(26, 28, 30);">: 稳定发布版 (只读)。</font>
    - <font style="color:rgb(50, 48, 44);">dev</font><font style="color:rgb(26, 28, 30);">: 日常开发主分支。</font>
    - <font style="color:rgb(50, 48, 44);">feature/xxx</font><font style="color:rgb(26, 28, 30);">: 新功能分支 (从 dev 切出)。</font>
+ **<font style="color:rgb(26, 28, 30);">提交信息 (Commit Message)</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - <font style="color:rgb(50, 48, 44);">feat: 新增 xx 功能</font>
    - <font style="color:rgb(50, 48, 44);">fix: 修复 xx bug</font>
    - <font style="color:rgb(50, 48, 44);">ui: 优化 xx 界面</font>
    - <font style="color:rgb(50, 48, 44);">refactor: 重构 xx 代码</font>
+ **<font style="color:rgb(26, 28, 30);">注意事项</font>**<font style="color:rgb(26, 28, 30);">：</font>
    - **<font style="color:rgb(26, 28, 30);">不要提交</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">config/settings.json</font><font style="color:rgb(26, 28, 30);">（已在 .gitignore 中）。</font>
    - **<font style="color:rgb(26, 28, 30);">不要提交</font>**<font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">__pycache__</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">或</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">.idea</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">文件夹。</font>
    - <font style="color:rgb(26, 28, 30);">提交前请运行</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(50, 48, 44);">main.py</font><font style="color:rgb(26, 28, 30);"> </font><font style="color:rgb(26, 28, 30);">确保无报错。</font>

---

<font style="color:rgb(26, 28, 30);">  
</font>

