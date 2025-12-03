import math
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QSizePolicy, QListWidget, QListWidgetItem, QFrame, QSplitter)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QKeyEvent, QColor

from qfluentwidgets import (PushButton, PrimaryPushButton, ToolButton,
                            FluentIcon, isDarkTheme, InfoBar, CardWidget,
                            TransparentToolButton, SubtitleLabel, BodyLabel)
from core.plugin_interface import PluginInterface
from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


# ==========================================
# 1. 插件定义
# ==========================================
class CalculatorPlugin(PluginInterface):
    @property
    def name(self) -> str: return "科学计算器"

    @property
    def icon(self):
        return qicon("calculator")

    @property
    def group(self) -> str: return "办公工具"

    @property
    def theme_color(self) -> str: return "#E81123"

    @property
    def description(self) -> str: return "支持历史记录与键盘输入的现代计算器。"

    def create_widget(self) -> QWidget: return CalculatorWidget()


# ==========================================
# 2. 历史记录项
# ==========================================
class HistoryItem(QWidget):
    def __init__(self, expression, result, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_expr = QLabel(expression, self)
        self.lbl_expr.setAlignment(Qt.AlignRight)
        self.lbl_expr.setStyleSheet("color: gray; font-size: 12px;")

        # 结果显示也要带千位分隔符
        self.lbl_result = BodyLabel(result, self)
        self.lbl_result.setAlignment(Qt.AlignRight)
        font = self.lbl_result.font()
        font.setBold(True)
        font.setPixelSize(16)
        self.lbl_result.setFont(font)

        layout.addWidget(self.lbl_expr)
        layout.addWidget(self.lbl_result)


# ==========================================
# 3. 计算器主界面
# ==========================================
class CalculatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.current_val = "0"
        self.expression = []
        self.is_result_shown = False

        self.h_layout = QHBoxLayout(self)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.h_layout.setSpacing(10)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(2)
        split_col = "#333" if isDarkTheme() else "#e0e0e0"
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {split_col}; }}")

        self.calc_panel = QWidget()
        self.init_calc_ui()

        self.history_panel = QWidget()
        self.init_history_ui()

        self.splitter.addWidget(self.calc_panel)
        self.splitter.addWidget(self.history_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        self.h_layout.addWidget(self.splitter)
        self.setFocusPolicy(Qt.StrongFocus)

    def init_calc_ui(self):
        layout = QVBoxLayout(self.calc_panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        display_card = CardWidget(self.calc_panel)
        d_layout = QVBoxLayout(display_card)
        d_layout.setContentsMargins(15, 10, 15, 10)

        self.history_label = QLabel("", self)
        self.history_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.history_label.setStyleSheet("color: gray; font-size: 14px;")
        self.history_label.setFixedHeight(24)

        self.display_label = QLabel("0", self)
        self.display_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        text_color = "white" if isDarkTheme() else "#202020"
        self.display_label.setStyleSheet(
            f"color: {text_color}; font-size: 48px; font-weight: bold; font-family: 'Segoe UI', sans-serif;")
        self.display_label.setFixedHeight(64)

        d_layout.addWidget(self.history_label)
        d_layout.addWidget(self.display_label)
        layout.addWidget(display_card)

        grid = QGridLayout()
        grid.setSpacing(8)

        buttons = [
            ('%', 0, 0, 'func', None), ('CE', 0, 1, 'func', None), ('C', 0, 2, 'func', None), ('⌫', 0, 3, 'func', None),
            ('¹/x', 1, 0, 'sci', None), ('x²', 1, 1, 'sci', None), ('√x', 1, 2, 'sci', None), ('÷', 1, 3, 'op', '/'),
            ('7', 2, 0, 'num', None), ('8', 2, 1, 'num', None), ('9', 2, 2, 'num', None), ('×', 2, 3, 'op', '*'),
            ('4', 3, 0, 'num', None), ('5', 3, 1, 'num', None), ('6', 3, 2, 'num', None), ('-', 3, 3, 'op', '-'),
            ('1', 4, 0, 'num', None), ('2', 4, 1, 'num', None), ('3', 4, 2, 'num', None), ('+', 4, 3, 'op', '+'),
            ('+/-', 5, 0, 'sci', None), ('0', 5, 1, 'num', None), ('.', 5, 2, 'num', None), ('=', 5, 3, 'eq', None),
        ]

        try:
            theme_col = self.window().config_data.get('theme_color', '#009faa')
        except:
            theme_col = '#009faa'

        for text, r, c, type_, val in buttons:
            if type_ == 'eq':
                btn = PrimaryPushButton(text, self.calc_panel)
                btn.setStyleSheet(f"""
                    QPushButton {{ font-size: 20px; font-weight: bold; border-radius: 8px; background-color: {theme_col}; }}
                """)
            else:
                btn = PushButton(text, self.calc_panel)
                bg_color = "transparent"
                if type_ in ['num']:
                    font_size = 20;
                    weight = "bold"
                    if not isDarkTheme(): bg_color = "#f9f9f9"
                else:
                    font_size = 16;
                    weight = "normal"
                    if not isDarkTheme(): bg_color = "#f0f0f0"

                border_col = '#333' if isDarkTheme() else '#e0e0e0'
                hover_col = '#3a3a3a' if isDarkTheme() else '#eaeaea'

                btn.setStyleSheet(f"""
                    QPushButton {{ font-size: {font_size}px; font-weight: {weight}; border-radius: 8px; background-color: {bg_color}; border: 1px solid {border_col}; }}
                    QPushButton:hover {{ background-color: {hover_col}; }}
                """)

            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda ch=False, t=text, tp=type_, v=val: self.on_btn_click(t, tp, v))
            grid.addWidget(btn, r, c)

        layout.addLayout(grid)
        layout.setStretch(1, 1)

    def init_history_ui(self):
        layout = QVBoxLayout(self.history_panel)
        layout.setContentsMargins(0, 20, 20, 20)

        h_layout = QHBoxLayout()
        h_layout.addWidget(SubtitleLabel("历史记录", self.history_panel))
        h_layout.addStretch(1)

        icon_clear = getattr(FluentIcon, 'DELETE', FluentIcon.CLOSE)

        btn_clear = TransparentToolButton(icon_clear, self)
        btn_clear.setToolTip("清空历史")
        btn_clear.clicked.connect(self.clear_history)
        h_layout.addWidget(btn_clear)

        layout.addLayout(h_layout)

        self.history_list = QListWidget(self.history_panel)
        self.history_list.setFrameShape(QListWidget.NoFrame)
        self.history_list.setStyleSheet("background: transparent;")
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.itemClicked.connect(self.on_history_clicked)

        layout.addWidget(self.history_list)

        self.empty_label = QLabel("尚无历史记录", self.history_panel)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: gray;")
        layout.addWidget(self.empty_label)
        self.empty_label.hide()
        self.check_history_empty()

    # ==========================
    # 核心：格式化数字 (解决科学计数法问题)
    # ==========================
    def format_number(self, value):
        """将数字转换为字符串，智能处理科学计数法"""
        try:
            # 如果已经是 Error，直接返回
            if "Error" in str(value): return str(value)

            f = float(value)

            # 1. 检查是否为整数 (例如 79006544.0)
            if f.is_integer():
                # 如果数字太大(超过16位)，还是用科学计数法，否则显示完整整数
                if abs(f) > 1e16:
                    return f"{f:.6e}"
                else:
                    return f"{int(f)}"

            # 2. 小数处理
            # 如果绝对值非常小 (小于 1e-6) 且不为0，用科学计数法
            if 0 < abs(f) < 1e-6:
                return f"{f:.6e}"

            # 否则，保留最多10位小数，并去除末尾的0
            s = f"{f:.10f}".rstrip('0').rstrip('.')
            return s
        except:
            return "Error"

    def format_display_text(self, text):
        """为显示添加千位分隔符"""
        if "Error" in text or "inf" in text: return text

        # 处理负号
        is_negative = text.startswith('-')
        clean_text = text[1:] if is_negative else text

        parts = clean_text.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else ""

        # 仅对整数部分添加逗号
        try:
            # 防止空字符串报错
            if not integer_part: integer_part = "0"
            formatted_int = "{:,}".format(int(integer_part))
        except:
            formatted_int = integer_part

        result = formatted_int
        if len(parts) > 1:
            result += "." + decimal_part
        elif text.endswith('.'):
            result += "."

        return "-" + result if is_negative else result

    # ==========================
    # 逻辑处理
    # ==========================
    def on_btn_click(self, text, type_, val_override=None):
        self.setFocus()
        val = val_override if val_override else text
        if type_ == 'num':
            self.handle_number(text)
        elif type_ == 'op':
            self.handle_operator(text, val)
        elif type_ == 'eq':
            self.calculate_result()
        elif type_ == 'func':
            self.handle_func(text)
        elif type_ == 'sci':
            self.handle_scientific(text)

    def handle_number(self, text):
        if self.is_result_shown:
            self.current_val = "0";
            self.is_result_shown = False;
            self.history_label.setText("");
            self.expression = []
        if text == '.':
            if '.' not in self.current_val: self.current_val += text
        else:
            if self.current_val == "0":
                self.current_val = text
            else:
                self.current_val += text
        self.update_display()

    def handle_operator(self, text, val):
        if self.is_result_shown: self.expression = [self.current_val]; self.is_result_shown = False
        if not self.current_val and self.expression:
            self.expression[-1] = val
        else:
            self.expression.append(self.current_val); self.expression.append(val)
        self.current_val = "";
        self.update_history_label()

    def handle_func(self, text):
        if text == 'C':
            self.current_val = "0"; self.expression = []; self.history_label.setText("")
        elif text == 'CE':
            self.current_val = "0"
        elif text == '⌫':
            if not self.is_result_shown:
                if len(self.current_val) > 1:
                    self.current_val = self.current_val[:-1]
                else:
                    self.current_val = "0"
        elif text == '%':
            try:
                self.current_val = self.format_number(float(self.current_val) / 100)
            except:
                pass
        self.update_display()

    def handle_scientific(self, text):
        try:
            val = float(self.current_val)
            expr_str = ""
            res = 0
            if text == '¹/x':
                if val == 0: raise ZeroDivisionError
                res = 1 / val;
                expr_str = f"1/({self.format_display_text(self.current_val)})"
            elif text == 'x²':
                res = val ** 2;
                expr_str = f"sqr({self.format_display_text(self.current_val)})"
            elif text == '√x':
                if val < 0: raise ValueError
                res = math.sqrt(val);
                expr_str = f"√({self.format_display_text(self.current_val)})"
            elif text == '+/-':
                res = -val;
                expr_str = f"neg({self.format_display_text(self.current_val)})"

            # 使用新的格式化函数
            self.current_val = self.format_number(res)
            self.is_result_shown = True

            if expr_str:
                self.add_to_history_list(expr_str + " =", self.format_display_text(self.current_val))
        except:
            self.current_val = "Error"
        self.update_display()

    def calculate_result(self):
        if not self.expression and not self.current_val: return
        final_expr = self.expression + [self.current_val]

        # 显示用的字符串 (带逗号)
        display_parts = []
        for p in final_expr:
            if p in ['+', '-', '*', '/']:
                p_map = {'*': '×', '/': '÷'}
                display_parts.append(p_map.get(p, p))
            else:
                display_parts.append(self.format_display_text(p))
        display_str = " ".join(display_parts) + " ="

        eval_str = "".join(final_expr)
        try:
            res = eval(eval_str)
            # 使用新的格式化函数
            res_str = self.format_number(res)

            # 添加历史记录
            self.add_to_history_list(display_str, self.format_display_text(res_str))

            self.current_val = res_str
            self.expression = [];
            self.is_result_shown = True;
            self.history_label.setText("")
        except:
            self.current_val = "Error"; self.is_result_shown = True
        self.update_display()

    def update_display(self):
        # 1. 获取带逗号的显示文本
        formatted_text = self.format_display_text(self.current_val)

        # 2. 动态调整字体大小 (防止数字过长溢出)
        length = len(formatted_text)
        if length > 20:
            font_size = 24
        elif length > 14:
            font_size = 32
        elif length > 10:
            font_size = 40
        else:
            font_size = 48

        # 更新样式表
        current_style = self.display_label.styleSheet()
        # 替换 font-size
        import re
        new_style = re.sub(r'font-size: \d+px', f'font-size: {font_size}px', current_style)
        self.display_label.setStyleSheet(new_style)

        self.display_label.setText(formatted_text)

    def update_history_label(self):
        disp = []
        for item in self.expression:
            if item == '*':
                disp.append('×')
            elif item == '/':
                disp.append('÷')
            else:
                # 运算符之间的数字也要加逗号
                disp.append(self.format_display_text(item))
        self.history_label.setText(" ".join(disp))

    def add_to_history_list(self, expr, result):
        item_widget = HistoryItem(expr, result)
        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self.history_list.insertItem(0, item)
        self.history_list.setItemWidget(item, item_widget)
        self.check_history_empty()

    def clear_history(self):
        self.history_list.clear(); self.check_history_empty()

    def check_history_empty(self):
        is_empty = self.history_list.count() == 0
        self.empty_label.setVisible(is_empty);
        self.history_list.setVisible(not is_empty)

    def on_history_clicked(self, item):
        widget = self.history_list.itemWidget(item)
        if widget:
            # 还原去掉逗号的纯数字
            raw_text = widget.lbl_result.text().replace(',', '')
            self.current_val = raw_text
            self.update_display()
            self.is_result_shown = True

    def keyPressEvent(self, event: QKeyEvent):
        k = event.key();
        t = event.text()
        if Qt.Key_0 <= k <= Qt.Key_9:
            self.handle_number(t)
        elif k == Qt.Key_Period:
            self.handle_number('.')
        elif k == Qt.Key_Plus:
            self.handle_operator('+', '+')
        elif k == Qt.Key_Minus:
            self.handle_operator('-', '-')
        elif k == Qt.Key_Asterisk or t == '*':
            self.handle_operator('×', '*')
        elif k == Qt.Key_Slash or t == '/':
            self.handle_operator('÷', '/')
        elif k in [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Equal]:
            self.calculate_result()
        elif k == Qt.Key_Backspace:
            self.handle_func('⌫')
        elif k == Qt.Key_Escape:
            self.handle_func('C')
        super().keyPressEvent(event)