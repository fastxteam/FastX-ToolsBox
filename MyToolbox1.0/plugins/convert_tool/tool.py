import json
import sqlite3
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QFileDialog, QFrame, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard

from qfluentwidgets import (PlainTextEdit, PrimaryPushButton, PushButton,
                            FluentIcon, SegmentedWidget, InfoBar,
                            LineEdit, SubtitleLabel, BodyLabel, TransparentToolButton,
                            ToolTipFilter, ToolTipPosition)
from core.plugin_interface import PluginInterface
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon

# ==========================================
# 1. 插件入口
# ==========================================
class TextProcessorPlugin(PluginInterface):
    @property
    def name(self) -> str: return "数据转换工坊"

    @property
    def icon(self):
        # 安全获取 SYNC 图标
        return qicon("Convert")

    @property
    def group(self) -> str: return "开发工具"

    @property
    def theme_color(self) -> str: return "#673AB7"

    @property
    def description(self) -> str: return "JSON/Excel/SQL 多功能数据转换工具"

    def create_widget(self) -> QWidget: return DataConverterWidget()


# ==========================================
# 2. 主界面 Widget
# ==========================================
class DataConverterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(20, 20, 20, 20)
        self.v_layout.setSpacing(15)

        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("json", "JSON 助手")
        self.pivot.addItem("excel", "Excel 工具")
        self.pivot.addItem("sql", "数据库工具")
        self.pivot.setCurrentItem("json")
        self.v_layout.addWidget(self.pivot)

        self.stacked_widget = QStackedWidget(self)
        self.v_layout.addWidget(self.stacked_widget)

        self.page_json = JsonPage(self)
        self.page_excel = ExcelPage(self)
        self.page_sql = SqlPage(self)

        self.stacked_widget.addWidget(self.page_json)
        self.stacked_widget.addWidget(self.page_excel)
        self.stacked_widget.addWidget(self.page_sql)

        self.pivot.currentItemChanged.connect(
            lambda k: self.stacked_widget.setCurrentIndex(["json", "excel", "sql"].index(k))
        )


# ==========================================
# 3. 子页面：JSON 助手 (增强版)
# ==========================================
class JsonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # --- 左侧：输入区域 ---
        left_widget = QWidget()
        l_layout = QVBoxLayout(left_widget)
        l_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧工具栏
        l_tool_layout = QHBoxLayout()
        l_tool_layout.addWidget(SubtitleLabel("输入内容", self))
        l_tool_layout.addStretch(1)

        self.btn_load = self.create_tool_btn("FOLDER", "加载文件", self.load_file)
        self.btn_paste = self.create_tool_btn("PASTE", "粘贴", self.paste_input)
        self.btn_clear_in = self.create_tool_btn("DELETE", "清空", lambda: self.input_edit.clear())

        l_tool_layout.addWidget(self.btn_load)
        l_tool_layout.addWidget(self.btn_paste)
        l_tool_layout.addWidget(self.btn_clear_in)
        l_layout.addLayout(l_tool_layout)

        self.input_edit = PlainTextEdit(self)
        self.input_edit.setPlaceholderText("在此粘贴 JSON 字符串或 Python 字典...")
        l_layout.addWidget(self.input_edit)

        # 底部操作按钮
        action_layout = QHBoxLayout()
        icon_accept = getattr(FluentIcon, 'ACCEPT', FluentIcon.ADD)
        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.EDIT)

        self.btn_format = PrimaryPushButton(icon_accept, "格式化", self)
        self.btn_compress = PushButton(icon_sync, "压缩", self)

        action_layout.addWidget(self.btn_format)
        action_layout.addWidget(self.btn_compress)
        l_layout.addLayout(action_layout)

        # --- 右侧：输出区域 ---
        right_widget = QWidget()
        r_layout = QVBoxLayout(right_widget)
        r_layout.setContentsMargins(0, 0, 0, 0)

        # 右侧工具栏
        r_tool_layout = QHBoxLayout()
        r_tool_layout.addWidget(SubtitleLabel("转换结果", self))
        r_tool_layout.addStretch(1)

        self.btn_copy = self.create_tool_btn("COPY", "复制结果", self.copy_output)
        self.btn_save = self.create_tool_btn("SAVE", "导出文件", self.save_output)

        r_tool_layout.addWidget(self.btn_copy)
        r_tool_layout.addWidget(self.btn_save)
        r_layout.addLayout(r_tool_layout)

        self.output_edit = PlainTextEdit(self)
        self.output_edit.setReadOnly(True)
        r_layout.addWidget(self.output_edit)

        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        # 逻辑连接
        self.btn_format.clicked.connect(lambda: self.process_json(indent=4))
        self.btn_compress.clicked.connect(lambda: self.process_json(indent=None))

    def create_tool_btn(self, icon_name, tooltip, slot):
        # 安全获取图标，包含回退逻辑
        icon = getattr(FluentIcon, icon_name, None)
        if not icon:
            # 简单的回退映射
            fallback = {
                "PASTE": getattr(FluentIcon, 'EDIT', FluentIcon.ADD),
                "COPY": getattr(FluentIcon, 'DOCUMENT', FluentIcon.ADD),
                "DELETE": FluentIcon.CLOSE
            }
            icon = fallback.get(icon_name, FluentIcon.ADD)

        btn = TransparentToolButton(icon, self)
        btn.setToolTip(tooltip)
        btn.installEventFilter(ToolTipFilter(btn, showDelay=300, position=ToolTipPosition.BOTTOM))
        btn.clicked.connect(slot)
        return btn

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载 JSON", "", "JSON/Text (*.json *.txt);;All (*.*)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.input_edit.setPlainText(f.read())
            except Exception as e:
                InfoBar.error("错误", f"读取失败: {e}", parent=self.window())

    def paste_input(self):
        text = QApplication.clipboard().text()
        if text: self.input_edit.setPlainText(text)

    def copy_output(self):
        text = self.output_edit.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success("成功", "结果已复制到剪贴板", parent=self.window())

    def save_output(self):
        text = self.output_edit.toPlainText()
        if not text: return
        path, _ = QFileDialog.getSaveFileName(self, "导出 JSON", "result.json", "JSON (*.json)")
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                InfoBar.success("成功", "文件已保存", parent=self.window())
            except Exception as e:
                InfoBar.error("错误", f"保存失败: {e}", parent=self.window())

    def process_json(self, indent):
        text = self.input_edit.toPlainText()
        if not text: return
        try:
            try:
                data = json.loads(text)
            except:
                import ast
                try:
                    data = ast.literal_eval(text)
                except:
                    data = eval(text)

            result = json.dumps(data, indent=indent, ensure_ascii=False)
            self.output_edit.setPlainText(result)
            InfoBar.success("成功", "转换完成", parent=self.window())
        except Exception as e:
            InfoBar.error("解析错误", str(e), parent=self.window())


# ==========================================
# 4. 子页面：Excel 工具 (增强版)
# ==========================================
class ExcelPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- 顶部操作区 ---
        top_frame = QFrame(self)
        top_frame.setObjectName("Card")
        top_layout = QVBoxLayout(top_frame)

        top_layout.addWidget(SubtitleLabel("Excel 转 JSON", self))

        file_layout = QHBoxLayout()
        self.path_edit = LineEdit(self)
        self.path_edit.setPlaceholderText("请选择 .xlsx / .csv 文件")
        self.btn_select = PushButton(FluentIcon.FOLDER, "选择文件", self)
        file_layout.addWidget(self.path_edit)
        file_layout.addWidget(self.btn_select)
        top_layout.addLayout(file_layout)

        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.EDIT)
        self.btn_convert = PrimaryPushButton(icon_sync, "转换为 JSON 数组", self)
        top_layout.addWidget(self.btn_convert)

        layout.addWidget(top_frame)

        # --- 结果预览区 ---
        # 增加标题栏和操作按钮
        res_header = QHBoxLayout()
        res_header.addWidget(BodyLabel("预览结果:", self))
        res_header.addStretch(1)

        self.btn_copy = self.create_tool_btn("COPY", "复制结果", self.copy_output)
        self.btn_save = self.create_tool_btn("SAVE", "导出 JSON", self.save_output)

        res_header.addWidget(self.btn_copy)
        res_header.addWidget(self.btn_save)
        layout.addLayout(res_header)

        self.result_view = PlainTextEdit(self)
        layout.addWidget(self.result_view)

        self.btn_select.clicked.connect(self.select_file)
        self.btn_convert.clicked.connect(self.convert_excel)

    def create_tool_btn(self, icon_name, tooltip, slot):
        icon = getattr(FluentIcon, icon_name, None)
        if not icon:
            icon = FluentIcon.ADD  # Fallback
        btn = TransparentToolButton(icon, self)
        btn.setToolTip(tooltip)
        btn.clicked.connect(slot)
        return btn

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择表格", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if path: self.path_edit.setText(path)

    def convert_excel(self):
        path = self.path_edit.text()
        if not path:
            InfoBar.warning("提示", "请先选择文件", parent=self.window())
            return

        try:
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)

            # 转为 JSON 字符串
            json_str = df.to_json(orient='records', force_ascii=False, indent=4)
            self.result_view.setPlainText(json_str)
            InfoBar.success("转换成功", f"共处理 {len(df)} 行数据", parent=self.window())
        except Exception as e:
            InfoBar.error("转换失败", str(e), parent=self.window())

    def copy_output(self):
        text = self.result_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            InfoBar.success("成功", "已复制到剪贴板", parent=self.window())

    def save_output(self):
        text = self.result_view.toPlainText()
        if not text: return
        path, _ = QFileDialog.getSaveFileName(self, "保存 JSON", "data.json", "JSON (*.json)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            InfoBar.success("成功", f"已保存到 {path}", parent=self.window())


# ==========================================
# 5. 子页面：数据库工具 (保持不变，已通过测试)
# ==========================================
class SqlPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card1 = QFrame(self)
        card1.setStyleSheet("QFrame{border: 1px solid #e0e0e0; border-radius: 8px; background: transparent;}")
        l1 = QVBoxLayout(card1)
        l1.addWidget(SubtitleLabel("Excel 导入 SQLite", self))

        h1 = QHBoxLayout()
        self.excel_path = LineEdit()
        self.excel_path.setPlaceholderText("Excel 文件路径")
        self.btn_excel_sel = PushButton(FluentIcon.FOLDER, "浏览", self)
        h1.addWidget(self.excel_path)
        h1.addWidget(self.btn_excel_sel)

        h2 = QHBoxLayout()
        self.db_path_1 = LineEdit()
        self.db_path_1.setPlaceholderText("目标数据库路径 (例如 data.db)")
        self.table_name = LineEdit()
        self.table_name.setPlaceholderText("表名 (例如 users)")
        self.btn_import = PrimaryPushButton("导入数据库", self)
        h2.addWidget(self.db_path_1)
        h2.addWidget(self.table_name)
        h2.addWidget(self.btn_import)

        l1.addLayout(h1)
        l1.addLayout(h2)
        layout.addWidget(card1)

        card2 = QFrame(self)
        card2.setStyleSheet("QFrame{border: 1px solid #e0e0e0; border-radius: 8px; background: transparent;}")
        l2 = QVBoxLayout(card2)
        l2.addWidget(SubtitleLabel("数据库查询转 JSON", self))

        h3 = QHBoxLayout()
        self.db_path_2 = LineEdit()
        self.db_path_2.setPlaceholderText("源数据库路径")
        self.btn_db_sel = PushButton(FluentIcon.FOLDER, "浏览", self)
        h3.addWidget(self.db_path_2)
        h3.addWidget(self.btn_db_sel)

        self.sql_edit = PlainTextEdit()
        self.sql_edit.setPlaceholderText("SQL 语句 (例如: SELECT * FROM users LIMIT 10)")
        self.sql_edit.setFixedHeight(80)

        icon_search = getattr(FluentIcon, 'SEARCH', FluentIcon.EDIT)
        self.btn_query = PrimaryPushButton(icon_search, "查询并导出 JSON", self)

        l2.addLayout(h3)
        l2.addWidget(self.sql_edit)
        l2.addWidget(self.btn_query)
        layout.addWidget(card2)

        layout.addStretch(1)

        self.btn_excel_sel.clicked.connect(lambda: self.sel_file(self.excel_path, "Excel (*.xlsx *.csv)"))
        self.btn_db_sel.clicked.connect(lambda: self.sel_file(self.db_path_2, "DB (*.db *.sqlite)"))
        self.btn_import.clicked.connect(self.import_to_db)
        self.btn_query.clicked.connect(self.query_to_json)

    def sel_file(self, line_edit, filt):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", filt)
        if path: line_edit.setText(path)

    def import_to_db(self):
        excel = self.excel_path.text()
        db = self.db_path_1.text()
        table = self.table_name.text()
        if not (excel and db and table):
            InfoBar.warning("缺少参数", "请填写完整路径和表名", parent=self.window())
            return
        try:
            if excel.endswith('.csv'):
                df = pd.read_csv(excel)
            else:
                df = pd.read_excel(excel)
            conn = sqlite3.connect(db)
            df.to_sql(table, conn, if_exists='replace', index=False)
            conn.close()
            InfoBar.success("成功", f"已导入到表: {table}", parent=self.window())
        except Exception as e:
            InfoBar.error("导入失败", str(e), parent=self.window())

    def query_to_json(self):
        db = self.db_path_2.text()
        sql = self.sql_edit.toPlainText()
        if not (db and sql):
            InfoBar.warning("缺少参数", "请选择数据库并输入 SQL", parent=self.window())
            return
        try:
            conn = sqlite3.connect(db)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            path, _ = QFileDialog.getSaveFileName(self, "保存 JSON", "export.json", "JSON (*.json)")
            if path:
                df.to_json(path, orient='records', force_ascii=False, indent=4)
                InfoBar.success("导出成功", f"已保存到 {path}", parent=self.window())
        except Exception as e:
            InfoBar.error("查询失败", str(e), parent=self.window())