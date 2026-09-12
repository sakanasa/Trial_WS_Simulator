# -*- coding: utf-8 -*-
"""
決策樹評估器與入口 (Decision Tree Evaluator & Entry Runners)
包含 Expectimax 勝率回溯計算算法與完整決策樹構建入口。
"""

import math
from typing import Any, Optional, Callable, List

from .tree_model import TreeNode, GameStateSnapshot, sanitize_zone_data
from .branch_expanders import DecisionTreeBuilder, EffectRegistry


def evaluate_tree_expectations(node: TreeNode) -> float:
    """自底向上反向回溯計算整棵樹的期望勝率（Expectimax 算法）"""
    if node.node_type == "terminal" or not node.children:
        node.exp_winrate = 1.0 if (node.state_snapshot and node.state_snapshot.game_over) else 0.0
        return node.exp_winrate

    if node.node_type == "decision":
        for child in node.children:
            evaluate_tree_expectations(child)

        best_rate = max((c.exp_winrate for c in node.children), default=0.0)
        node.exp_winrate = best_rate

        for child in node.children:
            if best_rate > 0.0 and math.isclose(child.exp_winrate, best_rate, abs_tol=1e-6):
                child.is_optimal = True
                node.best_choice = child.name.split(" (")[0]
            else:
                child.is_optimal = False

    else:
        for child in node.children:
            evaluate_tree_expectations(child)

        node.exp_winrate = sum(c.prob * c.exp_winrate for c in node.children)

    return node.exp_winrate


def build_full_decision_tree(
    my_deck: list,
    my_control: list,
    my_stock: list,
    my_level: Any,
    my_clock: Any,
    enemy_deck_normal: int,
    enemy_deck_climax: int,
    enemy_control_normal: int,
    enemy_control_climax: int,
    enemy_level_meat: int,
    enemy_level_climax: int,
    enemy_clock_meat: int,
    enemy_clock_climax: int,
    enemy_front_roles: dict,
    condition_roles: list,
    condition_front_cards: dict,
    on_progress_cb: Optional[Callable[[int], None]] = None,
) -> TreeNode:
    """構建整棵決策樹的總入口函數，支持 on_progress_cb 節點生成進度回調"""
    node_counter_ref = [0]

    clean_my_deck = sanitize_zone_data(my_deck)
    clean_my_control = sanitize_zone_data(my_control)
    clean_my_stock = sanitize_zone_data(my_stock)
    clean_my_level = sanitize_zone_data(my_level)
    clean_my_clock = sanitize_zone_data(my_clock)
    clean_front_cards = sanitize_zone_data(condition_front_cards)

    root_snapshot = GameStateSnapshot(
        my_deck=clean_my_deck,
        my_control=clean_my_control,
        my_stock=clean_my_stock,
        my_level=clean_my_level,
        my_clock=clean_my_clock,
        enemy_deck_normal=enemy_deck_normal,
        enemy_deck_climax=enemy_deck_climax,
        enemy_control_normal=enemy_control_normal,
        enemy_control_climax=enemy_control_climax,
        enemy_level_meat=enemy_level_meat,
        enemy_level_climax=enemy_level_climax,
        enemy_clock_meat=enemy_clock_meat,
        enemy_clock_climax=enemy_clock_climax,
        enemy_front_roles=enemy_front_roles,
        condition_front_cards=clean_front_cards,
        role_soul=3,
    )

    root_node = TreeNode(
        name="🌐 初始局勢 (概率 100%)",
        node_type="root",
        prob=1.0,
        cum_prob=1.0,
        state_snapshot=root_snapshot,
        details="決策樹推演開始，成功初始化局勢狀態。",
        node_counter_ref=node_counter_ref,
        on_progress_cb=on_progress_cb,
    )

    pos_choices = DecisionTreeBuilder.expand_position_swap_decision(root_node, node_counter_ref, on_progress_cb)

    slots = ["前列1", "前列2", "前列3"]
    for choice in pos_choices:
        DecisionTreeBuilder.expand_attack_sequence(
            parent_node=choice,
            remaining_slots=slots,
            enemy_front_roles=enemy_front_roles,
            attack_index=1,
            node_counter_ref=node_counter_ref,
            on_progress_cb=on_progress_cb,
        )

    evaluate_tree_expectations(root_node)

    return root_node


def get_registered_operations_info() -> str:
    """獲取所有已註冊 Operation 操作的格式化信息（用於 CTkTextbox 展示）"""
    ops = EffectRegistry.get_registered_operations()
    if not ops:
        return "暫無已註冊的操作"
    return "📌 當前已註冊的操作列表：\n\n" + "\n".join([f" • {op}" for op in ops])