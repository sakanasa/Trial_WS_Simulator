# -*- coding: utf-8 -*-
"""
核心結算引擎 (Core Combat Engine)
包含了 Weiss Schwarz 核心規則結算：
傷害結算、牌組刷新與刷新傷害、等級區升級溢出、多潮取消、拔底聯動、摩卡、龍星、吃傷看頂等。
"""

import random
from typing import List, Dict, Tuple, Any, Callable, Optional, Union

from core.models import (
    Card, GameState, card_is_climax, card_is_normal,
    get_card_kind, get_card_level, get_card_soul, get_card_base_soul
)


def build_deck(normal: int, climax: int) -> List[str]:
    """構建並打亂牌組（常規模式極速字符串形式）"""
    deck = ["普通"] * normal + ["名場面"] * climax
    random.shuffle(deck)
    return deck


def add_cards_to_clock(
    clock: Union[List[Any], Dict[str, List[Any]]],
    cards: List[Any],
    level: Union[List[Any], Dict[str, List[Any]]],
    control: List[Any],
    stabilize_func: Callable[[], bool]
) -> bool:
    """自適應將卡牌放入傷害區（支持列表形式與工況字典形式）"""
    if isinstance(clock, list):
        clock.extend(cards)
    elif isinstance(clock, dict):
        for card in cards:
            placed = False
            for i in range(1, 8):
                k = f"傷害{i}"
                if not clock.get(k):
                    clock[k] = [card]
                    placed = True
                    break
            if not placed:
                control.append(card)

    return stabilize_func()


def process_clock_overflow(
    clock: Union[List[Any], Dict[str, List[Any]]],
    level: Union[List[Any], Dict[str, List[Any]]],
    control: List[Any]
) -> bool:
    """處理傷害區溢出升級（>= 7張）"""
    if isinstance(clock, dict):
        clock_list = [clock[f"傷害{i}"][0] for i in range(1, 8) if clock.get(f"傷害{i}")]
    else:
        clock_list = clock

    while len(clock_list) >= 7:
        first7 = clock_list[:7]
        chosen_idx = 0

        for i, card in enumerate(first7):
            if card_is_normal(card):
                chosen_idx = i
                break

        chosen = first7.pop(chosen_idx)

        # 放入等級區
        if isinstance(level, dict):
            placed = False
            for i in range(1, 5):
                lk = f"等級{i}"
                if not level.get(lk):
                    level[lk] = [chosen]
                    placed = True
                    break
            if not placed:
                return True
        else:
            level.append(chosen)
            if len(level) >= 4:
                control.extend(first7)
                del clock_list[:7]
                return True

        control.extend(first7)
        del clock_list[:7]

        if isinstance(clock, dict):
            for i in range(1, 8):
                clock[f"傷害{i}"].clear()
            for idx, c in enumerate(clock_list):
                if idx < 7:
                    clock[f"傷害{idx+1}"] = [c]

    return False


def stabilize(
    deck: List[Any],
    control: List[Any],
    level: Union[List[Any], Dict[str, List[Any]]],
    clock: Union[List[Any], Dict[str, List[Any]]]
) -> bool:
    """通用遊戲穩定性狀態修正"""
    while True:
        level_count = sum(1 for v in level.values() if v) if isinstance(level, dict) else len(level)
        if level_count >= 4 or (len(deck) + len(control) == 0):
            return True

        if not deck and control:
            deck[:] = control[:]
            random.shuffle(deck)
            control.clear()
            top = deck.pop()
            add_cards_to_clock(clock, [top], level, control, lambda: False)
            continue

        clock_count = sum(1 for v in clock.values() if v) if isinstance(clock, dict) else len(clock)
        if clock_count >= 7:
            if process_clock_overflow(clock, level, control):
                return True
            continue

        break
    return False


def resolve_damage(
    deck: List[Any],
    control: List[Any],
    clock: Union[List[Any], Dict[str, List[Any]]],
    damage: int,
    stabilize_func: Callable[[], bool]
) -> Tuple[int, bool, bool, Optional[int]]:
    """傷害判定結算（明確返回在第 X 張取消）"""
    total_damage = 0
    resolution = []
    cancelled = False
    cancel_position = None

    for i in range(damage):
        if not deck:
            if stabilize_func():
                return total_damage, cancelled, True, cancel_position
            if not deck:
                return total_damage, cancelled, True, cancel_position

        card = deck.pop()
        resolution.append(card)

        if not deck:
            if stabilize_func():
                return total_damage, cancelled, True, cancel_position

        if card_is_climax(card):
            cancel_position = len(resolution)
            control.extend(resolution)
            resolution.clear()
            cancelled = True
            break

    if not cancelled:
        total_damage = len(resolution)
        over = add_cards_to_clock(clock, resolution, [], control, stabilize_func)
        resolution.clear()
        if over:
            return total_damage, cancelled, True, cancel_position

    return total_damage, cancelled, False, cancel_position


def execute_ice_armor(
    deck: List[Any],
    control: List[Any],
    clock: Any,
    level: Any,
    X: int,
    stabilize_func: Callable[[], bool]
) -> Tuple[int, bool]:
    """吃傷看頂能力觸發：命中 X 次時，從牌組頂端翻開最多 X 張肉牌推入控制室"""
    Y = 0
    for _ in range(X):
        if not deck:
            if stabilize_func():
                return Y, True
            break
        top_card = deck[-1]
        if card_is_climax(top_card):
            break

        card = deck.pop()
        control.append(card)
        Y += 1
        if stabilize_func():
            return Y, True

    return Y, False


def push_cards(deck: List[Any], control: List[Any], count: int, stabilize_func: Callable[[], bool]):
    remaining = count
    pushed_normal = 0
    pushed_climax = 0

    while remaining > 0:
        if not deck:
            if stabilize_func():
                return True, {'pushed': count - remaining, 'normal': pushed_normal, 'climax': pushed_climax}
            if not deck:
                break

        card = deck.pop()
        control.append(card)
        if card_is_normal(card):
            pushed_normal += 1
        else:
            pushed_climax += 1

        remaining -= 1
        if not deck:
            if stabilize_func():
                return True, {'pushed': count - remaining, 'normal': pushed_normal, 'climax': pushed_climax}

    return False, {'pushed': count - remaining, 'normal': pushed_normal, 'climax': pushed_climax}


def drain_climax(control: List[Any], deck: List[Any], keep_count: int) -> None:
    if not control:
        return

    climax_count = sum(1 for c in control if card_is_climax(c))
    keep_count = min(keep_count, climax_count)

    new_control = []
    returned = []
    kept_climax = 0

    for card in control:
        if card_is_climax(card) and kept_climax < keep_count:
            new_control.append(card)
            kept_climax += 1
        else:
            returned.append(card)

    control[:] = new_control
    deck.extend(returned)
    random.shuffle(deck)


def normal_wash(control: List[Any], deck: List[Any], count: int) -> None:
    if not control or count <= 0:
        return

    normal_cards = [c for c in control if card_is_normal(c)]
    if not normal_cards:
        return

    selected_count = min(count, len(normal_cards))
    selected = []
    new_control = []

    for card in control:
        if card_is_normal(card) and len(selected) < selected_count:
            selected.append(card)
        else:
            new_control.append(card)

    control[:] = new_control
    deck.extend(selected)
    random.shuffle(deck)


def shake_stock(deck: List[Any], stock: List[Any]) -> None:
    n = len(stock)
    if n == 0:
        return

    deck.extend(stock)
    stock.clear()
    random.shuffle(deck)

    for _ in range(n):
        if deck:
            stock.append(deck.pop())
        else:
            break


def wash_stock(deck: List[Any], control: List[Any], stock: List[Any], stabilize_func: Optional[Callable[[], bool]] = None) -> None:
    n = len(stock)
    if n == 0:
        return

    control.extend(stock)
    stock.clear()

    for _ in range(n):
        if not deck:
            if stabilize_func:
                if stabilize_func():
                    return
                if not deck:
                    break
            else:
                break
        stock.append(deck.pop())


def mocha_operation(deck: List[Any], control: List[Any], count: int, mode: str, stabilize_func: Callable[[], bool]):
    take = min(count, len(deck))
    if take == 0:
        if not deck:
            if stabilize_func():
                return True, {'looked': 0, 'normal_in_looked': 0, 'climax_in_looked': 0, 'sent_to_control': 0}
            take = min(count, len(deck))
            if take == 0:
                return False, {'looked': 0, 'normal_in_looked': 0, 'climax_in_looked': 0, 'sent_to_control': 0}

    top_cards = deck[-take:]
    del deck[-take:]

    normal_in_looked = sum(1 for c in top_cards if card_is_normal(c))
    climax_in_looked = sum(1 for c in top_cards if card_is_climax(c))

    climax_cards = [c for c in top_cards if card_is_climax(c)]
    normal_cards = [c for c in top_cards if card_is_normal(c)]

    control.extend(climax_cards)
    deck.extend(normal_cards)

    if not deck:
        if stabilize_func():
            return True, {'looked': take, 'normal_in_looked': normal_in_looked, 'climax_in_looked': climax_in_looked, 'sent_to_control': len(climax_cards)}

    if mode == "洗牌":
        random.shuffle(deck)

    return False, {'looked': take, 'normal_in_looked': normal_in_looked, 'climax_in_looked': climax_in_looked, 'sent_to_control': len(climax_cards)}


def dragon_star_diffusion(deck: List[Any], control: List[Any], clock: Any, level: Any, count: int, mode: str, stabilize_func: Callable[[], bool]):
    if mode == "公開":
        take = min(count, len(deck))
        if take == 0:
            if not deck:
                if stabilize_func():
                    return True, {'looked': 0, 'normal_in_looked': 0, 'climax_in_looked': 0, 'sent_to_clock': 0}
                take = min(count, len(deck))
                if take == 0:
                    return False, {'looked': 0, 'normal_in_looked': 0, 'climax_in_looked': 0, 'sent_to_clock': 0}

        top_cards = deck[-take:]
        normal_in_looked = sum(1 for c in top_cards if card_is_normal(c))
        climax_in_looked = sum(1 for c in top_cards if card_is_climax(c))
        C = climax_in_looked
        random.shuffle(deck)

        sent_to_clock = 0
        for _ in range(C):
            if not deck:
                if stabilize_func():
                    return True, {'looked': take, 'normal_in_looked': normal_in_looked, 'climax_in_looked': C, 'sent_to_clock': sent_to_clock}
                if not deck:
                    break
            card = deck.pop()
            add_cards_to_clock(clock, [card], level, control, stabilize_func)
            sent_to_clock += 1
            if stabilize_func():
                return True, {'looked': take, 'normal_in_looked': normal_in_looked, 'climax_in_looked': C, 'sent_to_clock': sent_to_clock}

        return False, {'looked': take, 'normal_in_looked': normal_in_looked, 'climax_in_looked': C, 'sent_to_clock': sent_to_clock}

    else:
        remaining = count
        pushed_normal = 0
        pushed_climax = 0

        while remaining > 0:
            if not deck:
                if stabilize_func():
                    return True, {'pushed': count - remaining, 'normal_pushed': pushed_normal, 'climax_pushed': pushed_climax, 'sent_to_clock': 0}
                if not deck:
                    break
            card = deck.pop()
            control.append(card)
            if card_is_normal(card):
                pushed_normal += 1
            else:
                pushed_climax += 1
            remaining -= 1

            if not deck:
                if stabilize_func():
                    return True, {'pushed': count - remaining, 'normal_pushed': pushed_normal, 'climax_pushed': pushed_climax, 'sent_to_clock': 0}

        D = pushed_climax
        sent_to_clock = 0
        for _ in range(D):
            if not deck:
                if stabilize_func():
                    return True, {'pushed': count - remaining, 'normal_pushed': pushed_normal, 'climax_pushed': D, 'sent_to_clock': sent_to_clock}
                if not deck:
                    break
            card = deck.pop()
            add_cards_to_clock(clock, [card], level, control, stabilize_func)
            sent_to_clock += 1
            if stabilize_func():
                return True, {'pushed': count - remaining, 'normal_pushed': pushed_normal, 'climax_pushed': D, 'sent_to_clock': sent_to_clock}

        return False, {'pushed': count - remaining, 'normal_pushed': pushed_normal, 'climax_pushed': D, 'sent_to_clock': sent_to_clock}


def perform_bottom_drain_and_burn(deck: List[Any], control: List[Any], stock: List[Any], level: Any, clock: Any, X: int, linkage_type: str, params: Dict[str, Any]):
    def local_stabilize():
        return stabilize(deck, control, level, clock)

    C = 0
    for i in range(X):
        if not deck:
            if local_stabilize():
                return True, f"拔底{X}張，潮{C}張；遊戲勝利", 0, 0, 0
            if not deck:
                break

        card = deck.pop(0)
        control.append(card)
        if card_is_climax(card):
            C += 1

        if not deck:
            if local_stabilize():
                return True, f"拔底{X}張，潮{C}張；遊戲勝利", 0, 0, 0

    total_burn_damage = 0
    cancel_count = 0
    hit_count = 0

    if linkage_type == "有潮":
        if C >= 1:
            damage = params["damage"]
            times = params["times"]
            for _ in range(times):
                if local_stabilize():
                    return True, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害；遊戲勝利", total_burn_damage, cancel_count, hit_count
                added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, local_stabilize)
                total_burn_damage += added
                if cancelled:
                    cancel_count += 1
                else:
                    hit_count += 1
                if win or local_stabilize():
                    return True, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害；遊戲勝利", total_burn_damage, cancel_count, hit_count
            return False, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害", total_burn_damage, cancel_count, hit_count
        else:
            return False, f"拔底{X}張，潮0張；無名場面，不造成傷害", 0, 0, 0
    else:
        A = params["base_damage"]
        B = params["base_times"]
        damage_bonus = C if params.get("damage_bonus") == "潮數" else 0
        times_bonus = C if params.get("times_bonus") == "潮數" else 0
        damage = A + damage_bonus
        times = B + times_bonus

        for _ in range(times):
            if local_stabilize():
                return True, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害；遊戲勝利", total_burn_damage, cancel_count, hit_count
            added, cancelled, win, cancel_pos = resolve_damage(deck, control, clock, damage, local_stabilize)
            total_burn_damage += added
            if cancelled:
                cancel_count += 1
            else:
                hit_count += 1
            if win or local_stabilize():
                return True, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害；遊戲勝利", total_burn_damage, cancel_count, hit_count
        return False, f"拔底{X}張，潮{C}張；後續判定：{damage}點{times}次，取消{cancel_count}次，命中{hit_count}次，共造成{total_burn_damage}點傷害", total_burn_damage, cancel_count, hit_count