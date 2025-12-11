import os
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QScrollArea,
                               QTabWidget, QLabel, QTabBar, QToolButton, QHBoxLayout)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QIcon, QPainter, QColor, QPixmap
from qfluentwidgets import FlowLayout, TitleLabel, FluentIcon, InfoBar, InfoBarPosition, SearchLineEdit
from core.config import ConfigManager
from .gallery_card import ToolCard


class HomeView(QWidget):
    tool_selected = Signal(object)
    tool_new_tab = Signal(object)
    tool_new_window = Signal(object)

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.current_plugins = plugins
        self.bg_pixmap = None

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 【核心修复1】ScrollArea 全透明
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        # 移除边框，背景透明
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll.viewport().setStyleSheet("background: transparent;")
        # 强制属性透明
        self.scroll.setAttribute(Qt.WA_TranslucentBackground)
        self.scroll.viewport().setAttribute(Qt.WA_TranslucentBackground)

        self.main_layout.addWidget(self.scroll)

        self.scroll_content = QWidget()
        self.scroll_content.setAttribute(Qt.WA_TranslucentBackground)
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.scroll_content)

        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(30, 30, 30, 30)
        self.scroll_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header_layout.addWidget(TitleLabel("工具导航", self))
        header_layout.addStretch(1)

        self.search_edit = SearchLineEdit(self)
        self.search_edit.setPlaceholderText("搜索工具...")
        self.search_edit.setFixedWidth(260)
        self.search_edit.textChanged.connect(self.filter_cards)
        header_layout.addWidget(self.search_edit)

        self.scroll_layout.addLayout(header_layout)

        self.flow_widget = QWidget()
        self.flow_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.flow_widget.setStyleSheet("background: transparent;")

        self.flow_layout = FlowLayout(self.flow_widget, needAni=True)
        self.flow_layout.setContentsMargins(0, 10, 0, 0)
        self.flow_layout.setVerticalSpacing(20)
        self.flow_layout.setHorizontalSpacing(20)

        self.scroll_layout.addWidget(self.flow_widget)
        self.scroll_layout.addStretch(1)

        self.render_cards(plugins)
        self.load_background()

    def load_background(self):
        config = ConfigManager.load()
        rel_path = config.get("background_image", "")
        if not rel_path:
            self.bg_pixmap = None;
            self.update();
            return

        if os.path.exists(rel_path):
            self.bg_pixmap = QPixmap(rel_path)
        else:
            project_root = Path(__file__).resolve().parent.parent
            abs_path = project_root / rel_path
            if abs_path.exists():
                self.bg_pixmap = QPixmap(str(abs_path))
            else:
                self.bg_pixmap = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            scaled = self.bg_pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)

    def render_cards(self, plugins):
        self.flow_layout.removeAllWidgets()
        for child in self.flow_widget.children():
            if isinstance(child, ToolCard): child.deleteLater()

        for plugin in plugins:
            card = ToolCard(plugin, self.flow_widget)
            card.tool_clicked.connect(self.tool_selected)
            card.open_new_tab.connect(self.tool_new_tab)
            card.open_new_window.connect(self.tool_new_window)

            search_pool = [plugin.name.lower()]
            if hasattr(plugin, 'description'): search_pool.append(plugin.description.lower())
            if hasattr(plugin, 'group'): search_pool.append(plugin.group.lower())
            if hasattr(plugin, 'keywords'): search_pool.extend([k.lower() for k in plugin.keywords])
            if hasattr(plugin, 'dynamic_tags'): search_pool.extend(plugin.dynamic_tags)
            card.search_index = " ".join(search_pool)
            self.flow_layout.addWidget(card)

    def filter_cards(self, text):
        query = text.lower().strip();
        query_parts = query.split()
        for i in range(self.flow_layout.count()):
            item = self.flow_layout.itemAt(i);
            widget = item.widget()
            if isinstance(widget, ToolCard):
                index_text = getattr(widget, 'search_index', '')
                is_match = all(part in index_text for part in query_parts)
                if is_match:
                    widget.show()
                else:
                    widget.hide()


class CentralTabWidget(QWidget):
    tool_new_window = Signal(object)

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        # 【核心修复2】主容器透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setAttribute(Qt.WA_TranslucentBackground)

        # 【核心修复3】QTabWidget 样式强制透明
        self.tab_widget.setStyleSheet("""
            QTabWidget { background: transparent; border: none; }
            QTabWidget::pane { 
                border-top: 1px solid rgba(0,0,0,0.1); 
                background: transparent; 
                top: -1px; 
            }
            QTabWidget::tab-bar { left: 8px; }
            QTabBar::tab { 
                height: 36px; 
                padding: 0 16px; 
                border: none; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px; 
                margin-right: 2px;
                background: transparent; 
            }
            QTabBar::tab:selected { 
                background: rgba(255, 255, 255, 0.9); 
                border-bottom: 2px solid #009faa; 
            }
            QTabBar::tab:!selected:hover { 
                background: rgba(255, 255, 255, 0.1); 
            }
        """)

        self.tab_bar = self.tab_widget.tabBar()
        self.add_btn = QToolButton(self.tab_bar)
        self.add_btn.setText("+")
        self.add_btn.setToolTip("新建当前工具标签页")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedSize(32, 32)
        if hasattr(FluentIcon, 'ADD'): self.add_btn.setIcon(FluentIcon.ADD.icon())
        self.add_btn.setStyleSheet("""
            QToolButton { border: none; border-radius: 4px; background: transparent; color: #555; font-size: 16px; padding-bottom: 2px; }
            QToolButton:hover { background-color: rgba(0,0,0,0.1); }
        """)
        self.add_btn.clicked.connect(self.duplicate_current_tab)
        self.tab_bar.installEventFilter(self)

        self.layout.addWidget(self.tab_widget)
        self.singleton_tabs = {}

        self.home_view = HomeView(plugins, self)
        self.home_view.tool_selected.connect(lambda p: self.add_tool_tab(p, force_new=False))
        self.home_view.tool_new_tab.connect(lambda p: self.add_tool_tab(p, force_new=True))
        self.home_view.tool_new_window.connect(self.tool_new_window)

        icon_home = getattr(FluentIcon, 'HOME', None)
        if not icon_home:
            icon_home = getattr(FluentIcon, 'TILES', FluentIcon.EDIT).icon()
        else:
            icon_home = icon_home.icon()

        self.tab_widget.addTab(self.home_view, icon_home, "首页")
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

    def colorize_icon(self, icon_source, color_str):
        pixmap = QPixmap(32, 32);
        pixmap.fill(Qt.transparent)
        if isinstance(icon_source, FluentIcon):
            icon = icon_source.icon()
        elif isinstance(icon_source, str):
            from core.resource_manager import qicon; icon = qicon(icon_source)
        else:
            icon = icon_source
        painter = QPainter(pixmap);
        painter.setRenderHint(QPainter.Antialiasing);
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        icon.paint(painter, 0, 0, 32, 32)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.setBrush(QColor(color_str));
        painter.setPen(Qt.NoPen);
        painter.drawRect(pixmap.rect());
        painter.end()
        return QIcon(pixmap)

    def eventFilter(self, obj, event):
        if obj == self.tab_bar:
            if event.type() in [QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Paint]: self.move_add_button()
        return super().eventFilter(obj, event)

    def move_add_button(self):
        count = self.tab_bar.count()
        if count > 0:
            last_tab_rect = self.tab_bar.tabRect(count - 1)
            x = last_tab_rect.x() + last_tab_rect.width() + 4
            y = (self.tab_bar.height() - self.add_btn.height()) // 2
            self.add_btn.move(x, y);
            self.add_btn.show();
            self.add_btn.raise_()

    def duplicate_current_tab(self):
        current_index = self.tab_widget.currentIndex()
        if current_index == 0: InfoBar.info("提示", "请先选择一个工具，再点击 + 号进行多开。", parent=self); return
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'plugin_instance'):
            plugin = current_widget.plugin_instance
            self.add_tool_tab(plugin, force_new=True)

    def add_tool_tab(self, plugin, force_new=False):
        if not force_new:
            if plugin.name in self.singleton_tabs:
                target_widget = self.singleton_tabs[plugin.name]
                self.tab_widget.setCurrentWidget(target_widget);
                return
        widget = plugin.create_widget()
        # 【核心修复4】确保插件 Widget 背景也透明 (如果它自己没设)
        widget.setAttribute(Qt.WA_TranslucentBackground)
        widget.setProperty("plugin_name", plugin.name)
        widget.setProperty("is_singleton", not force_new)
        widget.plugin_instance = plugin
        theme_color = ConfigManager.get_color(plugin)
        colored_icon = self.colorize_icon(plugin.icon, theme_color)
        index = self.tab_widget.addTab(widget, colored_icon, plugin.name)
        self.tab_widget.setCurrentIndex(index)
        if not force_new: self.singleton_tabs[plugin.name] = widget
        self.move_add_button()

    def close_tab(self, index):
        if index == 0: return
        widget = self.tab_widget.widget(index)
        if widget:
            if widget.property("is_singleton"):
                plugin_name = widget.property("plugin_name")
                if plugin_name in self.singleton_tabs:
                    if self.singleton_tabs[plugin_name] == widget: del self.singleton_tabs[plugin_name]
            self.tab_widget.removeTab(index);
            widget.deleteLater()
        self.move_add_button()