# -*- coding: utf-8 -*-
"""
決策樹數據模型與局勢快照 (Decision Tree Models & State Snapshot)
包含 TreeNode 樹節點類、GameStateSnapshot 狀態快照類以及 pure-data 數據清洗函數。
"""

import copy
import random
import tkinter as tk
import customtkinter as ctk
from typing import List, Dict, Any, Tuple, Optional, Callable


def sanitize_card_dict(card: Any) -> Any:
    """從卡牌/操作字典中徹底剔除所有 Tkinter/CTk 控件與 Variable 句柄，只留純數據"""
    if isinstance(card, str):
        return card
    if not isinstance(card, dict):
        return str(card)

    cleaned = {}
    for k, v in card.items():
        if isinstance(v, (tk.Variable, tk.Widget, ctk.CTkBaseClass)):
            continue
        if k.endswith("_var") or k.startswith("btn_") or k in ("card_container", "pos_label", "desc_box", "row_frame", "frame", "ops_frame", "ctrl_group"):
            continue
        if isinstance(v, dict):
            cleaned[k] = sanitize_card_dict(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_card_dict(item) for item in v]
        else:
            cleaned[k] = copy.copy(v)
    return cleaned


def sanitize_zone_data(zone_data: Any) -> Any:
    """遞歸清理卡區字典或列表中的卡牌數據，防止 deepcopy 拋出 pickle tkapp 錯誤"""
    if isinstance(zone_data, list):
        return [sanitize_card_dict(c) for c in zone_data]
    elif isinstance(zone_data, dict):
        return {k: [sanitize_card_dict(c) for c in v] for k, v in zone_data.items()}
    return zone_data


def _sanitize_enemy_front_roles(raw_roles: dict) -> dict:
    """清洗敵方前列角色數據，將 tk.StringVar/tk.IntVar 轉為原生類型"""
    clean = {}
    if not raw_roles:
        return clean
    for k, v in raw_roles.items():
        if isinstance(v, dict):
            lvl = v.get("level", "0")
            pwr = v.get("power", 500)
            is_rev = v.get("is_reversed", False)

            if hasattr(lvl, "get"):
                lvl = lvl.get()
            if hasattr(pwr, "get"):
                pwr = pwr.get()

            clean[k] = {
                "level": str(lvl),
                "power": int(pwr or 500),
                "is_reversed": bool(is_rev)
            }
    return clean


class GameStateSnapshot:
    """局勢狀態快照類"""

    def __init__(
        self,
        my_deck: list = None,
        deterministic_top: list = None,
        my_control: list = None,
        my_stock: list = None,
        my_level: Any = None,
        my_clock: Any = None,
        enemy_deck_normal: int = 17,
        enemy_deck_climax: int = 8,
        enemy_control_normal: int = 0,
        enemy_control_climax: int = 0,
        enemy_clock_meat: int = 0,
        enemy_clock_climax: int = 0,
        enemy_level_meat: int = 0,
        enemy_level_climax: int = 0,
        enemy_front_roles: dict = None,
        condition_front_cards: dict = None,
        role_soul: int = 3,
        role_power: int = 500,
        attack_mode: str = "正面",
        game_over: bool = False,
        my_failed: bool = False,
    ):
        self.my_deck = sanitize_zone_data(my_deck or [])
        self.deterministic_top = sanitize_zone_data(deterministic_top or [])
        self.my_control = sanitize_zone_data(my_control or [])
        self.my_stock = sanitize_zone_data(my_stock or [])
        self.my_level = sanitize_zone_data(my_level or {})
        self.my_clock = sanitize_zone_data(my_clock or {})

        self.enemy_deck_normal = max(0, enemy_deck_normal)
        self.enemy_deck_climax = max(0, enemy_deck_climax)
        self.enemy_control_normal = max(0, enemy_control_normal)
        self.enemy_control_climax = max(0, enemy_control_climax)

        self.enemy_clock_meat = max(0, enemy_clock_meat)
        self.enemy_clock_climax = max(0, enemy_clock_climax)
        self.enemy_level_meat = max(0, enemy_level_meat)
        self.enemy_level_climax = max(0, enemy_level_climax)

        self.enemy_front_roles = _sanitize_enemy_front_roles(enemy_front_roles)
        self.condition_front_cards = sanitize_zone_data(condition_front_cards or {f"前列{i}": [] for i in range(1, 4)})

        self.role_soul = role_soul
        self.role_power = role_power
        self.attack_mode = attack_mode
        self.game_over = game_over
        self.my_failed = my_failed

    @property
    def enemy_deck_total(self) -> int:
        return self.enemy_deck_normal + self.enemy_deck_climax

    def is_top_deterministic(self, count: int = 1) -> bool:
        return len(self.deterministic_top) >= count

    def push_to_deterministic_top(self, cards: list, reverse: bool = True):
        to_push = reversed(cards) if reverse else cards
        for card in to_push:
            self.deterministic_top.append(sanitize_card_dict(card))

    def clone(self) -> "GameStateSnapshot":
        return GameStateSnapshot(
            my_deck=self.my_deck,
            deterministic_top=self.deterministic_top,
            my_control=self.my_control,
            my_stock=self.my_stock,
            my_level=self.my_level,
            my_clock=self.my_clock,
            enemy_deck_normal=self.enemy_deck_normal,
            enemy_deck_climax=self.enemy_deck_climax,
            enemy_control_normal=self.enemy_control_normal,
            enemy_control_climax=self.enemy_control_climax,
            enemy_clock_meat=self.enemy_clock_meat,
            enemy_clock_climax=self.enemy_clock_climax,
            enemy_level_meat=self.enemy_level_meat,
            enemy_level_climax=self.enemy_level_climax,
            enemy_front_roles=self.enemy_front_roles,
            condition_front_cards=self.condition_front_cards,
            role_soul=self.role_soul,
            role_power=self.role_power,
            attack_mode=self.attack_mode,
            game_over=self.game_over,
            my_failed=self.my_failed,
        )

    def pop_my_deck_card(self) -> Tuple[Any, bool]:
        if self.deterministic_top:
            return self.deterministic_top.pop(), True
        elif self.my_deck:
            return self.my_deck.pop(), False
        return None, False

    def refresh_my_deck_if_empty(self):
        if not self.deterministic_top and not self.my_deck and self.my_control:
            self.my_deck.extend(self.my_control)
            self.my_control.clear()
            random.shuffle(self.my_deck)
            if self.my_deck:
                top = self.my_deck.pop()
                # 依賴 core.engine 的規則進行刷新傷害判定
                from core.engine import add_cards_to_clock
                add_cards_to_clock(self.my_clock, [top], self.my_level, self.my_control, lambda: False)

    def apply_enemy_damage(self, dmg_count: int):
        for _ in range(dmg_count):
            self.enemy_clock_meat += 1
            if self.enemy_clock_meat + self.enemy_clock_climax >= 7:
                self.enemy_clock_meat -= 7
                self.enemy_level_meat += 1
                if self.enemy_level_meat + self.enemy_level_climax >= 4:
                    self.game_over = True


class TreeNode:
    """決策樹節點結構類"""

    def __init__(
        self,
        name: str,
        node_type: str = "info",
        prob: float = 1.0,
        cum_prob: float = 1.0,
        state_snapshot: GameStateSnapshot = None,
        details: str = "",
        remaining_plan: list = None,
        node_counter_ref: list = None,
        on_progress_cb: Optional[Callable[[int], None]] = None,
    ):
        self.name = name
        self.node_type = node_type
        self.prob = prob
        self.cum_prob = cum_prob
        self.state_snapshot = state_snapshot
        self.details = details
        self.remaining_plan = remaining_plan or []
        self.children: List["TreeNode"] = []
        self.parent: Optional["TreeNode"] = None

        self.exp_winrate: float = 0.0
        self.is_optimal: bool = False
        self.best_choice: str = ""

        if node_counter_ref is not None:
            node_counter_ref[0] += 1
            if on_progress_cb and node_counter_ref[0] % 50 == 0:
                on_progress_cb(node_counter_ref[0])

    def add_child(self, child: "TreeNode"):
        child.parent = self
        child.cum_prob = self.cum_prob * child.prob
        self.children.append(child)