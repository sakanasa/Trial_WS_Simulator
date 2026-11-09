# -*- coding: utf-8 -*-
"""
自定義卡庫持久化服務 (Custom Cards Service)
負責本地 custom_cards.json 文件的讀取、保存、默認示例卡片生成與內存數據管理。
"""

import os
import json
from typing import List, Dict, Any

# 本地自定義卡庫持久化存儲文件路徑 (自動定位到項目根目錄)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUSTOM_CARDS_FILE = os.path.join(BASE_DIR, "custom_cards.json")


class CustomCardsService:
    """自定義卡庫數據管理與持久化服務類（單例服務）"""

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
        """從本地 JSON 文件讀取卡庫數據，若無文件則自動生成默認示例卡"""
        self.cards_data = []
        if os.path.exists(CUSTOM_CARDS_FILE):
            try:
                with open(CUSTOM_CARDS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list) and data:
                    self.cards_data = data
            except Exception as e:
                print(f"[WARN] 讀取本地 custom_cards.json 失敗: {e}")

        if not self.cards_data:
            self.cards_data = [self._get_default_example_card()]
            self.save()

        return self.cards_data

    def save(self, cards_data: List[Dict[str, Any]] = None) -> bool:
        """將當前卡庫數據寫盤保存到本地 JSON 文件中"""
        if cards_data is not None:
            self.cards_data = cards_data

        try:
            with open(CUSTOM_CARDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cards_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] 保存 custom_cards.json 失敗: {e}")
            return False

    def get_all(self) -> List[Dict[str, Any]]:
        """獲取所有卡庫數據"""
        return self.cards_data

    @staticmethod
    def _get_default_example_card() -> Dict[str, Any]:
        """默認示例卡片模板"""
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
                "attack_type": [{"type": "攻擊方式", "attack_type": "正面"}],
                "on_attack": [{"type": "摩卡", "mocha_mode": "原位", "mocha_count": 2}],
                "trigger_step": [{"type": "一般判定"}],
                "deal_damage": [{"type": "角色傷害", "role_damage_base": 0, "role_bonus_type": "魂點", "trigger_rate": 0.0}],
                "on_reverse": [{"type": "普通傷害", "damage": 2, "trigger_rate": 0.0}],
                "post_attack": []
            }
        }


# 全局單例服務實例
custom_cards_service = CustomCardsService()