# -*- coding: utf-8 -*-
"""
工况模式专属算卡操作 (Condition Operations) - 核心纯计算层
包含专门在工况模式下生效的特有操作（工况判定、翻顶烧、推顶烧、羽未）。
完全不依赖 customtkinter/tkinter GUI 库。
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
        return False, "非工况环境，跳过工况判定", {"total_damage": 0, "soul_points": soul_points}

    if not condition_deck:
        if app:
            app._refresh_condition_deck()
            if not condition_deck:
                return True, "我方卡组与控制室均为0，我方败北", {"total_damage": 0, "soul_points": soul_points}
        else:
            return True, "我方卡组与控制室均为0，我方败北", {"total_damage": 0, "soul_points": soul_points}

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
        return True, "我方触发败北条件，操作强制截断", {"total_damage": 0, "soul_points": new_soul}

    desc = f"工况判定: 翻顶牌[{get_card_kind(top_card)}]，触发魂+{soul_bonus}，移入库存区"
    return False, desc, {"total_damage": 0, "soul_points": new_soul}


def _exec_top_check_burn(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    condition_deck = kwargs.get("condition_deck")
    app = kwargs.get("app")

    if condition_deck is None or not condition_deck:
        if app:
            app._refresh_condition_deck()
            if not condition_deck:
                return True, "翻顶烧: 我方卡组空，我方败北", {"total_damage": 0}
        else:
            return True, "翻顶烧: 我方卡组空，我方败北", {"total_damage": 0}

    top_card = condition_deck[-1]
    kind = get_card_kind(top_card)
    card_lvl = get_card_level(top_card)

    filter_kind = op.get("filter_kind", "任意")
    if filter_kind != "任意":
        if filter_kind == "普通" and not card_is_normal(top_card):
            return False, f"翻顶烧: 顶牌为[{kind} Lv.{card_lvl}]，不满足种类[{filter_kind}]条件", {"total_damage": 0}
        elif filter_kind != "普通" and kind != filter_kind:
            return False, f"翻顶烧: 顶牌为[{kind} Lv.{card_lvl}]，不满足种类[{filter_kind}]条件", {"total_damage": 0}

    filter_level = op.get("filter_level", "等级")
    if filter_level != "等级":
        try:
            target_lvl = int(filter_level)
            if card_lvl != target_lvl:
                return False, f"翻顶烧: 顶牌为[{kind} Lv.{card_lvl}]，不满足等级[{filter_level}]条件", {"total_damage": 0}
        except (ValueError, TypeError):
            pass

    base_dmg = op.get("burn_damage", 1)
    bonus_type = op.get("burn_bonus_type", "0")
    times = max(0, op.get("burn_times", 1))

    bonus = 0
    if bonus_type == "等级":
        bonus = card_lvl
    elif bonus_type == "基础魂点":
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

    cond_desc = f"条件[{filter_kind}" + (f", Lv.{filter_level}]" if filter_level != "等级" else "]")
    desc = f"翻顶烧: {cond_desc}，顶牌[{kind} Lv.{card_lvl}]，烧({base_dmg}+{bonus_type})点伤害{times}次"
    desc += f" (实际结算{damage}点{times}次: 命中{hit_count}次/取消{cancel_count}次，共{total_added}点伤害)"

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
            return True, f"推顶烧: 推{len(pushed_cards)}张后我方败北", {"total_damage": 0}

    def calc_bonus(bonus_type, cards):
        if bonus_type == "0":
            return 0
        tot = 0
        for card in cards:
            if bonus_type == "触发魂点":
                tot += get_card_trigger_soul(card)
            elif bonus_type == "等级":
                tot += get_card_level(card)
            elif bonus_type == "潮数":
                if card_is_climax(card):
                    tot += 1
            elif bonus_type == "基础魂点":
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

    desc = f"推顶烧: 推{len(pushed_cards)}张，烧({base_dmg}+{damage_bonus_type})点({base_times}+{times_bonus_type})次"
    desc += f"，实际结算{damage}点{times}次 (命中{hit_count}次/取消{cancel_count}次，共{total_added}点伤害)"

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
            return False, "羽未(决策用): 我方卡组与控制室均为空，跳过操作", {"total_damage": 0}

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

    stock_info = f"1张[{get_card_kind(stock_card)}]" if stock_card else "0张"
    desc = f"羽未(决策用): 看顶{take_count}张，充库{stock_info}，余{len(pushed_cards)}张重排置顶"

    game_over = False
    if app:
        game_over = app.stabilize_condition()
    elif stabilize_func:
        game_over = stabilize_func()

    if game_over:
        return True, desc + " (触发卡组刷新/败北)", {"total_damage": 0}

    return False, desc, {"total_damage": 0}

# 在 core/condition_operations.py 中添加 _exec_look_select 函数：

# 修改 core/condition_operations.py 中的 _exec_look_select 函数：

def _exec_look_select(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    """
    选判算卡操作解算逻辑（控顶滤牌版）：
    1. 看卡组顶 1 张牌 c1。
    2. 策略判断：若 c1 是高潮或高触发魂，选择 [留在原位]；
       否则选择 [再看 1 张] 翻出 c2。
    3. 若翻出 c2：比较 c1 与 c2，选择好牌（CX/高魂）置顶，未选择的另一张送入控制室！
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
            return False, "选判: 卡组与控制室均为空，跳过操作", {"total_damage": 0}

    # 1. 看第 1 张牌 c1
    c1 = target_deck.pop()
    c1_kind = get_card_kind(c1)
    c1_soul = get_card_trigger_soul(c1)
    c1_is_cx = card_is_climax(c1)
    c1_info = f"[{c1_kind} Lv.{get_card_level(c1)}, 触发魂{c1_soul}]"

    # 若卡组只有 1 张牌，直接留在原位
    if not target_deck:
        target_deck.append(c1)
        return False, f"选判: 仅有 1 张牌 {c1_info}，留在卡组顶", {"total_damage": 0}

    # 策略判定：如果第 1 张已经是 CX 或触发魂 >= 2，选择留在原位
    if c1_is_cx or c1_soul >= 2:
        target_deck.append(c1)
        desc = f"选判: 看第 1 张 {c1_info}，选择 [留在原位]"
        return False, desc, {"total_damage": 0}

    # 2. 选择 [再看 1 张] 翻出 c2
    c2 = target_deck.pop()
    c2_kind = get_card_kind(c2)
    c2_soul = get_card_trigger_soul(c2)
    c2_is_cx = card_is_climax(c2)
    c2_info = f"[{c2_kind} Lv.{get_card_level(c2)}, 触发魂{c2_soul}]"

    # 3. 从 c1 与 c2 中选 1 张置顶，未选择的另一张送入控制室！
    if c2_is_cx or (not c1_is_cx and c2_soul > c1_soul):
        # c2 置顶，c1 送控制室
        target_deck.append(c2)
        target_control.append(c1)
        chosen_info = f"置顶[{c2_info}]，把[{c1_info}]送入控制室"
    else:
        # c1 置顶，c2 送控制室
        target_deck.append(c1)
        target_control.append(c2)
        chosen_info = f"置顶[{c1_info}]，把[{c2_info}]送入控制室"

    desc = f"选判: 看第 1 张 {c1_info} ➔ 选 [再看1张] {c2_info} ➔ 结果: {chosen_info}"
    return False, desc, {"total_damage": 0}

def register_condition_operations():
    """注册工况专属算卡算法"""
    registry.register(
        "工况判定",
        params_def=[],
        modes=["condition"],
        execute=_exec_condition_trigger_check
    )

    registry.register(
        "翻顶烧",
        params_def=[
            {"name": "filter_kind", "default": "任意", "label": "条件:", "widget": "combobox", "width": 6, "values": ["任意", "角色", "事件", "高潮", "普通"]},
            {"name": "filter_level", "default": "等级", "label": "", "widget": "combobox", "width": 6, "values": ["等级", "0", "1", "2", "3"]},
        ],
        modes=["condition"],
        execute=_exec_top_check_burn
    )

    registry.register(
        "推顶烧",
        params_def=[
            {"name": "push_count", "default": 1, "label": "推", "widget": "entry", "width": 3, "suffix": "张,"},
        ],
        modes=["condition"],
        execute=_exec_top_push_burn
    )

    registry.register(
        "羽未(决策用)",
        params_def=[
            {"name": "look_count", "default": 3, "label": "看顶", "widget": "entry", "width": 3, "suffix": "张,"},
            {"name": "max_stock", "default": 1, "label": "充库至多", "widget": "entry", "width": 3, "suffix": "张"},
        ],
        modes=["condition"],
        execute=_exec_look_top_stock_reorder
    )

    registry.register(
        "选判",
        params_def=[],
        modes=["condition"],
        execute=_exec_look_select
    )