import os
import re
from datetime import datetime

try:
    from natsort import natsorted
except ImportError:
    natsorted = sorted

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QFileDialog, QFrame,
                               QComboBox, QSpinBox, QCheckBox, QSplitter, QStackedWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush

from qfluentwidgets import (PrimaryPushButton, PushButton, LineEdit,
                            StrongBodyLabel, SubtitleLabel, CardWidget,
                            InfoBar, SegmentedWidget, ComboBox, ToolButton,
                            FluentIcon, TransparentToolButton, BodyLabel)

from core.plugin_interface import PluginInterface
from core.resource_manager import qicon


# ==========================================
# 1. 插件定义
# ==========================================
class BatchRenamePlugin(PluginInterface):
    @property
    def name(self) -> str: return "批量重命名"

    @property
    def icon(self):
        return qicon("rename")

    @property
    def group(self) -> str: return "文件工具"

    @property
    def theme_color(self) -> str: return "#009688"

    @property
    def description(self) -> str: return "支持正则、序号、模板重命名的高级工具"

    def create_widget(self) -> QWidget: return BatchRenameWidget()


# ==========================================
# 2. 核心逻辑：重命名引擎
# ==========================================
class RenameEngine:
    @staticmethod
    def process(filename, rules):
        name, ext = os.path.splitext(filename)
        mode = rules.get('mode', 0)  # 0: Replace, 1: Rewrite

        if mode == 1:
            template = rules.get('template_str', '{old}')
            if '{seq}' in template:
                idx = rules['seq_index']
                padding = rules['seq_padding']
                seq_str = f"{idx:0{padding}d}"
                template = template.replace('{seq}', seq_str)
            template = template.replace('{old}', name)
            if '{date}' in template:
                now_str = datetime.now().strftime('%Y%m%d')
                template = template.replace('{date}', now_str)
            new_name = template
        else:
            new_name = name
            if rules['replace_enabled']:
                find_str = rules['find_text']
                rep_str = rules['replace_text']
                if find_str:
                    if rules['use_regex']:
                        try:
                            new_name = re.sub(find_str, rep_str, new_name)
                        except:
                            pass
                    else:
                        new_name = new_name.replace(find_str, rep_str)
            if rules['add_text_enabled']:
                new_name = f"{rules['prefix_text']}{new_name}{rules['suffix_text']}"

        case_mode = rules['case_mode']
        if case_mode == 1:
            new_name = new_name.lower()
        elif case_mode == 2:
            new_name = new_name.upper()
        elif case_mode == 3:
            new_name = new_name.title()

        if rules['ext_mode'] == 1:
            ext = ext.lower()
        elif rules['ext_mode'] == 2:
            ext = ext.upper()

        return f"{new_name}{ext}"


# ==========================================
# 3. 主界面 Widget
# ==========================================
class BatchRenameWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.files = []
        self.init_ui()
        self.setAcceptDrops(True)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)

        # --- 左侧：配置面板 ---
        config_card = CardWidget(self)
        config_card.setFixedWidth(320)
        self.config_layout = QVBoxLayout(config_card)
        self.config_layout.setSpacing(10)

        self.pivot = SegmentedWidget(self)
        self.pivot.addItem("replace", "文本替换")
        self.pivot.addItem("rewrite", "全新命名")
        self.pivot.setCurrentItem("replace")
        self.config_layout.addWidget(self.pivot)

        self.config_layout.addWidget(self.create_separator())

        self.stack = QStackedWidget()

        # Page 1
        self.page_replace = QWidget()
        pr_layout = QVBoxLayout(self.page_replace)
        pr_layout.setContentsMargins(0, 0, 0, 0)

        pr_layout.addWidget(StrongBodyLabel("查找与替换", self))
        self.find_edit = LineEdit(self);
        self.find_edit.setPlaceholderText("查找内容...")
        self.rep_edit = LineEdit(self);
        self.rep_edit.setPlaceholderText("替换为...")
        self.chk_regex = QCheckBox("使用正则表达式", self)

        pr_layout.addWidget(self.find_edit)
        pr_layout.addWidget(self.rep_edit)
        pr_layout.addWidget(self.chk_regex)
        pr_layout.addSpacing(10)

        pr_layout.addWidget(StrongBodyLabel("添加文本", self))
        self.prefix_edit = LineEdit(self);
        self.prefix_edit.setPlaceholderText("前缀...")
        self.suffix_edit = LineEdit(self);
        self.suffix_edit.setPlaceholderText("后缀...")
        pr_layout.addWidget(self.prefix_edit)
        pr_layout.addWidget(self.suffix_edit)
        pr_layout.addStretch(1)

        # Page 2
        self.page_rewrite = QWidget()
        pw_layout = QVBoxLayout(self.page_rewrite)
        pw_layout.setContentsMargins(0, 0, 0, 0)

        pw_layout.addWidget(StrongBodyLabel("文件名模板", self))
        self.template_edit = LineEdit(self)
        self.template_edit.setPlaceholderText("例如: Photo_{date}_{seq}")
        self.template_edit.setText("{old}_{seq}")
        pw_layout.addWidget(self.template_edit)

        btn_vars_layout = QHBoxLayout()
        for tag in ['{seq}', '{date}', '{old}']:
            btn = PushButton(tag, self)
            btn.clicked.connect(lambda ch=False, t=tag: self.template_edit.insert(t))
            btn.setFixedHeight(28)
            btn_vars_layout.addWidget(btn)
        pw_layout.addLayout(btn_vars_layout)

        pw_layout.addWidget(BodyLabel("变量说明:\n{seq}=序号, {date}=日期, {old}=原名", self))
        pw_layout.addStretch(1)

        self.stack.addWidget(self.page_replace)
        self.stack.addWidget(self.page_rewrite)
        self.config_layout.addWidget(self.stack)

        self.config_layout.addWidget(self.create_separator())

        # 通用设置
        self.config_layout.addWidget(StrongBodyLabel("序号设置", self))
        seq_layout = QHBoxLayout()
        self.seq_start = QSpinBox();
        self.seq_start.setRange(0, 9999);
        self.seq_start.setValue(1);
        self.seq_start.setPrefix("起始: ")
        self.seq_padding = QSpinBox();
        self.seq_padding.setRange(1, 10);
        self.seq_padding.setValue(3);
        self.seq_padding.setPrefix("位数: ")
        seq_layout.addWidget(self.seq_start)
        seq_layout.addWidget(self.seq_padding)
        self.config_layout.addLayout(seq_layout)

        self.config_layout.addWidget(self.create_separator())

        self.config_layout.addWidget(StrongBodyLabel("通用格式化", self))
        self.combo_case = ComboBox();
        self.combo_case.addItems(["保持原样", "全部小写", "全部大写", "首字母大写"])
        self.combo_ext = ComboBox();
        self.combo_ext.addItems(["扩展名不变", "扩展名小写", "扩展名大写"])
        self.config_layout.addWidget(self.combo_case)
        self.config_layout.addWidget(self.combo_ext)

        self.config_layout.addStretch(1)

        self.btn_apply = PrimaryPushButton("执行重命名", self)
        self.btn_apply.clicked.connect(self.apply_rename)
        self.config_layout.addWidget(self.btn_apply)

        # --- 右侧：文件列表 ---
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        tool_bar = QHBoxLayout()

        self.btn_add_files = PushButton(qicon("add"), "添加文件", self)
        self.btn_clear = PushButton(qicon("delete"), "清空", self)
        self.lbl_count = SubtitleLabel("0 个文件", self)

        tool_bar.addWidget(self.lbl_count)
        tool_bar.addStretch(1)
        tool_bar.addWidget(self.btn_add_files)
        tool_bar.addWidget(self.btn_clear)

        list_layout.addLayout(tool_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["原文件名", "新文件名", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        list_layout.addWidget(self.table)

        splitter.addWidget(config_card)
        splitter.addWidget(list_container)
        layout.addWidget(splitter)

        # 信号连接
        self.pivot.currentItemChanged.connect(self.on_mode_changed)

        widgets = [
            self.find_edit, self.rep_edit, self.chk_regex,
            self.prefix_edit, self.suffix_edit,
            self.seq_start, self.seq_padding,
            self.combo_case, self.combo_ext,
            self.template_edit
        ]

        # 信号安全连接
        for w in widgets:
            if isinstance(w, LineEdit):
                w.textChanged.connect(self.update_preview)
            elif isinstance(w, QSpinBox):
                w.valueChanged.connect(self.update_preview)
            elif isinstance(w, (QComboBox, ComboBox)):
                w.currentIndexChanged.connect(self.update_preview)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self.update_preview)

        self.btn_add_files.clicked.connect(self.add_files_dialog)
        self.btn_clear.clicked.connect(self.clear_files)

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #e0e0e0;")
        return line

    def on_mode_changed(self, k):
        # 【核心修复】直接使用信号传回来的 key (字符串) 判断
        is_replace = (k == 'replace')
        self.stack.setCurrentIndex(0 if is_replace else 1)
        self.update_preview()

    def get_current_rules(self):
        # 【核心修复】不依赖 SegmentedWidget 的方法，直接依赖 stack 的当前页索引
        # 0: replace, 1: rewrite
        is_rewrite = (self.stack.currentIndex() == 1)

        return {
            'mode': 1 if is_rewrite else 0,
            'template_str': self.template_edit.text(),
            'replace_enabled': bool(self.find_edit.text()),
            'find_text': self.find_edit.text(),
            'replace_text': self.rep_edit.text(),
            'use_regex': self.chk_regex.isChecked(),
            'add_text_enabled': bool(self.prefix_edit.text() or self.suffix_edit.text()),
            'prefix_text': self.prefix_edit.text(),
            'suffix_text': self.suffix_edit.text(),
            'seq_index': self.seq_start.value(),
            'seq_padding': self.seq_padding.value(),
            'case_mode': self.combo_case.currentIndex(),
            'ext_mode': self.combo_ext.currentIndex(),
        }

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "All Files (*)")
        if files: self.add_files(files)

    def add_files(self, file_paths):
        try:
            file_paths = natsorted(file_paths)
        except:
            file_paths.sort()

        for path in file_paths:
            if any(f['path'] == path for f in self.files): continue
            self.files.append({
                'path': path,
                'name': os.path.basename(path),
                'new_name': os.path.basename(path),
                'status': '待处理'
            })
        self.update_preview()

    def clear_files(self):
        self.files = []
        self.update_table_view()
        self.lbl_count.setText("0 个文件")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                for f in os.listdir(path):
                    full = os.path.join(path, f)
                    if os.path.isfile(full): paths.append(full)
            else:
                paths.append(path)
        if paths: self.add_files(paths)

    def update_preview(self):
        if not self.files: return
        rules = self.get_current_rules()
        start_idx = rules['seq_index']
        conflict_map = {}

        for i, file in enumerate(self.files):
            current_rules = rules.copy()
            current_rules['seq_index'] = start_idx + i
            new_name = RenameEngine.process(file['name'], current_rules)
            file['new_name'] = new_name

            if new_name in conflict_map:
                file['status'] = '冲突'
                conflict_map[new_name] = True
            else:
                file['status'] = 'OK'
                conflict_map[new_name] = False

        self.update_table_view()
        self.lbl_count.setText(f"{len(self.files)} 个文件")

    def update_table_view(self):
        self.table.setRowCount(len(self.files))
        for i, file in enumerate(self.files):
            item_old = QTableWidgetItem(file['name'])
            self.table.setItem(i, 0, item_old)

            item_new = QTableWidgetItem(file['new_name'])
            if file['new_name'] != file['name']:
                item_new.setForeground(QBrush(QColor("#009688")))
            if file['status'] == '冲突':
                item_new.setForeground(QBrush(QColor("#F44336")))
                item_new.setText(f"{file['new_name']} (冲突)")
            self.table.setItem(i, 1, item_new)
            self.table.setItem(i, 2, QTableWidgetItem(file['status']))

    def apply_rename(self):
        if not self.files: return
        if any(f['status'] == '冲突' for f in self.files):
            InfoBar.error("错误", "存在命名冲突", parent=self)
            return

        success = 0
        for file in self.files:
            if file['new_name'] == file['name']: continue
            old_path = file['path']
            new_path = os.path.join(os.path.dirname(old_path), file['new_name'])
            try:
                os.rename(old_path, new_path)
                file['name'] = file['new_name']
                file['path'] = new_path
                file['status'] = '完成'
                success += 1
            except Exception as e:
                file['status'] = f'失败: {e}'

        self.update_table_view()
        InfoBar.success("完成", f"成功重命名 {success} 个文件", parent=self)