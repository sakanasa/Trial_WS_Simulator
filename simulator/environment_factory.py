# -*- coding: utf-8 -*-
"""
模擬環境與初始狀態工廠 (Game Environment Factory)
負責從界面配置參數中提取初始數值，並實例化/隨機洗牌生成初始 (deck, control, stock, level, clock) 遊戲環境。
"""

import random
from typing import Tuple, Dict, Any
from core.engine import build_deck


class GameEnvironmentFactory:
    """模擬初始環境生成工廠類"""

    @staticmethod
    def extract_fixed_params(left_col_view: Any) -> Dict[str, Any]:
        """從左側欄視圖提取牌組、控室、能量、等級區與傷害區的固定參數"""
        return {
            "deck_normal": left_col_view.deck_normal.get(),
            "deck_climax": left_col_view.deck_climax.get(),
            "control_normal": left_col_view.control_normal.get(),
            "control_climax": left_col_view.control_climax.get(),
            "stock_normal": left_col_view.stock_normal.get(),
            "stock_climax": left_col_view.stock_climax.get(),
            "level_climax_count": sum(1 for v in left_col_view.level_vars if v.get() == "潮"),
            "level_meat_count": sum(1 for v in left_col_view.level_vars if v.get() == "肉"),
            "clock_climax_count": sum(1 for v in left_col_view.clock_vars if v.get() == "潮"),
            "clock_meat_count": sum(1 for v in left_col_view.clock_vars if v.get() == "肉"),
        }

    @staticmethod
    def build_initial_state(fixed: Dict[str, Any]) -> Tuple[list, list, list, list, list]:
        """基於固定參數構建打亂後的 (deck, control, stock, level, clock) 局勢"""
        deck = build_deck(fixed["deck_normal"], fixed["deck_climax"])
        control = ["普通"] * fixed["control_normal"] + ["名場面"] * fixed["control_climax"]
        stock = ["普通"] * fixed["stock_normal"] + ["名場面"] * fixed["stock_climax"]

        level_meat = fixed.get("level_meat_count", sum(1 for _ in range(4 - fixed["level_climax_count"])))
        level_climax = fixed["level_climax_count"]
        level = ["名場面"] * level_climax + ["普通"] * min(level_meat, 4 - level_climax)
        random.shuffle(level)

        clock_meat = fixed.get("clock_meat_count", sum(1 for _ in range(6 - fixed["clock_climax_count"])))
        clock_climax = fixed["clock_climax_count"]
        clock = ["名場面"] * clock_climax + ["普通"] * min(clock_meat, 6 - clock_climax)
        random.shuffle(clock)

        return deck, control, stock, level, clock