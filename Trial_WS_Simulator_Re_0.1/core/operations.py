# -*- coding: utf-8 -*-
"""
操作定義與實現 (Operations Implementation) - 核心純計算層
只包含核心算卡算法與參數提取，100% 不依賴 customtkinter/tkinter GUI 庫。
"""

import random
from typing import Tuple, Dict, Any, Callable

from utils.registry import registry
from core.models import card_is_normal, card_is_climax, get_card_kind, get_card_level, get_card_soul, get_card_base_soul
from core.engine import (
    resolve_damage, push_cards, drain_climax, normal_wash,
    shake_stock, wash_stock, mocha_operation, dragon_star_diffusion,
    perform_bottom_drain_and_burn, add_cards_to_clock
)


# ==================== 1. 所有底層算卡執行邏輯函數 ====================

def _exec_normal_damage(deck, control, clock, op, stabilize_func):
    damage = op["damage"]
    trigger_rate = op.get("trigger_rate", 0)
    triggered = False

    if trigger_rate > 0 and random.random() < trigger_rate / 100.0:
        damage += 1
        triggered = True

    added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, stabilize_func)
    desc = f"普通傷害: {'觸發，' if triggered else ''}"
    if cancelled:
        desc += f"{damage}點傷害在第{cancel_pos}張取消"
    else:
        desc += f"造成{added}點傷害"

    return win, desc, {
        "cancelled_damage": damage if cancelled else None,
        "hit_count": 0 if cancelled else 1,
        "cancel_count": 1 if cancelled else 0,
        "total_damage": added,
    }


def _exec_cancel_damage(deck, control, clock, op, stabilize_func, **kwargs):
    base_damage = op.get("cancel_damage_base", 1)
    bonus_type = op.get("cancel_damage_bonus", "0")
    cancelled_damage = kwargs.get("cancelled_damage", 0) or 0
    soul_points = kwargs.get("soul_points", 0) or 0

    bonus = 0
    if bonus_type == "取消傷害":
        bonus = cancelled_damage
    elif bonus_type == "魂點":
        bonus = soul_points

    damage = max(0, base_damage + bonus)
    added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, stabilize_func)

    desc = f"取消傷害: 基礎{base_damage}+{bonus_type}({bonus})="
    if cancelled:
        desc += f"{damage}點傷害在第{cancel_pos}張取消"
    else:
        desc += f"造成{added}點傷害"

    return win, desc, {
        "cancelled_damage": damage if cancelled else None,
        "hit_count": 0 if cancelled else 1,
        "cancel_count": 1 if cancelled else 0,
        "total_damage": added,
    }


def _exec_role_damage(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    soul_points = kwargs.get("soul_points", 0)
    damage_base = op.get("role_damage_base", 0)
    bonus_type = op.get("role_bonus_type", "魂點")
    trigger_rate = op.get("trigger_rate", 0)

    condition_deck = kwargs.get("condition_deck")
    if condition_deck is None and trigger_rate > 0 and random.random() < trigger_rate / 100.0:
        soul_points += 1

    damage = damage_base + (soul_points if bonus_type == "魂點" else 0)
    added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, stabilize_func)

    desc = f"角色傷害: 基礎{damage_base}+{bonus_type}，當前魂點{soul_points}"
    if cancelled:
        desc += f"，在第{cancel_pos}張取消"
    else:
        desc += f"，造成{added}點傷害"

    return win, desc, {
        "soul_points": soul_points,
        "cancelled_damage": damage if cancelled else None,
        "hit_count": 0 if cancelled else 1,
        "cancel_count": 1 if cancelled else 0,
        "total_damage": added,
    }


def _exec_attack_type(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    attack_type = op.get("attack_type", "正面")
    front_slot = kwargs.get("front_slot")
    enemy_front_roles = kwargs.get("enemy_front_roles")
    soul_points = kwargs.get("soul_points", 0)

    enemy_role = None
    if enemy_front_roles and front_slot in enemy_front_roles:
        enemy_role = enemy_front_roles[front_slot]

    enemy_level_str = "空"
    if enemy_role:
        lvl_item = enemy_role.get("level")
        if hasattr(lvl_item, "get"):
            enemy_level_str = str(lvl_item.get())
        else:
            enemy_level_str = str(lvl_item or "空")

    if enemy_level_str == "空":
        new_soul = soul_points + 1
        desc = f"攻擊方式: 對方角色為空，自動轉為[直擊]，魂點+1 (當前魂點{new_soul})"
        return False, desc, {"total_damage": 0, "soul_points": new_soul, "attack_mode": "直擊"}
    else:
        try:
            e_level = int(enemy_level_str)
        except (ValueError, TypeError):
            e_level = 0

        if attack_type == "側面":
            new_soul = max(0, soul_points - e_level)
            desc = f"攻擊方式: [側面]，減去對方等級({e_level})魂點，當前魂點{new_soul}"
            return False, desc, {"total_damage": 0, "soul_points": new_soul, "attack_mode": "側面", "enemy_level": e_level}
        else:
            desc = f"攻擊方式: [正面]，保持原魂點{soul_points} (對手等級{e_level})"
            return False, desc, {"total_damage": 0, "soul_points": soul_points, "attack_mode": "正面", "enemy_level": e_level}


def _exec_push(deck, control, op, stabilize_func):
    count = op["push_count"]
    over, stats = push_cards(deck, control, count, stabilize_func)
    desc = f"推{stats['pushed']}張，{stats['normal']}肉{stats['climax']}潮"
    return over, desc, {"total_damage": 0}


def _exec_drain_climax(deck, control, op, stabilize_func):
    count = op["count"]
    drain_climax(control, deck, count)
    over = stabilize_func()
    return over, f"按潮反洗: 按{count}潮", {"total_damage": 0}


def _exec_normal_wash(deck, control, op, stabilize_func):
    count = op["normal_wash_count"]
    normal_wash(control, deck, count)
    over = stabilize_func()
    return over, f"普通反洗: 反洗{count}張", {"total_damage": 0}


def _exec_shake(deck, stock, stabilize_func):
    shake_stock(deck, stock)
    over = stabilize_func()
    return over, "搖勻完成", {"total_damage": 0}


def _exec_wash_stock(deck, control, stock, stabilize_func):
    wash_stock(deck, control, stock, stabilize_func)
    over = stabilize_func()
    return over, "洗費完成", {"total_damage": 0}


def _exec_bottom_drain(deck, control, stock, level, clock, op, stabilize_func):
    X = op["X"]
    linkage_type = op.get("linkage_type", "有潮")
    if linkage_type == "有潮":
        params = {"damage": op.get("burn_damage", 1), "times": op.get("burn_times", 1)}
    else:
        params = {
            "base_damage": op.get("base_damage", 3),
            "base_times": op.get("base_times", 0),
            "damage_bonus": op.get("damage_bonus", "0"),
            "times_bonus": op.get("times_bonus", "潮數"),
        }

    over, msg, dmg, cancel_count, hit_count = perform_bottom_drain_and_burn(
        deck, control, stock, level, clock, X, linkage_type, params
    )
    return over, msg, {"total_damage": dmg, "cancel_count": cancel_count, "hit_count": hit_count}


def _exec_dragon_star(deck, control, clock, level, op, stabilize_func):
    count = op["dragon_count"]
    mode = op["dragon_mode"]
    over, stats = dragon_star_diffusion(deck, control, clock, level, count, mode, stabilize_func)
    damage = stats.get("sent_to_clock", 0)

    if mode == "公開":
        desc = f"公開{stats['looked']}張，{stats['normal_in_looked']}肉{stats['climax_in_looked']}潮，放{stats['sent_to_clock']}張，造成{damage}點傷害"
    else:
        desc = f"推{stats['pushed']}張，{stats['normal_pushed']}肉{stats['climax_pushed']}潮，放{stats['sent_to_clock']}張，造成{damage}點傷害"

    return over, desc, {"total_damage": damage}


def _exec_mocha(deck, control, op, stabilize_func):
    count = op["mocha_count"]
    mode = op["mocha_mode"]
    over, stats = mocha_operation(deck, control, count, mode, stabilize_func)
    desc = f"摩{stats['looked']}卡，{stats['normal_in_looked']}肉{stats['climax_in_looked']}潮，送控{stats['sent_to_control']}潮"
    return over, desc, {"total_damage": 0}


def _exec_shoot(deck, control, clock, op, stabilize_func):
    mode = op["shoot_mode"]
    count = op.get("shoot_count", 1) if mode == "牌組" else 1
    damage_dealt = 0

    if mode == "場上":
        clock.append("普通")
        damage_dealt = 1
        over = stabilize_func()
        desc = "射血(場上): 放置1張肉牌到傷害區，造成1點傷害"
    else:
        for _ in range(count):
            if not deck:
                over = stabilize_func()
                if over or not deck:
                    break
            card = deck.pop()
            clock.append(card)
            damage_dealt += 1
            over = stabilize_func()
            if over:
                break
        desc = f"射血(牌組): 放置{damage_dealt}張牌到傷害區，造成{damage_dealt}點傷害"

    return over, desc, {"total_damage": damage_dealt}


def _exec_top_deck(deck, control, op, stabilize_func):
    mode = op["top_deck_mode"]
    if mode == "控室":
        X = op.get("top_deck_count", 1)
        meats = [c for c in control if card_is_normal(c)]
        selected_count = min(X, len(meats))
        removed = 0
        new_control = []
        for c in control:
            if card_is_normal(c) and removed < selected_count:
                removed += 1
            else:
                new_control.append(c)
        control[:] = new_control
        for _ in range(selected_count):
            deck.append("普通")
        desc = f"上頂: 從控制室放{selected_count}張肉到牌組頂"
    else:
        deck.append("普通")
        desc = "上頂: 從場上放1張肉到牌組頂"

    over = stabilize_func()
    return over, desc, {"total_damage": 0}


def _exec_multi_climax_cancel(deck, control, clock, op, stabilize_func):
    X = op["damage"]
    Y = op["required_climax"]
    resolution = []
    climax_positions = []
    climax_count = 0
    cancelled = False
    cancel_position = None
    total_damage = 0

    for i in range(X):
        if not deck:
            if stabilize_func():
                if climax_count >= Y:
                    control.extend(resolution)
                    cancelled = True
                    cancel_position = len(resolution)
                else:
                    total_damage = len(resolution)
                    add_cards_to_clock(clock, resolution, [], control, stabilize_func)
                return True, f"多潮取消: 傷害{X}需{Y}潮，遊戲結束", {"total_damage": total_damage}
            if not deck:
                break

        card = deck.pop()
        resolution.append(card)
        if card_is_climax(card):
            climax_count += 1
            climax_positions.append(len(resolution))

        if climax_count >= Y:
            control.extend(resolution)
            cancelled = True
            cancel_position = len(resolution)
            break

    if not cancelled:
        total_damage = len(resolution)
        add_cards_to_clock(clock, resolution, [], control, stabilize_func)

    game_over = stabilize_func()
    pos_str = ", ".join(map(str, climax_positions)) if climax_positions else "無"
    if cancelled:
        desc = f"多潮取消: 傷害{X}，需{Y}潮。取消，在第{cancel_position}張達到{Y}潮（名場面位置:{pos_str}）"
    else:
        desc = f"多潮取消: 傷害{X}，需{Y}潮。未取消，造成{total_damage}點傷害（名場面位置:{pos_str}）"

    return game_over, desc, {
        "total_damage": total_damage,
        "cancelled_damage": X if cancelled else None,
        "hit_count": 0 if cancelled else 1,
        "cancel_count": 1 if cancelled else 0
    }


def _exec_special_linkage(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    char = op.get("special_char", "早川秋")
    if char == "早川秋":
        X = op.get("hayakawa_count", 0)
        used_actions = 0
        result_parts = []
        phase1_stopped = False
        for i in range(X):
            if not deck:
                if stabilize_func():
                    return True, f"早川秋: 行動{used_actions}次後牌組空，遊戲勝利", {"total_damage": 0}
                if not deck:
                    break
            card = deck[0]
            if card_is_normal(card):
                deck.pop(0)
                control.append(card)
                used_actions += 1
            else:
                used_actions += 1
                phase1_stopped = True
                break
        if used_actions > 0:
            result_parts.append(f"第一階段消耗{used_actions}次行動")
            if phase1_stopped:
                result_parts.append("遇名場面停止")

        params = {"base_damage": 1, "base_times": 0, "damage_bonus": "0", "times_bonus": "潮數"}
        over, msg, dmg, _, _ = perform_bottom_drain_and_burn(deck, control, stock, level, clock, 4, "潮數", params)
        if over:
            return True, f"早川秋: {', '.join(result_parts)}；拔底聯動: {msg}", {"total_damage": dmg}

        remaining = X - used_actions
        if remaining > 0:
            phase2_used = 0
            for i in range(remaining):
                if not deck:
                    if stabilize_func():
                        return True, f"早川秋: 第二階段{phase2_used}次後遊戲勝利", {"total_damage": dmg}
                    if not deck:
                        break
                card = deck[0]
                if card_is_normal(card):
                    deck.pop(0)
                    control.append(card)
                    phase2_used += 1
                else:
                    phase2_used += 1
                    break
            if phase2_used > 0:
                result_parts.append(f"第二階段消耗{phase2_used}次行動")

        over = stabilize_func()
        return over, f"早川秋: {', '.join(result_parts)}；拔底聯動造成{dmg}點傷害", {"total_damage": dmg}

    elif char == "源櫻":
        total_damage = 0
        added, cancelled, win, _ = resolve_damage(deck, control, clock, 1, stabilize_func)
        total_damage += added
        if win or not cancelled:
            return win, f"源櫻: 1點傷害{'取消' if cancelled else '命中'}", {"total_damage": total_damage}

        added2, cancelled2, win2, _ = resolve_damage(deck, control, clock, 2, stabilize_func)
        total_damage += added2
        if win2 or not cancelled2:
            return win2, f"源櫻: 1點取消，2點傷害{'取消' if cancelled2 else '命中'}", {"total_damage": total_damage}

        for _ in range(3):
            if not deck:
                if stabilize_func():
                    return True, "源櫻: 兩次取消置牌時牌組空，勝利", {"total_damage": total_damage}
                if not deck:
                    break
            c = deck.pop()
            add_cards_to_clock(clock, [c], level, control, stabilize_func)

        over = stabilize_func()
        return over, "源櫻: 兩次取消，置3張牌到傷害區", {"total_damage": total_damage}

    else:
        condition_deck = kwargs.get("condition_deck")
        if condition_deck is None or not condition_deck:
            return False, "藍頭盔: 缺少工況數據", {"total_damage": 0}

        top_card = condition_deck[-1]
        is_r0 = (get_card_kind(top_card) == "角色" and get_card_level(top_card) == 0)
        damage_per_hit = 3 if is_r0 else 1

        total_damage = 0
        cancel_count = 0
        hit_count = 0
        game_over = False

        for _ in range(2):
            added, cancelled, win, _ = resolve_damage(deck, control, clock, damage_per_hit, stabilize_func)
            total_damage += added
            if cancelled:
                cancel_count += 1
            else:
                hit_count += 1
            if win or stabilize_func():
                game_over = True
                break

        desc = f"藍頭盔: 頂牌{'是' if is_r0 else '非'}0級角色，造成{damage_per_hit}點傷害2次（取消{cancel_count}次，命中{hit_count}次）"
        return game_over, desc, {"total_damage": total_damage}


def _exec_reduce_soul(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    reduce_amount = op.get("reduce_amount", 0)
    soul_points = kwargs.get("soul_points", 0)
    new_soul = max(0, soul_points - reduce_amount)
    desc = f"減魂: 減少{reduce_amount}點魂，當前魂點{new_soul}"
    return False, desc, {"total_damage": 0, "soul_points": new_soul}


def _exec_ice_armor(ice_armors):
    ice_id = len(ice_armors) + 1
    ice_armors.append({"id": ice_id})
    return False, f"冰甲{ice_id} 能力已激活", {"total_damage": 0}


def _exec_multi_step_operation(deck, control, stock, level, clock, op, stabilize_func, **kwargs):
    steps = op.get("steps", [])
    if not steps:
        return False, "多步驟操作: 步數為0", {"total_damage": 0}

    total_dmg = 0
    hit_count = 0
    cancel_count = 0
    cancelled_dmg_list = []
    descriptions = []
    game_over = False

    for step_idx, step_op in enumerate(steps):
        if game_over or stabilize_func():
            game_over = True
            break

        sub_opt = step_op.get("type", "未知操作")
        if sub_opt in registry.types and registry.types[sub_opt]["execute"]:
            over, sub_desc, sub_extra = registry.execute(
                sub_opt, deck, control, stock, level, clock, step_op, stabilize_func, **kwargs
            )
            dmg = sub_extra.get("total_damage", 0)
            total_dmg += dmg
            hit_count += sub_extra.get("hit_count", 0)
            cancel_count += sub_extra.get("cancel_count", 0)

            if sub_extra.get("cancelled_damage") is not None:
                cancelled_dmg_list.append(sub_extra["cancelled_damage"])

            descriptions.append(f"步{step_idx+1}[{sub_desc}]")

            if over or stabilize_func():
                game_over = True
                break

    full_desc = "多步驟操作: " + " ➔ ".join(descriptions)
    last_cancelled = cancelled_dmg_list[-1] if cancelled_dmg_list else None

    return game_over, full_desc, {
        "total_damage": total_dmg,
        "hit_count": hit_count,
        "cancel_count": cancel_count,
        "cancelled_damage": last_cancelled
    }


# ==================== 2. 集中註冊算卡算法（純粹 Schema 與算法定義） ====================

ALL_MODES = ["single", "regular", "char", "advanced", "condition"]


def register_all_operations():
    """集中註冊基礎算卡算法"""

    registry.register(
        "普通傷害",
        params_def=[
            {"name": "damage", "default": 3, "label": "傷害:", "widget": "entry", "width": 3},
            {"name": "trigger_rate", "default": 0.0, "label": "觸發率", "widget": "entry", "width": 4, "suffix": "%"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_normal_damage(deck, control, clock, op, stab),
    )

    registry.register(
        "取消傷害",
        params_def=[
            {"name": "cancel_damage_base", "default": 1, "label": "傷害:", "widget": "entry", "width": 3},
            {"name": "cancel_damage_bonus", "default": "0", "label": "+", "widget": "combobox", "width": 7, "values": ["0", "取消傷害", "魂點"]},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_cancel_damage(deck, control, clock, op, stab, **kw),
    )

    registry.register(
        "角色傷害",
        params_def=[
            {"name": "role_damage_base", "default": 0, "label": "", "widget": "entry", "width": 3},
            {"name": "role_bonus_type", "default": "魂點", "label": "+", "widget": "combobox", "width": 5, "values": ["魂點", "0"]},
            {"name": "trigger_rate", "default": 30.0, "label": "觸發率", "widget": "entry", "width": 4, "suffix": "%"},
        ],
        modes=["char", "advanced", "condition"],
        execute=_exec_role_damage,
    )

    registry.register(
        "攻擊方式",
        params_def=[
            {"name": "attack_type", "default": "正面", "label": "方式:", "widget": "combobox", "width": 6, "values": ["正面", "側面"]},
        ],
        modes=["condition"],
        execute=_exec_attack_type,
    )

    registry.register(
        "推牌",
        params_def=[
            {"name": "push_count", "default": 1, "label": "推", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_push(deck, control, op, stab),
    )

    registry.register(
        "按潮反洗",
        params_def=[
            {"name": "count", "default": 1, "label": "按", "widget": "entry", "width": 4, "suffix": "潮"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_drain_climax(deck, control, op, stab),
    )

    registry.register(
        "普通反洗",
        params_def=[
            {"name": "normal_wash_count", "default": 1, "label": "反洗", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_normal_wash(deck, control, op, stab),
    )

    registry.register(
        "搖勻",
        params_def=[],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_shake(deck, stock, stab),
    )

    registry.register(
        "洗費",
        params_def=[],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_wash_stock(deck, control, stock, stab),
    )

    registry.register(
        "拔底聯動",
        params_def=[
            {"name": "X", "default": 1, "label": "拔", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_bottom_drain(deck, control, stock, level, clock, op, stab),
    )

    registry.register(
        "龍星擴散爆",
        params_def=[
            {"name": "dragon_mode", "default": "公開", "label": "", "widget": "combobox", "width": 6, "values": ["公開", "推"]},
            {"name": "dragon_count", "default": 1, "label": "", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_dragon_star(deck, control, clock, level, op, stab),
    )

    registry.register(
        "摩卡",
        params_def=[
            {"name": "mocha_mode", "default": "原位", "label": "", "widget": "combobox", "width": 5, "values": ["原位", "洗牌"]},
            {"name": "mocha_count", "default": 1, "label": "摩", "widget": "entry", "width": 4, "suffix": "卡"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_mocha(deck, control, op, stab),
    )

    registry.register(
        "射血",
        params_def=[
            {"name": "shoot_mode", "default": "牌組", "label": "", "widget": "combobox", "width": 6, "values": ["牌組", "場上"], "suffix": "射"},
            {"name": "shoot_count", "default": 1, "label": "", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_shoot(deck, control, clock, op, stab),
    )

    registry.register(
        "上頂",
        params_def=[
            {"name": "top_deck_mode", "default": "控室", "label": "", "widget": "combobox", "width": 6, "values": ["控室", "場上"]},
            {"name": "top_deck_count", "default": 1, "label": "", "widget": "entry", "width": 4, "suffix": "張"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_top_deck(deck, control, op, stab),
    )

    registry.register(
        "多潮取消",
        params_def=[
            {"name": "damage", "default": 3, "label": "傷害:", "widget": "entry", "width": 3},
            {"name": "required_climax", "default": 1, "label": "所需取消潮數:", "widget": "entry", "width": 3},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_multi_climax_cancel(deck, control, clock, op, stab),
    )

    registry.register(
        "特殊聯動",
        params_def=[
            {"name": "special_char", "default": "早川秋", "label": "", "widget": "combobox", "width": 7, "values": ["早川秋", "源櫻"]},
            {"name": "hayakawa_count", "default": 0, "label": "", "widget": "entry", "width": 4, "suffix": "煙"},
        ],
        modes=ALL_MODES,
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_special_linkage(deck, control, stock, level, clock, op, stab, **kw),
    )

    registry.register(
        "減魂",
        params_def=[
            {"name": "reduce_amount", "default": 1, "label": "減", "widget": "entry", "width": 4, "suffix": "魂"},
        ],
        modes=["char", "advanced", "condition"],
        execute=_exec_reduce_soul,
    )

    registry.register(
        "取消觸發",
        params_def=[],
        modes=["char", "advanced", "condition"],
    )

    registry.register(
        "冰甲",
        params_def=[],
        modes=["char", "advanced", "condition"],
        execute=lambda deck, control, stock, level, clock, op, stab, **kw: _exec_ice_armor(kw.get("ice_armors", [])),
    )

    registry.register(
        "多步驟操作",
        params_def=[],
        modes=["char", "advanced", "condition"],
        execute=_exec_multi_step_operation,
    )

    from core.condition_operations import register_condition_operations
    register_condition_operations()


register_all_operations()