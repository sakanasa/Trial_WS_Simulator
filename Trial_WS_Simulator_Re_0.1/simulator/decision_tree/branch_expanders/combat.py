# -*- coding: utf-8 -*-
"""
戰鬥與傷害類 Operation 處理器 (Combat Operations Handlers)
包含：普通傷害、角色傷害、取消傷害、取消觸發 4 種戰鬥機制的展開邏輯
"""
from typing import List
from ..tree_model import TreeNode, sanitize_card_dict
from ..tree_helpers import calc_damage_branches
from .base import BaseEffectHandler, ExpansionContext, register_effect


def expand_role_damage_helper(
    parent_node: TreeNode, damage: int, op_name: str, ctx: ExpansionContext
) -> List[TreeNode]:
    """戰鬥傷害分支展開核心輔助函數"""
    snapshot = parent_node.state_snapshot
    branches = calc_damage_branches(snapshot, damage)
    child_nodes = []

    for desc, p, used_N, used_C, cancel_pos in branches:
        next_state = snapshot.clone()
        next_state.enemy_deck_normal -= used_N
        next_state.enemy_deck_climax -= used_C

        if cancel_pos > 0:
            next_state.enemy_control_normal += used_N
            next_state.enemy_control_climax += used_C
            node_title = f"🎲 [{p*100:.1f}%] 傷害在第 {cancel_pos} 張取消"
            details = f"判定: {damage} 點傷害在第 {cancel_pos} 張取消。敵控室肉+{used_N}, 潮+1。"
        else:
            next_state.apply_enemy_damage(damage)
            node_title = f"🎲 [{p*100:.1f}%] 全部命中 {damage} 點"
            details = f"判定: {damage} 點傷害全部命中！敵傷害區肉+{damage}。"

        child = TreeNode(
            name=node_title, 
            node_type="terminal" if next_state.game_over or next_state.my_failed else "chance",
            prob=p, state_snapshot=next_state, details=details, remaining_plan=parent_node.remaining_plan,
            node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
        )
        parent_node.add_child(child)
        child_nodes.append(child)

    return child_nodes


@register_effect("取消觸發")
class CancelTriggerHandler(BaseEffectHandler):
    """【取消觸發】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        if ctx.slot and parent_node.state_snapshot:
            cards = parent_node.state_snapshot.condition_front_cards.get(ctx.slot, [])
            if cards:
                cards[0].setdefault("equipped_cancel_triggers", []).append(sanitize_card_dict(op))
        return [parent_node]


@register_effect("取消傷害")
class CancelDamageHandler(BaseEffectHandler):
    """【取消傷害】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        base_dmg, bonus_type = op.get("cancel_damage_base", 1), op.get("cancel_damage_bonus", "0")
        bonus = ctx.cancelled_damage if bonus_type == "取消傷害" else (
            parent_node.state_snapshot.role_soul if bonus_type == "魂點" and parent_node.state_snapshot else 3
        )
        total_dmg = max(0, base_dmg + bonus)
        return expand_role_damage_helper(
            parent_node, total_dmg, f"取消傷害({base_dmg}+{bonus_type}({bonus})={total_dmg}點)", ctx
        )


@register_effect("普通傷害")
class NormalDamageHandler(BaseEffectHandler):
    """【普通傷害】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        dmg = op.get("damage", 1)
        return expand_role_damage_helper(parent_node, dmg, f"普通傷害({dmg}點)", ctx)


@register_effect("角色傷害")
class RoleDamageHandler(BaseEffectHandler):
    """【角色傷害】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        base_dmg = op.get("role_damage_base", 0)
        soul = parent_node.state_snapshot.role_soul if parent_node.state_snapshot else 3
        return expand_role_damage_helper(parent_node, base_dmg + soul, f"角色傷害({base_dmg + soul}點)", ctx)