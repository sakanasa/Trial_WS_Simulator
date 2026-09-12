# -*- coding: utf-8 -*-
"""
統計分析計算器 (Statistics Calculator)
負責置信區間計算、顯著差異評估、斬殺率與傷害統計等數學邏輯。
"""

import math
from typing import Tuple, Dict, Any


def calc_winrate(wins: int, total_runs: int) -> float:
    """計算斬殺率 (%)"""
    if total_runs <= 0:
        return 0.0
    return (wins / total_runs) * 100.0


def calc_avg_damage(total_damage: int, total_runs: int) -> float:
    """計算平均傷害"""
    if total_runs <= 0:
        return 0.0
    return total_damage / total_runs


def calc_wilson_score_interval(
    winrate_percent: float, total_runs: int, z: float = 1.96
) -> Tuple[float, float]:
    """
    使用 Wilson 得分區間 (Wilson Score Interval) 計算 95% 置信區間
    返回: (下限%, 上限%)
    """
    if total_runs <= 0:
        return 0.0, 0.0

    p = winrate_percent / 100.0
    n = total_runs
    denom = 1 + (z ** 2) / n
    center = (p + (z ** 2) / (2 * n)) / denom
    se = math.sqrt((p * (1 - p) + (z ** 2) / (4 * n)) / n)
    half = (z * se) / denom

    lower = max(0.0, center - half) * 100.0
    upper = min(1.0, center + half) * 100.0
    return lower, upper


def calc_significant_difference_threshold(
    winrate_percent: float, total_runs: int, z: float = 1.96
) -> float:
    """
    計算基於雙樣本比例檢驗的 95% 顯著差異所需最小差值（百分點）
    """
    if total_runs <= 0:
        return 0.0

    p = winrate_percent / 100.0
    n = total_runs
    # 假設兩組模擬樣本量相同 n，合併標準誤計算
    diff_min = z * math.sqrt((2 * p * (1 - p)) / n) * 100.0
    return diff_min


def format_elapsed_time(seconds: float) -> str:
    """將耗時秒數格式化為 readable 文本（如 X分Y.Z秒 或 X.YZ秒）"""
    if seconds < 0:
        seconds = 0.0

    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}分{secs:.1f}秒"
    else:
        return f"{secs:.2f}秒"