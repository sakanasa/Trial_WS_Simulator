# -*- coding: utf-8 -*-
"""
模拟执行器 (Simulation Runner) - 触发架构重构版
负责常规模式、高级模式、工况模式以及批量矩阵统计的多线程后台计算。
引入 TriggerQueueManager，实现我方优先(My Priority)、队列化平铺与规则优先机制。
支持自定义卡牌 7 步攻击流水线 (1)~(7) 与敌方前列击倒比对。
"""

import time
import random
import copy
import threading
from typing import List, Dict, Tuple, Any, Callable, Optional

from core.models import GameState, RoleState, card_is_normal, card_is_climax, clone_card_list
from core.engine import (
    build_deck, stabilize, resolve_damage, push_cards,
    drain_climax, normal_wash, mocha_operation, perform_bottom_drain_and_burn,
    execute_ice_armor, add_cards_to_clock
)
from utils.registry import registry
from simulator.statistics import calc_winrate, calc_avg_damage


class TrialConditionHelper:
    """单次模拟独立的线程安全工况助手（代表我方场上状态）"""

    def __init__(self, cond_deck: list, cond_control: list, cond_stock: list, cond_level: Any, cond_clock: Any):
        self.cond_deck = cond_deck
        self.cond_control = cond_control
        self.cond_stock = cond_stock
        self.cond_level = cond_level
        self.cond_clock = cond_clock
        self.failed = False  # 我方败北标志

    def _refresh_condition_deck(self):
        """我方卡组刷新与刷新伤害"""
        if not self.cond_deck and self.cond_control:
            self.cond_deck.extend(self.cond_control)
            self.cond_control.clear()
            random.shuffle(self.cond_deck)
            if self.cond_deck:
                top = self.cond_deck.pop()
                add_cards_to_clock(self.cond_clock, [top], self.cond_level, self.cond_control, lambda: False)

    def stabilize_condition(self) -> bool:
        """检查我方工况区域是否败北（我方 Level 4 或无牌）"""
        res = stabilize(self.cond_deck, self.cond_control, self.cond_level, self.cond_clock)
        if res:
            self.failed = True
        return res


class TriggerQueueManager:
    """
    触发队列管理器：
    严格遵循 WS 规范：我方优先(My Priority) -> 敌方(Enemy) 顺序平铺弹出现有队列。
    """

    def __init__(self):
        self.my_queue: List[Dict[str, Any]] = []
        self.enemy_queue: List[Dict[str, Any]] = []

    def add_task(self, owner: str, task: Dict[str, Any]):
        """入池：根据 owner 标签压入对应队列"""
        if owner == "my":
            self.my_queue.append(task)
        else:
            self.enemy_queue.append(task)

    def has_pending(self) -> bool:
        return len(self.my_queue) > 0 or len(self.enemy_queue) > 0

    def pop_next_task(self) -> Optional[Dict[str, Any]]:
        """我方优先弹出原则：只要 my_queue 有任务，永远先弹 my_queue"""
        if self.my_queue:
            return self.my_queue.pop(0)
        if self.enemy_queue:
            return self.enemy_queue.pop(0)
        return None

    def resolve_all(
        self,
        deck: list, control: list, stock: list, level: list, clock: list,
        soul_points: int, stabilize_func: Callable[[], bool],
        pending_pass: dict, role_idx: int, num_roles: int,
        steps_info: list = None, triggered_by_op: Any = None,
        cond_helper: Any = None,
        abilities: list = None,
        ice_armors: list = None,
        role_state: dict = None,
        front_slot: str = None,
        enemy_front_roles: dict = None
    ) -> Tuple[bool, int, int]:
        """队列解算主循环"""
        game_over = False
        total_cancel_damage = 0
        role_no = role_idx + 1

        while self.has_pending():
            if game_over or (cond_helper and cond_helper.failed):
                break

            task = self.pop_next_task()
            if not task:
                break

            task_type = task.get("task_type")

            if task_type == "cancel_trigger":
                nested_op = task.get("nested_op")
                cancelled_damage = task.get("cancelled_damage", 0)

                if nested_op and nested_op.get("type") in registry.types:
                    opt = nested_op["type"]
                    kwargs = {
                        "soul_points": soul_points,
                        "cancelled_damage": cancelled_damage,
                        "ice_armors": ice_armors,
                        "condition_deck": getattr(cond_helper, "cond_deck", None),
                        "condition_stock": getattr(cond_helper, "cond_stock", None),
                        "app": cond_helper,
                        "front_slot": front_slot,
                        "enemy_front_roles": enemy_front_roles
                    }

                    over, desc, extra = registry.execute(
                        opt, deck, control, stock, level, clock, nested_op, stabilize_func, **kwargs
                    )
                    
                    sub_dmg = extra.get("total_damage", 0)
                    hit_count = extra.get("hit_count", 0)
                    total_cancel_damage += sub_dmg

                    if "soul_points" in extra:
                        soul_points = extra["soul_points"]

                    if over or stabilize_func() or (cond_helper and cond_helper.stabilize_condition()):
                        game_over = True

                    if steps_info is not None:
                        title = f"角色{role_no}取消操作(由操作{triggered_by_op}触发)"
                        steps_info.append({
                            "is_cancel": True, "title": title, "index": title, "desc": f"取消触发: {desc}",
                            "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                            "level": level.copy(), "clock": clock.copy(), "soul": soul_points,
                            "abilities": copy.deepcopy(abilities) if abilities else [],
                            "game_over": game_over
                        })

                    sub_cancelled = extra.get("cancelled_damage")
                    if sub_cancelled is not None and not game_over and abilities:
                        for ab_item in abilities:
                            trig = False
                            if ab_item.get("type") == "single" and not ab_item.get("triggered", False):
                                ab_item["triggered"] = True
                                trig = True
                            elif ab_item.get("type") == "multi":
                                cnt = ab_item.get("triggered_count", 0)
                                tot = ab_item.get("total", 1)
                                if cnt < tot:
                                    ab_item["triggered_count"] = cnt + 1
                                    ab_item["remaining"] = tot - ab_item["triggered_count"]
                                    trig = True

                            if trig:
                                nested_ops = ab_item.get("nested_ops", [])
                                sub_nested = ab_item.get("nested_op") if ab_item.get("type") == "single" else (
                                    nested_ops[cnt] if cnt < len(nested_ops) else None
                                )
                                if sub_nested:
                                    # 🌟【传火逻辑修复】：若开启了 pass_on_trigger，将能力传递给目标角色
                                    if ab_item.get("pass_on_trigger"):
                                        target_idx = ab_item.get("pass_target", 1) - 1

                                        # 🌟 增加顺延判断：
                                        if target_idx <= role_idx:
                                            target_idx = role_idx + 1

                                        if 0 <= target_idx < num_roles:
                                            passed_ability = {
                                                "type": "single",
                                                "owner": ab_item.get("owner", "my"),
                                                "nested_op": copy.deepcopy(sub_nested),
                                                "triggered": False,
                                                "pass_on_trigger": True,                          # 🌟 继承传火标志
                                                "pass_target": ab_item.get("pass_target", 1)      # 🌟 继承传火目标
                                            }
                                            pending_pass.setdefault(target_idx, []).append(passed_ability)

                                    self.add_task(
                                        owner=ab_item.get("owner", "my"),
                                        task={"task_type": "cancel_trigger", "nested_op": sub_nested, "cancelled_damage": sub_cancelled}
                                    )

            elif task_type == "ice_armor":
                hits = task.get("hits", 0)
                ice_idx = task.get("ice_idx", 1)
                ice_title = f"角色{role_no}冰甲{ice_idx}(由操作{triggered_by_op}触发)"

                Y, ice_over = execute_ice_armor(deck, control, clock, level, hits, stabilize_func)
                desc_ice = f"冰甲{ice_idx}: 受到{hits}次命中伤害，冰甲响应从卡组顶推入{Y}张肉牌到控制室"

                if ice_over or (cond_helper and cond_helper.stabilize_condition()):
                    game_over = True

                if steps_info is not None:
                    steps_info.append({
                        "is_cancel": False, "is_ice_armor": True, "title": ice_title, "index": ice_title, "desc": desc_ice,
                        "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                        "level": level.copy(), "clock": clock.copy(), "soul": soul_points,
                        "abilities": copy.deepcopy(abilities) if abilities else [],
                        "game_over": game_over
                    })

        return game_over, soul_points, total_cancel_damage


class SimulationRunner:
    """多线程蒙特卡洛模拟核心控制器"""

    @staticmethod
    def simulate_role_ops_segment(
        deck: list, control: list, stock: list, level: list, clock: list,
        role_state: dict, ops_list: list, start_idx: int, end_idx: int,
        pending_pass: dict, role_idx: int, num_roles: int,
        collect_steps: bool = False, global_ice_armors: list = None,
        condition_deck: list = None, condition_stock: list = None, app: Any = None,
        front_slot: str = None, enemy_front_roles: dict = None
    ) -> Tuple[bool, int, list]:
        """单角色/阶段操作模拟核心引擎"""
        soul_points = role_state.get("soul", 3)
        abilities = role_state.setdefault("abilities", [])
        ice_armors = global_ice_armors if global_ice_armors is not None else role_state.setdefault("ice_armors", [])

        if role_idx in pending_pass:
            while pending_pass[role_idx]:
                ab = pending_pass[role_idx].pop(0)
                ab["triggered"] = False
                abilities.append(ab)

        game_over = False
        segment_damage = 0
        steps_info = [] if collect_steps else []
        stabilize_func = lambda: stabilize(deck, control, level, clock)
        role_no = role_idx + 1

        queue_manager = TriggerQueueManager()

        for i in range(start_idx, end_idx + 1):
            if i >= len(ops_list):
                break
            op = ops_list[i]
            opt = op["type"]
            op_no = i + 1

            if opt == "取消触发":
                sub_mode = op.get("sub_mode", "单次触发")
                if sub_mode in ("单次触发", "传火"):
                    ability = {
                        "type": "single", "owner": "my",
                        "nested_op": op.get("nested_op"),
                        "triggered": False
                    }
                    if sub_mode == "传火":
                        ability["pass_on_trigger"] = True
                        ability["pass_target"] = op.get("pass_target", 1)
                    abilities.append(ability)

                elif sub_mode == "多次触发":
                    total = op.get("total_triggers", 1)
                    ability = {
                        "type": "multi", "owner": "my",
                        "total": total, "triggered_count": 0, "remaining": total,
                        "nested_ops": op.get("nested_ops", [])
                    }
                    abilities.append(ability)

                desc = "添加取消触发能力"
                if collect_steps:
                    steps_info.append({
                        "is_cancel": False, "title": f"角色{role_no}操作{op_no}", "index": op_no, "desc": desc,
                        "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                        "level": level.copy(), "clock": clock.copy(), "soul": soul_points,
                        "abilities": copy.deepcopy(abilities), "game_over": game_over
                    })
                continue

            if opt == "多步骤操作":
                steps = op.get("steps", [])
                m_dmg = 0
                for step_idx, step_op in enumerate(steps):
                    if game_over or (app and getattr(app, "failed", False)):
                        break
                    
                    sub_opt = step_op.get("type", "未知操作")
                    sub_title = f"角色{role_no}操作{op_no}.{step_idx+1} ({sub_opt})"

                    s_over, s_desc, s_extra = registry.execute(
                        sub_opt, deck, control, stock, level, clock, step_op, stabilize_func,
                        soul_points=soul_points, ice_armors=ice_armors,
                        condition_deck=condition_deck, condition_stock=condition_stock, app=app,
                        front_slot=front_slot, enemy_front_roles=enemy_front_roles
                    )
                    sub_dmg = s_extra.get("total_damage", 0)
                    m_dmg += sub_dmg
                    hit_count = s_extra.get("hit_count", 0)

                    if "soul_points" in s_extra:
                        soul_points = s_extra["soul_points"]

                    if s_over:
                        game_over = True

                    if collect_steps:
                        steps_info.append({
                            "is_cancel": False,
                            "title": sub_title,
                            "index": f"{op_no}.{step_idx+1}",
                            "desc": s_desc,
                            "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                            "level": level.copy(), "clock": clock.copy(), "soul": soul_points,
                            "abilities": copy.deepcopy(abilities), "game_over": game_over
                        })

                    s_cancelled_dmg = s_extra.get("cancelled_damage")
                    if s_cancelled_dmg is not None and not game_over:
                        for ab in abilities:
                            trig = False
                            nested_op_to_run = None
                            if ab.get("type") == "single" and not ab.get("triggered", False):
                                ab["triggered"] = True
                                trig = True
                                nested_op_to_run = ab.get("nested_op")
                            elif ab.get("type") == "multi":
                                cnt = ab.get("triggered_count", 0)
                                tot = ab.get("total", 1)
                                if cnt < tot:
                                    ab["triggered_count"] = cnt + 1
                                    ab["remaining"] = tot - ab["triggered_count"]
                                    trig = True
                                    nested_ops = ab.get("nested_ops", [])
                                    if cnt < len(nested_ops):
                                        nested_op_to_run = nested_ops[cnt]

                            if trig and nested_op_to_run:
                                # 🌟【传火与顺延逻辑】：若开启了传火，将能力传递给下一个有效角色
                                if ab.get("pass_on_trigger"):
                                    target_idx = ab.get("pass_target", 1) - 1
                                    if target_idx <= role_idx:
                                        target_idx = role_idx + 1  # 目标 <= 当前时，自动顺延传给下一个角色 (X + 1)
                                    if 0 <= target_idx < num_roles:
                                        passed_ability = {
                                            "type": "single",
                                            "owner": ab.get("owner", "my"),
                                            "nested_op": copy.deepcopy(nested_op_to_run),
                                            "triggered": False,
                                            "pass_on_trigger": True,                    # 🌟 继承传火标志（实现无限连锁）
                                            "pass_target": ab.get("pass_target", 1)     # 🌟 继承原始目标参数
                                        }
                                        pending_pass.setdefault(target_idx, []).append(passed_ability)

                                queue_manager.add_task(
                                    owner=ab.get("owner", "my"),
                                    task={"task_type": "cancel_trigger", "nested_op": nested_op_to_run, "cancelled_damage": s_cancelled_dmg}
                                )

                    if ice_armors and sub_opt != "冰甲":
                        total_hits = hit_count + role_state.get("ice_armor_hits", 0)
                        if total_hits > 0:
                            for idx, ice in enumerate(ice_armors):
                                queue_manager.add_task(
                                    owner="enemy",
                                    task={"task_type": "ice_armor", "hits": total_hits, "ice_idx": idx + 1}
                                )
                            role_state["ice_armor_hits"] = 0

                q_over, soul_points, q_dmg = queue_manager.resolve_all(
                    deck, control, stock, level, clock, soul_points, stabilize_func,
                    pending_pass, role_idx, num_roles,
                    steps_info=steps_info if collect_steps else None,
                    triggered_by_op=op_no, cond_helper=app,
                    abilities=abilities, ice_armors=ice_armors, role_state=role_state,
                    front_slot=front_slot, enemy_front_roles=enemy_front_roles
                )
                m_dmg += q_dmg
                segment_damage += m_dmg
                if q_over or (app and getattr(app, "failed", False)):
                    game_over = True

                continue

            if opt in registry.types and registry.types[opt]["execute"]:
                kwargs = {
                    "soul_points": soul_points,
                    "ice_armors": ice_armors,
                    "condition_deck": condition_deck,
                    "condition_stock": condition_stock,
                    "condition_control": getattr(app, "cond_control", None),
                    "app": app,
                    "front_slot": front_slot,
                    "enemy_front_roles": enemy_front_roles
                }
                over, desc, extra = registry.execute(
                    opt, deck, control, stock, level, clock, op, stabilize_func, **kwargs
                )
                game_over = over
                op_dmg = extra.get("total_damage", 0)
                hit_count = extra.get("hit_count", 0)
                segment_damage += op_dmg

                if "soul_points" in extra:
                    soul_points = extra["soul_points"]

                # === 【新增】记录攻击方式状态 (正面/侧面/直击) ===
                if "attack_mode" in extra:
                    role_state["attack_mode"] = extra["attack_mode"]

                if collect_steps:
                    steps_info.append({
                        "is_cancel": False, "title": f"角色{role_no}操作{op_no}", "index": op_no, "desc": desc,
                        "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                        "level": level.copy(), "clock": clock.copy(), "soul": soul_points,
                        "abilities": copy.deepcopy(abilities), "game_over": game_over
                    })

                cancelled_dmg = extra.get("cancelled_damage")
                if cancelled_dmg is not None and not game_over:
                    for ab in abilities:
                        trig = False
                        nested_op_to_run = None
                        if ab.get("type") == "single" and not ab.get("triggered", False):
                            ab["triggered"] = True
                            trig = True
                            nested_op_to_run = ab.get("nested_op")
                        elif ab.get("type") == "multi":
                            cnt = ab.get("triggered_count", 0)
                            tot = ab.get("total", 1)
                            if cnt < tot:
                                ab["triggered_count"] = cnt + 1
                                ab["remaining"] = tot - ab["triggered_count"]
                                trig = True
                                nested_ops = ab.get("nested_ops", [])
                                if cnt < len(nested_ops):
                                    nested_op_to_run = nested_ops[cnt]

                        if trig and nested_op_to_run:
                            # 🌟【传火与顺延逻辑】：若开启了传火，将能力传递给下一个有效角色
                            if ab.get("pass_on_trigger"):
                                target_idx = ab.get("pass_target", 1) - 1
                                if target_idx <= role_idx:
                                    target_idx = role_idx + 1  # 目标 <= 当前时，自动顺延传给下一个角色 (X + 1)
                                if 0 <= target_idx < num_roles:
                                    passed_ability = {
                                        "type": "single",
                                        "owner": ab.get("owner", "my"),
                                        "nested_op": copy.deepcopy(nested_op_to_run),
                                        "triggered": False,
                                        "pass_on_trigger": True,                    # 🌟 继承传火标志（实现无限连锁）
                                        "pass_target": ab.get("pass_target", 1)     # 🌟 继承原始目标参数
                                    }
                                    pending_pass.setdefault(target_idx, []).append(passed_ability)

                            queue_manager.add_task(
                                owner=ab.get("owner", "my"),
                                task={"task_type": "cancel_trigger", "nested_op": nested_op_to_run, "cancelled_damage": cancelled_dmg}
                            )

                if ice_armors and opt != "冰甲":
                    total_hits = hit_count + role_state.get("ice_armor_hits", 0)
                    if total_hits > 0:
                        for idx, ice in enumerate(ice_armors):
                            queue_manager.add_task(
                                owner="enemy",
                                task={"task_type": "ice_armor", "hits": total_hits, "ice_idx": idx + 1}
                            )
                        role_state["ice_armor_hits"] = 0

                q_over, soul_points, q_dmg = queue_manager.resolve_all(
                    deck, control, stock, level, clock, soul_points, stabilize_func,
                    pending_pass, role_idx, num_roles,
                    steps_info=steps_info if collect_steps else None,
                    triggered_by_op=op_no, cond_helper=app,
                    abilities=abilities, ice_armors=ice_armors, role_state=role_state,
                    front_slot=front_slot, enemy_front_roles=enemy_front_roles
                )
                segment_damage += q_dmg
                if q_over or (app and getattr(app, "failed", False)):
                    game_over = True

            if game_over or (app and getattr(app, "failed", False)):
                break

        role_state["soul"] = soul_points
        return game_over, segment_damage, steps_info

    @staticmethod
    def simulate_custom_card_attack_pipeline(
        deck: list, control: list, stock: list, level: list, clock: list,
        card_data: dict, front_slot: str, enemy_front_roles: dict,
        pending_pass: dict, collect_steps: bool = False, global_ice_armors: list = None,
        cond_helper: Any = None
    ) -> Tuple[bool, int, list]:
        """
        对单个导入的自定义卡牌依次展开 (1)~(7) 攻击流水线：
        (1) 攻击前 -> (2) 攻击方式 -> (3) 攻击时 -> (4) 判定阶段 -> (5) 伤害结算 -> (击倒判定) -> (6) 击倒对手时 -> (7) 攻击结束
        """
        card_name = card_data.get("name", "自定义角色")
        effects = card_data.get("effects", {})
        my_power = int(card_data.get("power", 500) or 500)
        base_soul = int(card_data.get("soul", 1) or 1)

        role_state = {
            "soul": base_soul,
            "power": my_power,
            "abilities": [],
            "ice_armors": global_ice_armors if global_ice_armors is not None else []
        }

        steps_info = [] if collect_steps else []
        total_damage = 0
        game_over = False

        phases = [
            ("pre_attack", "(1) 攻击前"),
            ("attack_type", "(2) 攻击方式"),
            ("on_attack", "(3) 攻击时"),
            ("trigger_step", "(4) 判定阶段"),
            ("deal_damage", "(5) 伤害结算"),
            ("on_reverse", "(6) 击倒对手时"),
            ("post_attack", "(7) 攻击结束")
        ]

        is_reverse_success = False

        for phase_key, phase_label in phases:
            if game_over or (cond_helper and cond_helper.failed):
                break

            # 若未成功击倒敌方，跳过 (6) 击倒对手时
            if phase_key == "on_reverse" and not is_reverse_success:
                continue

            ops = effects.get(phase_key, [])
            if not ops and phase_key == "attack_type":
                ops = [{"type": "攻击方式", "attack_type": "正面"}]

            if not ops:
                continue

            over, phase_dmg, phase_steps = SimulationRunner.simulate_role_ops_segment(
                deck, control, stock, level, clock,
                role_state, ops, 0, len(ops) - 1,
                pending_pass, role_idx=0, num_roles=1,
                collect_steps=collect_steps, global_ice_armors=global_ice_armors,
                condition_deck=getattr(cond_helper, "cond_deck", None),
                condition_stock=getattr(cond_helper, "condition_stock", None),
                app=cond_helper,
                front_slot=front_slot,
                enemy_front_roles=enemy_front_roles
            )

            total_damage += phase_dmg
            if collect_steps:
                for st in phase_steps:
                    st["title"] = f"【{card_name}】{st['title']} [{phase_label}]"
                steps_info.extend(phase_steps)

            if over:
                game_over = True
                break

            # (5) 伤害结算完成后，进行击倒判定
            if phase_key == "deal_damage" and not game_over:
                current_attack_mode = role_state.get("attack_mode", "正面")  # 获取当前攻击方式
                enemy_role = enemy_front_roles.get(front_slot) if enemy_front_roles else None
                enemy_lvl_str = "空"
                enemy_pwr = 500
                is_rev = False

                if enemy_role:
                    lvl_item = enemy_role.get("level")
                    pwr_item = enemy_role.get("power")
                    is_rev = enemy_role.get("is_reversed", False)
                    enemy_lvl_str = str(lvl_item.get()) if hasattr(lvl_item, "get") else str(lvl_item or "空")
                    enemy_pwr = int(pwr_item.get()) if hasattr(pwr_item, "get") else int(pwr_item or 500)

                # === 【关键修正】只有 [正面攻击] 且 [对方槽位不为"空"] 且 [未被击倒] 时，才进行力量对比与击倒 ===
                if current_attack_mode == "正面" and enemy_lvl_str != "空" and not is_rev:
                    if my_power >= enemy_pwr:
                        enemy_role["is_reversed"] = True
                        is_reverse_success = True
                        if collect_steps:
                            steps_info.append({
                                "is_cancel": False,
                                "title": f"【{card_name}】正面战斗比对",
                                "index": "击倒判定",
                                "desc": f"击倒判定: 正面攻击力量({my_power}) >= 对方力量({enemy_pwr})，成功击倒对方【{front_slot}】角色！",
                                "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                                "level": level.copy(), "clock": clock.copy(), "soul": role_state.get("soul", 1),
                                "abilities": copy.deepcopy(role_state.get("abilities", [])),
                                "game_over": False
                            })
                # 如果是侧面攻击，记录侧击日志，不触发击倒
                elif current_attack_mode == "侧面" and collect_steps:
                    steps_info.append({
                        "is_cancel": False,
                        "title": f"【{card_name}】侧击判定",
                        "index": "侧击",
                        "desc": f"侧击判定: 攻击方式为[侧面]，不触发战斗比对与击倒结算。",
                        "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                        "level": level.copy(), "clock": clock.copy(), "soul": role_state.get("soul", 1),
                        "abilities": copy.deepcopy(role_state.get("abilities", [])),
                        "game_over": False
                    })
                # 如果对方角色为空，记录直击日志，不触发击倒
                elif enemy_lvl_str == "空" and collect_steps:
                    steps_info.append({
                        "is_cancel": False,
                        "title": f"【{card_name}】直击判定",
                        "index": "直击",
                        "desc": f"直击判定: 对方【{front_slot}】角色为空，自动进行直击，不触发战斗比对与击倒结算。",
                        "deck": deck.copy(), "control": control.copy(), "stock": stock.copy(),
                        "level": level.copy(), "clock": clock.copy(), "soul": role_state.get("soul", 1),
                        "abilities": copy.deepcopy(role_state.get("abilities", [])),
                        "game_over": False
                    })

        return game_over, total_damage, steps_info

    @staticmethod
    def run_regular_simulation_async(
        sim_times: int, ops_params: list, fixed_params: dict,
        level_meat: int, clock_meat: int,
        on_progress: Callable[[int, int], None],
        on_done: Callable[[float, float, float], None],
        on_error: Callable[[Exception], None],
    ):
        def _thread_target():
            start_time = time.time()
            wins = 0
            total_damage_sum = 0
            update_interval = max(1, sim_times // 100)

            try:
                for i in range(sim_times):
                    deck = build_deck(fixed_params["deck_normal"], fixed_params["deck_climax"])
                    control = ["普通"] * fixed_params["control_normal"] + ["高潮"] * fixed_params["control_climax"]
                    stock = ["普通"] * fixed_params["stock_normal"] + ["高潮"] * fixed_params["stock_climax"]

                    level_climax = fixed_params["level_climax_count"]
                    level = ["高潮"] * level_climax + ["普通"] * min(level_meat, 4 - level_climax)
                    random.shuffle(level)

                    clock_climax = fixed_params["clock_climax_count"]
                    clock = ["高潮"] * clock_climax + ["普通"] * min(clock_meat, 6 - clock_climax)
                    random.shuffle(clock)

                    stabilize_func = lambda: stabilize(deck, control, level, clock)
                    game_over = False
                    total_dmg = 0

                    for op in ops_params:
                        opt = op["type"]
                        if opt in registry.types and registry.types[opt]["execute"]:
                            over, desc, extra = registry.execute(
                                opt, deck, control, stock, level, clock, op, stabilize_func
                            )
                            total_dmg += extra.get("total_damage", 0)
                            if over:
                                game_over = True
                                break

                    total_damage_sum += total_dmg
                    if game_over:
                        wins += 1

                    if (i + 1) % update_interval == 0 or i == sim_times - 1:
                        on_progress(i + 1, int(((i + 1) / sim_times) * 100))

                elapsed = time.time() - start_time
                winrate = calc_winrate(wins, sim_times)
                avg_dmg = calc_avg_damage(total_damage_sum, sim_times)
                on_done(winrate, avg_dmg, elapsed)

            except Exception as e:
                on_error(e)

        threading.Thread(target=_thread_target, daemon=True).start()

    @staticmethod
    def run_advanced_simulation_async(
        sim_times: int, execution_plan: list, roles_params: list, fixed_params: dict,
        level_meat: int, clock_meat: int,
        on_progress: Callable[[int, int], None],
        on_done: Callable[[float, float, float], None],
        on_error: Callable[[Exception], None],
    ):
        def _thread_target():
            start_time = time.time()
            wins = 0
            total_damage_sum = 0
            update_interval = max(1, sim_times // 100)

            try:
                for i in range(sim_times):
                    deck = build_deck(fixed_params["deck_normal"], fixed_params["deck_climax"])
                    control = ["普通"] * fixed_params["control_normal"] + ["高潮"] * fixed_params["control_climax"]
                    stock = ["普通"] * fixed_params["stock_normal"] + ["高潮"] * fixed_params["stock_climax"]

                    level_climax = fixed_params["level_climax_count"]
                    level = ["高潮"] * level_climax + ["普通"] * min(level_meat, 4 - level_climax)
                    random.shuffle(level)

                    clock_climax = fixed_params["clock_climax_count"]
                    clock = ["高潮"] * clock_climax + ["普通"] * min(clock_meat, 6 - clock_climax)
                    random.shuffle(clock)

                    game_over = False
                    total_dmg = 0
                    pending_pass = {}
                    global_ice_armors = []

                    role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

                    for role_idx, start_idx, end_idx in execution_plan:
                        if game_over:
                            break
                        state = role_states[role_idx]
                        over, dmg, _ = SimulationRunner.simulate_role_ops_segment(
                            deck, control, stock, level, clock,
                            state, state["ops"], start_idx, end_idx,
                            pending_pass, role_idx, len(roles_params),
                            collect_steps=False, global_ice_armors=global_ice_armors
                        )
                        total_dmg += dmg
                        if over:
                            game_over = True

                    total_damage_sum += total_dmg
                    if game_over:
                        wins += 1

                    if (i + 1) % update_interval == 0 or i == sim_times - 1:
                        on_progress(i + 1, int(((i + 1) / sim_times) * 100))

                elapsed = time.time() - start_time
                winrate = calc_winrate(wins, sim_times)
                avg_dmg = calc_avg_damage(total_damage_sum, sim_times)
                on_done(winrate, avg_dmg, elapsed)

            except Exception as e:
                on_error(e)

        threading.Thread(target=_thread_target, daemon=True).start()

    @staticmethod
    def run_condition_simulation_async(
        sim_times: int, execution_plan: list, roles_params: list, fixed_params: dict,
        level_meat: int, clock_meat: int,
        condition_deck_cards: list, condition_control_cards: list,
        condition_stock_cards: list, condition_level_cards: dict, condition_clock_cards: dict,
        condition_front_cards: dict = None, enemy_front_roles: dict = None,
        on_progress: Callable[[int, int], None] = None,
        on_done: Callable[[float, float, float], None] = None,
        on_error: Callable[[Exception], None] = None,
    ):
        def _thread_target():
            start_time = time.time()
            wins = 0
            total_damage_sum = 0
            update_interval = max(1, sim_times // 100)

            try:
                for i in range(sim_times):
                    deck = build_deck(fixed_params["deck_normal"], fixed_params["deck_climax"])
                    control = ["普通"] * fixed_params["control_normal"] + ["高潮"] * fixed_params["control_climax"]
                    stock = ["普通"] * fixed_params["stock_normal"] + ["高潮"] * fixed_params["stock_climax"]

                    level_climax = fixed_params["level_climax_count"]
                    level = ["高潮"] * level_climax + ["普通"] * min(level_meat, 4 - level_climax)
                    random.shuffle(level)

                    clock_climax = fixed_params["clock_climax_count"]
                    clock = ["高潮"] * clock_climax + ["普通"] * min(clock_meat, 6 - clock_climax)
                    random.shuffle(clock)

                    cond_deck = clone_card_list(condition_deck_cards)
                    random.shuffle(cond_deck)
                    
                    cond_control = clone_card_list(condition_control_cards)
                    cond_stock = clone_card_list(condition_stock_cards)
                    cond_level = copy.deepcopy(condition_level_cards)
                    cond_clock = copy.deepcopy(condition_clock_cards)

                    cond_helper = TrialConditionHelper(cond_deck, cond_control, cond_stock, cond_level, cond_clock)

                    stabilize_func = lambda: stabilize(deck, control, level, clock)

                    if stabilize_func() or cond_helper.stabilize_condition():
                        if (i + 1) % update_interval == 0 or i == sim_times - 1:
                            if on_progress: on_progress(i + 1, int(((i + 1) / sim_times) * 100))
                        continue

                    game_over = False
                    total_dmg = 0
                    pending_pass = {}
                    global_ice_armors = []

                    # 拷贝敌方角色状态
                    local_enemy_front = {}
                    if enemy_front_roles:
                        for k, v in enemy_front_roles.items():
                            lval = v.get("level").get() if hasattr(v.get("level"), "get") else v.get("level", "0")
                            pval = v.get("power").get() if hasattr(v.get("power"), "get") else v.get("power", 500)
                            local_enemy_front[k] = {"level": lval, "power": pval, "is_reversed": False}

                    # 1. 解算角色定义区的操作
                    role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

                    for role_idx, start_idx, end_idx in execution_plan:
                        if game_over or cond_helper.failed:
                            break
                        rstate = role_states[role_idx]
                        over, dmg, _ = SimulationRunner.simulate_role_ops_segment(
                            deck, control, stock, level, clock,
                            rstate, rstate["ops"], start_idx, end_idx,
                            pending_pass, role_idx, len(roles_params),
                            collect_steps=False, global_ice_armors=global_ice_armors,
                            condition_deck=cond_helper.cond_deck, condition_stock=cond_helper.cond_stock, app=cond_helper,
                            front_slot=f"前列{role_idx+1}",  # <--- 修正：传入 front_slot
                            enemy_front_roles=local_enemy_front
                        )
                        total_dmg += dmg
                        if over:
                            game_over = True

                    # 2. 依次解算我方前列1 -> 前列2 -> 前列3 的 7 步流水线卡牌
                    if not game_over and not cond_helper.failed and condition_front_cards:
                        for front_key in ["前列1", "前列2", "前列3"]:
                            if game_over or cond_helper.failed:
                                break
                            f_cards = condition_front_cards.get(front_key, [])
                            if f_cards:
                                c_card = f_cards[0]
                                c_over, c_dmg, _ = SimulationRunner.simulate_custom_card_attack_pipeline(
                                    deck, control, stock, level, clock,
                                    c_card, front_key, local_enemy_front,
                                    pending_pass, collect_steps=False, global_ice_armors=global_ice_armors,
                                    cond_helper=cond_helper
                                )
                                total_dmg += c_dmg
                                if c_over:
                                    game_over = True

                    if game_over and not cond_helper.failed:
                        wins += 1
                    total_damage_sum += total_dmg

                    if (i + 1) % update_interval == 0 or i == sim_times - 1:
                        if on_progress: on_progress(i + 1, int(((i + 1) / sim_times) * 100))

                elapsed = time.time() - start_time
                winrate = calc_winrate(wins, sim_times)
                avg_dmg = calc_avg_damage(total_damage_sum, sim_times)
                if on_done: on_done(winrate, avg_dmg, elapsed)

            except Exception as e:
                if on_error: on_error(e)

        threading.Thread(target=_thread_target, daemon=True).start()