import sys
import os
import json
import threading
from io import BytesIO
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import keyring  # 记得导入

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QFileDialog, QFrame, QScrollArea, QApplication)
from PySide6.QtCore import Qt, Signal, QThread, QEvent  # 【核心修复】加上 QEvent
from PySide6.QtGui import QPixmap, QColor, QImage, QDragEnterEvent, QDropEvent

from qfluentwidgets import (CardWidget, StrongBodyLabel, BodyLabel, PrimaryPushButton,
                            PushButton, FluentIcon, InfoBar, SegmentedWidget,
                            TransparentToolButton, FlowLayout)

from plugins.color_assistant.services import CollectionService
from plugins.color_assistant.pages.fav_page import PaletteCard
from core.resource_manager import qicon
from core.config import ConfigManager

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from google import genai
    from google.genai import types

    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class ImagePalettePage(QWidget):
    analysis_finished = Signal(dict)
    analysis_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.current_image_path = ""
        self.init_ui()
        self.setAcceptDrops(True)

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)

        # --- 左侧：图片预览区 ---
        self.left_panel = CardWidget(self)
        l_layout = QVBoxLayout(self.left_panel)
        l_layout.setContentsMargins(0, 0, 0, 0)

        self.img_label = QLabel("拖拽图片到这里\n或点击上传", self.left_panel)
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("color: gray; font-size: 14px; border: 2px dashed #e0e0e0; border-radius: 8px;")
        self.img_label.setCursor(Qt.PointingHandCursor)
        self.img_label.mousePressEvent = self.open_file_dialog

        l_layout.addWidget(self.img_label)

        btn_bar = QFrame()
        btn_bar.setFixedHeight(60)
        btn_bar.setStyleSheet("background: transparent;")
        h_btn = QHBoxLayout(btn_bar)

        self.btn_extract = PrimaryPushButton(FluentIcon.PALETTE, "算法提取", self)
        self.btn_extract.clicked.connect(self.extract_colors_algorithm)
        self.btn_extract.setEnabled(False)

        icon_robot = getattr(FluentIcon, 'ROBOT', FluentIcon.PEOPLE)
        self.btn_ai = PushButton(icon_robot, "AI 深度分析", self)
        self.btn_ai.clicked.connect(self.analyze_with_ai)
        self.btn_ai.setEnabled(False)

        h_btn.addWidget(self.btn_extract)
        h_btn.addWidget(self.btn_ai)

        l_layout.addWidget(btn_bar)
        self.layout.addWidget(self.left_panel, 1)

        # --- 右侧：结果展示区 ---
        self.right_panel = QScrollArea()
        self.right_panel.setWidgetResizable(True)
        self.right_panel.setStyleSheet("border: none; background: transparent;")

        self.result_container = QWidget()
        self.right_panel.setWidget(self.result_container)
        r_layout = QVBoxLayout(self.result_container)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(20)

        r_layout.addWidget(StrongBodyLabel("提取结果", self))

        self.result_flow = FlowLayout(needAni=True)
        r_layout.addLayout(self.result_flow)
        r_layout.addStretch(1)

        self.layout.addWidget(self.right_panel, 1)

        self.analysis_finished.connect(self.on_ai_success)
        self.analysis_failed.connect(self.on_ai_error)

    def open_file_dialog(self, event):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path: self.load_image(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        path = event.mimeData().urls()[0].toLocalFile()
        if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
            self.load_image(path)

    def load_image(self, path):
        self.current_image_path = path
        pixmap = QPixmap(path)
        w, h = self.img_label.width(), self.img_label.height()
        self.img_label.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.img_label.setStyleSheet("border: none;")
        self.btn_extract.setEnabled(True)
        self.btn_ai.setEnabled(True)
        self.extract_colors_algorithm()

    def extract_colors_algorithm(self):
        if not self.current_image_path: return
        self.clear_results()
        InfoBar.info("处理中", "正在分析图片色彩...", parent=self.window())
        threading.Thread(target=self._run_kmeans).start()

    def _run_kmeans(self):
        try:
            img = Image.open(self.current_image_path)
            img.thumbnail((150, 150))
            arr = np.array(img)
            pixels = arr.reshape(-1, 3)
            kmeans = KMeans(n_clusters=6, n_init=10)
            kmeans.fit(pixels)
            colors = kmeans.cluster_centers_.astype(int)
            hex_colors = [f"#{r:02x}{g:02x}{b:02x}".upper() for r, g, b in colors]
            QApplication.instance().postEvent(self, ResultEvent(hex_code_list=hex_colors, mode="algo"))
        except Exception as e:
            print(f"KMeans Error: {e}")

    def analyze_with_ai(self):
        if not self.current_image_path: return
        config = ConfigManager.load()
        ai_conf = config.get("ai_palette_config", {})
        api_type = ai_conf.get("type", "OpenAI / DeepSeek")

        if api_type != "Google Gemini":
            InfoBar.warning("建议", "推荐使用 Google Gemini 进行图片分析", parent=self.window())

        if api_type == "Google Gemini" and not HAS_GEMINI:
            InfoBar.error("缺失库", "请安装: google-genai", parent=self.window())
            return

        self.btn_ai.setEnabled(False)
        self.btn_extract.setEnabled(False)
        InfoBar.info("AI 思考中", "正在上传图片并分析...", parent=self.window())

        # 安全获取 Key
        api_key = keyring.get_password("PythonFluentToolbox", f"api_key_{api_type}")
        if api_key: ai_conf['api_key'] = api_key

        threading.Thread(target=self._run_ai_vision, args=(ai_conf,)).start()

    def _run_ai_vision(self, conf):
        try:
            prompt = """
            Analyze this image and extract a color palette of 6-8 colors.
            Also, give this palette a poetic name and a short description of the mood.
            Return JSON only: { "name": "Name", "description": "Desc...", "colors": ["#HEX"] }
            """

            api_type = conf.get("type", "OpenAI / DeepSeek")

            if api_type == "Google Gemini":
                client = genai.Client(api_key=conf['api_key'])
                with open(self.current_image_path, "rb") as f:
                    image_bytes = f.read()

                # 使用新版 SDK 的正确调用方式
                # 注意：Gemini 2.0 可能需要特定的图像格式处理，这里使用最通用的方式
                # 如果报错，可能需要检查 SDK 版本
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(text=prompt),
                                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                            ]
                        )
                    ]
                )
                content = response.text.replace("```json", "").replace("```", "").strip()
                self.analysis_finished.emit(json.loads(content))

            else:
                self.analysis_failed.emit("当前仅支持 Google Gemini 进行图片分析")

        except Exception as e:
            self.analysis_failed.emit(str(e))

    def on_ai_success(self, data):
        self.btn_ai.setEnabled(True);
        self.btn_extract.setEnabled(True)
        self.clear_results()

        item = {
            "name": data.get("name", "AI 提取色板"),
            "colors": data.get("colors", []),
            "type": "palette",
            "id": "temp"
        }

        card = PaletteCard(item, self)
        # 修改删除按钮为收藏
        try:
            # 找到删除按钮并修改
            # 这里假设 PaletteCard 内部结构固定
            # 更稳妥的方式是在 PaletteCard 里加一个 setMode 方法
            # 这里简单修改图标和信号
            btn = card.findChildren(TransparentToolButton)[1]  # 第二个是删除按钮
            btn.setIcon(FluentIcon.HEART.icon())
            btn.setToolTip("收藏此色板")
            btn.clicked.disconnect()
            btn.clicked.connect(lambda: self.save_palette(item))
        except:
            pass

        self.result_flow.addWidget(card)
        desc = BodyLabel(data.get("description", ""), self)
        desc.setWordWrap(True)
        self.result_flow.addWidget(desc)
        InfoBar.success("分析完成", "AI 已提取配色方案", parent=self.window())

    def save_palette(self, item):
        CollectionService.add_palette(item['colors'], item['name'])
        InfoBar.success("已收藏", item['name'], parent=self.window())

    def on_ai_error(self, err):
        self.btn_ai.setEnabled(True);
        self.btn_extract.setEnabled(True)
        InfoBar.error("失败", str(err), parent=self.window())

    def customEvent(self, event):
        if hasattr(event, 'hex_code_list'):
            self.clear_results()
            item = {"name": "算法提取结果", "colors": event.hex_code_list, "type": "palette", "id": "algo_temp"}
            card = PaletteCard(item, self)
            # 同样修改为收藏按钮
            try:
                btn = card.findChildren(TransparentToolButton)[1]
                btn.setIcon(FluentIcon.HEART.icon())
                btn.setToolTip("收藏此色板")
                btn.clicked.disconnect()
                btn.clicked.connect(lambda: self.save_palette(item))
            except:
                pass
            self.result_flow.addWidget(card)

    def clear_results(self):
        while self.result_flow.count():
            item = self.result_flow.takeAt(0)
            if item.widget(): item.widget().deleteLater()


class ResultEvent(QEvent):
    def __init__(self, hex_code_list, mode):
        super().__init__(QEvent.Type(QEvent.User + 1))
        self.hex_code_list = hex_code_list
        self.mode = mode