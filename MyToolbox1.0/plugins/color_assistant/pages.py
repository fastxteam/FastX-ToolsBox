import sys
import math
import random
import json
import threading
import requests
import keyring
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QApplication, QDialog,
                               QGraphicsDropShadowEffect, QFormLayout, QFileDialog, QMenu)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer
from PySide6.QtGui import (QColor, QPainter, QBrush, QPen, QConicalGradient,
                           QRadialGradient, QCursor, QPixmap, QScreen, QLinearGradient, QClipboard, QAction)

from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, LineEdit,
                            PrimaryPushButton, PushButton, TransparentToolButton, FluentIcon,
                            InfoBar, Slider, ToolButton, FlowLayout, SubtitleLabel,
                            ColorPickerButton, ComboBox)

from plugins.color_assistant.color_data import TRADITIONAL_COLORS, UI_PALETTES
from core.resource_manager import qicon
from core.config import ConfigManager

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# ==========================================
# 0. 辅助控件
# ==========================================
class ColorBlock(QFrame):
    """【新增】可交互的色块组件"""

    def __init__(self, hex_code, name, parent=None):
        super().__init__(parent)
        self.hex_code = hex_code
        self.name = name
        self.setFixedSize(110, 90)
        self.setCursor(Qt.PointingHandCursor)

        # 布局
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(0)

        # 上半部分：颜色预览 (空 Frame，靠样式表上色)
        # 我们用一个 stretch 把文字挤到底部
        self.v_layout.addStretch(1)

        # 下半部分：文字标签
        self.lbl_name = QLabel(f"{name}\n{hex_code}", self)
        self.lbl_name.setAlignment(Qt.AlignCenter)
        self.lbl_name.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.95);
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            color: #333;
            font-size: 11px;
            padding: 4px;
        """)
        self.v_layout.addWidget(self.lbl_name)

        # 初始样式
        self.update_style(hover=False)

    def update_style(self, hover=False):
        border = "2px solid #009faa" if hover else "1px solid #e0e0e0"
        self.setStyleSheet(f"""
            ColorBlock {{
                background-color: {self.hex_code};
                border-radius: 8px;
                border: {border};
            }}
        """)

    def enterEvent(self, event):
        self.update_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(hover=False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.copy_hex()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(f"复制 HEX: {self.hex_code}").triggered.connect(self.copy_hex)

        c = QColor(self.hex_code)
        rgb = f"rgb({c.red()}, {c.green()}, {c.blue()})"
        menu.addAction(f"复制 RGB: {rgb}").triggered.connect(lambda: self.copy_text(rgb))

        menu.exec(event.globalPos())

    def copy_hex(self):
        self.copy_text(self.hex_code)

    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        InfoBar.success(
            title="已复制",
            content=f"{self.name} {text}",
            parent=self.window(),
            duration=1500
        )

class ScreenColorPicker(QDialog):
    colorSelected = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.pixmap = QApplication.primaryScreen().grabWindow(0)
        self.resize(self.pixmap.size())
        self.showFullScreen()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x, y = event.pos().x(), event.pos().y()
            dpr = self.devicePixelRatio()
            color = self.pixmap.toImage().pixelColor(int(x * dpr), int(y * dpr))
            self.colorSelected.emit(color);
            self.accept()
        else:
            self.reject()

    def paintEvent(self, event):
        p = QPainter(self);
        p.drawPixmap(0, 0, self.pixmap);
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))


class ColorWheel(QWidget):
    colorChanged = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self.hue = 0.0;
        self.saturation = 0.0;
        self.value = 1.0
        self.picker_pos = QPoint(110, 110);
        self.is_dragging = False

    def set_value(self, v):
        self.value = v / 255.0; self.update()

    def set_color(self, color):
        h, s, v, _ = color.getHsvF()
        self.hue = h if h != -1 else 0;
        self.saturation = s;
        self.value = v
        self.update_picker_pos();
        self.update()

    def update_picker_pos(self):
        r = (self.width() / 2) - 10
        angle = self.hue * 2 * math.pi
        dist = self.saturation * r
        cx, cy = self.width() / 2, self.height() / 2
        self.picker_pos = QPoint(int(cx + dist * math.cos(angle)), int(cy - dist * math.sin(angle)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.is_dragging = True; self.handle_mouse(e.pos())

    def mouseMoveEvent(self, e):
        if self.is_dragging: self.handle_mouse(e.pos())

    def mouseReleaseEvent(self, e):
        self.is_dragging = False

    def handle_mouse(self, pos):
        cx, cy = self.width() / 2, self.height() / 2
        dx = pos.x() - cx;
        dy = cy - pos.y()
        dist = math.sqrt(dx * dx + dy * dy);
        max_dist = cx - 10
        if dist > max_dist: ratio = max_dist / dist; dx *= ratio; dy *= ratio; dist = max_dist
        self.picker_pos = QPoint(int(cx + dx), int(cy - dy))
        angle = math.atan2(dy, dx)
        if angle < 0: angle += 2 * math.pi
        self.hue = angle / (2 * math.pi);
        self.saturation = dist / max_dist
        self.emit_color();
        self.update()

    def emit_color(self):
        self.colorChanged.emit(QColor.fromHsvF(self.hue, self.saturation, self.value))

    def paintEvent(self, event):
        p = QPainter(self);
        p.setRenderHint(QPainter.Antialiasing)
        r = (self.width() / 2) - 10;
        center = QPoint(self.width() // 2, self.height() // 2)
        conical = QConicalGradient(center, 0)
        for i, c in enumerate([Qt.red, Qt.magenta, Qt.blue, Qt.cyan, Qt.green, Qt.yellow, Qt.red]):
            conical.setColorAt(i / 6, c)
        p.setBrush(QBrush(conical));
        p.setPen(Qt.NoPen);
        p.drawEllipse(center, r, r)
        radial = QRadialGradient(center, r);
        radial.setColorAt(0, QColor(255, 255, 255, 255));
        radial.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(radial));
        p.drawEllipse(center, r, r)
        p.setPen(QPen(Qt.white, 2));
        p.setBrush(Qt.NoBrush);
        p.drawEllipse(self.picker_pos, 6, 6)
        p.setPen(QPen(Qt.black, 1));
        p.drawEllipse(self.picker_pos, 7, 7)


class ApiConfigDialog(QDialog):
    SERVICE_NAME = "PythonFluentToolbox"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("大模型 API 配置")
        self.resize(400, 200)
        layout = QVBoxLayout(self);
        form = QFormLayout()
        self.url_edit = LineEdit(self);
        self.url_edit.setPlaceholderText("https://api.deepseek.com")
        self.key_edit = LineEdit(self);
        self.key_edit.setEchoMode(LineEdit.Password);
        self.key_edit.setPlaceholderText("sk-xxxxxxxx")
        self.model_edit = LineEdit(self);
        self.model_edit.setPlaceholderText("deepseek-chat")

        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})
        self.url_edit.setText(ai_conf.get("base_url", "https://api.deepseek.com"))
        self.model_edit.setText(ai_conf.get("model", "deepseek-chat"))

        try:
            saved_key = keyring.get_password(self.SERVICE_NAME, "api_key")
            if saved_key: self.key_edit.setText(saved_key)
        except:
            pass

        form.addRow("Base URL:", self.url_edit);
        form.addRow("API Key:", self.key_edit);
        form.addRow("Model:", self.model_edit)
        layout.addLayout(form)
        tip = BodyLabel("提示：DeepSeek用户请填写 'https://api.deepseek.com' 和 'deepseek-chat'", self)
        tip.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(tip)

        btn_box = QHBoxLayout();
        btn_save = PrimaryPushButton("保存", self)
        btn_save.clicked.connect(self.save_config)
        btn_box.addStretch(1);
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def save_config(self):
        config = ConfigManager.load()
        config["ai_palette_config"] = {
            "base_url": self.url_edit.text().strip().rstrip('/'),
            "model": self.model_edit.text().strip()
        }
        ConfigManager.save(config)
        api_key = self.key_edit.text().strip()
        if api_key:
            try:
                keyring.set_password(self.SERVICE_NAME, "api_key", api_key)
            except:
                pass
        self.accept()


class ColorPickerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_color = QColor("#0078D4")
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self);
        self.main_layout.setContentsMargins(10, 10, 10, 10);
        self.main_layout.setSpacing(0)
        self.left_container = QWidget();
        self.left_container.setFixedWidth(400)
        self.left_container.setStyleSheet(
            f"background-color: {self.current_color.name()}; border-top-left-radius: 10px; border-bottom-left-radius: 10px;")
        l_layout = QVBoxLayout(self.left_container);
        l_layout.setContentsMargins(30, 30, 30, 30);
        l_layout.setSpacing(20)
        icon_eye = qicon("eye");
        if icon_eye.isNull(): icon_eye = getattr(FluentIcon, 'PENCIL_INK', FluentIcon.EDIT).icon()
        self.btn_pick = ToolButton(icon_eye, self.left_container);
        self.btn_pick.setFixedSize(36, 36)
        self.btn_pick.clicked.connect(self.start_screen_pick)
        l_layout.addWidget(self.btn_pick, 0, Qt.AlignLeft)
        self.color_wheel = ColorWheel(self.left_container);
        self.color_wheel.colorChanged.connect(self.on_wheel_changed)
        l_layout.addWidget(self.color_wheel, 0, Qt.AlignCenter)
        self.slider_v = Slider(Qt.Horizontal, self.left_container);
        self.slider_v.setRange(0, 255);
        self.slider_v.setValue(255)
        self.slider_v.valueChanged.connect(self.on_val_changed)
        self.slider_v.setStyleSheet(
            "QSlider::groove:horizontal { height: 16px; border-radius: 8px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:1 white); } QSlider::handle:horizontal { width: 20px; height: 20px; margin: -2px 0; border-radius: 10px; background: white; border: 2px solid #ddd; }")
        l_layout.addWidget(self.slider_v);
        l_layout.addStretch(1)
        self.right_container = QWidget();
        self.right_container.setStyleSheet(
            "QWidget { background-color: white; border-top-right-radius: 10px; border-bottom-right-radius: 10px; } QLabel { color: #333; } QLineEdit { border: 1px solid #e0e0e0; border-radius: 4px; padding: 4px; selection-background-color: #0078d4; }")
        r_scroll = QScrollArea();
        r_scroll.setWidget(self.right_container);
        r_scroll.setWidgetResizable(True);
        r_scroll.setStyleSheet("border: none; background: transparent;")
        r_layout = QVBoxLayout(self.right_container);
        r_layout.setContentsMargins(30, 30, 30, 30);
        r_layout.setSpacing(25)
        self.harmony_grid = QGridLayout();
        self.harmony_grid.setVerticalSpacing(15);
        self.harmony_grid.setHorizontalSpacing(15)
        self.harmony_widgets = {}
        for title, r, c in [("互补色", 0, 0), ("对比色", 0, 1), ("类似色", 1, 0), ("中差色", 1, 1)]:
            box = QWidget();
            h = QHBoxLayout(box);
            h.setContentsMargins(0, 0, 0, 0);
            h.setSpacing(8);
            h.addWidget(BodyLabel(title))
            frames = [];
            for _ in range(3): f = QFrame(); f.setFixedSize(24, 24); f.hide(); h.addWidget(f); frames.append(f)
            self.harmony_widgets[title] = frames;
            self.harmony_grid.addWidget(box, r, c)
        r_layout.addLayout(self.harmony_grid);
        line = QFrame();
        line.setFrameShape(QFrame.HLine);
        line.setStyleSheet("color: #eee;");
        r_layout.addWidget(line)
        self.value_inputs = {};
        f_layout = QVBoxLayout();
        f_layout.setSpacing(12)
        for key in ["HEX", "RGB", "HSV", "HSL", "CMYK"]:
            row = QHBoxLayout();
            lbl = BodyLabel(key);
            lbl.setFixedWidth(60)
            val = LineEdit();
            val.setReadOnly(True);
            self.value_inputs[key] = val
            btn = TransparentToolButton(getattr(FluentIcon, 'COPY', FluentIcon.DOCUMENT), self);
            btn.setFixedSize(28, 28)
            btn.clicked.connect(lambda ch=False, t=val: self.copy_text(t.text()))
            row.addWidget(lbl);
            row.addWidget(val);
            row.addWidget(btn);
            f_layout.addLayout(row)
        r_layout.addLayout(f_layout);
        r_layout.addStretch(1)
        self.main_layout.addWidget(self.left_container);
        self.main_layout.addWidget(r_scroll)
        self.color_wheel.set_color(self.current_color);
        self.update_all(self.current_color)

    def start_screen_pick(self):
        self.picker = ScreenColorPicker();
        self.picker.colorSelected.connect(self.on_wheel_changed);
        self.picker.show()

    def on_wheel_changed(self, color):
        self.current_color = color;
        self.update_all(color, False)

    def on_val_changed(self, val):
        self.color_wheel.set_value(val);
        self.color_wheel.emit_color()

    def update_all(self, color, update_wheel=True):
        text_col = "white" if color.lightness() < 180 else "black"
        self.left_container.setStyleSheet(
            f"background-color: {color.name()}; border-top-left-radius: 10px; border-bottom-left-radius: 10px;")
        self.btn_pick.setStyleSheet(
            f"background-color: rgba(255,255,255,0.3); border-radius: 18px; border: none; color: {text_col};")
        if update_wheel: self.color_wheel.set_color(color); self.slider_v.setValue(color.value())
        self.value_inputs["HEX"].setText(color.name().upper())
        self.value_inputs["RGB"].setText(f"{color.red()}, {color.green()}, {color.blue()}")
        self.value_inputs["HSV"].setText(f"{color.hsvHue()}, {color.hsvSaturation()}, {color.value()}")
        self.value_inputs["HSL"].setText(f"{color.hslHue()}, {color.hslSaturation()}, {color.lightness()}")
        c = 1 - color.red() / 255;
        m = 1 - color.green() / 255;
        y = 1 - color.blue() / 255;
        k = min(c, m, y)
        if k == 1:
            c = m = y = 0
        else:
            c = (c - k) / (1 - k); m = (m - k) / (1 - k); y = (y - k) / (1 - k)
        self.value_inputs["CMYK"].setText(f"{int(c * 100)}%, {int(m * 100)}%, {int(y * 100)}%, {int(k * 100)}%")
        self.update_harmony(color)

    def update_harmony(self, color):
        h = color.hsvHue() if color.hsvHue() != -1 else 0;
        s = color.hsvSaturation();
        v = color.value()

        def get_col(o): return QColor.fromHsv((h + o) % 360, s, v)

        self.set_blocks("互补色", [get_col(180)]);
        self.set_blocks("对比色", [get_col(150), get_col(210)])
        self.set_blocks("类似色", [get_col(-30), get_col(30)]);
        self.set_blocks("中差色", [get_col(90), get_col(270)])

    def set_blocks(self, title, colors):
        frames = self.harmony_widgets.get(title, [])
        for i, f in enumerate(frames):
            if i < len(colors):
                f.show(); f.setStyleSheet(
                    f"border-radius: 4px; background: {colors[i].name()}; border: 1px solid #ddd;"); f.setToolTip(
                    colors[i].name().upper())
            else:
                f.hide()

    def copy_text(self, text):
        QApplication.clipboard().setText(text);
        InfoBar.success("已复制", text, parent=self.window())


# ==========================================
# 2. 色卡展示页 (使用 ColorBlock)
# ==========================================
class PaletteGridPage(QScrollArea):
    def __init__(self, palette_type="ui"):
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent; border: none;")
        self.container = QWidget(); self.setWidget(self.container)
        self.main_layout = QVBoxLayout(self.container); self.main_layout.setContentsMargins(10, 10, 10, 10)
        if palette_type == "ui": self.load_ui_palettes()
        else: self.load_traditional_colors()

    def load_ui_palettes(self):
        for name, colors in UI_PALETTES.items():
            self.main_layout.addWidget(StrongBodyLabel(name, self.container))
            flow = QWidget(); flow_layout = FlowLayout(flow, needAni=False); flow_layout.setContentsMargins(0, 0, 0, 0)
            for hex_code in colors:
                # 使用 ColorBlock
                flow_layout.addWidget(ColorBlock(hex_code, hex_code))
            self.main_layout.addWidget(flow); self.main_layout.addSpacing(20)
        self.main_layout.addStretch(1)

    def load_traditional_colors(self):
        flow = QWidget(); flow_layout = FlowLayout(flow, needAni=False)
        for item in TRADITIONAL_COLORS:
            # 使用 ColorBlock
            flow_layout.addWidget(ColorBlock(item["hex"], item["name"]))
        self.main_layout.addWidget(flow); self.main_layout.addStretch(1)

# ==========================================
# 3. AI 配色页 (旗舰重构版)
# ==========================================
class AiPalettePage(QWidget):
    generation_finished = Signal(dict)
    generation_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)

        # --- 左侧：控制面板 ---
        self.left_panel = CardWidget(self)
        self.left_panel.setFixedWidth(320)
        l_layout = QVBoxLayout(self.left_panel)
        l_layout.setSpacing(20)

        l_layout.addWidget(StrongBodyLabel("AI 配色配置", self))

        # 1. 主色 (带吸管和粘贴)
        row1 = QHBoxLayout()
        row1.addWidget(BodyLabel("主色"))
        self.main_color_btn = ColorPickerButton(QColor("#0078D4"), "主色", self)
        self.main_color_btn.setFixedSize(40, 40)

        # 吸管
        icon_eye = qicon("eye")
        if icon_eye.isNull(): icon_eye = getattr(FluentIcon, 'PENCIL_INK', FluentIcon.EDIT).icon()
        self.btn_pick = ToolButton(icon_eye, self)
        self.btn_pick.setToolTip("屏幕取色")
        self.btn_pick.clicked.connect(self.start_screen_pick)

        # 粘贴 HEX
        icon_paste = getattr(FluentIcon, 'PASTE', FluentIcon.DOCUMENT)
        self.btn_paste = ToolButton(icon_paste, self)
        self.btn_paste.setToolTip("粘贴剪贴板颜色 (Hex)")
        self.btn_paste.clicked.connect(self.paste_hex_color)

        row1.addWidget(self.main_color_btn)
        row1.addWidget(self.btn_pick)
        row1.addWidget(self.btn_paste)
        row1.addStretch(1)
        l_layout.addLayout(row1)

        # 2. 风格
        l_layout.addWidget(BodyLabel("风格"))
        self.style_flow = FlowLayout(needAni=True)
        # 扩充预设风格
        styles = ["现代", "复古", "自然", "赛博朋克", "莫兰迪", "多巴胺", "国潮", "极简", "波普", "商务"]
        self.style_group = []
        # 获取当前主题色 (或写死一个颜色)
        accent_color = "#009688"  # 青色

        for s in styles:
            btn = PushButton(s, self)
            btn.setCheckable(True)
            btn.setFixedHeight(32)

            # 【核心修复】添加样式表，定义选中状态
            btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            border: 1px solid #e0e0e0;
                            border-radius: 6px;
                            color: #333;
                            font-size: 14px;
                        }}
                        QPushButton:hover {{
                            background-color: #f0f0f0;
                        }}
                        QPushButton:checked {{
                            background-color: {accent_color};
                            border: 1px solid {accent_color};
                            color: white;
                        }}
                    """)

            btn.clicked.connect(lambda ch, b=btn: self.on_style_click(b))
            self.style_flow.addWidget(btn)
            self.style_group.append(btn)

        style_container = QWidget()
        style_container.setLayout(self.style_flow)
        l_layout.addWidget(style_container)

        # 3. 自定义风格 (新增)
        self.custom_style_edit = LineEdit(self)
        self.custom_style_edit.setPlaceholderText("或输入自定义风格 (如: 五彩斑斓的黑)")
        l_layout.addWidget(self.custom_style_edit)

        # 4. 色系 & 数量
        l_layout.addWidget(BodyLabel("色系"))
        self.tone_combo = ComboBox(self)
        self.tone_combo.addItems(["不限", "暖色调", "冷色调", "中性色"])
        l_layout.addWidget(self.tone_combo)

        row_num = QHBoxLayout()
        row_num.addWidget(BodyLabel("数量"))
        self.spin_count = Slider(Qt.Horizontal, self)
        self.spin_count.setRange(3, 8);
        self.spin_count.setValue(5)
        self.lbl_count = BodyLabel("5")
        self.spin_count.valueChanged.connect(lambda v: self.lbl_count.setText(str(v)))
        row_num.addWidget(self.spin_count);
        row_num.addWidget(self.lbl_count)
        l_layout.addLayout(row_num)

        l_layout.addStretch(1)

        # API设置按钮
        self.btn_api_setting = TransparentToolButton(getattr(FluentIcon, 'SETTINGS', FluentIcon.EDIT), self)
        self.btn_api_setting.setToolTip("配置 API Key")
        self.btn_api_setting.clicked.connect(self.open_api_config)
        l_layout.addWidget(self.btn_api_setting)

        # 生成按钮
        icon_robot = getattr(FluentIcon, 'ROBOT', FluentIcon.PEOPLE)
        self.btn_gen = PrimaryPushButton(icon_robot, "AI 重新生成", self)
        self.btn_gen.clicked.connect(self.start_generation)
        l_layout.addWidget(self.btn_gen)

        # --- 右侧：结果展示 ---
        self.right_panel = QScrollArea()
        self.right_panel.setWidgetResizable(True)
        self.right_panel.setStyleSheet("border: none; background: transparent;")

        self.result_container = QWidget()
        self.r_layout = QVBoxLayout(self.result_container)
        self.r_layout.setContentsMargins(0, 0, 0, 0);
        self.r_layout.setSpacing(20)
        self.right_panel.setWidget(self.result_container)

        self.result_card = CardWidget(self)
        self.res_card_layout = QVBoxLayout(self.result_card);
        self.res_card_layout.setSpacing(15)

        self.lbl_title = StrongBodyLabel("等待生成...", self);
        self.lbl_title.setStyleSheet("font-size: 18px;")
        self.lbl_desc = BodyLabel("点击左侧按钮开始生成配色方案。", self);
        self.lbl_desc.setWordWrap(True);
        self.lbl_desc.setStyleSheet("color: gray;")
        self.res_card_layout.addWidget(self.lbl_title);
        self.res_card_layout.addWidget(self.lbl_desc);
        self.res_card_layout.addSpacing(10)

        self.colors_layout = QHBoxLayout();
        self.res_card_layout.addLayout(self.colors_layout)

        self.btn_export = PushButton(getattr(FluentIcon, 'SAVE', FluentIcon.EDIT), "导出色卡图片", self)
        self.btn_export.clicked.connect(self.export_image);
        self.btn_export.setEnabled(False)
        self.res_card_layout.addWidget(self.btn_export, 0, Qt.AlignRight)

        self.r_layout.addWidget(self.result_card);
        self.r_layout.addStretch(1)

        self.layout.addWidget(self.left_panel);
        self.layout.addWidget(self.right_panel, 1)

        self.generation_finished.connect(self.on_success)
        self.generation_failed.connect(self.on_error)

    # --- 新增功能 ---
    def start_screen_pick(self):
        # 复用 ScreenColorPicker
        self.picker = ScreenColorPicker()
        self.picker.colorSelected.connect(lambda c: self.main_color_btn.setColor(c))
        self.picker.show()

    def paste_hex_color(self):
        text = QApplication.clipboard().text().strip()
        if not text: return

        # 尝试解析
        if text.startswith('#'):
            color = QColor(text)
        else:
            color = QColor(f"#{text}")

        if color.isValid():
            self.main_color_btn.setColor(color)
            InfoBar.success("已粘贴", f"主色已设置为 {color.name().upper()}", parent=self.window(), duration=1500)
        else:
            InfoBar.warning("无效格式", "剪贴板内容不是有效的 HEX 颜色代码", parent=self.window())

    def on_style_click(self, clicked_btn):
        # 允许取消选中，如果点击已选中的，则取消选中
        if clicked_btn.isChecked():
            for btn in self.style_group:
                if btn != clicked_btn: btn.setChecked(False)
        else:
            # 如果取消了，就保持无选中状态
            pass

    def open_api_config(self):
        dialog = ApiConfigDialog(self.window())
        dialog.exec()

    def clear_color_blocks(self):
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def start_generation(self):
        if not HAS_OPENAI:
            InfoBar.error("缺失库", "请先安装: pip install openai", parent=self.window())
            return

        api_key = keyring.get_password(ApiConfigDialog.SERVICE_NAME, "api_key")
        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})

        if not api_key:
            InfoBar.warning("未配置", "请先配置 API Key", parent=self.window())
            return

        ai_conf['api_key'] = api_key

        self.btn_gen.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.lbl_title.setText("正在连接大模型思考中...")
        self.lbl_desc.setText("AI 正在构思色彩搭配...")
        self.clear_color_blocks()

        # --- 构建 Prompt ---
        # 1. 风格：优先自定义，其次预设，默认现代
        custom_style = self.custom_style_edit.text().strip()
        preset_style = "现代"
        for btn in self.style_group:
            if btn.isChecked(): preset_style = btn.text(); break

        final_style = custom_style if custom_style else preset_style

        # 2. 其他参数
        tone = self.tone_combo.currentText()
        count = self.spin_count.value()
        main_color_hex = self.main_color_btn.color.name()

        prompt = f"""
        请设计一组UI配色方案。

        核心约束：
        1. 风格/主题：{final_style}
        2. 必须包含主色：{main_color_hex}，并以此为基础拓展。
        3. 色调偏向：{tone}（需与主色协调）。
        4. 颜色数量：{count}个。

        请直接返回 JSON 格式，不要 Markdown：
        {{
            "name": "方案名称(富有创意)",
            "description": "设计理念(50字以内)",
            "colors": ["#HEX1", "#HEX2"]
        }}
        """

        threading.Thread(target=self.run_api_request, args=(ai_conf, prompt)).start()

    def run_api_request(self, conf, prompt):
        try:
            client = OpenAI(api_key=conf['api_key'], base_url=conf.get('base_url'))
            response = client.chat.completions.create(
                model=conf.get('model', 'deepseek-chat'),
                messages=[
                    {"role": "system", "content": "你是一位色彩设计大师，只输出纯 JSON。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8  # 稍微提高一点创造性
            )
            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            self.generation_finished.emit(json.loads(content))
        except Exception as e:
            self.generation_failed.emit(str(e))

    def on_success(self, data):
        self.btn_gen.setEnabled(True);
        self.btn_export.setEnabled(True)
        self.lbl_title.setText(data.get("name", "未命名方案"))
        self.lbl_desc.setText(data.get("description", "暂无描述"))

        for hex_code in data.get("colors", []):
            try:
                c = QWidget();
                v = QVBoxLayout(c);
                v.setContentsMargins(0, 0, 0, 0)
                f = QFrame();
                f.setMinimumSize(60, 80);
                f.setStyleSheet(f"background-color: {hex_code}; border-radius: 8px;");
                f.setToolTip(hex_code)
                l = BodyLabel(hex_code.upper());
                l.setAlignment(Qt.AlignCenter);
                l.setStyleSheet("font-size: 12px;")
                v.addWidget(f, 1);
                v.addWidget(l);
                self.colors_layout.addWidget(c)
            except:
                pass
        InfoBar.success("生成完成", "AI 已为您构建配色方案", parent=self.window())

    def on_error(self, err):
        self.btn_gen.setEnabled(True)
        self.lbl_title.setText("生成失败")
        self.lbl_desc.setText(f"错误信息: {err}")

    def export_image(self):
        # 截图前隐藏按钮
        self.btn_export.hide()
        QApplication.processEvents()
        pixmap = self.result_card.grab()
        self.btn_export.show()

        path, _ = QFileDialog.getSaveFileName(self, "保存", "palette.png", "Images (*.png)")
        if path:
            pixmap.save(path)
            InfoBar.success("成功", f"已保存到 {path}", parent=self.window())