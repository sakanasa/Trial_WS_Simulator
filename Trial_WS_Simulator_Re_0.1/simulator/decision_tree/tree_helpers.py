# -*- coding: utf-8 -*-
"""
决策树数学与排列辅助工具 (Decision Tree Helpers)
包含组合数 nCr、多元超几何分布抽卡、有效对战组等价排列算法与文本格式化。
"""

import math
import itertools
from typing import List, Dict, Any, Tuple, Optional

from core.models import get_card_level, get_card_kind, get_card_trigger_soul, get_card_soul


def nCr(n: int, r: int) -> int:
    if r < 0 or r > n:
        return 0
    return math.comb(n, r)


def format_card_info(card: Any) -> str:
    if not card:
        return "[空]"
    if isinstance(card, str):
        kind = "高潮" if card == "高潮" else "角色"
        return f"[{kind}] Lv.0, 触发魂0"
    
    kind = get_card_kind(card)
    name = card.get("name", kind) if isinstance(card, dict) else getattr(card, "name", kind)
    level = get_card_level(card)
    trig_soul = get_card_trigger_soul(card)
    
    if not name or name.startswith("新自定义") or name == "自定义角色":
        name = kind
        
    return f"[{name}] Lv.{level}, 触发魂{trig_soul}"


def get_umi_draw_combinations(deck_cards: list, k: int) -> List[Tuple[List[dict], float]]:
    if not deck_cards or k <= 0:
        return []

    groups: Dict[tuple, List[dict]] = {}
    for card in deck_cards:
        if isinstance(card, str):
            sig = ("高潮" if card == "高潮" else "角色", 0, 0, 1, card)
        else:
            sig = (
                get_card_kind(card),
                get_card_level(card),
                get_card_trigger_soul(card),
                get_card_soul(card),
                card.get("name", get_card_kind(card)) if isinstance(card, dict) else getattr(card, "name", "角色")
            )
        groups.setdefault(sig, []).append(card)

    group_keys = list(groups.keys())
    counts = [len(groups[key]) for key in group_keys]
    total_cards = len(deck_cards)
    sample_k = min(k, total_cards)
    total_combinations_count = nCr(total_cards, sample_k)

    if total_combinations_count <= 0:
        return []

    results = []

    def generate_partitions(group_idx: int, remaining_k: int, current_counts: list):
        if remaining_k == 0:
            full_counts = current_counts + [0] * (len(counts) - len(current_counts))
            num_ways = 1
            drawn_cards = []
            for i, drawn_cnt in enumerate(full_counts):
                num_ways *= nCr(counts[i], drawn_cnt)
                drawn_cards.extend(groups[group_keys[i]][:drawn_cnt])

            prob = num_ways / total_combinations_count
            if prob > 1e-6:
                results.append((drawn_cards, prob))
            return

        if group_idx >= len(counts):
            return

        max_take = min(counts[group_idx], remaining_k)
        for take in range(max_take, -1, -1):
            generate_partitions(group_idx + 1, remaining_k - take, current_counts + [take])

    generate_partitions(0, sample_k, [])
    return results


def get_slot_signature(slot_key: str, condition_front_cards: dict, enemy_front_roles: dict) -> tuple:
    my_cards = condition_front_cards.get(slot_key, [])
    my_sig = None
    if my_cards:
        c = my_cards[0]
        my_sig = (
            c.get("name", "角色"),
            int(c.get("level", 0) or 0),
            int(c.get("power", 500) or 500),
            int(c.get("soul", 1) or 1),
            str(c.get("effects", {}))
        )

    e_role = enemy_front_roles.get(slot_key, {})
    e_lvl = e_role.get("level", "0")
    if hasattr(e_lvl, "get"):
        e_lvl = e_lvl.get()
    e_pwr = e_role.get("power", 500)
    if hasattr(e_pwr, "get"):
        e_pwr = e_pwr.get()

    e_sig = (str(e_lvl), int(e_pwr or 500))
    return (my_sig, e_sig)


def group_slots_by_equivalence(available_slots: List[str], condition_front_cards: dict, enemy_front_roles: dict) -> List[Tuple[str, List[str], str]]:
    groups: Dict[tuple, List[str]] = {}
    for slot in available_slots:
        sig = get_slot_signature(slot, condition_front_cards, enemy_front_roles)
        groups.setdefault(sig, []).append(slot)

    result = []
    for sig, slot_list in groups.items():
        rep_slot = slot_list[0]
        if len(slot_list) == 1:
            display_text = rep_slot
        elif len(slot_list) == 2:
            other_slot = [s for s in slot_list if s != rep_slot][0]
            display_text = f"{rep_slot}(与{other_slot}等价)"
        else:
            others = "、".join([s for s in slot_list if s != rep_slot])
            display_text = f"{rep_slot}(与{others}等价)"
        result.append((rep_slot, slot_list, display_text))

    return result


def get_position_permutations(condition_front_cards: dict, enemy_front_roles: dict) -> List[Tuple[dict, bool]]:
    slots = ["前列1", "前列2", "前列3"]
    cards_only = []
    for s in slots:
        c_list = condition_front_cards.get(s, [])
        cards_only.append(c_list[0] if c_list else None)

    if not any(cards_only):
        return []

    unique_perms = []
    seen_multisets = set()

    for p in itertools.permutations(cards_only):
        new_front = {slots[i]: [p[i]] if p[i] else [] for i in range(3)}

        active_battles = []
        for i, s in enumerate(slots):
            my_c = p[i]
            if my_c:
                my_sig = (
                    my_c.get("name", "角色"),
                    int(my_c.get("level", 0) or 0),
                    int(my_c.get("power", 500) or 500),
                    int(my_c.get("soul", 1) or 1),
                    str(my_c.get("effects", {}))
                )

                e_role = enemy_front_roles.get(s, {})
                e_lvl = e_role.get("level", "0")
                if hasattr(e_lvl, "get"):
                    e_lvl = e_lvl.get()
                e_pwr = e_role.get("power", 500)
                if hasattr(e_pwr, "get"):
                    e_pwr = e_pwr.get()

                e_sig = (str(e_lvl or "空"), int(e_pwr or 500))
                active_battles.append((my_sig, e_sig))

        active_battles_sorted = tuple(sorted(active_battles, key=lambda x: (str(x[0]), str(x[1]))))

        if active_battles_sorted not in seen_multisets:
            seen_multisets.add(active_battles_sorted)

            is_original = True
            for s in slots:
                old_c = condition_front_cards.get(s, [])
                new_c = new_front.get(s, [])
                if (old_c and not new_c) or (not old_c and new_c):
                    is_original = False
                    break
                if old_c and new_c and old_c[0] is not new_c[0]:
                    is_original = False
                    break

            unique_perms.append((new_front, is_original))

    return unique_perms


def calc_damage_branches(snapshot: Any, damage: int) -> List[Tuple[str, float, int, int, int]]:
    N = snapshot.enemy_deck_normal
    C = snapshot.enemy_deck_climax
    T = N + C

    if T <= 0 or damage <= 0:
        return [("命中 0 点", 1.0, 0, 0, 0)]

    branches = []
    prob_sum = 0.0
    p_prev = 1.0
    cur_N, cur_T = N, T

    for k in range(1, damage + 1):
        if cur_T <= 0 or C <= 0 or cur_N < (k - 1):
            break

        p_k = p_prev * (C / cur_T)
        if p_k > 1e-6:
            branches.append((f"在第 {k} 张取消", p_k, k - 1, 1, k))
            prob_sum += p_k

        p_prev *= (cur_N / cur_T)
        cur_N -= 1
        cur_T -= 1

    if N >= damage and T >= damage:
        p_hit = 1.0
        for i in range(damage):
            p_hit *= (N - i) / (T - i)
        if p_hit > 1e-6:
            branches.append((f"全部命中 {damage} 点", p_hit, damage, 0, 0))
            prob_sum += p_hit

    if prob_sum > 0:
        branches = [(desc, p / prob_sum, n, c, pos) for desc, p, n, c, pos in branches]

    return branches