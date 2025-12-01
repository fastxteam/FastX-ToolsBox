from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentIconBase


class PluginInterface(ABC):
    """所有工具插件必须继承的基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @property
    @abstractmethod
    def icon(self) -> FluentIconBase | str:
        """插件图标"""
        pass

    @property
    @abstractmethod
    def group(self) -> str:
        """插件分组"""
        pass

    @property
    def description(self) -> str:
        """插件描述"""
        return "暂无描述"

    @property
    def theme_color(self) -> str:
        """
        【新增】插件默认主题色 (Hex 格式)
        默认为青色，子类可以重写此属性
        """
        return "#009faa"

    @abstractmethod
    def create_widget(self) -> QWidget:
        """返回插件的主界面 Widget"""
        pass