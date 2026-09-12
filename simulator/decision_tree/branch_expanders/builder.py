# -*- coding: utf-8 -*-
"""
決策樹分支生成彙總類 (DecisionTreeBuilder)
修復版：面對敵方角色時，100% 獨立展開【正面攻擊】與【側面攻擊】分支，精準呈現戰鬥階段走向。
"""
import copy
import itertools
from typing import List, Dict, Any, Tuple, Optional, Callable

from core.models import clone_card_list, card_is_normal, card_is_climax, get_card_level, get_card_kind, get_card_trigger_soul, get_card_base_soul
from ..tree_model import TreeNode, GameStateSnapshot, sanitize_card_dict
from ..tree_helpers import (
    format_card_info, get_umi_draw_combinations, calc_damage_branches,
    group_slots_by_equivalence, get_position_permutations
)
from .base import ExpansionContext
from .dispatcher import resolve_operation
from .pruning import default_pruner_manager


class DecisionTreeBuilder:
    """決策樹分支生成器彙總類"""

    @classmethod
    def expand_role_damage(
        cls, parent_node: TreeNode, damage: int, op_name: str, 
        node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None
    ) -> List[TreeNode]:
        """戰鬥傷害分支展開（代理至 combat 輔助機制）"""
        from .combat import expand_role_damage_helper
        ctx = ExpansionContext(node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb)
        return expand_role_damage_helper(parent_node, damage, op_name, ctx)

    @classmethod
    def _resolve_single_effect(
        cls, parent_node: TreeNode, effect_op: dict, slot: str = None, 
        cancelled_damage: int = 0, node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None
    ) -> List[TreeNode]:
        """統一效果分發出口"""
        if not effect_op or not isinstance(effect_op, dict): 
            return [parent_node]

        ctx = ExpansionContext(
            slot=slot, 
            cancelled_damage=cancelled_damage, 
            node_counter_ref=node_counter_ref, 
            on_progress_cb=on_progress_cb
        )
        res = resolve_operation(parent_node, effect_op, ctx)
        return res if res is not None else [parent_node]

    @classmethod
    def expand_same_phase_effects_order(
        cls, 
        parent_node: TreeNode, 
        effects_list: list, 
        slot: str = None, 
        phase_name: str = "攻擊時",
        node_counter_ref: list = None, 
        on_progress_cb: Optional[Callable[[int], None]] = None
    ) -> List[TreeNode]:
        if not effects_list:
            return [parent_node]

        if len(effects_list) == 1:
            eff_op = effects_list[0]
            op_name = eff_op.get("type", "效果") if isinstance(eff_op, dict) else "效果"
            
            phase_info_node = TreeNode(
                name=f"【{phase_name}】: {op_name}",
                node_type="info", prob=1.0, state_snapshot=parent_node.state_snapshot.clone(),
                details=f"觸發【{phase_name}】階段效果: {op_name}。",
                node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            parent_node.add_child(phase_info_node)
            return cls._resolve_single_effect(phase_info_node, eff_op, slot=slot, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb) or [phase_info_node]

        order_dec_node = TreeNode(
            name=f"🔀 [決策點] 選擇【{phase_name}】{len(effects_list)}個效果的發動順序",
            node_type="decision", prob=1.0, state_snapshot=parent_node.state_snapshot,
            details=f"正統WS規則：【{phase_name}】多個效果同時誘發，玩家可自由決策發動的先後順序。",
            node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
        )
        parent_node.add_child(order_dec_node)

        final_leaves = []
        permutations = list(itertools.permutations(range(len(effects_list))))

        for perm_idx, perm in enumerate(permutations):
            ordered_names = [effects_list[idx].get("type", "效果") if isinstance(effects_list[idx], dict) else "效果" for idx in perm]
            order_choice_node = TreeNode(
                name=f"🎯 順序 {perm_idx+1}: " + " ➔ ".join(ordered_names), node_type="choice", prob=1.0,
                state_snapshot=parent_node.state_snapshot.clone(),
                details=f"決策選擇【{phase_name}】效果發動順序為: {' ➔ '.join(ordered_names)}。",
                node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            order_dec_node.add_child(order_choice_node)

            current_level_nodes = [order_choice_node]
            for idx in perm:
                eff_op = effects_list[idx]
                next_level_nodes = []
                for node_item in current_level_nodes:
                    if node_item.state_snapshot.game_over or node_item.state_snapshot.my_failed:
                        next_level_nodes.append(node_item)
                        continue
                    res_nodes = cls._resolve_single_effect(node_item, eff_op, slot=slot, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb) or []
                    next_level_nodes.extend(res_nodes)
                current_level_nodes = next_level_nodes

            final_leaves.extend(current_level_nodes)

        return final_leaves

    @classmethod
    def expand_pass_fire_decision(
        cls, cancel_node: TreeNode, current_slot: str, remaining_slots: List[str], nested_op: dict,
        node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None
    ) -> List[TreeNode]:
        snapshot = cancel_node.state_snapshot
        candidates = [s for s in remaining_slots if s != current_slot and snapshot.condition_front_cards.get(s)]

        if not candidates:
            info_node = TreeNode(
                name="【傳火】: 無未行動目標，傳火終止",
                node_type="info", prob=1.0, state_snapshot=snapshot.clone(),
                details="因無其餘未行動角色，停止能力傳遞。",
                node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            cancel_node.add_child(info_node)
            return [info_node]

        groups: Dict[tuple, List[str]] = {}
        for slot in candidates:
            cards = snapshot.condition_front_cards.get(slot, [])
            if cards:
                c = cards[0]
                sig = (c.get("name", "角色"), int(c.get("level", 0) or 0), int(c.get("power", 500) or 500), int(c.get("soul", 1) or 1), str(c.get("effects", {})))
                groups.setdefault(sig, []).append(slot)

        dec_node = TreeNode(
            name=f"🔀 [決策點] 選擇【傳火】目標角色 (候選 {len(candidates)} 個)",
            node_type="decision", prob=1.0, state_snapshot=snapshot,
            details="傳火效果生效！請選擇將取消觸發能力傳遞給前列未行動的哪個角色。",
            remaining_plan=cancel_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
        )
        cancel_node.add_child(dec_node)

        choice_leaves = []
        for sig, slot_list in groups.items():
            rep_slot = slot_list[0]
            rep_card = snapshot.condition_front_cards[rep_slot][0]
            card_name = rep_card.get("name", "角色")
            display_text = f"🎯 傳火給 [{card_name}({rep_slot})]" if len(slot_list) == 1 else f"🎯 傳火給 [{card_name}({rep_slot})](與{'、'.join([s for s in slot_list if s != rep_slot])}等效)"

            next_state = snapshot.clone()
            target_card = next_state.condition_front_cards[rep_slot][0]
            target_card.setdefault("passed_cancel_triggers", []).append(sanitize_card_dict(nested_op))

            choice_node = TreeNode(
                name=display_text, node_type="choice", prob=1.0, state_snapshot=next_state,
                details=f"決策選擇將“傳火”能力傳遞給 [{card_name}({rep_slot})]。",
                remaining_plan=cancel_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            dec_node.add_child(choice_node)
            choice_leaves.append(choice_node)

        return choice_leaves

    @classmethod
    def get_all_cancel_triggers(cls, card: dict) -> List[Tuple[dict, bool]]:
        results = []
        if not card or not isinstance(card, dict): return results
        equipped = card.get("equipped_cancel_triggers", [])
        for op in equipped:
            if isinstance(op, dict):
                results.append((op, op.get("sub_mode", "單次觸發") == "傳火" or op.get("pass_on_trigger", False)))
        passed = card.get("passed_cancel_triggers", [])
        for op in passed:
            if isinstance(op, dict): results.append((op, True))
        return results

    @classmethod
    def expand_position_swap_decision(cls, parent_node: TreeNode, node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None) -> List[TreeNode]:
        snapshot = parent_node.state_snapshot
        front_cards = snapshot.condition_front_cards
        perms = get_position_permutations(front_cards, snapshot.enemy_front_roles)
        if len(perms) <= 1: return [parent_node]

        dec_node = TreeNode(
            name="🔀 [決策點] 調整【前列角色初始位置】", node_type="decision", prob=1.0, state_snapshot=snapshot,
            details="決策節點：在攻擊開始前可以自由調整我方前列角色的槽位排列。",
            remaining_plan=parent_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
        )
        parent_node.add_child(dec_node)

        choice_nodes = []
        for idx, (new_front, is_orig) in enumerate(perms):
            next_state = snapshot.clone()
            next_state.condition_front_cards = new_front
            desc_parts = [f"{s}[{new_front.get(s, [{}])[0].get('name', '角色') if new_front.get(s) else '空'}]" for s in ["前列1", "前列2", "前列3"]]

            choice_node = TreeNode(
                name=f"🎯 選擇排列 {idx+1}: {', '.join(desc_parts)}{' (保持原位)' if is_orig else ''}",
                node_type="choice", prob=1.0, state_snapshot=next_state, details=f"決策選擇初始位置排列：{', '.join(desc_parts)}。",
                remaining_plan=parent_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            dec_node.add_child(choice_node)
            choice_nodes.append(choice_node)

        return choice_nodes

    @classmethod
    def expand_single_card_pipeline(
        cls, choice_node: TreeNode, card_name: str, slot: str, effects: dict, soul_val: int,
        remaining_slots: List[str] = None, node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None
    ) -> List[TreeNode]:
        current_leaves = [choice_node]

        # 1. 攻擊前效果 (pre_attack)
        pre_ops = effects.get("pre_attack", [])
        if pre_ops:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue
                res_nodes = cls.expand_same_phase_effects_order(leaf, pre_ops, slot=slot, phase_name="攻擊前", node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb)
                next_leaves.extend(res_nodes)
            current_leaves = next_leaves

        # 2. 攻擊時效果 (on_attack)
        on_ops = effects.get("on_attack", [])
        if on_ops:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue
                res_nodes = cls.expand_same_phase_effects_order(leaf, on_ops, slot=slot, phase_name="攻擊時", node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb)
                next_leaves.extend(res_nodes)
            current_leaves = next_leaves

        # 3. 判定步驟 (trigger_step)
        raw_trigger_cfg = effects.get("trigger_step") if isinstance(effects, dict) else None
        should_do_trigger = True
        if raw_trigger_cfg is not None and isinstance(raw_trigger_cfg, list) and len(raw_trigger_cfg) == 0:
            should_do_trigger = False

        if should_do_trigger:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue
                children = cls.expand_condition_trigger_check(leaf, node_counter_ref, on_progress_cb)
                next_leaves.extend(children)
            current_leaves = next_leaves

        # 4. 傷害處理步驟 (deal_damage)
        raw_deal_cfg = effects.get("deal_damage") if isinstance(effects, dict) else None
        if raw_deal_cfg is None:
            deal_ops = [{"type": "角色傷害", "role_damage_base": 0, "role_bonus_type": "魂點"}]
        else:
            deal_ops = raw_deal_cfg

        if deal_ops:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue

                damage_phase_node = TreeNode(
                    name="【傷害步驟】: 結算角色傷害",
                    node_type="info", prob=1.0, state_snapshot=leaf.state_snapshot.clone(),
                    details="進入傷害步驟，結算角色的攻擊傷害。",
                    node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                )
                leaf.add_child(damage_phase_node)

                current_soul = damage_phase_node.state_snapshot.role_soul if damage_phase_node.state_snapshot else soul_val

                res_nodes = []
                for eff_op in deal_ops:
                    op_res = cls._resolve_single_effect(damage_phase_node, eff_op, slot=slot, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb) or []
                    res_nodes.extend(op_res)

                for child in res_nodes:
                    if child.state_snapshot.game_over or child.state_snapshot.my_failed:
                        next_leaves.append(child)
                        continue

                    if "取消" in child.name:
                        active_card = child.state_snapshot.condition_front_cards.get(slot, [{}])[0]
                        cancel_triggers = cls.get_all_cancel_triggers(active_card)

                        if cancel_triggers:
                            cancel_leaves = [child]
                            for raw_op, is_pass in cancel_triggers:
                                nested_op = raw_op.get("nested_op") if raw_op.get("type") == "取消觸發" else raw_op
                                level_next = []

                                for c_leaf in cancel_leaves:
                                    if c_leaf.state_snapshot.game_over or c_leaf.state_snapshot.my_failed:
                                        level_next.append(c_leaf)
                                        continue

                                    dmg_leaves = cls._resolve_single_effect(c_leaf, nested_op, slot=slot, cancelled_damage=current_soul, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb)

                                    if is_pass:
                                        for d_leaf in dmg_leaves:
                                            if d_leaf.state_snapshot.game_over or d_leaf.state_snapshot.my_failed:
                                                level_next.append(d_leaf)
                                                continue
                                            pass_res = cls.expand_pass_fire_decision(
                                                cancel_node=d_leaf, current_slot=slot, remaining_slots=remaining_slots or [],
                                                nested_op=raw_op, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb
                                            )
                                            level_next.extend(pass_res)
                                    else:
                                        level_next.extend(dmg_leaves)

                                cancel_leaves = level_next
                            next_leaves.extend(cancel_leaves)
                        else:
                            next_leaves.append(child)
                    else:
                        next_leaves.append(child)

            current_leaves = next_leaves

        # 5. 戰鬥階段 (on_reverse) —— 僅在決策樹中實際選定為"正面"攻擊且敵方存在角色時才展開！
        next_leaves = []
        for leaf in current_leaves:
            if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                next_leaves.append(leaf)
                continue

            snap = leaf.state_snapshot
            chosen_mode = getattr(snap, "attack_mode", "")
            
            enemy_role = snap.enemy_front_roles.get(slot, {})
            lvl_item = enemy_role.get("level", "0")
            enemy_level_str = str(lvl_item.get()) if hasattr(lvl_item, "get") else str(lvl_item or "空")

            reverse_ops = effects.get("on_reverse", []) if isinstance(effects, dict) else []

            if chosen_mode == "正面" and enemy_level_str != "空":
                my_cards = snap.condition_front_cards.get(slot, [])
                my_card = my_cards[0] if my_cards else {}
                
                try: my_pwr = int(my_card.get("power", 500) or 500)
                except (ValueError, TypeError): my_pwr = 500

                try:
                    e_pwr_item = enemy_role.get("power", 500)
                    e_pwr = int(e_pwr_item.get()) if hasattr(e_pwr_item, "get") else int(e_pwr_item or 500)
                except (ValueError, TypeError): e_pwr = 500

                if my_pwr >= e_pwr:
                    next_state = snap.clone()
                    if slot in next_state.enemy_front_roles:
                        next_state.enemy_front_roles[slot]["is_reversed"] = True
                    
                    if reverse_ops:
                        battle_node = TreeNode(
                            name=f"【戰鬥階段】: 成功擊倒對手 (力量 {my_pwr} vs {e_pwr})",
                            node_type="info", prob=1.0, state_snapshot=next_state,
                            details=f"正面戰鬥力量對比：我方 {my_pwr} >= 敵方 {e_pwr}，成功擊倒對手！",
                            node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                        )
                        leaf.add_child(battle_node)

                        res_nodes = cls.expand_same_phase_effects_order(
                            battle_node, reverse_ops, slot=slot, phase_name="擊倒時",
                            node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb
                        )
                        next_leaves.extend(res_nodes)
                    else:
                        battle_node = TreeNode(
                            name=f"【戰鬥階段】: 成功擊倒對手 (力量 {my_pwr} vs {e_pwr})",
                            node_type="info", prob=1.0, state_snapshot=next_state,
                            details=f"正面戰鬥力量對比：我方 {my_pwr} >= 敵方 {e_pwr}，成功擊倒對手。",
                            node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                        )
                        leaf.add_child(battle_node)
                        next_leaves.append(battle_node)
                else:
                    battle_node = TreeNode(
                        name=f"【戰鬥階段】: 未能擊倒對手 (力量 {my_pwr} vs {e_pwr})",
                        node_type="info", prob=1.0, state_snapshot=snap.clone(),
                        details=f"正面戰鬥力量對比：我方 {my_pwr} < 敵方 {e_pwr}，力量不足，未能擊倒對手。",
                        node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                    )
                    leaf.add_child(battle_node)
                    next_leaves.append(battle_node)
            else:
                next_leaves.append(leaf)

        current_leaves = next_leaves

        # 6. 攻擊後效果 (post_attack)
        post_ops = effects.get("post_attack", [])
        if post_ops:
            next_leaves = []
            for leaf in current_leaves:
                if leaf.state_snapshot.game_over or leaf.state_snapshot.my_failed:
                    next_leaves.append(leaf)
                    continue
                res_nodes = cls.expand_same_phase_effects_order(leaf, post_ops, slot=slot, phase_name="攻擊後", node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb)
                next_leaves.extend(res_nodes)
            current_leaves = next_leaves

        # 應用全局剪枝
        return default_pruner_manager.prune_leaves(current_leaves)

    @classmethod
    def expand_attack_sequence(cls, parent_node: TreeNode, remaining_slots: List[str], enemy_front_roles: dict, attack_index: int = 1, node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None):
        snapshot = parent_node.state_snapshot
        if snapshot.game_over or snapshot.my_failed or not remaining_slots: return

        available_slots = [s for s in remaining_slots if snapshot.condition_front_cards.get(s)]
        if not available_slots: return

        eq_groups = group_slots_by_equivalence(available_slots, snapshot.condition_front_cards, enemy_front_roles)

        all_choices = []
        for rep_slot, slot_list, display_text in eq_groups:
            card = snapshot.condition_front_cards[rep_slot][0]
            card_name = card.get("name", "自定義角色")
            base_soul = int(card.get("soul", 1) or 1)
            effects = card.get("effects", {})

            raw_attack_type_cfg = effects.get("attack_type") if isinstance(effects, dict) else None

            modes_choices = []
            if isinstance(raw_attack_type_cfg, list) and len(raw_attack_type_cfg) == 0:
                modes_choices.append((f"🎯 行動: [{card_name}({display_text})]", "無", base_soul))
            else:
                allowed_attack_types = None
                if raw_attack_type_cfg and isinstance(raw_attack_type_cfg, list):
                    allowed_attack_types = set()
                    for item in raw_attack_type_cfg:
                        if isinstance(item, dict):
                            at = item.get("attack_type", "")
                            if at: allowed_attack_types.add(at)
                        elif isinstance(item, str):
                            allowed_attack_types.add(item)

                if allowed_attack_types is not None and ("無" in allowed_attack_types or "不能攻擊" in allowed_attack_types):
                    continue

                enemy_role = enemy_front_roles.get(rep_slot, {})
                lvl_item = enemy_role.get("level", "0")
                enemy_level_str = str(lvl_item.get()) if hasattr(lvl_item, "get") else str(lvl_item or "空")

                if enemy_level_str == "空":
                    new_soul = base_soul + 1
                    if allowed_attack_types is None or ("直擊" in allowed_attack_types or "正面" in allowed_attack_types or "任意" in allowed_attack_types):
                        modes_choices.append((f"🎯 [{card_name}({display_text})] 直擊 (空位魂+1 ➔ 魂點 {new_soul})", "直擊", new_soul))
                else:
                    try: e_level = int(enemy_level_str)
                    except ValueError: e_level = 0

                    # 🌟 核心修正：無論是 Lv.0 還是高 Level，只要面前有敵方角色，均獨立展開【正面攻擊】與【側面攻擊】！
                    if allowed_attack_types is None or ("不能正面攻擊" not in allowed_attack_types and "只能側面攻擊" not in allowed_attack_types):
                        modes_choices.append((f"🎯 [{card_name}({display_text})] 正面攻擊 (魂點 {base_soul})", "正面", base_soul))
                    
                    side_soul = max(0, base_soul - e_level)
                    if allowed_attack_types is None or ("不能側面攻擊" not in allowed_attack_types and "只能正面攻擊" not in allowed_attack_types):
                        modes_choices.append((f"🎯 [{card_name}({display_text})] 側面攻擊 (減Lv.{e_level} ➔ 魂點 {side_soul})", "側面", side_soul))

            if modes_choices:
                all_choices.append((rep_slot, slot_list, display_text, card_name, effects, modes_choices))

        if not all_choices:
            return

        dec_title = f"🔀 [決策點] 選擇【第 {attack_index} 個發動行動】的角色"
        dec_node = TreeNode(
            name=dec_title, node_type="decision", prob=1.0, state_snapshot=snapshot,
            details=f"決策節點：選擇第 {attack_index} 個發動的角色。",
            remaining_plan=parent_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
        )
        parent_node.add_child(dec_node)

        for rep_slot, slot_list, display_text, card_name, effects, modes_choices in all_choices:
            for c_title, mode, final_soul in modes_choices:
                choice_state = snapshot.clone()
                choice_state.role_soul = final_soul
                choice_state.attack_mode = mode

                choice_node = TreeNode(
                    name=c_title, node_type="choice", prob=1.0, state_snapshot=choice_state,
                    details=f"決策選擇 [{card_name}] 從 [{display_text}] 發動{mode}，魂點為 {final_soul}。",
                    remaining_plan=parent_node.remaining_plan, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                )
                dec_node.add_child(choice_node)

                leaf_nodes = cls.expand_single_card_pipeline(
                    choice_node=choice_node, card_name=card_name, slot=rep_slot, effects=effects,
                    soul_val=final_soul, remaining_slots=available_slots, node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb
                )

                next_slots = [s for s in available_slots if s != rep_slot]
                for leaf in leaf_nodes:
                    if not leaf.state_snapshot.game_over and not leaf.state_snapshot.my_failed and next_slots:
                        cls.expand_attack_sequence(leaf, next_slots, enemy_front_roles, attack_index + 1, node_counter_ref, on_progress_cb)

    @classmethod
    def expand_condition_trigger_check(cls, parent_node: TreeNode, node_counter_ref: list = None, on_progress_cb: Optional[Callable[[int], None]] = None) -> List[TreeNode]:
        snapshot = parent_node.state_snapshot

        if snapshot.deterministic_top:
            next_state = snapshot.clone()
            top_card, _ = next_state.pop_my_deck_card()
            trig_soul = get_card_trigger_soul(top_card)
            next_state.role_soul += trig_soul
            next_state.my_stock.append(top_card)

            card_info = format_card_info(top_card)
            child = TreeNode(
                name=f"【判定階段】: [已知置頂] 翻出 {card_info} (觸發魂+{trig_soul} ➔ 魂點 {next_state.role_soul})", node_type="info", prob=1.0, state_snapshot=next_state,
                details=f"因前置操作已確定置頂牌，100% 確定翻出 {card_info}，觸發魂+{trig_soul} 入庫。", remaining_plan=parent_node.remaining_plan,
                node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            parent_node.add_child(child)
            return [child]

        if not snapshot.my_deck:
            next_state = snapshot.clone()
            next_state.refresh_my_deck_if_empty()
            if not next_state.my_deck:
                next_state.my_failed = True
                child = TreeNode(
                    name="【判定階段】: 我方牌組與控室均為0，判定敗北", node_type="terminal", prob=1.0, state_snapshot=next_state,
                    details="我方無法翻頂入庫，判定敗北。", remaining_plan=[], node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
                )
                parent_node.add_child(child)
                return [child]
            snapshot = next_state

        total_cards = len(snapshot.my_deck)
        groups: Dict[tuple, List[dict]] = {}
        for card in snapshot.my_deck:
            sig = ("名場面" if card == "名場面" else "角色", get_card_level(card), get_card_trigger_soul(card), card.get("name", "卡牌") if isinstance(card, dict) else str(card))
            groups.setdefault(sig, []).append(card)

        chance_nodes = []
        for sig, card_list in groups.items():
            count = len(card_list)
            prob = count / total_cards
            sample_card = card_list[0]
            trig_soul = get_card_trigger_soul(sample_card)

            next_state = snapshot.clone()
            for idx, c in enumerate(next_state.my_deck):
                if c is sample_card or (isinstance(c, dict) and c.get("name") == sample_card.get("name")):
                    next_state.my_deck.pop(idx)
                    break

            next_state.role_soul += trig_soul
            next_state.my_stock.append(sample_card)
            card_info = format_card_info(sample_card)

            child = TreeNode(
                name=f"🎲 [{prob*100:.1f}%] 【判定階段】: 翻出 {card_info} (觸發魂+{trig_soul} ➔ 魂點 {next_state.role_soul})", node_type="chance", prob=prob, state_snapshot=next_state,
                details=f"牌組剩餘 {total_cards} 張中共有 {count} 張 {card_info}，翻出概率為 {prob*100:.2f}%。", remaining_plan=parent_node.remaining_plan,
                node_counter_ref=node_counter_ref, on_progress_cb=on_progress_cb,
            )
            parent_node.add_child(child)
            chance_nodes.append(child)

        return chance_nodes