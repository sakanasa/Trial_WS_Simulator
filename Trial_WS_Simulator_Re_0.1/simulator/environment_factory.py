# -*- coding: utf-8 -*-
"""
模拟环境与初始状态工厂 (Game Environment Factory)
负责从界面配置参数中提取初始数值，并实例化/随机洗牌生成初始 (deck, control, stock, level, clock) 游戏环境。
"""

import random
from typing import Tuple, Dict, Any
from core.engine import build_deck


class GameEnvironmentFactory:
    """模拟初始环境生成工厂类"""

    @staticmethod
    def extract_fixed_params(left_col_view: Any) -> Dict[str, Any]:
        """从左侧栏视图提取卡组、控室、库存、等级区与计时区的固定参数"""
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
        """基于固定参数构建打乱后的 (deck, control, stock, level, clock) 局势"""
        deck = build_deck(fixed["deck_normal"], fixed["deck_climax"])
        control = ["普通"] * fixed["control_normal"] + ["高潮"] * fixed["control_climax"]
        stock = ["普通"] * fixed["stock_normal"] + ["高潮"] * fixed["stock_climax"]

        level_meat = fixed.get("level_meat_count", sum(1 for _ in range(4 - fixed["level_climax_count"])))
        level_climax = fixed["level_climax_count"]
        level = ["高潮"] * level_climax + ["普通"] * min(level_meat, 4 - level_climax)
        random.shuffle(level)

        clock_meat = fixed.get("clock_meat_count", sum(1 for _ in range(6 - fixed["clock_climax_count"])))
        clock_climax = fixed["clock_climax_count"]
        clock = ["高潮"] * clock_climax + ["普通"] * min(clock_meat, 6 - clock_climax)
        random.shuffle(clock)

        return deck, control, stock, level, clock