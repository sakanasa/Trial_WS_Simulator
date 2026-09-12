# -*- coding: utf-8 -*-
"""
牌組及翻牌類 Operation 處理器 (Deck Operations Handlers)
精簡規範版：【階段名】: 效果名
"""
import itertools
from typing import List, Dict
from core.models import (
    clone_card_list, 
    card_is_climax, 
    card_is_normal,
    get_card_kind,
    get_card_level, 
    get_card_trigger_soul, 
    get_card_base_soul
)
from ..tree_model import TreeNode, sanitize_card_dict
from ..tree_helpers import format_card_info, get_umi_draw_combinations
from .base import BaseEffectHandler, ExpansionContext, register_effect


@register_effect("推頂燒")
class TopPushBurnHandler(BaseEffectHandler):
    """【推頂燒】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        from .builder import DecisionTreeBuilder

        snapshot = parent_node.state_snapshot
        push_count = max(1, op.get("push_count", 1))
        base_dmg = op.get("base_damage", op.get("burn_damage", 1))
        dmg_bonus_type = op.get("damage_bonus", op.get("burn_bonus_type", "0"))
        base_times = op.get("base_times", 1)
        times_bonus_type = op.get("times_bonus", "0")

        current_deck = clone_card_list(snapshot.my_deck)

        if not snapshot.deterministic_top and not current_deck and snapshot.my_control:
            next_state = snapshot.clone()
            next_state.refresh_my_deck_if_empty()
            current_deck = clone_card_list(next_state.my_deck)
            info_node = TreeNode(
                name="【推頂燒】: 牌組空，觸發刷新受1點傷害",
                node_type="info", prob=1.0, state_snapshot=next_state,
                details="推頂燒前牌組為空，控制室重洗入牌組，受到1點刷新傷害。",
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            parent_node.add_child(info_node)
            parent_node = info_node
            snapshot = next_state

        available_deck = clone_card_list(snapshot.deterministic_top) + current_deck
        if not available_deck:
            return [parent_node]

        K = min(push_count, len(available_deck))

        def calc_bonus(bonus_type, cards):
            if bonus_type == "0": return 0
            tot = 0
            for card in cards:
                if bonus_type == "觸發魂點": tot += get_card_trigger_soul(card)
                elif bonus_type == "等級": tot += get_card_level(card)
                elif bonus_type == "潮數": tot += 1 if card_is_climax(card) else 0
                elif bonus_type == "基礎魂點": tot += get_card_base_soul(card)
            return tot

        push_branches = []

        if snapshot.is_top_deterministic(K):
            state_det = snapshot.clone()
            pushed_cards = [state_det.pop_my_deck_card()[0] for _ in range(K)]
            state_det.my_control.extend(pushed_cards)
            push_branches.append((pushed_cards, 1.0, state_det, "info"))
        else:
            draw_combos = get_umi_draw_combinations(available_deck, K)
            for drawn_cards, combo_prob in draw_combos:
                state_combo = snapshot.clone()
                rem_deck = clone_card_list(available_deck)
                for c_drawn in drawn_cards:
                    for idx_b, c_bag in enumerate(rem_deck):
                        if format_card_info(c_bag) == format_card_info(c_drawn):
                            rem_deck.pop(idx_b)
                            break
                
                state_combo.my_deck = rem_deck
                state_combo.deterministic_top = []
                state_combo.my_control.extend(drawn_cards)
                
                push_branches.append((drawn_cards, combo_prob, state_combo, "chance"))

        final_leaves = []

        for pushed_cards, prob, state_push, node_type in push_branches:
            push_info = " | ".join([format_card_info(c) for c in pushed_cards])
            add_dmg = calc_bonus(dmg_bonus_type, pushed_cards)
            add_times = calc_bonus(times_bonus_type, pushed_cards)
            total_burn_dmg = max(0, base_dmg + add_dmg)
            total_burn_times = max(0, base_times + add_times)

            if node_type == "chance":
                branch_node = TreeNode(
                    name=f"🎲 [{prob*100:.1f}%] 【推頂燒】: 送控 {push_info} ➔ 燒 {total_burn_dmg}點 {total_burn_times}次",
                    node_type="chance", prob=prob, state_snapshot=state_push,
                    details=f"推頂燒: 翻開推入控室 {push_info}，計算加成後傷害為 {total_burn_dmg} 點 {total_burn_times} 次。",
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                parent_node.add_child(branch_node)
                curr_parent = branch_node
            else:
                info_node = TreeNode(
                    name=f"【推頂燒】: [已知置頂] 送控 {push_info} ➔ 燒 {total_burn_dmg}點 {total_burn_times}次",
                    node_type="info", prob=1.0, state_snapshot=state_push,
                    details=f"已知置頂推入控室 {push_info}，計算加成後傷害為 {total_burn_dmg} 點 {total_burn_times} 次。",
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                parent_node.add_child(info_node)
                curr_parent = info_node

            if state_push.game_over or state_push.my_failed:
                final_leaves.append(curr_parent)
                continue

            burn_leaves = [curr_parent]
            for t in range(total_burn_times):
                next_burn_leaves = []
                for b_leaf in burn_leaves:
                    if b_leaf.state_snapshot.game_over or b_leaf.state_snapshot.my_failed:
                        next_burn_leaves.append(b_leaf)
                        continue
                    dmg_nodes = DecisionTreeBuilder.expand_role_damage(
                        b_leaf, total_burn_dmg, f"推頂燒({total_burn_dmg}點,第{t+1}/{total_burn_times}次)",
                        ctx.node_counter_ref, ctx.on_progress_cb
                    )
                    next_burn_leaves.extend(dmg_nodes)
                burn_leaves = next_burn_leaves

            final_leaves.extend(burn_leaves)

        return final_leaves


@register_effect("翻頂燒")
class TopCheckBurnHandler(BaseEffectHandler):
    """【翻頂燒】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        from .builder import DecisionTreeBuilder

        snapshot = parent_node.state_snapshot
        filter_kind, filter_level = op.get("filter_kind", "任意"), op.get("filter_level", "等級")
        base_dmg, bonus_type, times = op.get("burn_damage", 1), op.get("burn_bonus_type", "0"), max(1, op.get("burn_times", 1))

        current_deck = clone_card_list(snapshot.my_deck)
        if not snapshot.deterministic_top and not current_deck and snapshot.my_control:
            next_state = snapshot.clone()
            next_state.refresh_my_deck_if_empty()
            current_deck = clone_card_list(next_state.my_deck)
            info_node = TreeNode(
                name="【翻頂燒】: 牌組空，觸發刷新受1點傷害", node_type="info", prob=1.0, state_snapshot=next_state,
                details="翻頂燒前牌組為空，控制室重洗入牌組，受到1點刷新傷害。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            parent_node.add_child(info_node)
            parent_node, snapshot = info_node, next_state

        available_deck = clone_card_list(snapshot.deterministic_top) + current_deck
        if not available_deck: 
            return [parent_node]

        top_branches = []
        if snapshot.deterministic_top:
            top_card = snapshot.deterministic_top[-1]
            top_branches.append((top_card, 1.0, snapshot.clone(), "info"))
        else:
            total_cards = len(available_deck)
            groups: Dict[tuple, List[dict]] = {}
            for card in available_deck:
                sig = ("名場面" if card == "名場面" else "角色", get_card_level(card), get_card_trigger_soul(card), card.get("name", "卡牌") if isinstance(card, dict) else str(card))
                groups.setdefault(sig, []).append(card)

            for sig, card_list in groups.items():
                p_top = len(card_list) / total_cards
                top_card = card_list[0]
                top_branches.append((top_card, p_top, snapshot.clone(), "chance"))

        final_leaves = []
        for top_card, p_top, state_top, node_type in top_branches:
            card_info = format_card_info(top_card)
            card_kind, card_lvl = get_card_kind(top_card), get_card_level(top_card)

            curr_parent = parent_node
            if node_type == "chance":
                chance_node = TreeNode(
                    name=f"🎲 [{p_top*100:.1f}%] 【翻頂燒】: 確認頂牌 {card_info}", node_type="chance", prob=p_top, state_snapshot=state_top,
                    details=f"翻頂燒確認牌組頂牌為 {card_info} (發生概率 {p_top*100:.1f}%)。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                parent_node.add_child(chance_node)
                curr_parent = chance_node

            match_kind = not (filter_kind != "任意" and ((filter_kind == "普通" and not card_is_normal(top_card)) or (filter_kind != "普通" and card_kind != filter_kind)))
            match_lvl = True
            if filter_level != "等級":
                try: match_lvl = (card_lvl == int(filter_level))
                except (ValueError, TypeError): pass

            if match_kind and match_lvl:
                bonus = card_lvl if bonus_type == "等級" else (get_card_base_soul(top_card) if bonus_type == "基礎魂點" else 0)
                total_burn = max(0, base_dmg + bonus)

                burn_leaves = [curr_parent]
                for t in range(times):
                    next_burn_leaves = []
                    for b_leaf in burn_leaves:
                        if b_leaf.state_snapshot.game_over or b_leaf.state_snapshot.my_failed:
                            next_burn_leaves.append(b_leaf)
                            continue
                        dmg_nodes = DecisionTreeBuilder.expand_role_damage(
                            b_leaf, total_burn, f"翻頂燒({base_dmg}+{bonus_type}={total_burn}點,第{t+1}/{times}次)",
                            ctx.node_counter_ref, ctx.on_progress_cb
                        )
                        next_burn_leaves.extend(dmg_nodes)
                    burn_leaves = next_burn_leaves

                final_leaves.extend(burn_leaves)
            else:
                info_miss = TreeNode(
                    name=f"【翻頂燒】: 頂牌 {card_info} 不匹配條件，不觸發燒傷", node_type="info", prob=1.0, state_snapshot=state_top.clone(),
                    details=f"翻頂燒: 頂牌 {card_info} 不匹配條件，燒傷不觸發。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                curr_parent.add_child(info_miss)
                final_leaves.append(info_miss)

        return final_leaves


@register_effect("選判")
class LookSelectHandler(BaseEffectHandler):
    """【選判】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        snapshot = parent_node.state_snapshot
        current_deck = clone_card_list(snapshot.my_deck)

        if not snapshot.deterministic_top and not current_deck and snapshot.my_control:
            next_state = snapshot.clone()
            next_state.refresh_my_deck_if_empty()
            current_deck = clone_card_list(next_state.my_deck)
            info_node = TreeNode(
                name="【選判】: 牌組空，觸發刷新受1點傷害", node_type="info", prob=1.0, state_snapshot=next_state,
                details="選判前牌組為空，控制室重洗入牌組，受到1點刷新傷害。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            parent_node.add_child(info_node)
            parent_node, snapshot = info_node, next_state

        available_deck = clone_card_list(snapshot.deterministic_top) + current_deck
        if not available_deck: 
            return [parent_node]

        c1_branches = []
        if snapshot.deterministic_top:
            state_c1 = snapshot.clone()
            c1_card, _ = state_c1.pop_my_deck_card()
            c1_branches.append((c1_card, 1.0, state_c1, "info"))
        else:
            total_cards = len(snapshot.my_deck)
            groups: Dict[tuple, List[int]] = {}
            for idx, card in enumerate(snapshot.my_deck):
                sig = ("名場面" if card == "名場面" else "角色", get_card_level(card), get_card_trigger_soul(card), card.get("name", "卡牌") if isinstance(card, dict) else str(card))
                groups.setdefault(sig, []).append(idx)

            for sig, idx_list in groups.items():
                chosen_idx = idx_list[0]
                c1_card = snapshot.my_deck[chosen_idx]
                state_c1 = snapshot.clone()
                state_c1.my_deck.pop(chosen_idx)
                c1_branches.append((c1_card, len(idx_list) / total_cards, state_c1, "chance"))

        final_leaves = []
        for c1_card, p_c1, state_c1, c1_node_type in c1_branches:
            c1_info = format_card_info(c1_card)
            c1_parent = parent_node
            if c1_node_type == "chance":
                c1_node = TreeNode(
                    name=f"🎲 [{p_c1*100:.1f}%] 【選判】: 看第 1 張 {c1_info}", node_type="chance", prob=p_c1, state_snapshot=state_c1.clone(),
                    details=f"選判翻開第 1 張牌為 {c1_info} (發生概率 {p_c1*100:.1f}%)。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                parent_node.add_child(c1_node)
                c1_parent = c1_node

            dec1_node = TreeNode(
                name=f"🔀 [決策點] 選擇【選判】: 是否看第 2 張牌？(第1張: {c1_info})", node_type="decision", prob=1.0, state_snapshot=state_c1.clone(),
                details=f"當前已看第 1 張牌 {c1_info}。決策：選擇 [留在原位] 還是 [再看 1 張]？", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            c1_parent.add_child(dec1_node)

            state_keep = state_c1.clone()
            state_keep.push_to_deterministic_top([c1_card])
            choice_keep = TreeNode(
                name=f"🎯 [留在原位] {c1_info} 保持在牌組頂", node_type="choice", prob=1.0, state_snapshot=state_keep,
                details=f"決策選擇 [留在原位]，牌組頂保持為 {c1_info}。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            dec1_node.add_child(choice_keep)
            final_leaves.append(choice_keep)

            if not (clone_card_list(state_c1.deterministic_top) + clone_card_list(state_c1.my_deck)): 
                continue

            choice_look2 = TreeNode(
                name="🎯 [再看 1 張]", node_type="choice", prob=1.0, state_snapshot=state_c1.clone(),
                details="決策選擇 [再看 1 張]。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            dec1_node.add_child(choice_look2)

            c2_branches = []
            if state_c1.deterministic_top:
                state_c2 = state_c1.clone()
                c2_card, _ = state_c2.pop_my_deck_card()
                c2_branches.append((c2_card, 1.0, state_c2, "info"))
            else:
                total_cards2 = len(state_c1.my_deck)
                groups2: Dict[tuple, List[int]] = {}
                for idx2, card in enumerate(state_c1.my_deck):
                    sig = ("名場面" if card == "名場面" else "角色", get_card_level(card), get_card_trigger_soul(card), card.get("name", "卡牌") if isinstance(card, dict) else str(card))
                    groups2.setdefault(sig, []).append(idx2)

                for sig, idx_list2 in groups2.items():
                    chosen_idx2 = idx_list2[0]
                    c2_card = state_c1.my_deck[chosen_idx2]
                    state_c2 = state_c1.clone()
                    state_c2.my_deck.pop(chosen_idx2)
                    c2_branches.append((c2_card, len(idx_list2) / total_cards2, state_c2, "chance"))

            for c2_card, p_c2, state_c2, c2_node_type in c2_branches:
                c2_info = format_card_info(c2_card)
                c2_parent = choice_look2
                if c2_node_type == "chance":
                    c2_node = TreeNode(
                        name=f"🎲 [{p_c2*100:.1f}%] 【選判】: 看第 2 張 {c2_info}", node_type="chance", prob=p_c2, state_snapshot=state_c2.clone(),
                        details=f"選判翻開第 2 張牌為 {c2_info} (發生概率 {p_c2*100:.1f}%)。", 
                        node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                    )
                    choice_look2.add_child(c2_node)
                    c2_parent = c2_node

                dec2_node = TreeNode(
                    name=f"🔀 [決策點] 選擇【選判】: 1張置頂，1張送控 (1:{c1_info} vs 2:{c2_info})", node_type="decision", prob=1.0, state_snapshot=state_c2.clone(),
                    details=f"已看到兩張牌 (1:{c1_info}, 2:{c2_info})。請選擇哪一張置頂，未選擇的另一張將送入控制室。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                c2_parent.add_child(dec2_node)

                state_c1_top = state_c2.clone()
                state_c1_top.push_to_deterministic_top([c1_card])
                state_c1_top.my_control.append(c2_card)
                choice_c1_top = TreeNode(
                    name=f"🎯 [置頂第 1 張] {c1_info} (第2張{c2_info}送入控制室)", node_type="choice", prob=1.0, state_snapshot=state_c1_top,
                    details=f"決策選擇: 將第 1 張牌 {c1_info} 置頂，未選的第 2 張牌 {c2_info} 送入控制室。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                dec2_node.add_child(choice_c1_top)
                final_leaves.append(choice_c1_top)

                state_c2_top = state_c2.clone()
                state_c2_top.push_to_deterministic_top([c2_card])
                state_c2_top.my_control.append(c1_card)
                choice_c2_top = TreeNode(
                    name=f"🎯 [置頂第 2 張] {c2_info} (第1張{c1_info}送入控制室)", node_type="choice", prob=1.0, state_snapshot=state_c2_top,
                    details=f"決策選擇: 將第 2 張牌 {c2_info} 置頂，未選的第 1 張牌 {c1_info} 送入控制室。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                dec2_node.add_child(choice_c2_top)
                final_leaves.append(choice_c2_top)

        return final_leaves


@register_effect("羽未(決策用)")
class UmiDecisionHandler(BaseEffectHandler):
    """【羽未】解耦處理器"""

    def expand(self, parent_node: TreeNode, op: dict, ctx: ExpansionContext) -> List[TreeNode]:
        snapshot = parent_node.state_snapshot
        current_deck = clone_card_list(snapshot.my_deck)

        if not snapshot.deterministic_top and not current_deck and snapshot.my_control:
            next_state = snapshot.clone()
            next_state.refresh_my_deck_if_empty()
            current_deck = clone_card_list(next_state.my_deck)
            info_node = TreeNode(
                name="【羽未】: 牌組空，觸發刷新受1點傷害", node_type="info", prob=1.0, state_snapshot=next_state,
                details="看頂前牌組為空，控制室重洗入牌組，受到1點刷新傷害。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            parent_node.add_child(info_node)
            parent_node, snapshot = info_node, next_state

        available_deck = clone_card_list(snapshot.deterministic_top) + current_deck
        if not available_deck: 
            return [parent_node]

        draw_combos = get_umi_draw_combinations(available_deck, min(3, len(available_deck)))
        if not draw_combos: 
            return [parent_node]

        final_leaves = []
        for combo_idx, (drawn_cards, combo_prob) in enumerate(draw_combos):
            combo_summary = " | ".join([format_card_info(c) for c in drawn_cards])
            chance_node = TreeNode(
                name=f"🎲 [{combo_prob*100:.1f}%] 【羽未】: 翻出 {combo_summary}", node_type="chance", prob=combo_prob,
                state_snapshot=snapshot.clone(), details=f"羽未效果翻開牌組頂牌: {combo_summary} (概率 {combo_prob*100:.1f}%)。",
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            parent_node.add_child(chance_node)

            stock_dec_node = TreeNode(
                name="🔀 [決策點] 選擇【羽未】: 充庫卡牌", node_type="decision", prob=1.0, state_snapshot=snapshot.clone(),
                details=f"看到卡牌 {combo_summary}，請選擇至多 1 張放入能量區。", 
                node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
            )
            chance_node.add_child(stock_dec_node)

            stock_choices = [("不充庫 (所有卡牌重排放回)", -1)]
            seen_choice_sigs = set()
            for idx_c, card in enumerate(drawn_cards):
                card_info = format_card_info(card)
                if card_info not in seen_choice_sigs:
                    seen_choice_sigs.add(card_info)
                    stock_choices.append((f"充庫: {card_info}", idx_c))

            for choice_title, stock_idx in stock_choices:
                state_after_stock = snapshot.clone()
                remaining_bag = clone_card_list(available_deck)
                for c_drawn in drawn_cards:
                    for idx_b, c_bag in enumerate(remaining_bag):
                        if format_card_info(c_bag) == format_card_info(c_drawn):
                            remaining_bag.pop(idx_b)
                            break

                cards_to_reorder = [sanitize_card_dict(c) for c in drawn_cards]
                if stock_idx >= 0 and stock_idx < len(cards_to_reorder):
                    state_after_stock.my_stock.append(cards_to_reorder.pop(stock_idx))

                state_after_stock.my_deck = remaining_bag
                state_after_stock.deterministic_top = []

                stock_choice_node = TreeNode(
                    name=f"🎯 {choice_title}", node_type="choice", prob=1.0, state_snapshot=state_after_stock,
                    details=f"羽未決策: 選擇{choice_title}。", 
                    node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                )
                stock_dec_node.add_child(stock_choice_node)

                if len(cards_to_reorder) == 0:
                    if not state_after_stock.deterministic_top and not state_after_stock.my_deck:
                        state_after_stock.refresh_my_deck_if_empty()
                    final_leaves.append(stock_choice_node)
                    continue

                if len(cards_to_reorder) == 1:
                    state_after_stock.push_to_deterministic_top([cards_to_reorder[0]])
                    final_leaves.append(stock_choice_node)
                else:
                    reorder_dec_node = TreeNode(
                        name="🔀 [決策點] 選擇【羽未】: 置頂順序", node_type="decision", prob=1.0,
                        state_snapshot=state_after_stock, details=f"選擇剩餘 {len(cards_to_reorder)} 張牌放回牌組頂端的順序。",
                        node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                    )
                    stock_choice_node.add_child(reorder_dec_node)

                    seen_perms = set()
                    for perm_idx, perm in enumerate([p for p in itertools.permutations(cards_to_reorder) if not (tuple(format_card_info(c) for c in p) in seen_perms or seen_perms.add(tuple(format_card_info(c) for c in p)))]):
                        state_after_reorder = state_after_stock.clone()
                        state_after_reorder.push_to_deterministic_top(list(perm))
                        kinds_desc = " ➔ ".join([format_card_info(c) for c in perm])

                        reorder_choice_node = TreeNode(
                            name=f"🎯 置頂順序 {perm_idx+1}: [頂 ➔ 底] {kinds_desc}", node_type="choice", prob=1.0, state_snapshot=state_after_reorder,
                            details=f"羽未決策: 設置剩餘卡牌置頂順序為 [頂 ➔ 底]: {kinds_desc}。", 
                            node_counter_ref=ctx.node_counter_ref, on_progress_cb=ctx.on_progress_cb,
                        )
                        reorder_dec_node.add_child(reorder_choice_node)
                        final_leaves.append(reorder_choice_node)

        return final_leaves