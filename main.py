import sys
import os
import json
import random
import math
import numpy as np
import sounddevice as sd
import keyboard
import pygame
import collections
import time
import threading

# 尝试导入 tflite_runtime 或 tensorflow
try:
    import tensorflow.lite as tflite
except ImportError:
    try:
        import ai_edge_litert.interpreter as tflite
    except ImportError:
        tflite = None

from pynput import mouse
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QMessageBox, QSystemTrayIcon, QMenu, QInputDialog, QComboBox,
                             QDialog, QTabWidget, QTableWidget, QTableWidgetItem, QListWidget,
                             QListWidgetItem, QHeaderView, QLineEdit, QCheckBox, QStyledItemDelegate)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize, QTimer
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QFont

def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发和PyInstaller打包"""
    try:
        # PyInstaller 会创建一个临时文件夹，将路径存入 _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ----------------- 数据与规则管理器 -----------------
class RuleManager:
    def __init__(self):
        # 兼容 PyInstaller 打包后的路径识别
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe，路径设为 exe 所在目录
            self.pack_dir = os.path.dirname(sys.executable)
        else:
            # 如果是 py 源码运行，路径设为 py 文件所在目录
            self.pack_dir = os.path.dirname(os.path.abspath(__file__))

        self.rule_file = os.path.join(self.pack_dir, "rule.json")
        self.default_rules = {
            "hotkeys": {"random": "k"},
            "enable_hotkey": True,
            "enable_mouse": True,
            "tags": [],
            "tag_colors": {},
            "active_tags": [],
            "search_keyword": "",
            "audios": []
        }
        # 标签颜色管理
        self.tag_colors_palette = [
            "#FF6B6B",  # a: 红
            "#4ECDC4",  # b: 青
            "#45B7D1",  # c: 蓝
            "#96CEB4",  # d: 绿
            "#FFEAA7",  # e: 黄
            "#DDA15E",  # f: 棕
        ]
        self.rules = self.load_rules()

    def load_rules(self):
        if os.path.exists(self.rule_file):
            try:
                with open(self.rule_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return self.default_rules.copy()

    def save_rules(self):
        with open(self.rule_file, 'w', encoding='utf-8') as f:
            json.dump(self.rules, f, ensure_ascii=False, indent=4)

    def load_pack(self, folder_path):
        self.pack_dir = folder_path
        self.rule_file = os.path.join(self.pack_dir, "rule.json")
        self.rules = self.load_rules()
        self.save_rules()

    def open_rule_dir(self):
        import subprocess
        rule_path = os.path.normpath(self.rule_file)
        if os.name == 'nt' and os.path.exists(rule_path):
            subprocess.Popen(f'explorer /select,"{rule_path}"')
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.pack_dir))

    # 新增数据操作方法
    def get_all_audios(self):
        """获取所有音频列表"""
        return self.rules.get("audios", [])

    def delete_audio(self, audio_index):
        """通过索引删除音频"""
        if 0 <= audio_index < len(self.rules.get("audios", [])):
            self.rules["audios"].pop(audio_index)
            self.save_rules()

    def update_audio(self, audio_index, audio_item):
        """更新音频的分类和标签"""
        if 0 <= audio_index < len(self.rules.get("audios", [])):
            self.rules["audios"][audio_index] = audio_item
            self.save_rules()

    def delete_tag(self, tag_name):
        """删除标签，从所有音频中移除该标签"""
        # 从所有音频中删除该标签
        for audio in self.rules.get("audios", []):
            if tag_name in audio.get("tags", []):
                audio["tags"].remove(tag_name)

        # 从标签列表中删除
        if tag_name in self.rules.get("tags", []):
            self.rules["tags"].remove(tag_name)

        self.save_rules()

    def rename_tag(self, old_name, new_name):
        """重命名标签，更新所有关联音频"""
        # 在所有音频中更新标签名
        for audio in self.rules.get("audios", []):
            if old_name in audio.get("tags", []):
                idx = audio["tags"].index(old_name)
                audio["tags"][idx] = new_name

        # 在标签列表中更新
        if old_name in self.rules.get("tags", []):
            idx = self.rules["tags"].index(old_name)
            self.rules["tags"][idx] = new_name

        self.save_rules()

    def add_tag(self, tag_name):
        """添加新标签"""
        if tag_name and tag_name not in self.rules.get("tags", []):
            self.rules.setdefault("tags", []).append(tag_name)
            # 为新标签分配颜色
            color = self.assign_tag_color(tag_name)
            self.save_rules()
            return True
        return False

    # 标签颜色管理
    def assign_tag_color(self, tag_name):
        """为标签分配颜色（按首字母）"""
        if tag_name not in self.rules.get("tag_colors", {}):
            # 按首字母分配颜色
            first_char = tag_name[0].lower() if tag_name else 'a'
            char_code = ord(first_char) - ord('a')
            color_idx = char_code % len(self.tag_colors_palette)
            color = self.tag_colors_palette[color_idx]

            self.rules.setdefault("tag_colors", {})[tag_name] = color
            self.save_rules()
            return color
        return self.rules["tag_colors"][tag_name]

    def get_tag_color(self, tag_name):
        """获取标签颜色，不存在则分配"""
        if tag_name not in self.rules.get("tag_colors", {}):
            return self.assign_tag_color(tag_name)
        return self.rules["tag_colors"][tag_name]

    def update_audio_enabled(self, audio_index, enabled):
        """更新音频的启用状态"""
        if 0 <= audio_index < len(self.rules.get("audios", [])):
            self.rules["audios"][audio_index]["enabled"] = enabled
            self.save_rules()

    def get_random_audio(self, laugh_type, search_keyword=""):
        """根据笑声类型和搜索关键词获取随机音频"""
        active_tags = self.rules.get("active_tags", [])
        candidates = []

        for audio in self.rules.get("audios", []):
            # 检查启用状态
            if not audio.get("enabled", True):
                continue

            # 检查笑声类型
            if laugh_type != "any" and audio.get("type") != laugh_type:
                continue

            # 检查标签筛选
            if active_tags:
                if not any(tag in audio.get("tags", []) for tag in active_tags):
                    continue

            # 检查文件名搜索
            if search_keyword:
                audio_name = os.path.basename(audio.get("path", "")).lower()
                if search_keyword.lower() not in audio_name:
                    continue

            candidates.append(audio.get("path"))

        if candidates:
            # 处理相对路径
            path = random.choice(candidates)
            if not os.path.isabs(path):
                path = os.path.join(self.pack_dir, path)
            return path
        return None

    def set_search_keyword(self, keyword):
        """设置搜索关键词"""
        self.rules["search_keyword"] = keyword
        self.save_rules()

# ----------------- 后台监听线程 -----------------
class MicListener(QThread):
    trigger_signal = pyqtSignal(str) # bitter, awkward, belly

    def __init__(self):
        super().__init__()
        self.running = True
        # 初始化 YAMNet
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.target_indices = {}
        self.last_trigger_time = 0  # 添加冷却机制防止连续误触
        self.cooldown_period = 0.5  # 500ms 冷却时间
        
        if tflite is not None:
            try:
                # 获取路径使用 MEIPASS 确保打包后能找到 tflite 模型
                model_path = resource_path(os.path.join("assets", "models", "yamnet.tflite"))
                
                if os.path.exists(model_path):
                    self.interpreter = tflite.Interpreter(model_path=model_path)
                    self.interpreter.allocate_tensors()
                    self.input_details = self.interpreter.get_input_details()
                    self.output_details = self.interpreter.get_output_details()

                    # 直接硬编码 YAMNet 标准输出索引与类别的映射，彻底移除对 CSV 文件的依赖
                    self.target_indices = {
                        13: "laughter", 
                        14: "baby_laughter", 
                        15: "giggle", 
                        16: "snicker", 
                        17: "belly_laugh", 
                        18: "chuckle"
                    }
            except Exception as e:
                print(f"YAMNet初始化失败: {e}")

    def run(self):
        buffer_size = 15600 # 0.975s * 16000Hz (YamNet所需固定输入尺寸)
        self.audio_buffer = np.zeros(buffer_size, dtype=np.float32)

        def audio_callback(indata, frames, time, status):
            if not self.running: return
            
            # YAMNet 需要范围大概在这儿的数据单声道 float32[-1.0, 1.0]
            audio_data = indata[:, 0].astype(np.float32)
            
            if self.interpreter is not None and self.target_indices:
                self.process_audio(audio_data)
            else:
                # 依然留着无模型时的原始保底音量判断方案 (优化阈值)
                volume_norm = np.linalg.norm(audio_data) * 10
                if volume_norm > 100:
                    self.trigger_signal.emit("belly_laugh")
                elif volume_norm > 50:
                    self.trigger_signal.emit("laughter")
                elif volume_norm > 15:
                    self.trigger_signal.emit("chuckle")

        try:
            # 每 0.5s 回调拉取一次录音去过 YAMNet，平衡精度和性能
            block_size = int(16000 * 0.5) 
            with sd.InputStream(callback=audio_callback, channels=1, samplerate=16000, blocksize=block_size):
                while self.running:
                    self.msleep(100)
        except Exception as e:
            print("麦克风监听失败:", e)

    # 抽取出来专门处理缓冲和模型推理
    def process_audio(self, audio_data):
        current_time = time.time()
        # 检查冷却期，防止连续触发导致分类混乱
        if current_time - self.last_trigger_time < self.cooldown_period:
            return

        self.audio_buffer = np.roll(self.audio_buffer, -len(audio_data))
        self.audio_buffer[-len(audio_data):] = audio_data

        # 音量太小则跳过推理，节省CPU
        if np.linalg.norm(audio_data) * 10 < 0.5:
            return

        try:
            self.interpreter.set_tensor(self.input_details[0]['index'], self.audio_buffer.astype(np.float32))
            self.interpreter.invoke()
            scores = self.interpreter.get_tensor(self.output_details[0]['index'])[0] # shape (521,)

            # 每个笑声类别的专属置信度阈值 (根据识别难度和误分类风险调整)
            # 目标：提高准确度，减少误分类
            thresholds = {
                17: 0.10,  # belly_laugh (开怀大笑) - 最容易被snicker误识别，提高阈值
                18: 0.09,  # chuckle (憨笑) - 容易被giggle误识别，提高阈值
                16: 0.08,  # snicker (窃笑)
                15: 0.08,  # giggle (咯咯笑)
                14: 0.08,  # baby_laughter (婴儿笑)
                13: 0.07   # laughter (普通笑)
            }

            trigger_idx = None

            # 优先级顺序检查：先检查最明显的类别，防止被相似的混淆
            priority_order = [17, 18, 16, 15, 14, 13]  # belly_laugh优先，然后chuckle，最后普通笑

            for idx in priority_order:
                if scores[idx] >= thresholds[idx]:
                    trigger_idx = idx
                    break

            if trigger_idx is not None:
                self.trigger_signal.emit(self.target_indices[trigger_idx])
                self.last_trigger_time = current_time
                # 发射信号后清空缓冲，防止马上又连续触发
                self.audio_buffer.fill(0)
        except Exception as e:
            print(f"YAMNet 推理失败: {e}")

class MouseGestureListener(QThread):
    trigger_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.points = []
        self.enabled = True

    def run(self):
        def on_move(x, y):
            if not self.enabled or not self.running:
                return
            
            curr_time = time.time()
            self.points.append((x, y, curr_time))
            # 仅保留最近1.5秒内的轨迹点
            self.points = [p for p in self.points if curr_time - p[2] < 1.5]
            
            self.analyze_gesture()

        with mouse.Listener(on_move=on_move) as listener:
            while self.running:
                self.msleep(100)

    def analyze_gesture(self):
        if len(self.points) < 20: 
            return
        
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        
        # 计算轨迹总长度
        path_len = 0
        for i in range(1, len(self.points)):
            path_len += math.hypot(xs[i]-xs[i-1], ys[i]-ys[i-1])
            
        if path_len < 200:
            return
            
        # 检查起点和当前点的距离（闭合程度）
        start_end_dist = math.hypot(xs[-1]-xs[0], ys[-1]-ys[0])
        
        # 计算外接矩形
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w = max_x - min_x
        h = max_y - min_y
        
        if w < 50 or h < 50:
            return
            
        # 如果起点和终点距离太远，则不认为是闭合的圈
        if start_end_dist > max(w, h) * 0.4:
            return
            
        # 根据外接矩形估算一个圆的周长: pi * (w+h)/2
        expected_len = math.pi * (w + h) / 2
        
        # 如果轨迹长度在这个合理的圆的周长范围内
        if 0.6 * expected_len < path_len < 1.5 * expected_len:
            self.trigger_signal.emit("any")
            self.points.clear() # 清空避免连续触发

# --------- 标签多选对话框 ---------
class TagMultiSelectDialog(QDialog):
    """标签多选对话框"""
    def __init__(self, parent, all_tags, selected_tags, rule_manager):
        super().__init__(parent)
        self.all_tags = all_tags
        self.selected_tags = selected_tags
        self.rm = rule_manager
        self.checked_tags = set(selected_tags)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("编辑标签")
        self.setGeometry(200, 200, 400, 300)
        layout = QVBoxLayout(self)

        label = QLabel("选择标签 (可多选):")
        layout.addWidget(label)

        # 标签复选框区域
        self.checkboxes = {}
        for tag in self.all_tags:
            checkbox = QCheckBox(tag)
            checkbox.setChecked(tag in self.selected_tags)
            checkbox.stateChanged.connect(lambda state, t=tag: self.on_tag_toggled(t, state))
            self.checkboxes[tag] = checkbox
            layout.addWidget(checkbox)

        # 新增标签输入
        layout.addSpacing(10)
        input_layout = QHBoxLayout()
        input_label = QLabel("新增标签:")
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("输入新标签名...")
        btn_add_tag = QPushButton("添加")
        btn_add_tag.clicked.connect(self.add_new_tag)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.new_tag_input)
        input_layout.addWidget(btn_add_tag)
        layout.addLayout(input_layout)

        layout.addStretch()

        # 确认和取消按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_tag_toggled(self, tag, state):
        """处理标签勾选变化"""
        if state == Qt.CheckState.Checked.value:
            self.checked_tags.add(tag)
        else:
            self.checked_tags.discard(tag)

    def add_new_tag(self):
        """添加新标签"""
        tag_name = self.new_tag_input.text().strip()
        if tag_name and tag_name not in self.all_tags:
            if self.rm.add_tag(tag_name):
                checkbox = QCheckBox(tag_name)
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(lambda state, t=tag_name: self.on_tag_toggled(t, state))
                self.layout().insertWidget(self.layout().count() - 3, checkbox)
                self.checkboxes[tag_name] = checkbox
                self.all_tags.append(tag_name)
                self.checked_tags.add(tag_name)
                self.new_tag_input.clear()
                QMessageBox.information(self, "成功", f"标签 '{tag_name}' 已添加")

    def get_selected_tags(self):
        """获取选中的标签"""
        return list(self.checked_tags)

# --------- 表格委托类 ---------
class CategoryDelegate(QStyledItemDelegate):
    """笑声类别下拉列表委托"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.categories = ["普通笑", "婴儿笑", "咯咯笑", "窃笑", "开怀大笑", "憨笑"]
        self.type_map = {
            "普通笑": "laughter",
            "婴儿笑": "baby_laughter",
            "咯咯笑": "giggle",
            "窃笑": "snicker",
            "开怀大笑": "belly_laugh",
            "憨笑": "chuckle"
        }
        self.type_map_reverse = {v: k for k, v in self.type_map.items()}

    def createEditor(self, parent, option, index):
        """创建编辑器（下拉框）"""
        combo = QComboBox(parent)
        combo.addItems(self.categories)
        QTimer.singleShot(0, combo.showPopup)
        return combo

    def setEditorData(self, editor, index):
        """设置编辑器显示的数据"""
        text = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        combo = editor
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        """设置模型数据"""
        combo = editor
        text = combo.currentText()
        model.setData(index, text, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何数据"""
        editor.setGeometry(option.rect)


class TagDelegate(QStyledItemDelegate):
    """标签多选委托"""
    def __init__(self, parent, all_tags, rule_manager):
        super().__init__(parent)
        self.all_tags = all_tags
        self.rm = rule_manager

    def createEditor(self, parent, option, index):
        """创建编辑器 - 打开标签多选对话框"""
        # 这里我们直接返回一个按钮效果的编辑器
        # 实际上会通过双击或特殊处理触发对话框
        btn = QPushButton("编辑", parent)
        return btn

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何数据"""
        editor.setGeometry(option.rect)

class TagCellWidget(QWidget):
    def __init__(self, tags, rule_manager, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        for tag in tags:
            lbl = QLabel(tag)
            color = rule_manager.get_tag_color(tag)
            lbl.setStyleSheet(f"background-color: {color}; color: white; border-radius: 4px; padding: 2px 6px; font-weight: bold;")
            layout.addWidget(lbl)
        layout.addStretch()

class TagMenu(QMenu):
    def __init__(self, parent, all_tags, current_tags, rule_manager):
        super().__init__(parent)
        from PyQt6.QtWidgets import QWidgetAction, QCheckBox, QLineEdit, QHBoxLayout, QPushButton, QWidget, QCompleter, QInputDialog
        from PyQt6.QtCore import Qt, QStringListModel
        from PyQt6.QtGui import QAction
        
        self.rm = rule_manager
        self.all_tags = list(all_tags) 
        self.current_tags = set(current_tags)
        self.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #ccc; border-radius: 6px; padding: 4px; }
            QMenu::item { padding: 4px 10px; }
        """)
        
        self.items_per_page = 5
        self.current_page = 0
        self.checkboxes = {}
        
        # 1. 顶部搜索框
        self.search_action = QWidgetAction(self)
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("搜索标签...")
        self.search_box.setStyleSheet("QLineEdit { padding: 4px; border: 1px solid #aaa; border-radius: 4px; margin: 4px 10px; }")
        
        self.completer = QCompleter(self.all_tags, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setMaxVisibleItems(5)
        self.search_box.setCompleter(self.completer)
        
        self.search_action.setDefaultWidget(self.search_box)
        self.addAction(self.search_action)
        self.addSeparator()

        self.filtered_tags = list(self.all_tags)
        self.search_box.textChanged.connect(self._filter_tags)

        self.tag_actions = []
        
        # 2. 分页按钮支持
        self.page_action = QWidgetAction(self)
        self.page_widget = QWidget(self)
        self.page_layout = QHBoxLayout(self.page_widget)
        self.page_layout.setContentsMargins(10, 4, 10, 4)
        
        self.prev_btn = QPushButton("上一页")
        self.next_btn = QPushButton("下一页")
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn.clicked.connect(self._next_page)
        
        self.page_layout.addWidget(self.prev_btn)
        self.page_layout.addWidget(self.next_btn)
        self.page_action.setDefaultWidget(self.page_widget)
        
        # 3. 添加新标签
        self.add_separator = self.addSeparator()
        self.add_new_action = QAction("➕ 新增标签...", self)
        self.add_new_action.triggered.connect(self._add_new_tag)
        self.addAction(self.add_new_action)

        self._refresh_view()

    def _filter_tags(self, text):
        if not text:
            self.filtered_tags = list(self.all_tags)
        else:
            self.filtered_tags = [t for t in self.all_tags if text.lower() in t.lower()]
        self.current_page = 0
        self._refresh_view()

    def _refresh_view(self):
        from PyQt6.QtWidgets import QWidgetAction, QCheckBox
        
        # 移除旧项
        for act in self.tag_actions:
            self.removeAction(act)
        self.tag_actions.clear()
        
        if self.page_action in self.actions():
            self.removeAction(self.page_action)
        self.removeAction(self.add_separator)
        self.removeAction(self.add_new_action)
            
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_tags = self.filtered_tags[start_idx:end_idx]
        
        # 添加当前页的 tags
        for tag in page_tags:
            action = QWidgetAction(self)
            cb = QCheckBox(tag, self)
            cb.setChecked(tag in self.current_tags)
            cb.setStyleSheet("padding: 4px 10px;")
            cb.toggled.connect(lambda checked, t=tag: self._on_toggled(t, checked))
            action.setDefaultWidget(cb)
            
            self.addAction(action)
            self.tag_actions.append(action)
            self.checkboxes[tag] = cb
            
        # 添加分页按钮（如果大于5项）
        if len(self.filtered_tags) > self.items_per_page:
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(end_idx < len(self.filtered_tags))
            self.addAction(self.page_action)
            
        self.addAction(self.add_separator)
        self.addAction(self.add_new_action)

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_view()

    def _next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.filtered_tags):
            self.current_page += 1
            self._refresh_view()

    def _on_toggled(self, tag, checked):
        if checked:
            self.current_tags.add(tag)
        else:
            self.current_tags.discard(tag)

    def _add_new_tag(self):
        from PyQt6.QtWidgets import QInputDialog
        from PyQt6.QtCore import QStringListModel
        new_tag, ok = QInputDialog.getText(self.parent(), "添加标签", "输入新标签名:")
        if ok and new_tag:
            tag_name = new_tag.strip()
            if tag_name and tag_name not in self.rm.rules.get("tags", []):
                self.rm.add_tag(tag_name)
                
            if tag_name not in self.all_tags:
                self.all_tags.append(tag_name)
                # 更新自动补全模型
                self.completer.setModel(QStringListModel(self.all_tags))
                
            self.current_tags.add(tag_name)
            self.search_box.clear()
            self._filter_tags("")

    def get_selected_tags(self):
        return list(self.current_tags)

# ----------------- 音频管理对话框 -----------------
class AudioManagementDialog(QDialog):
    def __init__(self, parent, rule_manager):
        super().__init__(parent)
        self.rm = rule_manager
        self.parent_window = parent
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        self.setWindowTitle("管理")
        self.setGeometry(100, 100, 700, 500)
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tabs = QTabWidget()

        # 标签页1：音频管理
        self.audio_tab = QWidget()
        self.init_audio_tab()
        self.tabs.addTab(self.audio_tab, "🎵 音频管理")

        # 标签页2：导入管理
        self.import_tab = QWidget()
        self.init_import_tab()
        self.tabs.addTab(self.import_tab, "📦 音笑包管理")

        # 标签页3：标签管理
        self.tag_tab = QWidget()
        self.init_tag_tab()
        self.tabs.addTab(self.tag_tab, "🏷️ 标签管理")

        # 标签页4：分类管理
        self.category_tab = QWidget()
        self.init_category_tab()
        self.tabs.addTab(self.category_tab, "🤣 笑声类别")

        layout.addWidget(self.tabs)

    def init_audio_tab(self):
        layout = QVBoxLayout(self.audio_tab)

        # 提示文本
        hint_label = QLabel("单击笑声类别或标签下拉选择 | 双击文件路径浏览")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint_label)

        # 创建音频表格
        self.audio_table = QTableWidget()
        self.audio_table.setColumnCount(4)
        self.audio_table.setHorizontalHeaderLabels(["启用", "文件路径", "笑声类别", "标签"])
        self.audio_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.audio_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.audio_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.audio_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        # 设置分类列的委托（下拉列表）
        self.category_delegate = CategoryDelegate(self.audio_table)
        self.audio_table.setItemDelegateForColumn(2, self.category_delegate)

        # 连接信号
        self.audio_table.cellDoubleClicked.connect(self.on_audio_cell_double_clicked)
        self.audio_table.cellClicked.connect(self.on_audio_cell_clicked)
        self.audio_table.itemChanged.connect(self.on_audio_item_changed)
        layout.addWidget(self.audio_table)

        # 按钮区
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ 添加")
        btn_add.clicked.connect(self.add_audio_row)
        btn_layout.addWidget(btn_add)

        btn_delete = QPushButton("❌ 删除选中")
        btn_delete.clicked.connect(self.delete_audio)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

    def init_import_tab(self):
        layout = QVBoxLayout(self.import_tab)

        btn_style = """
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 6px;
                font-weight: bold;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #f2f2f7;
                border-color: #a0a0a0;
            }
            QPushButton:pressed {
                background-color: #e5e5ea;
            }
        """

        btn_import_pack = QPushButton("📥 导入音笑包")
        btn_import_pack.setFixedHeight(40)
        btn_import_pack.setStyleSheet(btn_style)
        btn_import_pack.clicked.connect(self.import_pack)
        layout.addWidget(btn_import_pack)

        btn_open_dir = QPushButton("📁 打开规则集位置")
        btn_open_dir.setFixedHeight(40)
        btn_open_dir.setStyleSheet(btn_style)
        btn_open_dir.clicked.connect(self.rm.open_rule_dir)
        layout.addWidget(btn_open_dir)

        layout.addStretch()

    def init_tag_tab(self):
        layout = QVBoxLayout(self.tag_tab)

        label = QLabel("已有标签列表:")
        layout.addWidget(label)

        # 标签列表
        self.tag_list = QListWidget()
        self.tag_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.tag_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.tag_list.setSpacing(5)
        self.tag_list.setMovement(QListWidget.Movement.Static)
        self.tag_list.itemDoubleClicked.connect(self.rename_tag)
        layout.addWidget(self.tag_list)

        # 按钮区
        btn_layout = QHBoxLayout()

        btn_add = QPushButton("➕ 添加")
        btn_add.clicked.connect(self.add_tag)
        btn_layout.addWidget(btn_add)

        btn_rename = QPushButton("✏️ 修改")
        btn_rename.clicked.connect(self.rename_tag)
        btn_layout.addWidget(btn_rename)

        btn_delete = QPushButton("❌ 删除")
        btn_delete.clicked.connect(self.delete_tag)
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

    def init_category_tab(self):
        layout = QVBoxLayout(self.category_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        
        card = QWidget()
        card.setStyleSheet("QWidget { background-color: #FFFFFF; border-radius: 10px; border: 1px solid #DEE2E6; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        title = QLabel("🔊 笑声分类说明")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("border: none; color: #333;")
        card_layout.addWidget(title)

        categories_info = [
            ("😀 普通笑 (laughter)", "一般性的笑声，未被细分归类的笑声"),
            ("🤭 窃笑 (snicker)", "哭笑不明，那就是笑了"),
            ("👶 婴儿笑 (baby_laughter)", "婴儿特有的笑声，较高频率"),
            ("🤓 憨笑 (chuckle)", "温和的、轻的笑声"),
            ("😆 咯咯笑 (giggle)", "轻快的、清脆的笑声"),
            ("🤣 开怀大笑 (belly_laugh)", "大声的、持续的笑声")
        ]

        for name, desc in categories_info:
            item_lbl = QLabel(f"<b>{name}</b>：{desc}")
            item_lbl.setFont(QFont("Microsoft YaHei", 11))
            item_lbl.setStyleSheet("border: none; color: #555;")
            card_layout.addWidget(item_lbl)

        card_layout.addStretch()
        layout.addWidget(card)

    def refresh_audio_table(self):
        """刷新音频表格"""
        if hasattr(self.parent(), 'refresh_search_completer'):
            self.parent().refresh_search_completer()
            
        self.audio_table.blockSignals(True)  # 临时阻止信号，避免在填充时触发
        self.audio_table.setRowCount(0)
        audios = self.rm.get_all_audios()

        type_names = {
            "laughter": "普通笑",
            "snicker": "窃笑",
            "baby_laughter": "婴儿笑",
            "giggle": "咯咯笑",
            "chuckle": "憨笑",
            "belly_laugh": "开怀大笑"
        }

        for idx, audio in enumerate(audios):
            self.audio_table.insertRow(idx)

            # 第0列：启用状态 (checkbox)
            checkbox = QCheckBox()
            checkbox.setChecked(audio.get("enabled", True))
            checkbox.toggled.connect(lambda checked, r=idx: self.rm.update_audio_enabled(r, checked))
            self.audio_table.setCellWidget(idx, 0, checkbox)

            # 第1列：文件路径
            path_item = QTableWidgetItem(audio.get("path", ""))
            self.audio_table.setItem(idx, 1, path_item)

            # 第2列：笑声类别
            type_name = type_names.get(audio.get("type", ""), audio.get("type", ""))
            type_item = QTableWidgetItem(type_name)
            self.audio_table.setItem(idx, 2, type_item)

            # 第3列：标签
            tags_item = QTableWidgetItem()
            # 这一列不可编辑，依然通过单击触发多选对话框
            tags_item.setFlags(tags_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.audio_table.setItem(idx, 3, tags_item)
            tag_widget = TagCellWidget(audio.get("tags", []), self.rm)
            self.audio_table.setCellWidget(idx, 3, tag_widget)

        self.audio_table.blockSignals(False)  # 恢复信号

    def on_audio_item_changed(self, item):
        """处理表格项变化"""
        row = item.row()
        col = item.column()
        if col == 2:
            new_text = item.text()
            if row < len(self.rm.rules.get("audios", [])):
                audio = self.rm.rules["audios"][row]
                type_map_reverse = {
                    "普通笑": "laughter", "婴儿笑": "baby_laughter",
                    "咯咯笑": "giggle", "窃笑": "snicker",
                    "开怀大笑": "belly_laugh", "憨笑": "chuckle"
                }
                audio["type"] = type_map_reverse.get(new_text, "laughter")
                self.rm.update_audio(row, audio)

    def on_audio_cell_clicked(self, row, col):
        """处理单元格单击事件"""
        if row < 0:
            return

        audio = self.rm.get_all_audios()[row]

        if col == 2:  # 笑声类别列 - 自动显示下拉列表
            self.audio_table.editItem(self.audio_table.item(row, col))

        elif col == 3:  # 标签列 - 打开标签多选下拉菜单
            all_tags = self.rm.rules.get("tags", [])
            current_tags = audio.get("tags", [])
            menu = TagMenu(self, all_tags, current_tags, self.rm)
            rect = self.audio_table.visualRect(self.audio_table.model().index(row, col))
            global_pos = self.audio_table.viewport().mapToGlobal(rect.bottomLeft())
            menu.exec(global_pos)
            
            selected_tags = menu.get_selected_tags()
            if set(selected_tags) != set(current_tags):
                audio["tags"] = selected_tags
                self.rm.update_audio(row, audio)
                self.parent_window.refresh_tag_combo()
                # 只刷新当前行的UI以提升体验
                tag_widget = TagCellWidget(selected_tags, self.rm)
                self.audio_table.setCellWidget(row, 3, tag_widget)

    def on_audio_cell_double_clicked(self, row, col):
        """处理单元格双击编辑"""
        if row < 0:
            return

        audio = self.rm.get_all_audios()[row]

        if col == 0:  # 启用列 - 切换checkbox
            checkbox = self.audio_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not checkbox.isChecked())
                enabled = checkbox.isChecked()
                self.rm.update_audio_enabled(row, enabled)

        elif col == 1:  # 文件路径列 - 打开文件浏览对话框
            file_path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "Audio Files (*.mp3 *.wav *.ogg)")
            if file_path:
                # 处理相对路径
                rel_path = file_path
                if os.path.dirname(file_path) == self.rm.pack_dir:
                    rel_path = os.path.basename(file_path)

                audio["path"] = rel_path
                self.rm.update_audio(row, audio)
                self.refresh_audio_table()

    def add_audio_row(self):
        """添加新音频行"""
        new_audio = {
            "path": "",
            "type": "laughter",
            "tags": [],
            "enabled": True
        }

        self.rm.rules.setdefault("audios", []).append(new_audio)
        self.rm.save_rules()
        self.parent_window.refresh_tag_combo()
        self.refresh_audio_table()
        
        # 选中并滚动到最后一行
        last_row = self.audio_table.rowCount() - 1
        if last_row >= 0:
            self.audio_table.selectRow(last_row)
            self.audio_table.scrollToBottom()

    def delete_audio(self):
        """删除选中的音频"""
        current_row = self.audio_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "提示", "请选择要删除的音频")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除此音频吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self.rm.delete_audio(current_row)
            self.parent_window.refresh_tag_combo()
            self.refresh_audio_table()
            QMessageBox.information(self, "成功", "音频已删除")

    def add_tag(self):
        """添加新标签"""
        new_tag, ok = QInputDialog.getText(self, "添加标签", "输入新标签名:")
        if ok and new_tag:
            if self.rm.add_tag(new_tag):
                self.parent_window.refresh_tag_combo()
                self.refresh_tag_list()
                QMessageBox.information(self, "成功", f"标签 '{new_tag}' 已添加")
            else:
                QMessageBox.warning(self, "提示", "标签已存在或输入为空")

    def refresh_tag_list(self):
        """刷新标签列表"""
        from PyQt6.QtGui import QBrush
        self.tag_list.clear()
        tags = self.rm.rules.get("tags", [])
        for tag in tags:
            item = QListWidgetItem()
            w = TagCellWidget([tag], self.rm)
            item.setSizeHint(w.sizeHint())
            # For data retrieval later 
            item.setText(tag)
            item.setForeground(QBrush(Qt.GlobalColor.transparent))
            self.tag_list.addItem(item)
            self.tag_list.setItemWidget(item, w)

    def rename_tag(self):
        """重命名标签"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要重命名的标签")
            return

        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "重命名标签", f"输入新名称 (当前: {old_name}):")

        if ok and new_name:
            self.rm.rename_tag(old_name, new_name)
            self.parent_window.refresh_tag_combo()
            self.refresh_tag_list()
            self.refresh_audio_table()
            QMessageBox.information(self, "成功", f"标签已重命名为 '{new_name}'")

    def delete_tag(self):
        """删除标签"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请选择要删除的标签")
            return

        tag_name = current_item.text()
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除标签'{tag_name}'吗？\n这将从所有音频中移除该标签，但不会删除音频本身。"
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.rm.delete_tag(tag_name)
            self.parent_window.refresh_tag_combo()
            self.refresh_tag_list()
            self.refresh_audio_table()
            QMessageBox.information(self, "成功", f"标签 '{tag_name}' 已删除")

    def import_pack(self):
        """导入音笑包"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择音笑包文件夹 (包含 rule.json)")
        if dir_path:
            self.rm.load_pack(dir_path)
            self.parent_window.refresh_tag_combo()
            self.refresh_all()
            QMessageBox.information(self, "成功", "音笑包已加载！")

    def refresh_all(self):
        """刷新所有内容"""
        self.refresh_audio_table()
        self.refresh_tag_list()

# ----------------- 主图形界面 -----------------
class HotkeyCaptureDialog(QDialog):
    def __init__(self, parent=None, current_hotkey=""):
        super().__init__(parent)
        self.setWindowTitle("捕捉快捷键")
        self.setFixedSize(320, 160)
        self.hotkey = current_hotkey
        
        layout = QVBoxLayout(self)
        self.lbl_instruction = QLabel("请直接按下你要设置的快捷键组合\n完成后按 Enter 确认，按 Esc 取消")
        self.lbl_instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_instruction)
        
        self.lbl_hotkey = QLabel(self.hotkey if self.hotkey else "等待按键...")
        self.lbl_hotkey.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hotkey.setStyleSheet("font-size: 18px; font-weight: bold; color: #007aff;")
        layout.addWidget(self.lbl_hotkey)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("确定")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        from PyQt6.QtGui import QKeySequence
        key = event.key()
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
            
        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("windows")
            
        key_text = ""
        if key not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            key_name = QKeySequence(key).toString().lower()
            if key_name == " ":
                key_text = "space"
            elif key_name:
                key_text = key_name
                
        parts = modifiers
        if key_text:
            parts.append(key_text)
            
        if parts:
            self.hotkey = "+".join(parts)
            self.lbl_hotkey.setText(self.hotkey)

    def get_hotkey(self):
        return self.hotkey

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rm = RuleManager()
        self.current_search_keyword = ""  # 搜索关键词
        self.init_ui()
        self.init_audio_player()
        self.init_threads()
        self.init_hotkeys()
        self.is_listening = False

    def init_ui(self):
        self.setWindowTitle("笑声罐头")
        self.setWindowIcon(QIcon(resource_path("laughter_can.ico")))
        self.setFixedSize(500, 600)
        self.setStyleSheet("background-color: #f5f5f7; color: #333;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 状态指示
        self.status_label = QLabel("点击开启检测")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        layout.addWidget(self.status_label)

        # 检测结果展示
        self.detect_label = QLabel("检测未开启")
        self.detect_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detect_label.setStyleSheet("color: #888; font-size: 13px; margin-bottom: 10px;")
        layout.addWidget(self.detect_label)

        # 核心巨大开关按钮
        self.toggle_btn = QPushButton("开启笑声检测")
        self.toggle_btn.setFixedSize(360, 100)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9500; 
                color: white; 
                border-radius: 15px; 
                border: none;
                font-size: 44px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover { background-color: #ffaa33; }
        """)
        self.toggle_btn.clicked.connect(self.toggle_listening)
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(5)
        
        # ====== 独立触发开关区 ======
        trigger_layout = QHBoxLayout()
        trigger_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cb_hotkey_enabled = QCheckBox("启用快捷键触发")
        self.cb_hotkey_enabled.setChecked(self.rm.rules.get("enable_hotkey", True))
        self.cb_hotkey_enabled.stateChanged.connect(self.on_hotkey_toggled)
        
        self.cb_mouse_enabled = QCheckBox("启用鼠标手势触发")
        self.cb_mouse_enabled.setChecked(self.rm.rules.get("enable_mouse", True))
        self.cb_mouse_enabled.stateChanged.connect(self.on_mouse_toggled)
        
        trigger_layout.addWidget(self.cb_hotkey_enabled)
        trigger_layout.addSpacing(10)
        trigger_layout.addWidget(self.cb_mouse_enabled)
        layout.addLayout(trigger_layout)

        layout.addSpacing(5)

        # ====== 组合筛选区域 ======
        filter_group = QWidget()
        filter_group.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }
            QLabel { border: none; background: transparent; }
            QPushButton { margin: 0; }
        """)
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(10)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("文件名筛选 🔍")
        search_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        search_label.setFixedWidth(100)
        self.search_input = QLineEdit()
        self.search_input.setText(self.rm.rules.get("search_keyword", ""))
        self.search_input.setPlaceholderText("请输入关键字...")
        self.search_input.setStyleSheet("border-radius: 4px; border: 1px solid #d1d1d6; padding: 4px;")
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        filter_layout.addLayout(search_layout)

        # 标签筛选
        from PyQt6.QtWidgets import QSizePolicy
        tag_layout = QHBoxLayout()
        tag_label = QLabel("标签筛选  🏷️")
        tag_label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        tag_label.setFixedWidth(100)
        self.btn_tag_filter = QPushButton("全部标签")
        self.btn_tag_filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_tag_filter.setFont(QFont("Microsoft YaHei", 10))
        self.btn_tag_filter.setStyleSheet("background-color: #f2f2f7; border: 1px solid #e5e5ea; border-radius: 4px; padding: 4px 10px; text-align: left;")
        self.btn_tag_filter.clicked.connect(self.open_tag_filter_dialog)
        tag_layout.addWidget(tag_label)
        tag_layout.addWidget(self.btn_tag_filter)
        filter_layout.addLayout(tag_layout)
        self.refresh_tag_combo()
        
        self.refresh_search_completer()

        # 应用按钮
        self.btn_apply = QPushButton("应用筛选")
        self.btn_apply.setMinimumHeight(36)
        self.btn_apply.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: #ffffff;
                border-radius: 6px;
                border: none;
                padding: 6px;
            }
            QPushButton:hover { background-color: #006ee6; }
            QPushButton:pressed { background-color: #005bb5; }
        """)
        self.btn_apply.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.btn_apply)

        layout.addWidget(filter_group)
        layout.addSpacing(2)
        # ==========================

        # 功能按钮区
        btn_style = """
            QPushButton { background-color: #e5e5ea; padding: 8px; border-radius: 8px; font-weight: bold; font-size: 16px;}
            QPushButton:hover { background-color: #d1d1d6; }
        """

        btn_layout = QHBoxLayout()
        self.btn_manage = QPushButton("⚙️ 管理")
        self.btn_manage.setStyleSheet(btn_style)
        self.btn_manage.clicked.connect(self.open_management_dialog)
        btn_layout.addWidget(self.btn_manage)

        # 保留快捷键修改按钮
        self.btn_hotkey = QPushButton("⌨️ 快捷键设置")
        self.btn_hotkey.setStyleSheet(btn_style)
        self.btn_hotkey.clicked.connect(self.change_hotkeys)
        btn_layout.addWidget(self.btn_hotkey)
        
        layout.addLayout(btn_layout)

        layout.addStretch()

        # ====== 底部信息卡片填补空白 ======
        info_card = QWidget()
        info_card.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px dashed #ced4da;
                border-radius: 8px;
            }
            QLabel {
                background: transparent;
                border: none;
                color: #6c757d;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(5, 10, 10, 10)
        
        info_title = QLabel("快速指南")
        info_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_text = QLabel(
            "1. 点击顶部大按钮开启麦克风监听\n"
            "2. 不同笑声会触发不同类型的音笑\n"
            "3. 鼠标手势圆形轨迹可触发笑声\n"
            "4. 使用快捷键手动触发当前筛选池内的音频"
        )
        info_text.setFont(QFont("Microsoft YaHei", 9))
        info_text.setWordWrap(True)
        
        # info_layout.addWidget(info_title)
        info_layout.addWidget(info_text)
        layout.addWidget(info_card)

        # 减小底部弹性空间，让内容分布更充实
        layout.addSpacing(5)

        # 作者与声明
        author_label = QLabel('作者<a href="https://space.bilibili.com/6297797" style="color:#00a1d6; text-decoration:none;">@依然匹萨吧</a>')
        author_label.setOpenExternalLinks(True)
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        disclaimer = QLabel("声明：本软件免费，禁止商用贩卖\n使用代表同意自行承担所有后果")
        disclaimer.setFont(QFont("Microsoft YaHei", 8))
        disclaimer.setStyleSheet("color: #8e8e93;")
        disclaimer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(author_label)
        layout.addWidget(disclaimer)

        # 托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(resource_path("laughter_can.ico")))
        tray_menu = QMenu()
        show_action = QAction("显示主界面", self)
        quit_action = QAction("退出", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def on_hotkey_toggled(self, state):
        enabled = (state == Qt.CheckState.Checked.value)
        self.rm.rules["enable_hotkey"] = enabled
        self.rm.save_rules()
        self.init_hotkeys()

    def on_mouse_toggled(self, state):
        enabled = (state == Qt.CheckState.Checked.value)
        self.rm.rules["enable_mouse"] = enabled
        self.rm.save_rules()
        if hasattr(self, 'mouse_thread'):
            self.mouse_thread.enabled = enabled

    def init_audio_player(self):
        pygame.mixer.init()
        self.is_playing = False
        self.pending_status_text = ""
        self.last_detect_time = 0
        
        # 使用定时器检查音频播放状态
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.check_audio_state)
        self.playback_timer.start(100) # 每100ms检查一次

    def init_threads(self):
        self.mic_thread = MicListener()
        self.mic_thread.trigger_signal.connect(lambda t: self.play_laughter(t, "mic"))
        
        self.mouse_thread = MouseGestureListener()
        self.mouse_thread.trigger_signal.connect(lambda t: self.play_laughter(t, "mouse"))
        self.mouse_thread.enabled = self.rm.rules.get("enable_mouse", True)
        self.mouse_thread.start()

    def init_hotkeys(self):
        keyboard.unhook_all()
        if not self.rm.rules.get("enable_hotkey", True):
            return
            
        hk = self.rm.rules.get("hotkeys", {})
        # 兼容旧配置，默认给k
        key = hk.get("random", hk.get("bitter", "k"))
        try:
            keyboard.add_hotkey(key, lambda: self.play_laughter("any", "hotkey"))
        except Exception as e:
            print("注册快捷键失败(可能需要管理员权限):", e)

    def toggle_listening(self):
        self.is_listening = not self.is_listening
        if self.is_listening:
            self.mic_thread.start()
            self.toggle_btn.setText("停止笑声检测")
            self.toggle_btn.setStyleSheet("""
                QPushButton { 
                    background-color: #ff3b30; 
                    color: white; 
                    border-radius: 15px; 
                    border: none;
                    font-size: 44px;
                    font-weight: bold;
                    font-family: "Microsoft YaHei";
                }
                QPushButton:hover { background-color: #ff6961; }
            """)
            self.status_label.setText("正在检测...")
            self.detect_label.setText("监听中...")
        else:
            self.mic_thread.running = False
            self.mic_thread.quit()
            self.toggle_btn.setText("开启笑声检测")
            self.toggle_btn.setStyleSheet("""
                QPushButton { 
                    background-color: #ff9500; 
                    color: white; 
                    border-radius: 15px; 
                    border: none;
                    font-size: 44px;
                    font-weight: bold;
                    font-family: "Microsoft YaHei";
                }
                QPushButton:hover { background-color: #ffaa33; }
            """)
            self.status_label.setText("点击开启检测")
            self.detect_label.setText("检测未开启")
            # 重置线程状态以便下次启动
            self.mic_thread = MicListener()
            self.mic_thread.trigger_signal.connect(lambda t: self.play_laughter(t, "mic"))

    def play_laughter(self, laugh_type, source="mic"):
        self.last_detect_time = time.time()
        type_names = {
            "laughter": "普通笑", "baby_laughter": "婴儿笑", 
            "giggle": "咯咯笑", "snicker": "窃笑", 
            "belly_laugh": "开怀大笑", "chuckle": "憨笑",
            "any": "手动随机触发"
        }
        display_name = type_names.get(laugh_type, laugh_type)
        
        if source == "mic":
            trigger_text = f"👂🤚 {display_name}"
        elif source == "hotkey":
            trigger_text = "快捷键触发"
        elif source == "mouse":
            trigger_text = "鼠标手势触发"
        else:
            trigger_text = display_name
            
        self.detect_label.setText(trigger_text)
        
        # 多线程处理播放加载，避免阻塞主GUI线程
        threading.Thread(target=self._async_playback, args=(laugh_type, display_name), daemon=True).start()

    def _async_playback(self, laugh_type, display_name):
        if getattr(self, 'is_playing', False) or pygame.mixer.music.get_busy(): return # 防重叠
        search_kw = getattr(self, 'current_search_keyword', "")
        path = self.rm.get_random_audio(laugh_type, search_kw)
        if path and os.path.exists(path):
            self.is_playing = True
            
            filename = os.path.basename(path)
            if len(filename) >= 20: 
                filename = filename[:17] + "..."
            self.pending_status_text = f"🔊 {filename}"
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except Exception as e:
                print(f"音频播放失败: {e}")
                self.is_playing = False

    def refresh_search_completer(self):
        from PyQt6.QtWidgets import QCompleter
        names = []
        for a in self.rm.get_all_audios():
            if "path" in a:
                # 提取文件名
                name = os.path.basename(a["path"])
                names.append(name)
        names = list(set(names))
        
        completer = QCompleter(names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        
        # 样式设置
        popup = completer.popup()
        popup.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CED4DA; selection-background-color: #007BFF; selection-color: #FFFFFF; outline: none; font-size: 13px;")
        
        self.search_input.setCompleter(completer)

    def check_audio_state(self):
        # 1. 安全地更新副线程派发的UI文本
        if hasattr(self, 'pending_status_text') and self.pending_status_text:
            self.status_label.setText(self.pending_status_text)
            self.pending_status_text = ""

        # 2. 检查播放是否结束，恢复主状态指示
        if getattr(self, 'is_playing', False) and not pygame.mixer.music.get_busy():
            self.is_playing = False
            if self.is_listening:
                self.status_label.setText("正在监听...")
            else:
                self.status_label.setText("点击开启检测")

        # 3. 处理检测显示标签：开启时保证显示1秒且播放完毕后恢复
        if getattr(self, 'is_playing', False) or (time.time() - getattr(self, 'last_detect_time', 0)) < 1.0:
            pass # 保持显示检测结果或播放状态
        else:
            if self.is_listening:
                if self.detect_label.text() != "监听中...":
                    self.detect_label.setText("监听中...")
            else:
                if self.detect_label.text() != "检测未开启":
                    self.detect_label.setText("检测未开启")

    def open_tag_filter_dialog(self):
        from PyQt6.QtCore import QPoint
        all_tags = self.rm.rules.get("tags", [])
        active_tags = getattr(self, '_temp_active_tags', self.rm.rules.get("active_tags", []))
        menu = TagMenu(self, all_tags, active_tags, self.rm)
        global_pos = self.btn_tag_filter.mapToGlobal(QPoint(0, self.btn_tag_filter.height()))
        menu.exec(global_pos)
        self._temp_active_tags = menu.get_selected_tags()
        self.refresh_tag_combo()

    def refresh_tag_combo(self):
        """刷新标签筛选显示"""
        active_tags = getattr(self, '_temp_active_tags', self.rm.rules.get("active_tags", []))
        if getattr(self, 'btn_tag_filter', None):
            # 删除旧的布局(如果有)
            if self.btn_tag_filter.layout():
                QWidget().setLayout(self.btn_tag_filter.layout())
                
            if not active_tags:
                self.btn_tag_filter.setText("全部标签")
            else:
                self.btn_tag_filter.setText("")
                layout = QHBoxLayout(self.btn_tag_filter)
                layout.setContentsMargins(4, 2, 4, 2)
                layout.setSpacing(4)
                
                # 最多显示3个标签，多余的用省略号
                displayed_tags = active_tags[:3]
                for tag in displayed_tags:
                    lbl = QLabel(tag)
                    color = self.rm.get_tag_color(tag)
                    lbl.setStyleSheet(f"background-color: {color}; color: white; border-radius: 4px; padding: 2px 6px; font-weight: bold; font-size: 11px;")
                    lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    layout.addWidget(lbl)
                    
                if len(active_tags) > 3:
                    lbl_more = QLabel("...")
                    lbl_more.setStyleSheet("color: #666; font-weight: bold;")
                    lbl_more.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                    layout.addWidget(lbl_more)
                layout.addStretch()

    def apply_filters(self):
        """应用搜索与标签过滤"""
        # 获取输入框文本并应用
        text = self.search_input.text()
        self.current_search_keyword = text
        self.rm.set_search_keyword(text)

        # 提交暂存的选定标签
        if hasattr(self, '_temp_active_tags'):
            self.rm.rules["active_tags"] = self._temp_active_tags
            self.rm.save_rules()
        
        QMessageBox.information(self, "筛选已应用", "现在只会播放符合筛选条件的笑声！")

    def on_search_text_changed(self, text):
        pass # 被废弃，现使用应用按钮

    def import_pack(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择音笑包文件夹 (包含 rule.json)")
        if dir_path:
            self.rm.load_pack(dir_path)
            self.refresh_tag_combo()
            QMessageBox.information(self, "成功", "音笑包已加载！")

    def change_hotkeys(self):
        hk = self.rm.rules.get("hotkeys", {})
        # 返回寻找以前的 k 键，平滑过渡
        old_val = hk.get("random", hk.get("bitter", "k"))
        dialog = HotkeyCaptureDialog(self, old_val)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            k1 = dialog.get_hotkey()
            if k1:
                self.rm.rules["hotkeys"] = {"random": k1.lower()}
                self.rm.save_rules()
                self.init_hotkeys()
                QMessageBox.information(self, "成功", "快捷键已更新！(部分按键可能需要重启软件或管理员权限)")

    def open_management_dialog(self):
        """打开音频管理对话框"""
        self.management_dialog = AudioManagementDialog(self, self.rm)
        self.management_dialog.show()

    def quit_app(self):
        self._is_quitting = True
        if hasattr(self, 'mic_thread'):
            self.mic_thread.running = False
        if hasattr(self, 'mouse_thread'):
            self.mouse_thread.running = False
        QApplication.instance().quit()

    def closeEvent(self, event):
        if getattr(self, '_is_quitting', False):
            event.accept()
            return
            
        # 重写关闭事件，使其最小化到托盘
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "笑声罐头",
            "已最小化到系统托盘，将在后台继续运行。",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

if __name__ == "__main__":
    # DPI 适配
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    # 扁平化 UI 样式表
    flat_style = """
        * {
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            font-size: 13px;
            color: #333333;
        }
        QMainWindow, QDialog, QWidget {
            background-color: #F8F9FA;
        }
        QPushButton {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #f1f3f5;
            border-color: #adb5bd;
        }
        QPushButton:pressed {
            background-color: #e9ecef;
            border-color: #868e96;
        }
        QLineEdit {
            background-color: #FFFFFF;
            border: 1px solid #CED4DA;
            border-radius: 6px;
            padding: 6px 10px;
            selection-background-color: #007BFF;
        }
        QLineEdit:focus {
            border: 1px solid #80BDFF;
        }
        QCheckBox {
            background-color: transparent;
        }
        QComboBox {
            background-color: #FFFFFF;
            border: 1px solid #CED4DA;
            border-radius: 6px;
            padding: 6px 10px;
            min-width: 6em;
        }
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        QComboBox::down-arrow {
            image: none; /* Can replace with real icon if wanted */
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #6C757D;
            margin-right: 10px;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #CED4DA;
            background-color: #FFFFFF;
            selection-background-color: #007BFF;
            selection-color: #FFFFFF;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            background-color: #FFFFFF;
            color: #333333;
            padding: 1px;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #007BFF;
            color: #FFFFFF;
        }
        QTableWidget {
            background-color: #FFFFFF;
            border: 1px solid #DEE2E6;
            border-radius: 6px;
            gridline-color: #E9ECEF;
            alternate-background-color: #FFFFFF;
        }
        QTableWidget::item {
            background-color: #FFFFFF;
            color: #333333;
        }
        QTableWidget::item:selected {
            background-color: #E9ECEF;
            color: #333333;
        }
        QHeaderView::section {
            background-color: #F8F9FA;
            border: none;
            border-bottom: 2px solid #DEE2E6;
            border-right: 1px solid #DEE2E6;
            padding: 8px;
            font-weight: bold;
            color: #495057;
        }
        QListWidget {
            background-color: #FFFFFF;
            border: 1px solid #DEE2E6;
            border-radius: 6px;
        }
        QListWidget::item:selected {
            background-color: #E9ECEF;
            color: #333333;
        }
        QTabWidget::pane {
            border: 1px solid #DEE2E6;
            border-radius: 6px;
            background-color: #FFFFFF;
        }
        QTabBar::tab {
            background-color: #F8F9FA;
            border: 1px solid #DEE2E6;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 16px;
            color: #6C757D;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #FFFFFF;
            color: #212529;
            font-weight: bold;
            border-bottom: 2px solid #007BFF;
        }
        QTabBar::tab:hover:!selected {
            background-color: #E9ECEF;
        }
        QMenu {
            background-color: #FFFFFF;
            border: 1px solid #CED4DA;
        }
        QMenu::item {
            background-color: transparent;
            padding: 4px 20px;
        }
        QMenu::item:selected {
            background-color: #007BFF;
            color: #FFFFFF;
        }
    """
    app.setStyleSheet(flat_style)

    # 保持后台运行
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
