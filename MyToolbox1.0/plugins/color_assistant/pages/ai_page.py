import sys
import math
import random
import json
import threading
import requests
import keyring
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QFrame, QScrollArea, QApplication, QDialog,
                               QGraphicsDropShadowEffect, QFormLayout, QFileDialog)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer
from PySide6.QtGui import (QColor, QPainter, QBrush, QPen, QConicalGradient,
                           QRadialGradient, QCursor, QPixmap, QScreen, QLinearGradient, QClipboard)

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

try:
    from google import genai

    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


# ==========================================
# 0. 辅助控件 (ScreenColorPicker, ColorWheel)
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


# ==========================================
# 1. API 配置弹窗
# ==========================================
class ApiConfigDialog(QDialog):
    SERVICE_NAME = "PythonFluentToolbox"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("大模型 API 配置")
        self.resize(450, 250)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = ComboBox(self)
        self.type_combo.addItems(["OpenAI / DeepSeek", "Google Gemini"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)

        self.url_edit = LineEdit(self)
        self.key_edit = LineEdit(self)
        self.key_edit.setEchoMode(LineEdit.Password)
        self.model_edit = LineEdit(self)

        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})

        current_type = ai_conf.get("type", "OpenAI / DeepSeek")
        idx = self.type_combo.findText(current_type)
        if idx != -1: self.type_combo.setCurrentIndex(idx)

        self.url_edit.setText(ai_conf.get("base_url", ""))
        self.model_edit.setText(ai_conf.get("model", ""))

        try:
            saved_key = keyring.get_password(self.SERVICE_NAME, f"api_key_{current_type}")
            if saved_key: self.key_edit.setText(saved_key)
        except:
            pass

        form.addRow("API 类型:", self.type_combo)
        form.addRow("Base URL:", self.url_edit)
        form.addRow("API Key:", self.key_edit)
        form.addRow("Model:", self.model_edit)
        layout.addLayout(form)

        self.tip_label = BodyLabel("", self)
        self.tip_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.tip_label)

        btn_box = QHBoxLayout()
        btn_save = PrimaryPushButton("保存", self)
        btn_save.clicked.connect(self.save_config)
        btn_box.addStretch(1);
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

        self.on_type_changed(self.type_combo.currentIndex())

    def on_type_changed(self, index):
        api_type = self.type_combo.currentText()
        self.key_edit.clear()

        if api_type == "Google Gemini":
            self.url_edit.setEnabled(False)
            self.url_edit.setPlaceholderText("(Gemini SDK 不需要)")
            self.model_edit.setPlaceholderText("gemini-1.5-flash")
            self.model_edit.setText("gemini-1.5-flash")
            self.tip_label.setText("提示：Google AI Studio API Key。无需 BaseURL。")
        else:
            self.url_edit.setEnabled(True)
            self.url_edit.setPlaceholderText("https://api.deepseek.com")
            self.model_edit.setPlaceholderText("deepseek-chat")
            self.tip_label.setText("提示：DeepSeek 请填 'https://api.deepseek.com' 和 'deepseek-chat'")

        try:
            key = keyring.get_password(self.SERVICE_NAME, f"api_key_{api_type}")
            if key: self.key_edit.setText(key)
        except:
            pass

    def save_config(self):
        api_type = self.type_combo.currentText()
        config = ConfigManager.load()
        config["ai_palette_config"] = {
            "type": api_type,
            "base_url": self.url_edit.text().strip().rstrip('/'),
            "model": self.model_edit.text().strip()
        }
        ConfigManager.save(config)

        api_key = self.key_edit.text().strip()
        if api_key:
            try:
                keyring.set_password(self.SERVICE_NAME, f"api_key_{api_type}", api_key)
            except:
                pass
        self.accept()


# ==========================================
# 2. AI 配色页
# ==========================================
class AiPalettePage(QWidget):
    generation_finished = Signal(dict)
    generation_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)

        # --- 左侧 ---
        self.left_panel = CardWidget(self)
        self.left_panel.setFixedWidth(320)
        l_layout = QVBoxLayout(self.left_panel)
        l_layout.setSpacing(20)

        l_layout.addWidget(StrongBodyLabel("AI 配色配置", self))

        row1 = QHBoxLayout()
        row1.addWidget(BodyLabel("主色"))
        self.main_color_btn = ColorPickerButton(QColor("#0078D4"), "主色", self)
        self.main_color_btn.setFixedSize(40, 40)

        icon_eye = qicon("eye")
        if icon_eye.isNull(): icon_eye = getattr(FluentIcon, 'PENCIL_INK', FluentIcon.EDIT).icon()
        self.btn_pick = ToolButton(icon_eye, self)
        self.btn_pick.setToolTip("屏幕取色")
        self.btn_pick.clicked.connect(self.start_screen_pick)

        icon_paste = getattr(FluentIcon, 'PASTE', FluentIcon.DOCUMENT)
        self.btn_paste = ToolButton(icon_paste, self)
        self.btn_paste.setToolTip("粘贴剪贴板颜色 (Hex)")
        self.btn_paste.clicked.connect(self.paste_hex_color)

        row1.addWidget(self.main_color_btn)
        row1.addWidget(self.btn_pick)
        row1.addWidget(self.btn_paste)
        row1.addStretch(1)
        l_layout.addLayout(row1)

        l_layout.addWidget(BodyLabel("风格"))
        self.style_flow = FlowLayout(needAni=True)
        styles = ["现代", "复古", "自然", "赛博朋克", "莫兰迪", "多巴胺", "国潮", "极简", "波普", "商务"]
        self.style_group = []
        accent_color = "#009688"
        for s in styles:
            btn = PushButton(s, self);
            btn.setCheckable(True);
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{ background-color: transparent; border: 1px solid #e0e0e0; border-radius: 6px; color: #333; font-size: 14px; }}
                QPushButton:hover {{ background-color: #f0f0f0; }}
                QPushButton:checked {{ background-color: {accent_color}; border: 1px solid {accent_color}; color: white; }}
            """)
            btn.clicked.connect(lambda ch, b=btn: self.on_style_click(b))
            self.style_flow.addWidget(btn);
            self.style_group.append(btn)
        style_container = QWidget();
        style_container.setLayout(self.style_flow)
        l_layout.addWidget(style_container)

        self.custom_style_edit = LineEdit(self)
        self.custom_style_edit.setPlaceholderText("或输入自定义风格 (如: 五彩斑斓的黑)")
        l_layout.addWidget(self.custom_style_edit)

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

        self.btn_api_setting = TransparentToolButton(getattr(FluentIcon, 'SETTINGS', FluentIcon.EDIT), self)
        self.btn_api_setting.setToolTip("配置 API Key")
        self.btn_api_setting.clicked.connect(self.open_api_config)
        l_layout.addWidget(self.btn_api_setting)

        icon_robot = getattr(FluentIcon, 'ROBOT', FluentIcon.PEOPLE)
        self.btn_gen = PrimaryPushButton(icon_robot, "AI 重新生成", self)
        self.btn_gen.clicked.connect(self.start_generation)
        l_layout.addWidget(self.btn_gen)

        # --- 右侧 ---
        self.right_panel = QScrollArea();
        self.right_panel.setWidgetResizable(True);
        self.right_panel.setStyleSheet("border: none; background: transparent;")
        self.result_container = QWidget();
        self.right_panel.setWidget(self.result_container)
        self.r_layout = QVBoxLayout(self.result_container);
        self.r_layout.setContentsMargins(0, 0, 0, 0);
        self.r_layout.setSpacing(20)

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

        # 操作按钮栏
        action_bar = QHBoxLayout()
        action_bar.addStretch(1)

        self.btn_fav = PushButton(getattr(FluentIcon, 'HEART', FluentIcon.HEART), "收藏方案", self)
        self.btn_fav.clicked.connect(self.save_current_palette)
        self.btn_fav.setEnabled(False)

        self.btn_export = PushButton(getattr(FluentIcon, 'SAVE', FluentIcon.EDIT), "导出图片", self)
        self.btn_export.clicked.connect(self.export_image);
        self.btn_export.setEnabled(False)

        action_bar.addWidget(self.btn_fav)
        action_bar.addWidget(self.btn_export)
        self.res_card_layout.addLayout(action_bar)

        self.r_layout.addWidget(self.result_card);
        self.r_layout.addStretch(1)
        self.layout.addWidget(self.left_panel);
        self.layout.addWidget(self.right_panel, 1)

        self.generation_finished.connect(self.on_success)
        self.generation_failed.connect(self.on_error)

    def start_screen_pick(self):
        from ..components.color_wheel import ScreenColorPicker
        self.picker = ScreenColorPicker()
        self.picker.colorSelected.connect(lambda c: self.main_color_btn.setColor(c))
        self.picker.show()

    def paste_hex_color(self):
        text = QApplication.clipboard().text().strip()
        if not text: return
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
        if clicked_btn.isChecked():
            for btn in self.style_group:
                if btn != clicked_btn: btn.setChecked(False)

    def open_api_config(self):
        dialog = ApiConfigDialog(self.window())
        dialog.exec()

    def clear_color_blocks(self):
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def save_current_palette(self):
        if not hasattr(self, 'current_data') or not self.current_data: return
        name = self.current_data.get("name", "未命名")
        colors = self.current_data.get("colors", [])
        if colors:
            from plugins.color_assistant.services import CollectionService
            CollectionService.add_palette(colors, name)
            InfoBar.success("已收藏", f"配色方案 '{name}' 已保存", parent=self.window())
            self.btn_fav.setDisabled(True)
            self.btn_fav.setText("已收藏")

    def start_generation(self):
        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})
        api_type = ai_conf.get("type", "OpenAI / DeepSeek")

        if api_type == "Google Gemini" and not HAS_GEMINI: return InfoBar.error("缺失库", "请安装: google-genai",
                                                                                parent=self.window())
        if api_type != "Google Gemini" and not HAS_OPENAI: return InfoBar.error("缺失库", "请安装: openai",
                                                                                parent=self.window())

        api_key = keyring.get_password(ApiConfigDialog.SERVICE_NAME, f"api_key_{api_type}")
        if not api_key: return InfoBar.warning("未配置", "请先配置 API Key", parent=self.window())

        ai_conf['api_key'] = api_key

        self.btn_gen.setEnabled(False);
        self.btn_export.setEnabled(False);
        self.btn_fav.setEnabled(False)
        self.lbl_title.setText("正在连接大模型思考中...")
        self.lbl_desc.setText("AI 正在构思色彩搭配...")
        self.clear_color_blocks()

        custom_style = self.custom_style_edit.text().strip()
        preset_style = "现代"
        for btn in self.style_group:
            if btn.isChecked(): preset_style = btn.text(); break
        final_style = custom_style if custom_style else preset_style

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
            "name": "方案名称",
            "description": "设计理念",
            "colors": ["#HEX1", "#HEX2"]
        }}
        """

        threading.Thread(target=self.run_api_request, args=(ai_conf, prompt)).start()

    def run_api_request(self, conf, prompt):
        try:
            api_type = conf.get("type", "OpenAI / DeepSeek")
            if api_type == "Google Gemini":
                client = genai.Client(api_key=conf['api_key'])
                model_name = conf.get('model', 'gemini-1.5-flash')
                response = client.models.generate_content(model=model_name, contents=prompt)
                content = response.text
            else:
                client = OpenAI(api_key=conf['api_key'], base_url=conf.get('base_url'))
                response = client.chat.completions.create(
                    model=conf.get('model', 'deepseek-chat'),
                    messages=[{"role": "system", "content": "你是一位色彩设计大师，只输出纯 JSON。"},
                              {"role": "user", "content": prompt}],
                    temperature=0.8
                )
                content = response.choices[0].message.content

            content = content.replace("```json", "").replace("```", "").strip()
            try:
                data = json.loads(content)
            except:
                import ast; data = ast.literal_eval(content)
            self.generation_finished.emit(data)
        except Exception as e:
            self.generation_failed.emit(str(e))

    def on_success(self, data):
        self.current_data = data
        self.btn_gen.setEnabled(True);
        self.btn_export.setEnabled(True);
        self.btn_fav.setEnabled(True)
        self.btn_fav.setText("收藏方案")

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
        self.btn_export.hide();
        self.btn_fav.hide()
        QApplication.processEvents()
        pixmap = self.result_card.grab()
        self.btn_export.show();
        self.btn_fav.show()

        path, _ = QFileDialog.getSaveFileName(self, "保存", "palette.png", "Images (*.png)")
        if path:
            pixmap.save(path)
            InfoBar.success("成功", f"已保存到 {path}", parent=self.window())