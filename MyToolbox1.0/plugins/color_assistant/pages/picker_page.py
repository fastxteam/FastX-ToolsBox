from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QFrame, QScrollArea, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, LineEdit,
                            TransparentToolButton, FluentIcon, ToolButton, Slider)

from ..components.color_wheel import ColorWheel, ScreenColorPicker
from core.resource_manager import qicon


class ColorPickerPage(QWidget):
    def __init__(self):
        super().__init__()
        self.current_color = QColor("#0078D4")
        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)

        # --- 左侧 ---
        self.left_container = QWidget()
        self.left_container.setFixedWidth(400)
        # 初始样式，后续会动态更新
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

        self.color_wheel = ColorWheel(self.left_container)
        self.color_wheel.colorChanged.connect(self.on_wheel_changed)
        l_layout.addWidget(self.color_wheel, 0, Qt.AlignCenter)

        self.slider_v = Slider(Qt.Horizontal, self.left_container)
        self.slider_v.setRange(0, 255);
        self.slider_v.setValue(255)
        self.slider_v.valueChanged.connect(self.on_val_changed)
        self.slider_v.setStyleSheet(
            "QSlider::groove:horizontal { height: 16px; border-radius: 8px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 black, stop:1 white); } QSlider::handle:horizontal { width: 20px; height: 20px; margin: -2px 0; border-radius: 10px; background: white; border: 2px solid #ddd; }")
        l_layout.addWidget(self.slider_v);
        l_layout.addStretch(1)

        # --- 右侧 ---
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
        self.color_wheel.set_col(self.current_color);
        self.update_all(self.current_color)

    def start_screen_pick(self):
        self.picker = ScreenColorPicker();
        self.picker.colorSelected.connect(self.on_wheel_changed);
        self.picker.show()

    def on_wheel_changed(self, color):
        self.current_color = color;
        self.update_all(color, False)

    def on_val_changed(self, val):
        self.color_wheel.set_val(val);
        self.color_wheel.emit()

    def update_all(self, color, update_wheel=True):
        text_col = "white" if color.lightness() < 180 else "black"
        self.left_container.setStyleSheet(
            f"background-color: {color.name()}; border-top-left-radius: 10px; border-bottom-left-radius: 10px;")
        self.btn_pick.setStyleSheet(
            f"background-color: rgba(255,255,255,0.3); border-radius: 18px; border: none; color: {text_col};")
        if update_wheel: self.color_wheel.set_col(color); self.slider_v.setValue(color.value())

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
        QApplication.clipboard().setText(text)