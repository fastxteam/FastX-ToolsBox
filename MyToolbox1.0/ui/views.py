from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                               QTabWidget, QLabel, QTabBar, QToolButton)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap
from qfluentwidgets import FlowLayout, TitleLabel, FluentIcon, InfoBar, InfoBarPosition
from core.config import ConfigManager
from .gallery_card import ToolCard


# ==========================================
# 1. 首页视图 (画廊展示)
# ==========================================
class HomeView(QWidget):
    """首页：展示工具卡片"""
    tool_selected = Signal(object)  # 左键点击 (默认单例)
    tool_new_tab = Signal(object)  # 右键-新标签页 (强制多开)
    tool_new_window = Signal(object)  # 右键-新窗口

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 滚动区域
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none; background: transparent;}")
        self.main_layout.addWidget(self.scroll)

        # 内容容器
        self.scroll_content = QWidget()
        self.scroll.setWidget(self.scroll_content)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        self.scroll_layout.setSpacing(20)

        # 标题
        self.scroll_layout.addWidget(TitleLabel("工具导航", self))

        # 流式布局 (用于放置卡片)
        self.flow_widget = QWidget()
        self.flow_layout = FlowLayout(self.flow_widget, needAni=True)
        self.flow_layout.setContentsMargins(0, 10, 0, 0)
        self.flow_layout.setVerticalSpacing(20)
        self.flow_layout.setHorizontalSpacing(20)

        # 添加卡片
        for plugin in plugins:
            card = ToolCard(plugin, self.flow_widget)
            # 连接卡片信号
            card.tool_clicked.connect(self.tool_selected)
            card.open_new_tab.connect(self.tool_new_tab)
            card.open_new_window.connect(self.tool_new_window)
            self.flow_layout.addWidget(card)

        self.scroll_layout.addWidget(self.flow_widget)
        self.scroll_layout.addStretch(1)


# ==========================================
# 2. 统一工作台 (核心 Tab 视图)
# ==========================================
class CentralTabWidget(QWidget):
    tool_new_window = Signal(object)

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 创建 TabWidget
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)

        # 样式优化
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border-top: 1px solid #e5e5e5; 
                background: transparent; 
                top: -1px; 
            }
            QTabWidget::tab-bar { 
                left: 8px; 
            }
            QTabBar::tab { 
                height: 36px; 
                padding: 0 16px; 
                border: none; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: #ffffff; 
                border-bottom: 2px solid #009faa; 
            }
            QTabBar::tab:!selected { 
                background: transparent; 
                margin-top: 2px; 
            }
            QTabBar::tab:hover { 
                background: rgba(0,0,0,0.05); 
            }
        """)

        # --- 跟随式 "+" 按钮逻辑 ---
        self.tab_bar = self.tab_widget.tabBar()
        self.add_btn = QToolButton(self.tab_bar)

        self.add_btn.setText("+")
        self.add_btn.setToolTip("新建当前工具标签页")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedSize(32, 32)

        # 设置图标
        if hasattr(FluentIcon, 'ADD'):
            self.add_btn.setIcon(FluentIcon.ADD.icon())

        # 按钮样式
        self.add_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 4px;
                background: transparent;
                color: #555;
                font-size: 16px;
                padding-bottom: 2px;
            }
            QToolButton:hover {
                background-color: rgba(0,0,0,0.1);
            }
        """)

        # 【注意】这里绑定了 duplicate_current_tab，该方法必须在下面定义
        self.add_btn.clicked.connect(self.duplicate_current_tab)

        # 安装事件过滤器
        self.tab_bar.installEventFilter(self)

        self.layout.addWidget(self.tab_widget)

        # 记录单例 Tab {plugin_name: widget}
        self.singleton_tabs = {}

        # --- 初始化首页 ---
        self.home_view = HomeView(plugins, self)

        # 首页信号连接
        self.home_view.tool_selected.connect(lambda p: self.add_tool_tab(p, force_new=False))
        self.home_view.tool_new_tab.connect(lambda p: self.add_tool_tab(p, force_new=True))
        self.home_view.tool_new_window.connect(self.tool_new_window)

        # 添加首页 Tab (索引 0)
        if hasattr(FluentIcon, 'HOME'):
            home_icon = FluentIcon.HOME.icon()
        else:
            home_icon = QIcon()

        self.tab_widget.addTab(self.home_view, home_icon, "首页")
        # 隐藏首页的关闭按钮
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)

        # 连接关闭信号
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

    # ============================================
    # 辅助功能：图标染色
    # ============================================
    def colorize_icon(self, icon_source, color_str):
        """将图标染成指定颜色"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        # 统一获取 QIcon 对象
        if isinstance(icon_source, FluentIcon):
            icon = icon_source.icon()
        elif isinstance(icon_source, str):
            # 如果插件接口返回的是字符串路径
            from core.resource_manager import qicon
            icon = qicon(icon_source)
        else:
            icon = icon_source  # 假设已经是 QIcon

        # ... 后面的绘制代码保持不变 ...
        # 绘制
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        icon.paint(painter, 0, 0, 32, 32)

        # 染色 (SourceIn模式)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setBrush(QColor(color_str))
        painter.setPen(Qt.NoPen)
        painter.drawRect(pixmap.rect())
        painter.end()

        return QIcon(pixmap)

    # ============================================
    # 事件过滤器：动态移动 "+" 按钮
    # ============================================
    def eventFilter(self, obj, event):
        if obj == self.tab_bar:
            if event.type() in [QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Paint]:
                self.move_add_button()
        return super().eventFilter(obj, event)

    def move_add_button(self):
        """计算并移动按钮到最后一个 Tab 右侧"""
        count = self.tab_bar.count()
        if count > 0:
            last_tab_rect = self.tab_bar.tabRect(count - 1)
            # 放在右边 4px 处
            x = last_tab_rect.x() + last_tab_rect.width() + 4
            # 垂直居中
            y = (self.tab_bar.height() - self.add_btn.height()) // 2

            self.add_btn.move(x, y)
            self.add_btn.show()
            self.add_btn.raise_()

    # ============================================
    # 核心逻辑 (你之前报错缺失的就是这个方法)
    # ============================================
    def duplicate_current_tab(self):
        """点击 "+" 号时调用"""
        current_index = self.tab_widget.currentIndex()

        # 如果当前是首页，提示用户
        if current_index == 0:
            InfoBar.info(
                title="提示",
                content="请先选择一个工具，再点击 + 号进行多开。",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        current_widget = self.tab_widget.currentWidget()
        # 获取之前绑定的插件实例
        if hasattr(current_widget, 'plugin_instance'):
            plugin = current_widget.plugin_instance
            # 强制新建 (force_new=True)
            self.add_tool_tab(plugin, force_new=True)

    def add_tool_tab(self, plugin, force_new=False):
        """添加工具 Tab"""
        # 1. 单例检查
        if not force_new:
            if plugin.name in self.singleton_tabs:
                target_widget = self.singleton_tabs[plugin.name]
                self.tab_widget.setCurrentWidget(target_widget)
                return

        # 2. 创建 Widget
        widget = plugin.create_widget()
        widget.setProperty("plugin_name", plugin.name)
        widget.setProperty("is_singleton", not force_new)
        # 绑定插件实例，供 duplicate_current_tab 使用
        widget.plugin_instance = plugin

        # 3. 处理图标并染色
        theme_color = ConfigManager.get_color(plugin)
        colored_icon = self.colorize_icon(plugin.icon, theme_color)

        # 4. 添加 Tab
        index = self.tab_widget.addTab(widget, colored_icon, plugin.name)
        self.tab_widget.setCurrentIndex(index)

        # 5. 记录单例
        if not force_new:
            self.singleton_tabs[plugin.name] = widget

        # 强制更新按钮位置
        self.move_add_button()

    def close_tab(self, index):
        """关闭 Tab"""
        if index == 0: return

        widget = self.tab_widget.widget(index)
        if widget:
            # 清理单例记录
            if widget.property("is_singleton"):
                plugin_name = widget.property("plugin_name")
                if plugin_name in self.singleton_tabs:
                    if self.singleton_tabs[plugin_name] == widget:
                        del self.singleton_tabs[plugin_name]

            self.tab_widget.removeTab(index)
            widget.deleteLater()

        # 强制更新按钮位置
        self.move_add_button()