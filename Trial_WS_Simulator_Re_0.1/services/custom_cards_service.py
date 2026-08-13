# -*- coding: utf-8 -*-
"""
自定义卡库持久化服务 (Custom Cards Service)
负责本地 custom_cards.json 文件的读取、保存、默认示例卡片生成与内存数据管理。
"""

import os
import json
from typing import List, Dict, Any

# 本地自定义卡库持久化存储文件路径 (自动定位到项目根目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_CARDS_FILE = os.path.join(BASE_DIR, "custom_cards.json")


class CustomCardsService:
    """自定义卡库数据管理与持久化服务类（单例服务）"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.cards_data: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> List[Dict[str, Any]]:
        """从本地 JSON 文件读取卡库数据，若无文件则自动生成默认示例卡"""
        self.cards_data = []
        if os.path.exists(CUSTOM_CARDS_FILE):
            try:
                with open(CUSTOM_CARDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    self.cards_data = data
            except Exception as e:
                print(f"[WARN] 读取本地 custom_cards.json 失败: {e}")

        if not self.cards_data:
            self.cards_data = [self._get_default_example_card()]
            self.save()

        return self.cards_data

    def save(self, cards_data: List[Dict[str, Any]] = None) -> bool:
        """将当前卡库数据写盘保存到本地 JSON 文件中"""
        if cards_data is not None:
            self.cards_data = cards_data

        try:
            with open(CUSTOM_CARDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cards_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] 保存 custom_cards.json 失败: {e}")
            return False

    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有卡库数据"""
        return self.cards_data

    @staticmethod
    def _get_default_example_card() -> Dict[str, Any]:
        """默认示例卡片模板"""
        return {
            "name": "示例·早川秋 (角色)",
            "type": "角色",
            "level": 3,
            "cost": 2,
            "power": 10000,
            "soul": 2,
            "trigger": "魂",
            "trigger_soul": 1,
            "effects": {
                "pre_attack": [],
                "attack_type": [{"type": "攻击方式", "attack_type": "正面"}],
                "on_attack": [{"type": "摩卡", "mocha_mode": "原位", "mocha_count": 2}],
                "trigger_step": [{"type": "工况判定"}],
                "deal_damage": [{"type": "角色伤害", "role_damage_base": 0, "role_bonus_type": "魂点", "trigger_rate": 0.0}],
                "on_reverse": [{"type": "普通伤害", "damage": 2, "trigger_rate": 0.0}],
                "post_attack": []
            }
        }


# 全局单例服务实例
custom_cards_service = CustomCardsService()