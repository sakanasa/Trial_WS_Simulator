# -*- coding: utf-8 -*-
"""
自定义卡片编辑器与选择弹窗 (Custom Cards Dialog & Selector) - CustomTkinter 浅色适配版
支持单卡/整库导入导出、手动保存、卡片上下位置调整及持久化自动写盘。
"""

import os
import json
import copy
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from typing import Any, List, Dict, Optional, Callable

from utils.registry import registry, safe_trace
from ui.components.app_dropdown import AppDropdown

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD

from ui.dialogs.select_from_library_dialog import SelectFromLibraryDialog

from ui.components.common.effect_formatter import format_operation

class CustomCardsDialog(ctk.CTkToplevel):
    """自定义卡片管理与编辑器对话框类"""

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("WS 自定义卡片编辑器 ver.1.3")
        self.geometry("1100x780+80+60")
        
        # 🌟 1. 设置自适应大背景色，消除硬编码 #F8FAFC
        self.configure(fg_color=PALETTE["bg_main"])

        # 🌟 强制置顶与焦点修复
        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        if hasattr(self.app, "custom_cards_data") and self.app.custom_cards_data:
            self.cards_data = self.app.custom_cards_data
        else:
            self.cards_data = [
                {
                    "name": "示例·早川秋 (角色)",
                    "type": "角色",
                    "level": 3, "cost": 2, "power": 10000, "soul": 2,
                    "trigger": "魂", "trigger_soul": 1,
                    "effects": {
                        "pre_attack": [],
                        "attack_type": [{"type": "攻击方式", "attack_type": "正面"}],
                        "on_attack": [{"type": "摩卡", "mocha_mode": "原位", "mocha_count": 2}],
                        "trigger_step": [{"type": "工况判定"}],
                        "deal_damage": [{"type": "角色伤害", "role_damage_base": 0, "role_bonus_type": "魂点", "trigger_rate": 0.0}],
                        "on_reverse": [{"type": "普通伤害", "damage": 2, "trigger_rate": 0.0}],
                        "post_attack": []
                    }
                }
            ]
            if hasattr(self.app, "custom_cards_data"):
                self.app.custom_cards_data = self.cards_data

        self.current_card_index: int = 0
        self.phase_ops: Dict[str, List[dict]] = {}
        self.card_buttons: List[ctk.CTkButton] = []  # 🌟 记录 CTk 列表项按钮引用

        self._init_variables()
        self._build_ui()
        self._load_card_to_editor(0)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_op_type_change(self, op: dict):
        """当下拉框切换操作类型时，重置参数并重新渲染对应的 UI"""
        op["params"].clear()
        op["controls"].clear()
        registry.build_widgets(
            op, 
            op["params_frame"], 
            op["linkage_frame"], 
            op.get("cancel_detail_frame"), 
            "condition", 
            op.get("steps_frame")
        )
        self._update_card_preview()

    def _sync_to_app(self):
        """同步数据至 App 控制器，并通知主界面刷新卡牌下拉框与算卡选择器"""
        if hasattr(self.app, "custom_cards_data"):
            self.app.custom_cards_data = self.cards_data
        if hasattr(self.app, "save_custom_cards_data"):
            self.app.save_custom_cards_data()

        # 🌟 自动触发主界面的刷新函数（兼容多种主程序刷新接口）
        for refresh_method in ("refresh_custom_cards_ui", "refresh_ui", "load_custom_cards", "update_card_dropdowns"):
            if hasattr(self.app, refresh_method):
                try:
                    getattr(self.app, refresh_method)()
                except Exception as e:
                    print(f"[WARN] 触发主界面卡库刷新接口 {refresh_method} 提示: {e}")

    def _manual_save_cards(self):
        """手动保存卡库数据，并刷新编辑器与左侧列表"""
        self._save_editor_to_card(self.current_card_index)
        self._sync_to_app()
        # 🌟 重新渲染左侧卡片列表与右侧效果预览
        self._refresh_card_listbox()
        self._update_card_preview()
        messagebox.showinfo("保存成功", "当前卡库数据已成功保存并刷新！", parent=self)

    def _on_close(self):
        self._save_editor_to_card(self.current_card_index)
        self._sync_to_app()
        self.destroy()

    def _init_variables(self):
        self.var_name = tk.StringVar(value="")
        self.var_type = tk.StringVar(value="角色")
        self.var_level = tk.IntVar(value=0)
        self.var_cost = tk.IntVar(value=0)
        self.var_power = tk.IntVar(value=0)
        self.var_soul = tk.IntVar(value=1)
        self.var_trigger = tk.StringVar(value="无")
        self.var_trigger_soul = tk.IntVar(value=0)

        for var in (self.var_name, self.var_type, self.var_level, self.var_cost, self.var_power, self.var_soul, self.var_trigger, self.var_trigger_soul):
            var.trace("w", lambda *a: self._update_card_preview())

    def _build_ui(self):
        """🌟 全量 CTk 统一组件与自适应配色重构（已修复布局挤压问题）"""
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        main_pane = ctk.CTkFrame(self, fg_color="transparent")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # -------------------------------------------------------------
        # 1. 左侧卡库管理列 (二级卡片底座: PALETTE["card_bg"])
        # -------------------------------------------------------------
        left_col = ctk.CTkFrame(
            main_pane, 
            fg_color=("#F1F5F9", "#111827"),  # 🌟 替换为 left 列同款哑光蓝灰，消除纯白刺眼感
            corner_radius=12, 
            border_width=1,
            border_color=PALETTE["card_border"],
            width=300
        )
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 4))
        left_col.pack_propagate(False)

        # 1.1 顶部列标题
        ctk.CTkLabel(
            left_col, 
            text="卡库管理", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(side=tk.TOP, anchor="w", padx=10, pady=(8, 4))

        # 次要功能按钮的统一通用样式参数
        sec_btn_kwargs = {
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"],
            "height": 28
        }

        #🌟 1.2 底部固定控制按钮容器（重新编排为 5 行极简双按键对齐布局）
        bottom_btn_container = ctk.CTkFrame(left_col, fg_color="transparent")
        bottom_btn_container.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=(2, 6))

        # 🌟 第一行：【💾 保存卡库数据】（单按钮独占整行，相当于 2 个按钮的宽度，高度为 28）
        ctk.CTkButton(
            bottom_btn_container, 
            text="💾 保存卡库数据", 
            command=self._manual_save_cards,
            fg_color=PALETTE["primary"], 
            hover_color=PALETTE["primary_hover"], 
            text_color=("#FFFFFF", "#0B0F19"), 
            font=FONT_GLOBAL_BOLD, 
            height=28
        ).pack(fill=tk.X, pady=(2, 2))

        # 🌟 第二行：【新建】 / 【删除】
        btn_row1 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row1.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row1, text="新建", command=self._add_new_card, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row1, text="删除", command=self._delete_card, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第三行：【▲ 上移】 / 【▼ 下移】
        btn_row2 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row2.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row2, text="▲ 上移", command=self._move_card_up, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row2, text="▼ 下移", command=self._move_card_down, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第四行：【导出整库】 / 【导入整库】
        btn_row3 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row3.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row3, text="导出整库", command=self._export_cards_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row3, text="导入整库", command=self._import_cards_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第五行：【导出单卡】 / 【导入单卡】
        btn_row4 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row4.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row4, text="导出单卡", command=self._export_single_card_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row4, text="导入单卡", command=self._import_single_card_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 1.3 自适应滚动卡片列表（最后放置，使用 side=tk.TOP 自动填满标题与底部按钮之间的剩余空间）
        self.card_scroll_list = ctk.CTkScrollableFrame(
            left_col, 
            fg_color="transparent",
            corner_radius=6
        )
        self.card_scroll_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        # -------------------------------------------------------------
        # 2. 右侧卡面与效果编辑器（自适应 PALETTE 规范）
        # -------------------------------------------------------------
        right_card = ctk.CTkFrame(main_pane, fg_color="transparent")
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))

        # 2.1 右上：卡面展示区卡片
        card_preview_frame = ctk.CTkFrame(
            right_card, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=12, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        card_preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))  # 👈 将原 fill=tk.X 改为 fill=tk.BOTH, expand=True

        ctk.CTkLabel(card_preview_frame, text="WS 卡面效果实时预览", font=header_font, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(6, 2))

        top_bar = ctk.CTkFrame(card_preview_frame, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=8, pady=2)

        # 样式参数
        preview_entry_opts = {
            "height": 26,
            "font": label_font,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"], # 🌟 统一高对比度描边
            "border_width": 1.5,                     # 🌟 统一 1.5px 描边
            "text_color": PALETTE["text_main"]
        }

        ctk.CTkLabel(top_bar, text="等级:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(top_bar, textvariable=self.var_level, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="费用:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(top_bar, textvariable=self.var_cost, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="触发标记:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        AppDropdown(top_bar, variable=self.var_trigger, values=["无", "魂", "门", "裤", "风", "电", "金砖", "池"], width=75).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="触发魂点:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(top_bar, textvariable=self.var_trigger_soul, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=2)

        # 效果文本框
        middle_box = ctk.CTkFrame(card_preview_frame, fg_color="transparent")
        middle_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.preview_text = ctk.CTkTextbox(
            middle_box, 
            wrap="word", 
            font=FONT_GLOBAL, 
            fg_color=PALETTE["secondary"], 
            text_color=PALETTE["text_main"], 
            height=100
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

        bottom_frame = ctk.CTkFrame(card_preview_frame, fg_color="transparent")
        bottom_frame.pack(fill=tk.X, padx=8, pady=(2, 6))

        bot_row1 = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bot_row1.pack(fill=tk.X, pady=1)

        ctk.CTkLabel(bot_row1, text="种类:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        AppDropdown(bot_row1, variable=self.var_type, values=["角色", "事件", "高潮"], width=75).pack(side=tk.LEFT, padx=(2, 8))

        ctk.CTkLabel(bot_row1, text="卡名:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row1, textvariable=self.var_name, **preview_entry_opts).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        bot_row2 = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bot_row2.pack(fill=tk.X, pady=1)

        ctk.CTkLabel(bot_row2, text="力量 (Power):", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row2, textvariable=self.var_power, width=80, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 12))

        ctk.CTkLabel(bot_row2, text="基础魂点 (Soul):", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row2, textvariable=self.var_soul, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=2)

        # 2.2 右下：7 大攻击节点编辑器卡片
        editor_card = ctk.CTkFrame(
            right_card, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=12, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        editor_card.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        ctk.CTkLabel(editor_card, text="角色攻击阶段效果配置面板", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(4, 1))

        # 1. 绑定 command=self._update_tab_text_colors，在点击切换页签时动态更新文字颜色
        self.phase_tabview = ctk.CTkTabview(
            editor_card,
            command=self._update_tab_text_colors,
            fg_color="transparent",
            segmented_button_fg_color=PALETTE["secondary"],
            segmented_button_selected_color=PALETTE["primary"],             # 选中蓝底
            segmented_button_selected_hover_color=PALETTE["primary_hover"], # 选中悬停
            segmented_button_unselected_color=PALETTE["secondary"],         # 未选中灰底
            segmented_button_unselected_hover_color=PALETTE["secondary_hover"]
        )
        self.phase_tabview._segmented_button.configure(font=FONT_GLOBAL_BOLD)

        self.phase_tabview.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        self.phase_names = [
            ("pre_attack", "(1) 攻击前"),
            ("attack_type", "(2) 攻击方式"),
            ("on_attack", "(3) 攻击时"),
            ("trigger_step", "(4) 判定阶段"),
            ("deal_damage", "(5) 伤害结算"),
            ("on_reverse", "(6) 击倒对手时"),
            ("post_attack", "(7) 攻击结束"),
        ]

        self.phase_tabs: Dict[str, ctk.CTkFrame] = {}
        for phase_key, phase_label in self.phase_names:
            tab = self.phase_tabview.add(phase_label)
            self.phase_tabs[phase_key] = tab
            self._build_phase_tab_ui(tab, phase_key)

        # 2. 7 个页签添加完成后，初始化调用一次，设置初始状态颜色
        self._update_tab_text_colors()
        self._refresh_card_listbox()
 
    def _update_tab_text_colors(self, selected_tab=None):
        """🌟 保持与 RightColumnView / MiddleColumnView 完全一致的按钮颜色引用模式"""
        if not hasattr(self, "phase_tabview") or not hasattr(self.phase_tabview, "_segmented_button"):
            return
        current_tab = selected_tab or self.phase_tabview.get()
        buttons_dict = getattr(self.phase_tabview._segmented_button, "_buttons_dict", {})
        
        for tab_name, btn in buttons_dict.items():
            if tab_name == current_tab:
                # 🌟 选中态：参考 right_column.py，使用 ("#FFFFFF", "#0B0F19")
                btn.configure(text_color=("#FFFFFF", "#0B0F19"))
            else:
                # 🌟 未选中常态：参考 right_column.py，直接引用 PALETTE["text_main"]
                btn.configure(text_color=PALETTE["text_main"])

    def _build_phase_tab_ui(self, parent: ctk.CTkFrame, phase_key: str):
        """🌟 统一提示行字体为 5 号字 FONT_GLOBAL (-14px)"""
        top_row = ctk.CTkFrame(parent, fg_color="transparent", height=26)
        top_row.pack(fill=tk.X, pady=(0, 2), padx=2)

        phase_tip_map = {
            "pre_attack": "【(1) 攻击前】附加效果：",
            "attack_type": "【(2) 攻击方式】附加效果：",
            "on_attack": "【(3) 攻击时】附加效果：",
            "trigger_step": "【(4) 判定阶段】附加效果：",
            "deal_damage": "【(5) 伤害结算】附加效果：",
            "on_reverse": "【(6) 击倒对手时】附加效果：",
            "post_attack": "【(7) 攻击结束】附加效果："
        }
        tip_text = phase_tip_map.get(phase_key, f"【{phase_key}】附加效果：")

        # 🌟 统一为 FONT_GLOBAL (五号字 -14px)
        ctk.CTkLabel(
            top_row, 
            text=tip_text, 
            font=FONT_GLOBAL, 
            text_color=PALETTE["text_sub"],
            height=24
        ).pack(side=tk.LEFT, padx=0)

        # 🌟 统一为 FONT_GLOBAL (五号字 -14px)
        ctk.CTkButton(
            top_row, 
            text="+ 添加操作", 
            width=80, 
            height=24, 
            font=FONT_GLOBAL,
            fg_color=PALETTE["primary"], 
            hover_color=PALETTE["primary_hover"],
            text_color=("#FFFFFF", "#0B0F19"),
            command=lambda pk=phase_key: self._add_op_to_phase(pk)
        ).pack(side=tk.RIGHT, padx=0)

        ops_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        ops_container.pack(fill=tk.BOTH, expand=True, pady=0, padx=0)

        self.phase_ops[phase_key] = []
        parent.ops_container = ops_container

    def _select_card_by_index(self, index: int):
        """🌟 处理卡片列表点击选择与高亮切换"""
        if not (0 <= index < len(self.cards_data)):
            return

        if self.current_card_index != index:
            self._save_editor_to_card(self.current_card_index)
            self.current_card_index = index
            self._load_card_to_editor(self.current_card_index)

        # 刷新所有按钮高亮样式
        for i, btn in enumerate(self.card_buttons):
            is_selected = (i == self.current_card_index)
            btn.configure(
                fg_color=PALETTE["primary"] if is_selected else PALETTE["secondary"],
                hover_color=PALETTE["primary_hover"] if is_selected else PALETTE["secondary_hover"],
                text_color=("#FFFFFF", "#0B0F19") if is_selected else PALETTE["text_main"]
            )

    def _refresh_card_listbox(self):
        """🌟 刷新 CTk 卡片按钮列表"""
        self.card_buttons.clear()
        for child in self.card_scroll_list.winfo_children():
            child.destroy()

        if not self.cards_data:
            ctk.CTkLabel(
                self.card_scroll_list, 
                text="当前卡库为空", 
                font=FONT_GLOBAL, 
                text_color=PALETTE["text_sub"]
            ).pack(pady=20, padx=10)
            return

        for idx, card in enumerate(self.cards_data):
            c_type = card.get('type', '角色')
            c_name = card.get('name', '未命名卡片')
            btn_text = f"[{c_type}] {c_name}"

            is_selected = (idx == self.current_card_index)

            btn = ctk.CTkButton(
                self.card_scroll_list,
                text=btn_text,
                font=FONT_GLOBAL,
                anchor="w",
                height=30,
                corner_radius=6,
                fg_color=PALETTE["primary"] if is_selected else PALETTE["secondary"],
                hover_color=PALETTE["primary_hover"] if is_selected else PALETTE["secondary_hover"],
                text_color=("#FFFFFF", "#0B0F19") if is_selected else PALETTE["text_main"],
                command=lambda i=idx: self._select_card_by_index(i)
            )
            btn.pack(fill=tk.X, pady=2, padx=2)
            self.card_buttons.append(btn)

    def _on_card_selected(self, event=None):
        """兼容接口：向下兼容原有选择回调"""
        self._select_card_by_index(self.current_card_index)

    def _move_card_up(self):
        if not self.cards_data:
            return
        idx = self.current_card_index
        if idx > 0:
            self._save_editor_to_card(idx)
            self.cards_data[idx], self.cards_data[idx - 1] = self.cards_data[idx - 1], self.cards_data[idx]
            self.current_card_index = idx - 1
            self._sync_to_app()
            self._refresh_card_listbox()

    def _move_card_down(self):
        if not self.cards_data:
            return
        idx = self.current_card_index
        if idx < len(self.cards_data) - 1:
            self._save_editor_to_card(idx)
            self.cards_data[idx], self.cards_data[idx + 1] = self.cards_data[idx + 1], self.cards_data[idx]
            self.current_card_index = idx + 1
            self._sync_to_app()
            self._refresh_card_listbox()

    def _hydrate_op(self, raw_op: dict) -> dict:
        """🌟 修复版水化反序列化函数：精准映射 steps_ops 与 nested_ops，确保多步骤操作的详细配置不丢失"""
        if not isinstance(raw_op, dict):
            return {"type_var": tk.StringVar(value="普通伤害"), "controls": {}, "params": {}}

        if "type_var" in raw_op and isinstance(raw_op["type_var"], tk.StringVar):
            return raw_op

        type_name = raw_op.get("type", "普通伤害")
        ui_op = {"type_var": tk.StringVar(value=type_name), "controls": {}, "params": {}}

        for key, val in raw_op.items():
            if key == "type":
                continue

            # 🌟 关键修复：特规映射 steps -> steps_ops 和 nested_ops -> nested_ops
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

    def _load_card_to_editor(self, index: int):
        if not (0 <= index < len(self.cards_data)):
            return
        card = self.cards_data[index]

        self.var_name.set(card.get("name", ""))
        self.var_type.set(card.get("type", "角色"))
        self.var_level.set(card.get("level", 0))
        self.var_cost.set(card.get("cost", 0))
        self.var_power.set(card.get("power", 0))
        self.var_soul.set(card.get("soul", 1))
        self.var_trigger.set(card.get("trigger", "无"))
        self.var_trigger_soul.set(card.get("trigger_soul", 0))

        effects = card.get("effects", {})
        for phase_key, _ in self.phase_names:
            raw_ops = effects.get(phase_key, [])
            ops_list = [self._hydrate_op(op) for op in raw_ops]
            self.phase_ops[phase_key] = ops_list
            self._render_phase_tab(phase_key)

        self._update_card_preview()

    def _save_editor_to_card(self, index: int):
        if not (0 <= index < len(self.cards_data)):
            return
        card = self.cards_data[index]
        card["name"] = self.var_name.get()
        card["type"] = self.var_type.get()
        card["level"] = self.var_level.get()
        card["cost"] = self.var_cost.get()
        card["power"] = self.var_power.get()
        card["soul"] = self.var_soul.get()
        card["trigger"] = self.var_trigger.get()
        card["trigger_soul"] = self.var_trigger_soul.get()

        card["effects"] = {
            pk: [registry.extract_params(op) for op in self.phase_ops.get(pk, [])]
            for pk, _ in self.phase_names
        }

    def _render_phase_tab(self, phase_key: str):
        """🌟 根治版页签渲染：清空 DOM 时同步解绑死变量 Trace，防止野指针回调"""
        tab = self.phase_tabs[phase_key]
        ops_list = self.phase_ops[phase_key]
        container = tab.ops_container

        # 1. 彻底销毁旧的 DOM 控件
        for widget in container.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        # 2. 🌟 关键修复：清空旧 UI 句柄并解绑残留的 Trace，防范 bad window path name 崩溃
        for op in ops_list:
            if "_trace_ids" in op and op["_trace_ids"]:
                # 解绑已记录的所有旧 Trace 监听
                for key, tid in list(op["_trace_ids"].items()):
                    var_name = f"{key}_var"
                    if var_name in op["params"]:
                        try:
                            op["params"][var_name].trace_vdelete("w", tid)
                        except Exception:
                            pass
                op["_trace_ids"].clear()

            # 清理已被销毁的 UI 句柄
            op.pop("params_frame", None)
            op.pop("linkage_frame", None)
            op.pop("cancel_detail_frame", None)
            op.pop("steps_frame", None)
            op.pop("row_frame", None)

        # 3. 重新物理构建 UI 控件
        ctrl_btn_opts = {
            "width": 24,
            "height": 24,
            "corner_radius": 4,
            "font": FONT_GLOBAL_BOLD,
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"]
        }

        for i, op in enumerate(ops_list):
            op_container = ctk.CTkFrame(container, fg_color="transparent")
            op_container.pack(fill=tk.X, pady=(0, 2))

            row_frame = ctk.CTkFrame(op_container, fg_color="transparent", height=26)
            row_frame.grid(row=0, column=0, sticky="w")

            ctk.CTkButton(row_frame, text="-", command=lambda idx=i, pk=phase_key: self._remove_op_from_phase(pk, idx), **ctrl_btn_opts).grid(row=0, column=0, padx=1)
            ctk.CTkButton(row_frame, text="+", command=lambda idx=i, pk=phase_key: self._add_op_to_phase(pk, idx), **ctrl_btn_opts).grid(row=0, column=1, padx=1)

            params_frame = ctk.CTkFrame(row_frame, fg_color="transparent", height=26)
            params_frame.grid(row=0, column=3, sticky="w", padx=2)
            op["params_frame"] = params_frame

            linkage_frame = ctk.CTkFrame(op_container, fg_color="transparent")
            linkage_frame.grid(row=1, column=0, sticky="w", pady=(1, 0))
            linkage_frame.grid_remove()
            op["linkage_frame"] = linkage_frame

            cancel_detail_frame = ctk.CTkFrame(op_container, fg_color="transparent")
            cancel_detail_frame.grid(row=1, column=0, sticky="w", pady=(1, 0))
            cancel_detail_frame.grid_remove()
            op["cancel_detail_frame"] = cancel_detail_frame

            steps_frame = ctk.CTkFrame(op_container, fg_color="transparent")
            steps_frame.grid(row=1, column=0, sticky="w", pady=(1, 0))
            steps_frame.grid_remove()
            op["steps_frame"] = steps_frame

            type_values = registry.get_type_names("condition")
            type_combo = AppDropdown(
                row_frame, 
                variable=op["type_var"], 
                values=type_values, 
                width=130,
                command=lambda val, o=op: self._on_op_type_change(o)
            )
            type_combo.grid(row=0, column=2, padx=2)

            registry.build_widgets(op, params_frame, linkage_frame, cancel_detail_frame, "condition", steps_frame)

    def _add_op_to_phase(self, phase_key: str, index: Optional[int] = None):
        ops_list = self.phase_ops[phase_key]
        default_type = "普通伤害"
        if phase_key == "attack_type":
            default_type = "攻击方式"
        elif phase_key == "trigger_step":
            default_type = "工况判定"
        elif phase_key == "deal_damage":
            default_type = "角色伤害"

        new_op = {
            "type_var": tk.StringVar(value=default_type),
            "controls": {}, "params": {}
        }
        idx = len(ops_list) if index is None else index + 1
        ops_list.insert(idx, new_op)
        self._render_phase_tab(phase_key)
        self._update_card_preview()

    def _remove_op_from_phase(self, phase_key: str, index: int):
        ops_list = self.phase_ops[phase_key]
        if 0 <= index < len(ops_list):
            del ops_list[index]
            self._render_phase_tab(phase_key)
            self._update_card_preview()

    def _bind_op_param_traces(self, op: dict):
        """🌟 递归遍历算卡操作及其衍生/嵌套操作，自动绑定所有变量的实时卡文更新"""
        if not isinstance(op, dict):
            return

        trace_dict = op.setdefault("_preview_trace_ids", {})

        # 防刷频与时序同步：延迟 10ms 执行预览刷新，确保 UI 重绘（如衍生子步骤 DOM 生成）彻底完成
        def _deferred_update(*args):
            self.after(10, self._update_card_preview)

        # 1. 绑定操作自身的 type_var（包含主操作与衍生子操作类型下拉框）
        if "type_var" in op and isinstance(op["type_var"], tk.Variable):
            safe_trace(
                op["type_var"],
                "w",
                _deferred_update,
                trace_dict,
                "type_var"
            )

        # 2. 绑定 params 中的所有参数变量
        params = op.get("params", {})
        for p_name, p_val in list(params.items()):
            if isinstance(p_val, tk.Variable):
                safe_trace(
                    p_val,
                    "w",
                    _deferred_update,
                    trace_dict,
                    p_name
                )
            # 3. 递归绑定“多步骤操作”子步骤
            elif p_name == "steps_ops" and isinstance(p_val, list):
                for sub in p_val:
                    self._bind_op_param_traces(sub)
            # 4. 递归绑定“多次触发”嵌套操作
            elif p_name == "nested_ops" and isinstance(p_val, list):
                for sub in p_val:
                    self._bind_op_param_traces(sub)
            # 5. 递归绑定“单次触发/传火”嵌套操作
            elif p_name == "nested_op" and isinstance(p_val, dict):
                self._bind_op_param_traces(p_val)

    def _update_card_preview(self):
        """🌟 实时刷新 WS 卡文格式化预览（含左侧列表文本与衍生子操作实时感知）"""
        # 🌟 0. 实时同步刷新左侧卡库列表中当前卡片的按钮文本（如输入新卡名时）
        if hasattr(self, "card_buttons") and 0 <= self.current_card_index < len(self.card_buttons):
            c_type = self.var_type.get()
            c_name = self.var_name.get() or "未命名卡片"
            self.card_buttons[self.current_card_index].configure(text=f"[{c_type}] {c_name}")

        # 1. 自动为当前卡片所有 Phase 中的算卡操作及其衍生子操作变量绑定实时 Trace
        for phase_key, _ in self.phase_names:
            for op in self.phase_ops.get(phase_key, []):
                self._bind_op_param_traces(op)

        # 2. 清空并重新格式化生成预览文案
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)

        ctype = self.var_type.get()
        lines = []

        if ctype != "角色":
            lines.append(f"【{ctype}卡效果占位】")
            lines.append("（事件与高潮卡片的效果定义界面暂留空，将在后续版本上线）")
        else:
            has_effect = False
            phase_desc_map = {
                "pre_attack": "(1) 攻击前",
                "attack_type": "(2) 攻击方式",
                "on_attack": "(3) 攻击时",
                "trigger_step": "(4) 判定阶段",
                "deal_damage": "(5) 伤害结算",
                "on_reverse": "(6) 击倒对手时",
                "post_attack": "(7) 攻击结束"
            }

            for phase_key, label in phase_desc_map.items():
                ops = self.phase_ops.get(phase_key, [])
                if ops:
                    has_effect = True
                    op_descs = [format_operation(op) for op in ops]
                    lines.append(f"【自】[{label}]：" + "；".join(op_descs) + "。")

            if not has_effect:
                lines.append("【通常】（无特殊效果文本）")

        self.preview_text.insert(tk.END, "\n".join(lines))
        self.preview_text.configure(state="disabled")

    def _add_new_card(self):
        new_card = {
            "name": f"新自定义卡片 {len(self.cards_data)+1}",
            "type": "角色",
            "level": 0, "cost": 0, "power": 3000, "soul": 1,
            "trigger": "无", "trigger_soul": 0,
            "effects": {pk: [] for pk, _ in self.phase_names}
        }
        self.cards_data.append(new_card)
        self.current_card_index = len(self.cards_data) - 1
        self._sync_to_app()
        self._refresh_card_listbox()
        self._load_card_to_editor(self.current_card_index)

    def _delete_card(self):
        if len(self.cards_data) <= 1:
            messagebox.showwarning("提示", "卡库中至少需要保留一张卡牌！", parent=self)
            return
        del self.cards_data[self.current_card_index]
        self.current_card_index = max(0, self.current_card_index - 1)
        self._sync_to_app()
        self._refresh_card_listbox()
        self._load_card_to_editor(self.current_card_index)

    def _export_cards_json(self):
        self._save_editor_to_card(self.current_card_index)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON Files", "*.json")], parent=self
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.cards_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("导出成功", "自定义卡库已成功导出为 JSON 文件。", parent=self)
            except Exception as e:
                messagebox.showerror("导出失败", f"导出失败：\n{e}", parent=self)

    def _import_cards_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], parent=self)
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list) and data:
                self.cards_data = data
                self.current_card_index = 0
                self._sync_to_app()
                self._refresh_card_listbox()
                self._load_card_to_editor(0)
                messagebox.showinfo("导入成功", f"成功导入卡库，共 {len(data)} 张卡片。", parent=self)

            elif isinstance(data, dict) and ("name" in data or "type" in data or "effects" in data):
                self.cards_data.append(data)
                self.current_card_index = len(self.cards_data) - 1
                self._sync_to_app()
                self._refresh_card_listbox()
                self._load_card_to_editor(self.current_card_index)
                messagebox.showinfo("导入成功", f"成功导入单张卡片：【{data.get('name', '未命名')}】。", parent=self)

            else:
                messagebox.showwarning("导入失败", "导入的文件格式不符合卡片或卡库 JSON 规范。", parent=self)

        except Exception as e:
            messagebox.showerror("导入失败", f"读取卡库文件失败：\n{e}", parent=self)

    def _export_single_card_json(self):
        self._save_editor_to_card(self.current_card_index)
        if not (0 <= self.current_card_index < len(self.cards_data)):
            return

        card = self.cards_data[self.current_card_index]
        card_name = card.get("name", "自定义卡片")

        file_path = filedialog.asksaveasfilename(
            initialfile=f"{card_name}.json",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            parent=self
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(card, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("导出成功", f"单卡【{card_name}】已成功导出为 JSON 文件。", parent=self)
            except Exception as e:
                messagebox.showerror("导出失败", f"导出单卡失败：\n{e}", parent=self)

    def _import_single_card_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], parent=self)
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            card_data = data[0] if isinstance(data, list) and data else data
            if isinstance(card_data, dict) and ("name" in card_data or "effects" in card_data):
                self.cards_data.append(card_data)
                self.current_card_index = len(self.cards_data) - 1
                self._sync_to_app()
                self._refresh_card_listbox()
                self._load_card_to_editor(self.current_card_index)
                messagebox.showinfo("导入成功", f"成功导入单张卡片：【{card_data.get('name', '未命名')}】。", parent=self)
            else:
                messagebox.showwarning("导入失败", "选择的文件不包含有效的单卡 JSON 数据。", parent=self)
        except Exception as e:
            messagebox.showerror("导入失败", f"读取单卡文件失败：\n{e}", parent=self)