# -*- coding: utf-8 -*-
"""
圖表專用分類配色 (Chart Categorical Palette)
沿用經過 CVD（色覺辨識）相鄰色對驗證的 8 色分類色票，
供多序列比較圖固定配色使用——顏色依「名稱」穩定映射，不會因為勾選/取消其他項目而改變。
"""

from typing import Dict, List

# (亮色模式, 暗色模式)
CATEGORICAL_PALETTE = [
    ("#2a78d6", "#3987e5"),  # 1 blue
    ("#eb6834", "#d95926"),  # 2 orange
    ("#1baf7a", "#199e70"),  # 3 aqua
    ("#eda100", "#c98500"),  # 4 yellow
    ("#e87ba4", "#d55181"),  # 5 magenta
    ("#008300", "#008300"),  # 6 green
    ("#4a3aa7", "#9085e9"),  # 7 violet
    ("#e34948", "#e66767"),  # 8 red
]


def assign_series_colors(all_names: List[str], is_dark: bool = False) -> Dict[str, str]:
    """依名稱在「全部存檔名稱」中的固定字母順序分配顏色，選取子集合時同一名稱顏色不變"""
    sorted_names = sorted(all_names)
    idx = 1 if is_dark else 0
    return {
        name: CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)][idx]
        for i, name in enumerate(sorted_names)
    }
