import json
import sqlite3
import pandas as pd
from io import StringIO

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QFileDialog, QFrame, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from qfluentwidgets import (PlainTextEdit, PrimaryPushButton, PushButton,
                            FluentIcon, SegmentedWidget, InfoBar,
                            ComboBox, LineEdit, SubtitleLabel, BodyLabel)
from core.plugin_interface import PluginInterface
from core.config import ConfigManager
from core.resource_manager import qicon

# ==========================================
# 1. 插件入口
# ==========================================
class TextProcessorPlugin(PluginInterface):
    @property
    def name(self) -> str: return "数据转换工坊"

    @property
    def icon(self):
        # 尝试获取 Convert，如果没有就用 EDIT
        return qicon("Convert")

    @property
    def group(self) -> str: return "开发工具"

    @property
    def theme_color(self) -> str: return "#673AB7"  # 深紫色

    @property
    def description(self) -> str: return "JSON格式化、Excel转换、数据库导出等多功能数据处理工具。"

    def create_widget(self) -> QWidget: return DataConverterWidget()


# ==========================================
# 2. 主界面 Widget
# ==========================================
class DataConverterWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(20, 20, 20, 20)
        self.v_layout.setSpacing(20)

        # --- 顶部导航栏 ---
        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("json", "JSON 助手")
        self.pivot.addItem("excel", "Excel 工具")
        self.pivot.addItem("sql", "数据库工具")
        self.pivot.setCurrentItem("json")

        self.v_layout.addWidget(self.pivot)

        # --- 多页面容器 ---
        self.stacked_widget = QStackedWidget(self)
        self.v_layout.addWidget(self.stacked_widget)

        # 初始化子页面
        self.page_json = JsonPage(self)
        self.page_excel = ExcelPage(self)
        self.page_sql = SqlPage(self)

        self.stacked_widget.addWidget(self.page_json)
        self.stacked_widget.addWidget(self.page_excel)
        self.stacked_widget.addWidget(self.page_sql)

        # 信号连接
        self.pivot.currentItemChanged.connect(
            lambda k: self.stacked_widget.setCurrentIndex(["json", "excel", "sql"].index(k))
        )


# ==========================================
# 3. 子页面：JSON 助手
# ==========================================
class JsonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 左侧输入
        left_widget = QWidget()
        l_layout = QVBoxLayout(left_widget)
        l_layout.addWidget(SubtitleLabel("输入内容", self))
        self.input_edit = PlainTextEdit(self)
        self.input_edit.setPlaceholderText("在此粘贴 JSON 字符串或 Python 字典...")
        l_layout.addWidget(self.input_edit)

        # 操作栏
        action_layout = QHBoxLayout()

        # 【核心修复】安全获取图标
        # 优先 ACCEPT (勾号)，保底 ADD (加号，绝对存在)
        icon_accept = getattr(FluentIcon, 'ACCEPT', FluentIcon.ADD)
        # 优先 SYNC (同步)，保底 EDIT (编辑，绝对存在)
        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.EDIT)

        self.btn_format = PrimaryPushButton(icon_accept, "格式化", self)
        self.btn_compress = PushButton(icon_sync, "压缩", self)

        action_layout.addWidget(self.btn_format)
        action_layout.addWidget(self.btn_compress)
        l_layout.addLayout(action_layout)

        # 右侧输出
        right_widget = QWidget()
        r_layout = QVBoxLayout(right_widget)
        r_layout.addWidget(SubtitleLabel("转换结果", self))
        self.output_edit = PlainTextEdit(self)
        self.output_edit.setReadOnly(True)
        r_layout.addWidget(self.output_edit)

        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        # 逻辑连接
        self.btn_format.clicked.connect(lambda: self.process_json(indent=4))
        self.btn_compress.clicked.connect(lambda: self.process_json(indent=None))

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
# 4. 子页面：Excel 工具
# ==========================================
class ExcelPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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

        # 安全获取图标
        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.EDIT)
        self.btn_convert = PrimaryPushButton(icon_sync, "转换为 JSON 数组", self)
        top_layout.addWidget(self.btn_convert)

        layout.addWidget(top_frame)

        layout.addWidget(BodyLabel("预览结果:", self))
        self.result_view = PlainTextEdit(self)
        layout.addWidget(self.result_view)

        self.btn_select.clicked.connect(self.select_file)
        self.btn_convert.clicked.connect(self.convert_excel)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择表格", "", "Excel/CSV (*.xlsx *.xls *.csv)")
        if path:
            self.path_edit.setText(path)

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

            json_str = df.to_json(orient='records', force_ascii=False, indent=4)
            self.result_view.setPlainText(json_str)
            InfoBar.success("转换成功", f"共处理 {len(df)} 行数据", parent=self.window())
        except Exception as e:
            InfoBar.error("转换失败", str(e), parent=self.window())


# ==========================================
# 5. 子页面：数据库工具
# ==========================================
class SqlPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 区域1
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

        # 区域2
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
        self.sql_edit.setPlaceholderText("在此输入 SQL 语句，例如: SELECT * FROM users LIMIT 10")
        self.sql_edit.setFixedHeight(80)

        # 安全获取图标
        icon_search = getattr(FluentIcon, 'SEARCH', FluentIcon.EDIT)
        self.btn_query = PrimaryPushButton(icon_search, "查询并导出 JSON", self)

        l2.addLayout(h3)
        l2.addWidget(self.sql_edit)
        l2.addWidget(self.btn_query)
        layout.addWidget(card2)

        layout.addStretch(1)

        # 逻辑连接
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
            InfoBar.success("成功", f"已将数据导入到 {table} 表中", parent=self.window())
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

            save_path, _ = QFileDialog.getSaveFileName(self, "保存 JSON", "export.json", "JSON (*.json)")
            if save_path:
                df.to_json(save_path, orient='records', force_ascii=False, indent=4)
                InfoBar.success("导出成功", f"已保存到 {save_path}", parent=self.window())
        except Exception as e:
            InfoBar.error("查询失败", str(e), parent=self.window())