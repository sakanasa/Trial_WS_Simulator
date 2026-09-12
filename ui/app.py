# -*- coding: utf-8 -*-
"""
主程序控制器 (Main App Controller) - 徹底重構純淨版
負責整體 GUI 佈局調度、事件路由派發、模擬引擎接入與狀態服務橋接。
"""

import json
import random
import copy
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from typing import List, Dict, Any, Optional

# 1. 導入服務層與工廠
from services.custom_cards_service import custom_cards_service
from services.condition_state_service import condition_state_service
from services.regular_ops_service import regular_ops_service
from services.advanced_roles_service import advanced_roles_service
from simulator.environment_factory import GameEnvironmentFactory
from simulator.plan_parser import PlanParser
from simulator.runner import SimulationRunner, TrialConditionHelper

# 2. 核心算法模型與操作註冊
from core.models import card_is_climax, card_is_normal, get_card_trigger_soul, get_card_level, clone_card_list
from core.engine import stabilize
from core.operations import register_all_operations
from utils.registry import registry
from simulator.statistics import (
    calc_wilson_score_interval, calc_significant_difference_threshold, format_elapsed_time
)

# 3. 視圖層與組件
from ui.views.left_column import LeftColumnView
from ui.views.middle_column import MiddleColumnView
from ui.views.right_column import RightColumnView

from ui.dialogs.batch_dialog import BatchStatisticsDialog
from ui.dialogs.custom_cards_dialog import CustomCardsDialog
from ui.dialogs.card_table_dialog import CardTableDialog
from ui.dialogs.decision_tree_dialog import DecisionTreeDialog

from ui.components.common.ops_list_builder import OpsListBuilder
from ui.components.common.role_card import RoleListManager
from ui.components.common.plan_step_manager import PlanStepManager
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class App:
    """主程序控制器類"""

    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("試製 二六式黑白雙翼模擬器 ver.0.3 (重構完備版)")
        self.root.geometry("1500x820+0+0")

        register_all_operations()
        self._init_condition_state()
        self._build_layout()
        self._init_default_operations()
        self.refresh_field_canvas_stats()

    # =========================================================================
    # 1. 屬性代理與服務接入 (Proxies to Services & Components)
    # =========================================================================

    @property
    def custom_cards_data(self) -> list:
        return custom_cards_service.get_all()

    @custom_cards_data.setter
    def custom_cards_data(self, val: list):
        custom_cards_service.cards_data = val

    def save_custom_cards_data(self):
        custom_cards_service.save()

    @property
    def condition_deck_cards(self): return condition_state_service.deck_cards
    @property
    def condition_control_cards(self): return condition_state_service.control_cards
    @property
    def condition_memory_cards(self): return condition_state_service.memory_cards
    @property
    def condition_stock_cards(self): return condition_state_service.stock_cards
    @property
    def condition_cx_cards(self): return condition_state_service.cx_cards
    @property
    def condition_hand_cards(self): return condition_state_service.hand_cards
    @property
    def condition_level_cards(self): return condition_state_service.level_cards
    @property
    def condition_clock_cards(self): return condition_state_service.clock_cards
    @property
    def condition_front_cards(self): return condition_state_service.front_cards
    @property
    def condition_back_cards(self): return condition_state_service.back_cards
    @property
    def condition_enemy_front_cards(self): return condition_state_service.enemy_front_cards
    @property
    def condition_zones(self): return condition_state_service.zones
    @property
    def zone_max_cards(self): return condition_state_service.zone_max_cards
    @property
    def adv_roles(self): return condition_state_service.adv_roles
    @property
    def plan_steps(self): return condition_state_service.plan_steps
    @property
    def condition_roles(self): return condition_state_service.condition_roles
    @property
    def condition_plan_steps(self): return condition_state_service.condition_plan_steps

    @property
    def single_op(self) -> dict: return self.left_col.single_op_card.single_op
    @property
    def char_ops(self) -> list: return self.left_col.char_sim_card.char_ops

    @property
    def enemy_front_roles(self) -> dict:
        """動態提取敵方前列 1~3 的 Level 和 Power"""
        result = {}
        for i in range(1, 4):
            key_enemy = f"敵前列{i}"
            key_short = f"前列{i}"
            cards = self.condition_zones.get(key_enemy, [])
            if cards:
                c = cards[0]
                lvl = str(get_card_level(c))
                pwr = int(c.get("power", 500) or 500)
            else:
                lvl = "空"
                pwr = 500
            
            role_dict = {"level": lvl, "power": pwr, "is_reversed": False}
            result[key_short] = role_dict
            result[key_enemy] = role_dict
        return result

    # =========================================================================
    # 2. 佈局初始化與主題同步 (Layout & Theme)
    # =========================================================================

    def _init_condition_state(self):
        condition_state_service.init_state()

    def _build_layout(self):
        """重構分欄佈局：TPanedWindow + 三大獨立組件面板"""
        style = ttk.Style()
        style.theme_use("clam")
        
        current_mode = ctk.get_appearance_mode()
        bg_color = PALETTE["bg_main"][0] if current_mode == "Light" else PALETTE["bg_main"][1]
        
        style.configure("TPanedwindow", background=bg_color)
        style.configure("TPanedwindow.Sash", background=bg_color, sashthickness=8, sashpad=0)

        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.left_col = LeftColumnView(
            self.paned_window, app_controller=self, width=480,
            bg_color=PALETTE["bg_main"], corner_radius=12, border_width=0, border_color=PALETTE["card_border"]
        )
        self.paned_window.add(self.left_col, weight=1)

        self.middle_col = MiddleColumnView(
            self.paned_window, app_controller=self, width=480,
            bg_color=PALETTE["bg_main"], corner_radius=12, border_width=0, border_color=PALETTE["card_border"]
        )
        self.paned_window.add(self.middle_col, weight=1)

        self.right_col = RightColumnView(
            self.paned_window, app_controller=self, width=480,
            bg_color=PALETTE["bg_main"], corner_radius=12, border_width=0, border_color=PALETTE["card_border"]
        )
        self.paned_window.add(self.right_col, weight=1)

    def set_theme(self, mode: str):
        ctk.set_appearance_mode(mode)
        mode_idx = 0 if mode.lower() == "light" else 1
        bg_color = PALETTE["bg_main"][mode_idx]
        
        style = ttk.Style()
        style.configure("TPanedwindow", background=bg_color)
        style.configure("TPanedwindow.Sash", background=bg_color)
        self.refresh_field_canvas_stats()

    def toggle_multi_mode(self):
        self.middle_col.toggle_multi_mode()

    def _init_default_operations(self):
        self.reg_ops: List[dict] = []
        self.add_regular_operation()

        self.add_advanced_role()
        if not self.condition_roles:
            self.add_condition_role()

    # =========================================================================
    # 3. UI 委託助手 (Ops, Roles, Plans UI Delegates)
    # =========================================================================

    def refresh_advanced_roles_ui(self):
        self.refresh_roles_ui("advanced")

    def refresh_condition_roles_ui(self):
        self.refresh_roles_ui("condition")

    def refresh_plan_ui(self):
        self.refresh_plan_ui_generic("advanced")

    def refresh_condition_plan_ui(self):
        self.refresh_plan_ui_generic("condition")

    def _create_ops_list_ui(self, ops_list: list, parent_frame: Any, mode: str, role: Optional[dict] = None):
        OpsListBuilder.create_ops_list_ui(ops_list, parent_frame, mode, role, app_controller=self)

    def _add_op(self, ops_list: list, index: int, mode: str, role: Optional[dict] = None):
        OpsListBuilder.add_op(ops_list, index, mode, role, app_controller=self)

    def _remove_op(self, ops_list: list, index: int, mode: str, role: Optional[dict] = None):
        OpsListBuilder.remove_op(ops_list, index, mode, role, app_controller=self)

    def _move_op_up(self, ops_list: list, index: int, mode: str, role: Optional[dict] = None):
        OpsListBuilder.move_op_up(ops_list, index, mode, role, app_controller=self)

    def _move_op_down(self, ops_list: list, index: int, mode: str, role: Optional[dict] = None):
        OpsListBuilder.move_op_down(ops_list, index, mode, role, app_controller=self)

    def _remove_op_by_ref(self, ops_list: list, op: dict, mode: str, role: Optional[dict] = None):
        OpsListBuilder.remove_op_by_ref(ops_list, op, mode, role, app_controller=self)

    def _add_op_by_ref(self, ops_list: list, op: dict, mode: str, role: Optional[dict] = None):
        OpsListBuilder.add_op_by_ref(ops_list, op, mode, role, app_controller=self)

    def _move_op_up_by_ref(self, ops_list: list, op: dict, mode: str, role: Optional[dict] = None):
        OpsListBuilder.move_op_up_by_ref(ops_list, op, mode, role, app_controller=self)

    def _move_op_down_by_ref(self, ops_list: list, op: dict, mode: str, role: Optional[dict] = None):
        OpsListBuilder.move_op_down_by_ref(ops_list, op, mode, role, app_controller=self)

    def _refresh_ops_ui(self, ops_list: list, mode: str, role: Optional[dict] = None):
        OpsListBuilder.refresh_ops_ui(ops_list, mode, role, app_controller=self)

    def _on_op_type_change(self, op: dict, mode: str):
        OpsListBuilder.on_op_type_change(op, mode)

    def _get_role_context(self, mode: str):
        if mode == "advanced":
            return (
                self.adv_roles, self.middle_col.adv_roles_container,
                self.add_advanced_role, self.remove_advanced_role,
                self.move_advanced_role_up, self.move_advanced_role_down,
            )
        else:
            return (
                self.condition_roles, self.middle_col.condition_roles_container,
                self.add_condition_role, self.remove_condition_role,
                self.move_condition_role_up, self.move_condition_role_down,
            )

    def refresh_roles_ui(self, mode: str):
        roles, container, add_fn, remove_fn, up_fn, down_fn = self._get_role_context(mode)
        RoleListManager.refresh_roles_ui(
            roles_list=roles, container=container, mode=mode,
            on_add=add_fn, on_remove=remove_fn, on_up=up_fn, on_down=down_fn,
            app_controller=self
        )

    def add_character_operation(self): self.left_col.char_sim_card.add_operation()
    def add_regular_operation(self): self._add_op(self.reg_ops, len(self.reg_ops) - 1, "regular")

    # --- 常規操作列表：具名存檔／匯入（內嵌工具列，無彈窗） ---
    def get_regular_ops_preset_names(self) -> List[str]:
        return regular_ops_service.get_names()

    def save_regular_ops_preset_as(self, name: str):
        ops_data = [registry.extract_params(op) for op in self.reg_ops]
        regular_ops_service.set_preset(name, ops_data)

    def import_regular_ops_preset(self, name: str):
        ops_data = regular_ops_service.get_preset(name)
        if not ops_data:
            return
        new_ops = [self._hydrate_op(op) for op in ops_data]
        if not new_ops:
            return
        self.reg_ops.clear()
        self.reg_ops.extend(new_ops)
        OpsListBuilder.refresh_ops_ui(self.reg_ops, "regular", app_controller=self)

    def delete_regular_ops_preset(self, name: str):
        regular_ops_service.delete_preset(name)

    # --- 高級模式角色定義：具名存檔／匯入（內嵌工具列，無彈窗） ---
    def get_advanced_roles_preset_names(self) -> List[str]:
        return advanced_roles_service.get_names()

    def save_advanced_roles_preset_as(self, name: str):
        roles_data = [
            {"soul": role["soul_var"].get(), "ops": [registry.extract_params(op) for op in role["ops"]]}
            for role in self.adv_roles
        ]
        advanced_roles_service.set_preset(name, roles_data)

    def import_advanced_roles_preset(self, name: str):
        roles_data = advanced_roles_service.get_preset(name)
        if not roles_data:
            return

        new_roles = []
        for item in roles_data:
            ops = [self._hydrate_op(op) for op in item.get("ops", [])]
            if not ops:
                ops = [self._hydrate_op({"type": "普通傷害"})]
            new_roles.append({
                "soul_var": tk.IntVar(value=item.get("soul", 3)),
                "ops": ops, "frame": None, "ops_frame": None
            })
        if not new_roles:
            return

        self.adv_roles.clear()
        self.adv_roles.extend(new_roles)
        self.refresh_roles_ui("advanced")
        self.update_plan_role_options()

    def delete_advanced_roles_preset(self, name: str):
        advanced_roles_service.delete_preset(name)

    def clear_advanced_roles(self):
        """清空所有已定義的角色，還原成單一個空白角色"""
        self.adv_roles.clear()
        role_data = {"soul_var": tk.IntVar(value=3), "ops": [], "frame": None, "ops_frame": None}
        self.adv_roles.append(role_data)
        self.refresh_roles_ui("advanced")
        self._add_op(role_data["ops"], -1, "advanced", role=role_data)
        self.update_plan_role_options()

    def add_advanced_role(self, insert_index: Optional[int] = None):
        if insert_index is not None and 0 <= insert_index < len(self.adv_roles):
            # 🌟 「+」是在複製該角色：連同它目前的初始魂點與已配置的操作效果一起複製
            source_role = self.adv_roles[insert_index]
            role_data = {
                "soul_var": tk.IntVar(value=source_role["soul_var"].get()),
                "ops": [OpsListBuilder.clone_op(op) for op in source_role["ops"]],
                "frame": None, "ops_frame": None
            }
            idx = insert_index + 1
        else:
            role_data = {"soul_var": tk.IntVar(value=3), "ops": [], "frame": None, "ops_frame": None}
            idx = len(self.adv_roles)

        self.adv_roles.insert(idx, role_data)
        self.refresh_roles_ui("advanced")
        if not role_data["ops"]:
            self._add_op(role_data["ops"], -1, "advanced", role=role_data)
        self.update_plan_role_options()

    def remove_advanced_role(self, index: int):
        if len(self.adv_roles) <= 1: return
        del self.adv_roles[index]
        self.refresh_roles_ui("advanced")
        self.update_plan_role_options()

    def move_advanced_role_up(self, index: int):
        if index > 0:
            self.adv_roles[index], self.adv_roles[index - 1] = self.adv_roles[index - 1], self.adv_roles[index]
            self.refresh_roles_ui("advanced")
            self.update_plan_role_options()

    def move_advanced_role_down(self, index: int):
        if index < len(self.adv_roles) - 1:
            self.adv_roles[index], self.adv_roles[index + 1] = self.adv_roles[index + 1], self.adv_roles[index]
            self.refresh_roles_ui("advanced")
            self.update_plan_role_options()

    def add_condition_role(self, insert_index: Optional[int] = None):
        idx = len(self.condition_roles) if insert_index is None else insert_index + 1
        role_data = {"soul_var": tk.IntVar(value=3), "ops": [], "frame": None, "ops_frame": None}
        self.condition_roles.insert(idx, role_data)
        self.refresh_roles_ui("condition")
        self._add_op(role_data["ops"], -1, "condition", role=role_data)
        self.update_condition_plan_role_options()

    def remove_condition_role(self, index: int):
        if len(self.condition_roles) <= 1: return
        del self.condition_roles[index]
        self.refresh_roles_ui("condition")
        self.update_condition_plan_role_options()

    def move_condition_role_up(self, index: int):
        if index > 0:
            self.condition_roles[index], self.condition_roles[index - 1] = self.condition_roles[index - 1], self.condition_roles[index]
            self.refresh_roles_ui("condition")
            self.update_condition_plan_role_options()

    def move_condition_role_down(self, index: int):
        if index < len(self.condition_roles) - 1:
            self.condition_roles[index], self.condition_roles[index + 1] = self.condition_roles[index + 1], self.condition_roles[index]
            self.refresh_roles_ui("condition")
            self.update_condition_plan_role_options()

    def _get_plan_context(self, mode: str):
        if mode == "advanced":
            return (
                self.plan_steps, self.adv_roles, self.middle_col.plan_list_frame,
                self.add_plan_step, self.remove_plan_step, self.move_plan_step_up, self.move_plan_step_down,
            )
        else:
            return (
                self.condition_plan_steps, self.condition_roles, self.middle_col.condition_plan_list_frame,
                self.add_condition_plan_step, self.remove_condition_plan_step,
                self.move_condition_plan_step_up, self.move_condition_plan_step_down,
            )

    def refresh_plan_ui_generic(self, mode: str):
        steps, roles, container, add_fn, remove_fn, up_fn, down_fn = self._get_plan_context(mode)
        PlanStepManager.refresh_plan_ui(
            steps_list=steps, roles_list=roles, container=container,
            on_add=add_fn, on_remove=remove_fn, on_up=up_fn, on_down=down_fn
        )

    def add_plan_step(self, insert_index: Optional[int] = None):
        idx = len(self.plan_steps) if insert_index is None else insert_index + 1
        step = {"role_var": tk.StringVar(value=""), "start_var": tk.IntVar(value=1), "end_var": tk.IntVar(value=1), "role_combo": None}
        self.plan_steps.insert(idx, step)
        self.refresh_plan_ui_generic("advanced")

    def remove_plan_step(self, index: int):
        if 0 <= index < len(self.plan_steps):
            del self.plan_steps[index]
            self.refresh_plan_ui_generic("advanced")

    def move_plan_step_up(self, index: int):
        if index > 0:
            self.plan_steps[index], self.plan_steps[index - 1] = self.plan_steps[index - 1], self.plan_steps[index]
            self.refresh_plan_ui_generic("advanced")

    def move_plan_step_down(self, index: int):
        if index < len(self.plan_steps) - 1:
            self.plan_steps[index], self.plan_steps[index + 1] = self.plan_steps[index + 1], self.plan_steps[index]
            self.refresh_plan_ui_generic("advanced")

    def clear_plan(self):
        self.plan_steps.clear()
        self.refresh_plan_ui_generic("advanced")

    def update_plan_role_options(self):
        PlanStepManager.update_role_options(self.plan_steps, self.adv_roles)

    def add_condition_plan_step(self, insert_index: Optional[int] = None):
        idx = len(self.condition_plan_steps) if insert_index is None else insert_index + 1
        step = {"role_var": tk.StringVar(value=""), "start_var": tk.IntVar(value=1), "end_var": tk.IntVar(value=1), "role_combo": None}
        self.condition_plan_steps.insert(idx, step)
        self.refresh_plan_ui_generic("condition")

    def remove_condition_plan_step(self, index: int):
        if 0 <= index < len(self.condition_plan_steps):
            del self.condition_plan_steps[index]
            self.refresh_plan_ui_generic("condition")

    def move_condition_plan_step_up(self, index: int):
        if index > 0:
            self.condition_plan_steps[index], self.condition_plan_steps[index - 1] = self.condition_plan_steps[index - 1], self.condition_plan_steps[index]
            self.refresh_plan_ui_generic("condition")

    def move_condition_plan_step_down(self, index: int):
        if index < len(self.condition_plan_steps) - 1:
            self.condition_plan_steps[index], self.condition_plan_steps[index + 1] = self.condition_plan_steps[index + 1], self.condition_plan_steps[index]
            self.refresh_plan_ui_generic("condition")

    def clear_condition_plan(self):
        self.condition_plan_steps.clear()
        self.refresh_plan_ui_generic("condition")

    def update_condition_plan_role_options(self):
        PlanStepManager.update_role_options(self.condition_plan_steps, self.condition_roles)

    # =========================================================================
    # 4. 戰局與畫布實時更新 (Canvas & State Formatting)
    # =========================================================================

    def refresh_field_canvas_stats(self):
        if not hasattr(self, "middle_col") or not hasattr(self.middle_col, "field_component"):
            return

        stats = {}
        for zone_name in ["牌組", "控制室", "能量", "思出"]:
            cards = self.condition_zones.get(zone_name, [])
            normal = sum(1 for c in cards if card_is_normal(c))
            climax = sum(1 for c in cards if card_is_climax(c))
            soul1 = sum(1 for c in cards if get_card_trigger_soul(c) == 1)
            soul2 = sum(1 for c in cards if get_card_trigger_soul(c) == 2)

            stats[zone_name] = {
                "cx": climax, "chara": normal, "soul1": soul1, "soul2": soul2, "total": len(cards)
            }

        single_zone_cards = {}
        single_zones = [
            "前列1", "前列2", "前列3", "後列1", "後列2",
            "傷害1", "傷害2", "傷害3", "傷害4", "傷害5", "傷害6",
            "等級1", "等級2", "等級3", "等級4", "CX",
            "敵前列1", "敵前列2", "敵前列3"
        ]
        for zn in single_zones:
            cards = self.condition_zones.get(zn, [])
            single_zone_cards[zn] = cards[0] if cards else None

        self.middle_col.field_component.set_all_zone_stats(stats, single_zone_cards)

    def _format_zone_state(self, deck, control, stock, level, clock) -> list:
        deck_cx = sum(1 for c in deck if card_is_climax(c))
        deck_normal = sum(1 for c in deck if card_is_normal(c))

        stock_cx = sum(1 for c in stock if card_is_climax(c))
        stock_normal = sum(1 for c in stock if card_is_normal(c))

        control_cx = sum(1 for c in control if card_is_climax(c))
        control_normal = sum(1 for c in control if card_is_normal(c))

        deck_pos = [i + 1 for i, c in enumerate(deck) if card_is_climax(c)]
        stock_pos = [i + 1 for i, c in enumerate(stock) if card_is_climax(c)]

        def format_cards_display(z):
            if not z: return "空"
            cards = [card for slot in z.values() for card in slot] if isinstance(z, dict) else z
            return " → ".join(["潮" if card_is_climax(c) else "肉" for c in cards]) if cards else "空"

        return [
            f"牌組: 潮{deck_cx}張，肉{deck_normal}張，共{len(deck)}張",
            f"牌組潮位置(底起): {', '.join(map(str, deck_pos)) if deck_pos else '無'}",
            f"能量區: 潮{stock_cx}張，肉{stock_normal}張，共{len(stock)}張",
            f"能量區潮位置(底起): {', '.join(map(str, stock_pos)) if stock_pos else '無'}",
            f"控制室: 潮{control_cx}張，肉{control_normal}張，共{len(control)}張",
            f"等級區(底→頂): {format_cards_display(level)}",
            f"傷害區(底→頂): {format_cards_display(clock)}",
        ]

    def show_condition_overview(self):
        win = ctk.CTkToplevel(self.root)
        win.title("場上情況概覽")
        win.geometry("520x600")
        win.configure(fg_color=PALETTE["bg_main"])

        win.after(10, lambda: win.lift())
        win.after(50, lambda: win.focus_force())

        text = ctk.CTkTextbox(
            win, wrap="word", font=FONT_GLOBAL, fg_color=PALETTE["card_bg"], text_color=PALETTE["text_main"]
        )
        text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        def count_cards(cards):
            normal = sum(1 for c in cards if card_is_normal(c))
            climax = sum(1 for c in cards if card_is_climax(c))
            return normal, climax, len(cards)

        def climax_positions_top(cards):
            positions = []
            n = len(cards)
            for i, c in enumerate(cards):
                if card_is_climax(c):
                    positions.append(n - i)
            return positions

        lines = []
        n, c, t = count_cards(self.condition_deck_cards)
        pos = climax_positions_top(self.condition_deck_cards)
        pos_str = ", ".join(map(str, pos)) if pos else "無"
        lines.append(f"牌組：潮{c}張，肉{n}張，共{t}張，潮位置(頂起)：{pos_str}")

        n, c, t = count_cards(self.condition_control_cards)
        lines.append(f"控制室：潮{c}張，肉{n}張，共{t}張")

        n, c, t = count_cards(self.condition_stock_cards)
        pos = climax_positions_top(self.condition_stock_cards)
        pos_str = ", ".join(map(str, pos)) if pos else "無"
        lines.append(f"能量區：潮{c}張，肉{n}張，共{t}張，潮位置(頂起)：{pos_str}")

        n, c, t = count_cards(self.condition_memory_cards)
        lines.append(f"思出區：潮{c}張，肉{n}張，共{t}張\n")

        for i in range(1, 4):
            cards = self.condition_front_cards[f"前列{i}"]
            detail = f"卡名:{cards[0].get('name','無')} 等級:{cards[0].get('level','0')} 力量:{cards[0].get('power','500')}" if cards else "空"
            lines.append(f"前列{i}：{detail}")

        for i in range(1, 3):
            cards = self.condition_back_cards[f"後列{i}"]
            detail = f"卡名:{cards[0].get('name','無')} 等級:{cards[0].get('level','0')} 力量:{cards[0].get('power','500')}" if cards else "空"
            lines.append(f"後列{i}：{detail}")

        cx_cards = self.condition_cx_cards
        detail = f"種類:{cx_cards[0].get('kind','無')} 觸發:{cx_cards[0].get('trigger','無')}" if cx_cards else "空"
        lines.append(f"CX區：{detail}\n")

        level_order = ["等級1", "等級2", "等級3", "等級4"]
        level_display = [self.condition_level_cards[k][0].get("kind", "無") for k in level_order if self.condition_level_cards[k]]
        lines.append(f"等級區(底→頂)：{' → '.join(level_display) if level_display else '空'}")

        clock_order = [f"傷害{i}" for i in range(1, 8)]
        clock_display = [self.condition_clock_cards[k][0].get("kind", "無") for k in clock_order if self.condition_clock_cards[k]]
        lines.append(f"傷害區(底→頂)：{' → '.join(clock_display) if clock_display else '空'}")

        text.insert(tk.END, "\n".join(lines))
        text.configure(state="disabled")

    # =========================================================================
    # 5. 模擬引擎調度與解析入口 (Simulation Runners)
    # =========================================================================

    def _get_fixed_state_params(self) -> dict:
        return GameEnvironmentFactory.extract_fixed_params(self.left_col)

    def _build_initial_state(self, fixed: dict) -> tuple:
        return GameEnvironmentFactory.build_initial_state(fixed)

    def _get_advanced_execution_plan(self) -> tuple:
        return PlanParser.parse_execution_plan(self.adv_roles, self.plan_steps)

    def _get_condition_execution_plan(self) -> tuple:
        return PlanParser.parse_execution_plan(self.condition_roles, self.condition_plan_steps)

    def execute_single(self):
        fixed = self._get_fixed_state_params()
        deck, control, stock, level, clock = self._build_initial_state(fixed)

        before_deck, before_control = deck.copy(), control.copy()
        before_stock, before_level, before_clock = stock.copy(), level.copy(), clock.copy()

        op_params = self.left_col.single_op_card.get_op_params()
        opt = op_params["type"]

        stabilize_func = lambda: stabilize(deck, control, level, clock)
        game_over, msg, extra = registry.execute(
            opt, deck, control, stock, level, clock, op_params, stabilize_func
        )

        b_lines = self._format_zone_state(before_deck, before_control, before_stock, before_level, before_clock)
        a_lines = self._format_zone_state(deck, control, stock, level, clock)

        self.right_col.render_single_op_result(msg, game_over, b_lines, a_lines)

    def execute_character_sim(self):
        self.right_col.notebook.select(self.right_col.char_tab)

        fixed = self._get_fixed_state_params()
        deck, control, stock, level, clock = self._build_initial_state(fixed)
        b_lines = self._format_zone_state(deck, control, stock, level, clock)

        soul_points = self.left_col.char_sim_card.get_soul()
        ops_params = self.left_col.char_sim_card.get_ops_params()

        role_state = {"soul": soul_points, "abilities": [], "ice_armors": []}
        pending_pass = {}

        game_over, total_damage, steps_info = SimulationRunner.simulate_role_ops_segment(
            deck, control, stock, level, clock,
            role_state, ops_params, 0, len(ops_params) - 1,
            pending_pass, role_idx=0, num_roles=1, collect_steps=True
        )

        self.right_col.render_char_results(
            steps_info=steps_info, game_over=game_over, before_lines=b_lines, format_zone_func=self._format_zone_state
        )

    def run_regular_simulation(self):
        self.right_col.notebook.select(self.right_col.multi_tab)
        sim_times = self.middle_col.reg_sim_times.get()
        if sim_times <= 0: return

        ops_params = [registry.extract_params(op) for op in self.reg_ops]
        fixed = self._get_fixed_state_params()
        level_meat = sum(1 for v in self.left_col.level_vars if v.get() == "肉")
        clock_meat = sum(1 for v in self.left_col.clock_vars if v.get() == "肉")

        self.middle_col.reg_progress_bar["maximum"] = sim_times
        self.middle_col.reg_progress_bar["value"] = 0

        SimulationRunner.run_regular_simulation_async(
            sim_times=sim_times, ops_params=ops_params, fixed_params=fixed,
            level_meat=level_meat, clock_meat=clock_meat,
            on_progress=lambda current, pct: self.root.after(
                0, lambda: self._update_progress(self.middle_col.reg_progress_bar, self.middle_col.reg_progress_label, current, pct)
            ),
            on_done=lambda winrate, avg_dmg, elapsed: self.root.after(
                0, lambda: self._on_sim_done(winrate, avg_dmg, elapsed, sim_times)
            ),
            on_error=lambda err: self.root.after(
                0, lambda: messagebox.showerror("模擬異常", f"多次模擬中途發生錯誤:\n{err}")
            )
        )

    def run_advanced_simulation(self):
        self.right_col.notebook.select(self.right_col.multi_tab)
        sim_times = self.middle_col.adv_sim_times.get()
        if sim_times <= 0: return

        execution_plan, roles_params = self._get_advanced_execution_plan()
        fixed = self._get_fixed_state_params()
        level_meat = sum(1 for v in self.left_col.level_vars if v.get() == "肉")
        clock_meat = sum(1 for v in self.left_col.clock_vars if v.get() == "肉")

        self.middle_col.adv_progress_bar["maximum"] = sim_times
        self.middle_col.adv_progress_bar["value"] = 0

        SimulationRunner.run_advanced_simulation_async(
            sim_times=sim_times, execution_plan=execution_plan, roles_params=roles_params,
            fixed_params=fixed, level_meat=level_meat, clock_meat=clock_meat,
            on_progress=lambda current, pct: self.root.after(
                0, lambda: self._update_progress(self.middle_col.adv_progress_bar, self.middle_col.adv_progress_label, current, pct)
            ),
            on_done=lambda winrate, avg_dmg, elapsed: self.root.after(
                0, lambda: self._on_sim_done(winrate, avg_dmg, elapsed, sim_times)
            ),
            on_error=lambda err: self.root.after(
                0, lambda: messagebox.showerror("模擬異常", f"高級模式模擬錯誤:\n{err}")
            )
        )

    def run_condition_simulation(self):
        self.right_col.notebook.select(self.right_col.multi_tab)
        sim_times = self.middle_col.cond_sim_times.get()
        if sim_times <= 0: return

        execution_plan, roles_params = self._get_condition_execution_plan()
        fixed = self._get_fixed_state_params()
        level_meat = sum(1 for v in self.left_col.level_vars if v.get() == "肉")
        clock_meat = sum(1 for v in self.left_col.clock_vars if v.get() == "肉")

        self.middle_col.cond_progress_bar["maximum"] = sim_times
        self.middle_col.cond_progress_bar["value"] = 0

        SimulationRunner.run_condition_simulation_async(
            sim_times=sim_times, execution_plan=execution_plan, roles_params=roles_params,
            fixed_params=fixed, level_meat=level_meat, clock_meat=clock_meat,
            condition_deck_cards=self.condition_deck_cards,
            condition_control_cards=self.condition_control_cards,
            condition_stock_cards=self.condition_stock_cards,
            condition_level_cards=self.condition_level_cards,
            condition_clock_cards=self.condition_clock_cards,
            condition_front_cards=self.condition_front_cards,
            enemy_front_roles=self.enemy_front_roles,
            on_progress=lambda current, pct: self.root.after(
                0, lambda: self._update_progress(self.middle_col.cond_progress_bar, self.middle_col.cond_progress_label, current, pct)
            ),
            on_done=lambda winrate, avg_dmg, elapsed: self.root.after(
                0, lambda: self._on_sim_done(winrate, avg_dmg, elapsed, sim_times)
            ),
            on_error=lambda err: self.root.after(
                0, lambda: messagebox.showerror("模擬異常", f"工況模式模擬錯誤:\n{err}")
            )
        )

    def run_advanced_single_test(self):
        fixed = self._get_fixed_state_params()
        deck, control, stock, level, clock = self._build_initial_state(fixed)
        execution_plan, roles_params = self._get_advanced_execution_plan()

        all_steps = []
        game_over = False
        pending_pass = {}
        global_ice_armors = []
        role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

        for role_idx, start_idx, end_idx in execution_plan:
            if game_over: break
            state = role_states[role_idx]
            over, dmg, steps = SimulationRunner.simulate_role_ops_segment(
                deck, control, stock, level, clock,
                state, state["ops"], start_idx, end_idx,
                pending_pass, role_idx, len(roles_params),
                collect_steps=True, global_ice_armors=global_ice_armors
            )
            all_steps.extend(steps)
            if over: game_over = True

        self._show_single_test_log_window("高級模式單次測試日誌", all_steps, game_over)

    def run_condition_single_test(self):
        fixed = self._get_fixed_state_params()
        deck, control, stock, level, clock = self._build_initial_state(fixed)

        cond_deck = clone_card_list(self.condition_deck_cards)
        random.shuffle(cond_deck)
        
        cond_control = clone_card_list(self.condition_control_cards)
        cond_stock = clone_card_list(self.condition_stock_cards)
        cond_level = copy.deepcopy(self.condition_level_cards)
        cond_clock = copy.deepcopy(self.condition_clock_cards)

        cond_helper = TrialConditionHelper(cond_deck, cond_control, cond_stock, cond_level, cond_clock)

        if cond_helper.stabilize_condition():
            self._show_single_test_log_window("工況模式單次測試日誌", [], game_over=False, our_failed=True)
            return

        execution_plan, roles_params = self._get_condition_execution_plan()

        all_steps = []
        game_over = False
        pending_pass = {}
        global_ice_armors = []

        local_enemy_front = {}
        for k, v in self.enemy_front_roles.items():
            lval = v["level"].get() if hasattr(v["level"], "get") else v["level"]
            pval = v["power"].get() if hasattr(v["power"], "get") else v["power"]
            local_enemy_front[k] = {"level": lval, "power": pval, "is_reversed": False}

        role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

        for role_idx, start_idx, end_idx in execution_plan:
            if game_over or cond_helper.failed: break
            state = role_states[role_idx]
            over, dmg, steps = SimulationRunner.simulate_role_ops_segment(
                deck, control, stock, level, clock,
                state, state["ops"], start_idx, end_idx,
                pending_pass, role_idx, len(roles_params),
                collect_steps=True, global_ice_armors=global_ice_armors,
                condition_deck=cond_helper.cond_deck, condition_stock=cond_helper.cond_stock, app=cond_helper,
                front_slot=f"前列{role_idx+1}",
                enemy_front_roles=local_enemy_front
            )
            all_steps.extend(steps)
            if over: game_over = True

        if not game_over and not cond_helper.failed:
            for front_key in ["前列1", "前列2", "前列3"]:
                if game_over or cond_helper.failed: break
                f_cards = self.condition_front_cards.get(front_key, [])
                if f_cards:
                    c_card = f_cards[0]
                    c_over, c_dmg, c_steps = SimulationRunner.simulate_custom_card_attack_pipeline(
                        deck, control, stock, level, clock,
                        c_card, front_key, local_enemy_front,
                        pending_pass, collect_steps=True, global_ice_armors=global_ice_armors,
                        cond_helper=cond_helper
                    )
                    all_steps.extend(c_steps)
                    if c_over: game_over = True

        self._show_single_test_log_window("工況模式單次測試日誌", all_steps, game_over, our_failed=cond_helper.failed)

    def _show_single_test_log_window(self, title: str, steps_info: list, game_over: bool, our_failed: bool = False):
        test_type = "高級" if "高級" in title else ("工況" if "工況" in title else "常規")
        fixed = self._get_fixed_state_params()
        deck, control, stock, level, clock = self._build_initial_state(fixed)
        b_lines = self._format_zone_state(deck, control, stock, level, clock)

        self.right_col.render_single_test_results(
            test_type=test_type, steps_info=steps_info, game_over=game_over, our_failed=our_failed,
            before_lines=b_lines, format_zone_func=self._format_zone_state
        )

    def _update_progress(self, progress_bar: Any, progress_label: Any, current: int, pct: int):
        if hasattr(progress_bar, "set"): progress_bar.set(pct / 100.0)
        else: progress_bar["value"] = current
            
        if hasattr(progress_label, "configure"): progress_label.configure(text=f"{pct}%")
        else: progress_label.config(text=f"{pct}%")

    def _on_sim_done(self, winrate: float, avg_dmg: float, elapsed: float, sim_times: int):
        self.right_col.multi_winrate_label.configure(text=f"斬殺率: {winrate:.2f}%")
        self.right_col.multi_avg_damage_label.configure(text=f"平均傷害: {avg_dmg:.2f}")

        lower, upper = calc_wilson_score_interval(winrate, sim_times)
        diff_threshold = calc_significant_difference_threshold(winrate, sim_times)

        self.right_col.multi_ci_label.configure(text=f"95%置信區間: [{lower:.2f}%, {upper:.2f}%]")
        self.right_col.multi_diff_label.configure(text=f"顯著差異最小差值: {diff_threshold:.2f} 個百分點")
        self.right_col.multi_time_label.configure(text=f"運行時間: {format_elapsed_time(elapsed)}")

    # =========================================================================
    # 6. 狀態持久化與彈窗路由 (Persistence & Dialog Openers)
    # =========================================================================

    def save_condition_state(self):
        enemy_front_serialized = {}
        for k, v in self.enemy_front_roles.items():
            lval = v["level"].get() if hasattr(v["level"], "get") else v["level"]
            pval = v["power"].get() if hasattr(v["power"], "get") else v["power"]
            enemy_front_serialized[k] = {"level": str(lval), "power": int(pval or 500)}

        roles_serialized = [
            {"soul": role["soul_var"].get(), "ops": [registry.extract_params(op) for op in role["ops"]]}
            for role in self.condition_roles
        ]
        plan_serialized = [
            {"role": step["role_var"].get(), "start": step["start_var"].get(), "end": step["end_var"].get()}
            for step in self.condition_plan_steps
        ]

        data = condition_state_service.serialize_data(
            enemy_front_serialized, roles_serialized, plan_serialized
        )
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("保存成功", "場上情況與工況配置已成功保存至 JSON 文件。")
            except Exception as e:
                messagebox.showerror("保存失敗", f"保存 JSON 文件失敗：\n{e}")

    def load_condition_state(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            condition_state_service.deserialize_data(data)

            if "enemy_front_roles" in data and isinstance(data["enemy_front_roles"], dict):
                field_enemy_roles = getattr(self.middle_col.field_component, "enemy_front_roles", {})
                for k, v in data["enemy_front_roles"].items():
                    if k in field_enemy_roles:
                        lval = str(v.get("level", "0"))
                        pval = int(v.get("power", 500))
                        if hasattr(field_enemy_roles[k]["level"], "set"): field_enemy_roles[k]["level"].set(lval)
                        if hasattr(field_enemy_roles[k]["power"], "set"): field_enemy_roles[k]["power"].set(pval)

            if "roles" in data and isinstance(data["roles"], list) and data["roles"]:
                self.condition_roles.clear()
                for rdata in data["roles"]:
                    role_obj = {
                        "soul_var": tk.IntVar(value=rdata.get("soul", 3)),
                        "ops": [], "frame": None, "ops_frame": None
                    }
                    self.condition_roles.append(role_obj)
                    ops_list = rdata.get("ops", [])
                    if ops_list:
                        for raw_op in ops_list:
                            ui_op = self._hydrate_op(raw_op)
                            role_obj["ops"].append(ui_op)
                    else:
                        self._add_op(role_obj["ops"], -1, "condition", role=role_obj)

                self.refresh_condition_roles_ui()  # 🌟 現在這個別名方法已補全

            # 5. 恢復中欄執行計劃步驟
            if "plan" in data and isinstance(data["plan"], list):
                self.condition_plan_steps.clear()
                for pdata in data["plan"]:
                    step_obj = {
                        "role_var": tk.StringVar(value=pdata.get("role", "")),
                        "start_var": tk.IntVar(value=pdata.get("start", 1)),
                        "end_var": tk.IntVar(value=pdata.get("end", 1)),
                        "role_combo": None
                    }
                    self.condition_plan_steps.append(step_obj)
                self.refresh_condition_plan_ui() 

            self.middle_col.field_component.canvas.event_generate("<Configure>")
            self.refresh_field_canvas_stats()
            messagebox.showinfo("導入成功", "場上情況與工況配置已成功導入。")
        except Exception as e:
            messagebox.showerror("導入失敗", f"讀取 JSON 文件失敗：\n{e}")

    def _hydrate_op(self, raw_op: dict) -> dict:
        """🌟 修復版水化反序列化函數：精準映射 steps_ops 與 nested_ops，確保多步驟操作的詳細配置不丟失"""
        if not isinstance(raw_op, dict):
            return {"type_var": tk.StringVar(value="普通傷害"), "controls": {}, "params": {}}

        if "type_var" in raw_op and isinstance(raw_op["type_var"], tk.StringVar):
            return raw_op

        type_name = raw_op.get("type", "普通傷害")
        ui_op = {"type_var": tk.StringVar(value=type_name), "controls": {}, "params": {}}

        for key, val in raw_op.items():
            if key == "type":
                continue

            # 🌟 關鍵修復：特規映射 steps -> steps_ops 和 nested_ops -> nested_ops
            if key == "steps":
                hydrated_steps = [self._hydrate_op(sub) for sub in val] if isinstance(val, list) else []
                ui_op["params"]["steps_ops"] = hydrated_steps
                ui_op["params"]["step_count_var"] = tk.IntVar(value=max(1, len(hydrated_steps)))
            elif key == "nested_ops":
                hydrated_nested = [self._hydrate_op(sub) for sub in val] if isinstance(val, list) else []
                ui_op["params"]["nested_ops"] = hydrated_nested
                ui_op["params"]["total_triggers_var"] = tk.IntVar(value=max(1, len(hydrated_nested)))
            elif key == "nested_op":
                ui_op["params"]["nested_op"] = self._hydrate_op(val) if isinstance(val, dict) else val
            else:
                var_name = f"{key}_var" if not key.endswith("_var") else key
                if isinstance(val, bool): ui_op["params"][var_name] = tk.BooleanVar(value=val)
                elif isinstance(val, int): ui_op["params"][var_name] = tk.IntVar(value=val)
                elif isinstance(val, float): ui_op["params"][var_name] = tk.DoubleVar(value=val)
                elif isinstance(val, str): ui_op["params"][var_name] = tk.StringVar(value=val)
                elif isinstance(val, list): ui_op["params"][var_name] = val
                elif isinstance(val, dict): ui_op["params"][var_name] = val

        return ui_op

    def open_card_detail_window(self, source_name: str):
        if source_name not in self.condition_zones: return
        CardTableDialog(self.root, source_name=source_name, app_controller=self)

    def open_batch_statistics(self):
        BatchStatisticsDialog(self.root, app_controller=self)

    def open_decision_tree_dialog(self):
        DecisionTreeDialog(self.root, app_controller=self)

    def open_custom_cards_dialog(self):
        CustomCardsDialog(self.root, app_controller=self)

    def open_ai_manual(self):
        webbrowser.open("manual.html")

    def show_author_notes(self):
        messagebox.showinfo("作者說明", "試製 二六式黑白雙翼模擬器 ver.0.3\n作者: Sillyslark\n重構完備版。")