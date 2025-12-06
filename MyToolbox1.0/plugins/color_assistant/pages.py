import sys
import math
import random
import json
import threading
import requests
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QApplication, QDialog,
                               QGraphicsDropShadowEffect, QFormLayout)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer
from PySide6.QtGui import (QColor, QPainter, QBrush, QPen, QConicalGradient,
                           QRadialGradient, QCursor, QPixmap, QScreen, QLinearGradient)

from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, LineEdit,
                            PrimaryPushButton, PushButton, TransparentToolButton, FluentIcon,
                            InfoBar, Slider, ToolButton, FlowLayout, SubtitleLabel,
                            ColorPickerButton, ComboBox)

from plugins.color_assistant.color_data import TRADITIONAL_COLORS, UI_PALETTES
from core.resource_manager import qicon
from core.config import ConfigManager  # <--- 【修复点】补全导入


# ==========================================
# 0. 辅助控件 (取色器、色轮、API弹窗)
# ==========================================
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
            self.colorSelected.emit(color)
            self.accept()
        else:
            self.reject()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))


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
        if dist > max_dist:
            ratio = max_dist / dist;
            dx *= ratio;
            dy *= ratio;
            dist = max_dist
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
        radial = QRadialGradient(center, r)
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("大模型 API 配置")
        self.resize(400, 200)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.url_edit = LineEdit(self)
        self.url_edit.setPlaceholderText("例如 https://api.openai.com/v1")
        self.key_edit = LineEdit(self)
        self.key_edit.setEchoMode(LineEdit.Password)
        self.key_edit.setPlaceholderText("sk-xxxxxxxx")
        self.model_edit = LineEdit(self)
        self.model_edit.setPlaceholderText("例如 gpt-3.5-turbo")

        # 读取旧配置
        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})
        self.url_edit.setText(ai_conf.get("base_url", "https://api.openai.com/v1"))
        self.key_edit.setText(ai_conf.get("api_key", ""))
        self.model_edit.setText(ai_conf.get("model", "gpt-3.5-turbo"))

        form.addRow("Base URL:", self.url_edit)
        form.addRow("API Key:", self.key_edit)
        form.addRow("Model:", self.model_edit)
        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_save = PrimaryPushButton("保存", self)
        btn_save.clicked.connect(self.save_config)
        btn_box.addStretch(1);
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def save_config(self):
        config = ConfigManager.load()
        config["ai_palette_config"] = {
            "base_url": self.url_edit.text().strip(),
            "api_key": self.key_edit.text().strip(),
            "model": self.model_edit.text().strip()
        }
        ConfigManager.save(config)
        self.accept()


# ==========================================
# 1. 综合取色页
# ==========================================
class ColorPickerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_color = QColor("#0078D4")
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)

        # 左侧
        self.left_container = QWidget()
        self.left_container.setFixedWidth(400)
        self.left_container.setStyleSheet(
            f"background-color: {self.current_color.name()}; border-top-left-radius: 10px; border-bottom-left-radius: 10px;")
        l_layout = QVBoxLayout(self.left_container);
        l_layout.setContentsMargins(30, 30, 30, 30);
        l_layout.setSpacing(20)

        # 吸管
        icon_eye = qicon("eye")
        if icon_eye.isNull(): icon_eye = getattr(FluentIcon, 'PENCIL_INK', FluentIcon.EDIT).icon()
        self.btn_pick = ToolButton(icon_eye, self.left_container)
        self.btn_pick.setFixedSize(36, 36)
        self.btn_pick.clicked.connect(self.start_screen_pick)
        l_layout.addWidget(self.btn_pick, 0, Qt.AlignLeft)

        self.color_wheel = ColorWheel(self.left_container)
        self.color_wheel.colorChanged.connect(self.on_wheel_changed)
        l_layout.addWidget(self.color_wheel, 0, Qt.AlignCenter)

        self.slider_v = Slider(Qt.Horizontal, self.left_container)
        self.slider_v.setRange(0, 255);
        self.slider_v.setValue(255)
        self.slider_v.valueChanged.connect(self.on_val_changed)
        self.slider_v.setStyleSheet(
            "QSlider::groove:horizontal { height: 16px; border-radius: 8px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:1 white); } QSlider::handle:horizontal { width: 20px; height: 20px; margin: -2px 0; border-radius: 10px; background: white; border: 2px solid #ddd; }")
        l_layout.addWidget(self.slider_v)
        l_layout.addStretch(1)

        # 右侧
        self.right_container = QWidget()
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
            h.setSpacing(8)
            h.addWidget(BodyLabel(title))
            frames = []
            for _ in range(3): f = QFrame(); f.setFixedSize(24, 24); f.hide(); h.addWidget(f); frames.append(f)
            self.harmony_widgets[title] = frames
            self.harmony_grid.addWidget(box, r, c)
        r_layout.addLayout(self.harmony_grid)

        line = QFrame();
        line.setFrameShape(QFrame.HLine);
        line.setStyleSheet("color: #eee;");
        r_layout.addWidget(line)

        self.value_inputs = {}
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
        self.picker = ScreenColorPicker()
        self.picker.colorSelected.connect(self.on_wheel_changed)
        self.picker.show()

    def on_wheel_changed(self, color):
        self.current_color = color
        self.update_all(color, False)

    def on_val_changed(self, val):
        self.color_wheel.set_value(val)
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
        h = color.hsvHue() if color.hsvHue() != -1 else 0
        s = color.hsvSaturation();
        v = color.value()

        def get_col(o): return QColor.fromHsv((h + o) % 360, s, v)

        self.set_blocks("互补色", [get_col(180)])
        self.set_blocks("对比色", [get_col(150), get_col(210)])
        self.set_blocks("类似色", [get_col(-30), get_col(30)])
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
        QApplication.clipboard().setText(text)
        InfoBar.success("已复制", text, parent=self.window())


# ==========================================
# 2. 色卡展示页
# ==========================================
class PaletteGridPage(QScrollArea):
    def __init__(self, palette_type="ui"):
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet("background: transparent; border: none;")
        self.container = QWidget();
        self.setWidget(self.container)
        self.main_layout = QVBoxLayout(self.container);
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        if palette_type == "ui":
            self.load_ui_palettes()
        else:
            self.load_traditional_colors()

    def load_ui_palettes(self):
        for name, colors in UI_PALETTES.items():
            self.main_layout.addWidget(StrongBodyLabel(name, self.container))
            flow = QWidget();
            flow_layout = FlowLayout(flow, needAni=False);
            flow_layout.setContentsMargins(0, 0, 0, 0)
            for hex_code in colors: flow_layout.addWidget(self.create_color_block(hex_code, hex_code))
            self.main_layout.addWidget(flow);
            self.main_layout.addSpacing(20)
        self.main_layout.addStretch(1)

    def load_traditional_colors(self):
        flow = QWidget();
        flow_layout = FlowLayout(flow, needAni=False)
        for item in TRADITIONAL_COLORS: flow_layout.addWidget(self.create_color_block(item["hex"], item["name"]))
        self.main_layout.addWidget(flow);
        self.main_layout.addStretch(1)

    def create_color_block(self, hex_code, text):
        w = QFrame();
        w.setFixedSize(100, 80);
        w.setCursor(Qt.PointingHandCursor)
        w.setStyleSheet(
            f"QFrame {{ background-color: {hex_code}; border-radius: 8px; border: 1px solid #e0e0e0; }} QFrame:hover {{ border: 2px solid #009faa; }}")
        v = QVBoxLayout(w);
        v.setContentsMargins(0, 0, 0, 0);
        v.addStretch(1)
        lbl = QLabel(text);
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.9); border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; color: #333; font-size: 11px; padding: 4px;")
        v.addWidget(lbl)
        return w


# ==========================================
# 3. AI 配色页 (完整修复版)
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

        # 1. 主色
        row1 = QHBoxLayout()
        row1.addWidget(BodyLabel("主色"))
        self.main_color_btn = ColorPickerButton(QColor("#0078D4"), "主色", self)
        self.main_color_btn.setFixedSize(40, 40)

        icon_sync = getattr(FluentIcon, 'SYNC', FluentIcon.EDIT)
        self.chk_random = TransparentToolButton(icon_sync, self)
        self.chk_random.setToolTip("随机主色")
        self.chk_random.setCheckable(True)
        self.chk_random.setChecked(True)

        row1.addWidget(self.main_color_btn)
        row1.addWidget(self.chk_random)
        row1.addStretch(1)
        l_layout.addLayout(row1)

        # 2. 风格
        l_layout.addWidget(BodyLabel("风格"))
        self.style_flow = FlowLayout(needAni=True)
        styles = ["现代", "复古", "自然", "赛博朋克", "莫兰迪", "多巴胺"]
        self.style_group = []
        for s in styles:
            btn = PushButton(s, self);
            btn.setCheckable(True);
            btn.setFixedHeight(30)
            btn.clicked.connect(lambda ch, b=btn: self.on_style_click(b))
            self.style_flow.addWidget(btn);
            self.style_group.append(btn)
        style_container = QWidget();
        style_container.setLayout(self.style_flow)
        l_layout.addWidget(style_container)

        # 3. 色系
        l_layout.addWidget(BodyLabel("色系"))
        self.tone_combo = ComboBox(self)
        self.tone_combo.addItems(["不限", "暖色调", "冷色调", "中性色"])
        l_layout.addWidget(self.tone_combo)

        # 4. 数量
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

    def on_style_click(self, clicked_btn):
        for btn in self.style_group:
            if btn != clicked_btn: btn.setChecked(False)

    def open_api_config(self):
        dialog = ApiConfigDialog(self.window())
        dialog.exec()

    def start_generation(self):
        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})
        if not ai_conf.get("api_key"):
            InfoBar.warning("未配置", "请先配置 API Key", parent=self.window())
            return

        self.btn_gen.setEnabled(False)
        self.lbl_title.setText("正在连接大模型思考中...")
        self.lbl_desc.setText("AI 正在构思色彩搭配...")

        style = "默认"
        for btn in self.style_group:
            if btn.isChecked(): style = btn.text(); break
        tone = self.tone_combo.currentText()
        count = self.spin_count.value()

        prompt = f"""请设计一组配色方案。风格要求：{style}，色调偏向：{tone}，颜色数量：{count}个。
        请直接返回JSON格式：{{ "name": "方案名称", "description": "描述", "colors": ["#HEX1", "#HEX2"] }}"""

        threading.Thread(target=self.run_api_request, args=(ai_conf, prompt)).start()

    def run_api_request(self, conf, prompt):
        try:
            headers = {"Authorization": f"Bearer {conf['api_key']}", "Content-Type": "application/json"}
            url = f"{conf['base_url'].rstrip('/')}/chat/completions"
            data = {"model": conf['model'], "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content'].replace("```json", "").replace("```", "").strip()
            self.generation_finished.emit(json.loads(content))
        except Exception as e:
            self.generation_failed.emit(str(e))

    def on_success(self, data):
        self.btn_gen.setEnabled(True);
        self.btn_export.setEnabled(True)
        self.lbl_title.setText(data.get("name", "未命名方案"))
        self.lbl_desc.setText(data.get("description", "暂无描述"))

        while self.colors_layout.count(): self.colors_layout.takeAt(0).widget().deleteLater()

        for hex_code in data.get("colors", []):
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
        InfoBar.success("生成完成", "AI 已为您构建配色方案", parent=self.window())

    def on_error(self, err):
        self.btn_gen.setEnabled(True)
        self.lbl_title.setText("生成失败")
        self.lbl_desc.setText(f"错误: {err}")
        InfoBar.error("请求失败", "请检查网络或配置", parent=self.window())

    def export_image(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "保存", "palette.png", "Images (*.png)")
        if path:
            self.result_card.grab().save(path)
            InfoBar.success("成功", f"已保存到 {path}", parent=self.window())