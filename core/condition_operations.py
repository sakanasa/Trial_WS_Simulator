# -*- coding: utf-8 -*-
"""
殘局模式專屬算卡操作 (Condition Operations) - 核心純計算層
包含專門在殘局模式下生效的特有操作（一般判定、翻頂燒、推頂燒、羽未）。
完全不依賴 customtkinter/tkinter GUI 庫。
"""

import random
from typing import Tuple, Dict, Any, Callable

from utils.registry import registry
from core.models import (
    card_is_normal, card_is_climax, get_card_kind, 
    get_card_level, get_card_soul, get_card_base_soul, get_card_trigger_soul
)
from core.engine import resolve_damage, add_cards_to_clock


def _exec_condition_trigger_check(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    condition_deck = kwargs.get("condition_deck")
    condition_stock = kwargs.get("condition_stock")
    app = kwargs.get("app")
    soul_points = kwargs.get("soul_points", 0)

    if condition_deck is None:
        return False, "非殘局環境，跳過一般判定", {"total_damage": 0, "soul_points": soul_points}

    if not condition_deck:
        if app:
            app._refresh_condition_deck()
            if not condition_deck:
                return True, "我方牌組與控制室均為0，我方敗北", {"total_damage": 0, "soul_points": soul_points}
        else:
            return True, "我方牌組與控制室均為0，我方敗北", {"total_damage": 0, "soul_points": soul_points}

    top_card = condition_deck.pop()

    if deck:
        str_top = deck.pop()
        if "stock" in kwargs and kwargs["stock"] is not None:
            kwargs["stock"].append(str_top)

    soul_bonus = get_card_trigger_soul(top_card)
    new_soul = soul_points + soul_bonus

    if condition_stock is not None:
        condition_stock.append(top_card)

    if not condition_deck and app:
        app._refresh_condition_deck()

    if app and app.stabilize_condition():
        return True, "我方觸發敗北條件，操作強制截斷", {"total_damage": 0, "soul_points": new_soul}

    desc = f"一般判定: 翻頂牌[{get_card_kind(top_card)}]，觸發魂+{soul_bonus}，移入能量區"
    return False, desc, {"total_damage": 0, "soul_points": new_soul}


def _exec_top_check_burn(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    condition_deck = kwargs.get("condition_deck")
    app = kwargs.get("app")

    if condition_deck is None or not condition_deck:
        if app:
            app._refresh_condition_deck()
            if not condition_deck:
                return True, "翻頂燒: 我方牌組空，我方敗北", {"total_damage": 0}
        else:
            return True, "翻頂燒: 我方牌組空，我方敗北", {"total_damage": 0}

    top_card = condition_deck[-1]
    kind = get_card_kind(top_card)
    card_lvl = get_card_level(top_card)

    filter_kind = op.get("filter_kind", "任意")
    if filter_kind != "任意":
        if filter_kind == "普通" and not card_is_normal(top_card):
            return False, f"翻頂燒: 頂牌為[{kind} Lv.{card_lvl}]，不滿足種類[{filter_kind}]條件", {"total_damage": 0}
        elif filter_kind != "普通" and kind != filter_kind:
            return False, f"翻頂燒: 頂牌為[{kind} Lv.{card_lvl}]，不滿足種類[{filter_kind}]條件", {"total_damage": 0}

    filter_level = op.get("filter_level", "等級")
    if filter_level != "等級":
        try:
            target_lvl = int(filter_level)
            if card_lvl != target_lvl:
                return False, f"翻頂燒: 頂牌為[{kind} Lv.{card_lvl}]，不滿足等級[{filter_level}]條件", {"total_damage": 0}
        except (ValueError, TypeError):
            pass

    base_dmg = op.get("burn_damage", 1)
    bonus_type = op.get("burn_bonus_type", "0")
    times = max(0, op.get("burn_times", 1))

    bonus = 0
    if bonus_type == "等級":
        bonus = card_lvl
    elif bonus_type == "基礎魂點":
        bonus = get_card_base_soul(top_card)

    damage = max(0, base_dmg + bonus)

    total_added = 0
    hit_count = 0
    cancel_count = 0
    game_over = False

    for _ in range(times):
        if game_over or stabilize_func():
            game_over = True
            break
        added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, stabilize_func)
        total_added += added
        if cancelled:
            cancel_count += 1
        else:
            hit_count += 1
        if win:
            game_over = True
            break

    cond_desc = f"條件[{filter_kind}" + (f", Lv.{filter_level}]" if filter_level != "等級" else "]")
    desc = f"翻頂燒: {cond_desc}，頂牌[{kind} Lv.{card_lvl}]，燒({base_dmg}+{bonus_type})點傷害{times}次"
    desc += f" (實際結算{damage}點{times}次: 命中{hit_count}次/取消{cancel_count}次，共{total_added}點傷害)"

    return game_over, desc, {
        "total_damage": total_added,
        "cancelled_damage": damage if cancel_count > 0 else None,
        "hit_count": hit_count,
        "cancel_count": cancel_count
    }


def _exec_top_push_burn(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    condition_deck = kwargs.get("condition_deck")
    condition_control = kwargs.get("condition_control")
    app = kwargs.get("app")

    push_count = op.get("push_count", 1)
    base_dmg = op.get("base_damage", op.get("burn_damage", 1))
    damage_bonus_type = op.get("damage_bonus", op.get("burn_bonus_type", "0"))
    base_times = op.get("base_times", 1)
    times_bonus_type = op.get("times_bonus", "0")

    pushed_cards = []
    for _ in range(push_count):
        if not condition_deck:
            if app:
                app._refresh_condition_deck()
                if not condition_deck:
                    break
            else:
                break

        card = condition_deck.pop()
        pushed_cards.append(card)
        if condition_control is not None:
            condition_control.append(card)

        if app and app.stabilize_condition():
            return True, f"推頂燒: 推{len(pushed_cards)}張後我方敗北", {"total_damage": 0}

    def calc_bonus(bonus_type, cards):
        if bonus_type == "0":
            return 0
        tot = 0
        for card in cards:
            if bonus_type == "觸發魂點":
                tot += get_card_trigger_soul(card)
            elif bonus_type == "等級":
                tot += get_card_level(card)
            elif bonus_type == "潮數":
                if card_is_climax(card):
                    tot += 1
            elif bonus_type == "基礎魂點":
                tot += get_card_base_soul(card)
        return tot

    add_dmg = calc_bonus(damage_bonus_type, pushed_cards)
    add_times = calc_bonus(times_bonus_type, pushed_cards)

    damage = max(0, base_dmg + add_dmg)
    times = max(0, base_times + add_times)

    total_added = 0
    hit_count = 0
    cancel_count = 0
    game_over = False

    for _ in range(times):
        if game_over or stabilize_func():
            game_over = True
            break
        added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, stabilize_func)
        total_added += added
        if cancelled:
            cancel_count += 1
        else:
            hit_count += 1
        if win:
            game_over = True
            break

    desc = f"推頂燒: 推{len(pushed_cards)}張，燒({base_dmg}+{damage_bonus_type})點({base_times}+{times_bonus_type})次"
    desc += f"，實際結算{damage}點{times}次 (命中{hit_count}次/取消{cancel_count}次，共{total_added}點傷害)"

    return game_over, desc, {
        "total_damage": total_added,
        "hit_count": hit_count,
        "cancel_count": cancel_count
    }


def _exec_look_top_stock_reorder(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    condition_deck = kwargs.get("condition_deck")
    condition_stock = kwargs.get("condition_stock")
    app = kwargs.get("app")

    look_count = op.get("look_count", 3)
    max_stock = op.get("max_stock", 1)

    target_deck = condition_deck if condition_deck is not None else deck
    target_stock = condition_stock if condition_stock is not None else stock

    if not target_deck:
        if app:
            app._refresh_condition_deck()
            target_deck = condition_deck if condition_deck is not None else deck
        elif stabilize_func:
            stabilize_func()
            target_deck = condition_deck if condition_deck is not None else deck

        if not target_deck:
            return False, "羽未(決策用): 我方牌組與控制室均為空，跳過操作", {"total_damage": 0}

    take_count = min(look_count, len(target_deck))
    pushed_cards = [target_deck.pop() for _ in range(take_count)]

    stock_card = None
    stock_idx = -1
    if max_stock > 0:
        for idx, c in enumerate(pushed_cards):
            if card_is_normal(c):
                stock_idx = idx
                break
        if stock_idx != -1:
            stock_card = pushed_cards.pop(stock_idx)
            target_stock.append(stock_card)

    pushed_cards.sort(key=lambda c: 1 if card_is_climax(c) else 0)
    for c in pushed_cards:
        target_deck.append(c)

    stock_info = f"1張[{get_card_kind(stock_card)}]" if stock_card else "0張"
    desc = f"羽未(決策用): 看頂{take_count}張，充庫{stock_info}，餘{len(pushed_cards)}張重排置頂"

    game_over = False
    if app:
        game_over = app.stabilize_condition()
    elif stabilize_func:
        game_over = stabilize_func()

    if game_over:
        return True, desc + " (觸發牌組刷新/敗北)", {"total_damage": 0}

    return False, desc, {"total_damage": 0}

# 在 core/condition_operations.py 中添加 _exec_look_select 函數：

# 修改 core/condition_operations.py 中的 _exec_look_select 函數：

def _exec_look_select(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    """
    選判算卡操作解算邏輯（控頂濾牌版）：
    1. 看牌組頂 1 張牌 c1。
    2. 策略判斷：若 c1 是名場面或高觸發魂，選擇 [留在原位]；
       否則選擇 [再看 1 張] 翻出 c2。
    3. 若翻出 c2：比較 c1 與 c2，選擇好牌（CX/高魂）置頂，未選擇的另一張送入控制室！
    """
    condition_deck = kwargs.get("condition_deck")
    condition_control = kwargs.get("condition_control")
    app = kwargs.get("app")

    target_deck = condition_deck if condition_deck is not None else deck
    target_control = condition_control if condition_control is not None else control

    if not target_deck:
        if app:
            app._refresh_condition_deck()
            target_deck = condition_deck if condition_deck is not None else deck
        elif stabilize_func:
            stabilize_func()
            target_deck = condition_deck if condition_deck is not None else deck

        if not target_deck:
            return False, "選判: 牌組與控制室均為空，跳過操作", {"total_damage": 0}

    # 1. 看第 1 張牌 c1
    c1 = target_deck.pop()
    c1_kind = get_card_kind(c1)
    c1_soul = get_card_trigger_soul(c1)
    c1_is_cx = card_is_climax(c1)
    c1_info = f"[{c1_kind} Lv.{get_card_level(c1)}, 觸發魂{c1_soul}]"

    # 若牌組只有 1 張牌，直接留在原位
    if not target_deck:
        target_deck.append(c1)
        return False, f"選判: 僅有 1 張牌 {c1_info}，留在牌組頂", {"total_damage": 0}

    # 策略判定：如果第 1 張已經是 CX 或觸發魂 >= 2，選擇留在原位
    if c1_is_cx or c1_soul >= 2:
        target_deck.append(c1)
        desc = f"選判: 看第 1 張 {c1_info}，選擇 [留在原位]"
        return False, desc, {"total_damage": 0}

    # 2. 選擇 [再看 1 張] 翻出 c2
    c2 = target_deck.pop()
    c2_kind = get_card_kind(c2)
    c2_soul = get_card_trigger_soul(c2)
    c2_is_cx = card_is_climax(c2)
    c2_info = f"[{c2_kind} Lv.{get_card_level(c2)}, 觸發魂{c2_soul}]"

    # 3. 從 c1 與 c2 中選 1 張置頂，未選擇的另一張送入控制室！
    if c2_is_cx or (not c1_is_cx and c2_soul > c1_soul):
        # c2 置頂，c1 送控制室
        target_deck.append(c2)
        target_control.append(c1)
        chosen_info = f"置頂[{c2_info}]，把[{c1_info}]送入控制室"
    else:
        # c1 置頂，c2 送控制室
        target_deck.append(c1)
        target_control.append(c2)
        chosen_info = f"置頂[{c1_info}]，把[{c2_info}]送入控制室"

    desc = f"選判: 看第 1 張 {c1_info} ➔ 選 [再看1張] {c2_info} ➔ 結果: {chosen_info}"
    return False, desc, {"total_damage": 0}

def register_condition_operations():
    """註冊殘局專屬算卡算法"""
    registry.register(
        "一般判定",
        params_def=[],
        modes=["condition"],
        execute=_exec_condition_trigger_check
    )

    registry.register(
        "翻頂燒",
        params_def=[
            {"name": "filter_kind", "default": "任意", "label": "條件:", "widget": "combobox", "width": 6, "values": ["任意", "角色", "事件", "名場面", "普通"]},
            {"name": "filter_level", "default": "等級", "label": "", "widget": "combobox", "width": 6, "values": ["等級", "0", "1", "2", "3"]},
        ],
        modes=["condition"],
        execute=_exec_top_check_burn
    )

    registry.register(
        "推頂燒",
        params_def=[
            {"name": "push_count", "default": 1, "label": "推", "widget": "entry", "width": 3, "suffix": "張,"},
        ],
        modes=["condition"],
        execute=_exec_top_push_burn
    )

    registry.register(
        "羽未(決策用)",
        params_def=[
            {"name": "look_count", "default": 3, "label": "看頂", "widget": "entry", "width": 3, "suffix": "張,"},
            {"name": "max_stock", "default": 1, "label": "充庫至多", "widget": "entry", "width": 3, "suffix": "張"},
        ],
        modes=["condition"],
        execute=_exec_look_top_stock_reorder
    )

    registry.register(
        "選判",
        params_def=[],
        modes=["condition"],
        execute=_exec_look_select
    )