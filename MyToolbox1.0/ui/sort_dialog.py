from PySide6.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView, QVBoxLayout
from PySide6.QtCore import Qt
from qfluentwidgets import MessageBoxBase, SubtitleLabel, BodyLabel


class ToolOrderDialog(MessageBoxBase):
    """工具排序对话框"""

    def __init__(self, plugins, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("调整工具顺序", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.infoLabel = BodyLabel("拖拽列表项来调整顺序", self)
        self.viewLayout.addWidget(self.infoLabel)

        self.listWidget = QListWidget(self)
        self.listWidget.setDragDropMode(QAbstractItemView.InternalMove)
        self.listWidget.setDefaultDropAction(Qt.MoveAction)
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.setMinimumHeight(300)
        self.listWidget.setMinimumWidth(400)

        for plugin in plugins:
            item = QListWidgetItem(plugin.name)
            self.listWidget.addItem(item)

        self.viewLayout.addWidget(self.listWidget)

        self.yesButton.setText("保存顺序")
        self.cancelButton.setText("取消")

    def get_new_order(self):
        """获取当前列表的文本顺序"""
        order = []
        count = self.listWidget.count()
        for i in range(count):
            item = self.listWidget.item(i)
            # 增加健壮性检查
            if item:
                order.append(item.text())

        print(f"[DEBUG] Dialog 返回顺序: {order}")  # 调试信息
        return order