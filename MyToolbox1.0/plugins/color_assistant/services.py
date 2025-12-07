import json
import time
import uuid
from pathlib import Path
from core.config import ConfigManager


class CollectionService:
    DATA_FILE = ConfigManager.CONFIG_DIR / "color_favorites.json"

    @classmethod
    def _load_data(cls):
        if not cls.DATA_FILE.exists(): return {"items": []}
        try:
            with open(cls.DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"items": []}

    @classmethod
    def _save_data(cls, data):
        with open(cls.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def add_color(cls, hex_code, name=""):
        """收藏单色"""
        item = {"id": str(uuid.uuid4()), "type": "color", "hex": hex_code, "name": name or hex_code,
                "timestamp": int(time.time())}
        cls._add_item(item)
        return item

    @classmethod
    def add_gradient(cls, colors, angle, name=""):
        """收藏渐变色"""
        item = {"id": str(uuid.uuid4()), "type": "gradient", "colors": colors, "angle": angle, "name": name,
                "timestamp": int(time.time())}
        cls._add_item(item)
        return item

    @classmethod
    def add_palette(cls, colors, name=""):
        """
        【核心修复】收藏 AI 生成的固定色板
        """
        item = {
            "id": str(uuid.uuid4()),
            "type": "palette",
            "colors": colors,
            "name": name,
            "timestamp": int(time.time())
        }
        cls._add_item(item)
        return item

    @classmethod
    def create_custom_palette(cls, name="新建色板"):
        """创建自定义色板"""
        item = {
            "id": str(uuid.uuid4()),
            "type": "custom_palette",
            "name": name,
            "colors": [],
            "timestamp": int(time.time())
        }
        cls._add_item(item)
        return item

    @classmethod
    def add_color_to_palette(cls, palette_id, hex_code):
        data = cls._load_data()
        for item in data['items']:
            if item['id'] == palette_id and item.get('type') == 'custom_palette':
                if hex_code not in item['colors']:
                    item['colors'].append(hex_code)
                    cls._save_data(data)
                    return True
        return False

    @classmethod
    def remove_color_from_palette(cls, palette_id, hex_code):
        data = cls._load_data()
        for item in data['items']:
            if item['id'] == palette_id:
                if hex_code in item['colors']:
                    item['colors'].remove(hex_code)
                    cls._save_data(data)
                    return True
        return False

    @classmethod
    def _add_item(cls, item):
        data = cls._load_data()
        # 简单查重 (仅针对单色)
        if item['type'] == 'color':
            for ex in data['items']:
                if ex['type'] == 'color' and ex['hex'] == item['hex']: return
        data['items'].insert(0, item)
        cls._save_data(data)

    @classmethod
    def remove_item(cls, item_id):
        data = cls._load_data()
        data['items'] = [i for i in data['items'] if i['id'] != item_id]
        cls._save_data(data)

    @classmethod
    def get_all(cls):
        data = cls._load_data()
        return data.get("items", [])

    @classmethod
    def get_custom_palettes(cls):
        return [i for i in cls.get_all() if i.get('type') == 'custom_palette']

    @classmethod
    def is_collected(cls, hex_code):
        for item in cls.get_all():
            if item['type'] == 'color' and item['hex'].upper() == hex_code.upper(): return True
        return False