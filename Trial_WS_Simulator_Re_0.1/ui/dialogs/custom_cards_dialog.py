# -*- coding: utf-8 -*-
"""
自定義卡片編輯器與選擇彈窗 (Custom Cards Dialog & Selector) - CustomTkinter 淺色適配版
支持單卡/整庫導入導出、手動保存、卡片上下位置調整及持久化自動寫盤。
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
    """自定義卡片管理與編輯器對話框類"""

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("WS 自定義卡片編輯器 ver.1.3")
        self.geometry("1100x780+80+60")
        
        # 🌟 1. 設置自適應大背景色，消除硬編碼 #F8FAFC
        self.configure(fg_color=PALETTE["bg_main"])

        # 🌟 強制置頂與焦點修復
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
                        "attack_type": [{"type": "攻擊方式", "attack_type": "正面"}],
                        "on_attack": [{"type": "摩卡", "mocha_mode": "原位", "mocha_count": 2}],
                        "trigger_step": [{"type": "工況判定"}],
                        "deal_damage": [{"type": "角色傷害", "role_damage_base": 0, "role_bonus_type": "魂點", "trigger_rate": 0.0}],
                        "on_reverse": [{"type": "普通傷害", "damage": 2, "trigger_rate": 0.0}],
                        "post_attack": []
                    }
                }
            ]
            if hasattr(self.app, "custom_cards_data"):
                self.app.custom_cards_data = self.cards_data

        self.current_card_index: int = 0
        self.phase_ops: Dict[str, List[dict]] = {}
        self.card_buttons: List[ctk.CTkButton] = []  # 🌟 記錄 CTk 列表項按鈕引用

        self._init_variables()
        self._build_ui()
        self._load_card_to_editor(0)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_op_type_change(self, op: dict):
        """當下拉框切換操作類型時，重置參數並重新渲染對應的 UI"""
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
        """同步數據至 App 控制器，並通知主界面刷新卡牌下拉框與算卡選擇器"""
        if hasattr(self.app, "custom_cards_data"):
            self.app.custom_cards_data = self.cards_data
        if hasattr(self.app, "save_custom_cards_data"):
            self.app.save_custom_cards_data()

        # 🌟 自動觸發主界面的刷新函數（兼容多種主程序刷新接口）
        for refresh_method in ("refresh_custom_cards_ui", "refresh_ui", "load_custom_cards", "update_card_dropdowns"):
            if hasattr(self.app, refresh_method):
                try:
                    getattr(self.app, refresh_method)()
                except Exception as e:
                    print(f"[WARN] 觸發主界面卡庫刷新接口 {refresh_method} 提示: {e}")

    def _manual_save_cards(self):
        """手動保存卡庫數據，並刷新編輯器與左側列表"""
        self._save_editor_to_card(self.current_card_index)
        self._sync_to_app()
        # 🌟 重新渲染左側卡片列表與右側效果預覽
        self._refresh_card_listbox()
        self._update_card_preview()
        messagebox.showinfo("保存成功", "當前卡庫數據已成功保存並刷新！", parent=self)

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
        self.var_trigger = tk.StringVar(value="無")
        self.var_trigger_soul = tk.IntVar(value=0)

        for var in (self.var_name, self.var_type, self.var_level, self.var_cost, self.var_power, self.var_soul, self.var_trigger, self.var_trigger_soul):
            var.trace("w", lambda *a: self._update_card_preview())

    def _build_ui(self):
        """🌟 全量 CTk 統一組件與自適應配色重構（已修復佈局擠壓問題）"""
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        main_pane = ctk.CTkFrame(self, fg_color="transparent")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # -------------------------------------------------------------
        # 1. 左側卡庫管理列 (二級卡片底座: PALETTE["card_bg"])
        # -------------------------------------------------------------
        left_col = ctk.CTkFrame(
            main_pane, 
            fg_color=("#F1F5F9", "#111827"),  # 🌟 替換為 left 列同款啞光藍灰，消除純白刺眼感
            corner_radius=12, 
            border_width=1,
            border_color=PALETTE["card_border"],
            width=300
        )
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 4))
        left_col.pack_propagate(False)

        # 1.1 頂部列標題
        ctk.CTkLabel(
            left_col, 
            text="卡庫管理", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(side=tk.TOP, anchor="w", padx=10, pady=(8, 4))

        # 次要功能按鈕的統一通用樣式參數
        sec_btn_kwargs = {
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"],
            "height": 28
        }

        #🌟 1.2 底部固定控制按鈕容器（重新編排為 5 行極簡雙按鍵對齊佈局）
        bottom_btn_container = ctk.CTkFrame(left_col, fg_color="transparent")
        bottom_btn_container.pack(side=tk.BOTTOM, fill=tk.X, padx=6, pady=(2, 6))

        # 🌟 第一行：【💾 保存卡庫數據】（單按鈕獨佔整行，相當於 2 個按鈕的寬度，高度為 28）
        ctk.CTkButton(
            bottom_btn_container, 
            text="💾 保存卡庫數據", 
            command=self._manual_save_cards,
            fg_color=PALETTE["primary"], 
            hover_color=PALETTE["primary_hover"], 
            text_color=("#FFFFFF", "#0B0F19"), 
            font=FONT_GLOBAL_BOLD, 
            height=28
        ).pack(fill=tk.X, pady=(2, 2))

        # 🌟 第二行：【新建】 / 【刪除】
        btn_row1 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row1.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row1, text="新建", command=self._add_new_card, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row1, text="刪除", command=self._delete_card, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第三行：【▲ 上移】 / 【▼ 下移】
        btn_row2 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row2.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row2, text="▲ 上移", command=self._move_card_up, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row2, text="▼ 下移", command=self._move_card_down, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第四行：【導出整庫】 / 【導入整庫】
        btn_row3 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row3.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row3, text="導出整庫", command=self._export_cards_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row3, text="導入整庫", command=self._import_cards_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 第五行：【導出單卡】 / 【導入單卡】
        btn_row4 = ctk.CTkFrame(bottom_btn_container, fg_color="transparent")
        btn_row4.pack(fill=tk.X, pady=2)
        ctk.CTkButton(btn_row4, text="導出單卡", command=self._export_single_card_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)
        ctk.CTkButton(btn_row4, text="導入單卡", command=self._import_single_card_json, **sec_btn_kwargs).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=1)

        # 🌟 1.3 自適應滾動卡片列表（最後放置，使用 side=tk.TOP 自動填滿標題與底部按鈕之間的剩餘空間）
        self.card_scroll_list = ctk.CTkScrollableFrame(
            left_col, 
            fg_color="transparent",
            corner_radius=6
        )
        self.card_scroll_list.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        # -------------------------------------------------------------
        # 2. 右側卡面與效果編輯器（自適應 PALETTE 規範）
        # -------------------------------------------------------------
        right_card = ctk.CTkFrame(main_pane, fg_color="transparent")
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))

        # 2.1 右上：卡面展示區卡片
        card_preview_frame = ctk.CTkFrame(
            right_card, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=12, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        card_preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))  # 👈 將原 fill=tk.X 改為 fill=tk.BOTH, expand=True

        ctk.CTkLabel(card_preview_frame, text="WS 卡面效果實時預覽", font=header_font, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(6, 2))

        top_bar = ctk.CTkFrame(card_preview_frame, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=8, pady=2)

        # 樣式參數
        preview_entry_opts = {
            "height": 26,
            "font": label_font,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"], # 🌟 統一高對比度描邊
            "border_width": 1.5,                     # 🌟 統一 1.5px 描邊
            "text_color": PALETTE["text_main"]
        }

        ctk.CTkLabel(top_bar, text="等級:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(top_bar, textvariable=self.var_level, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="費用:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(top_bar, textvariable=self.var_cost, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="觸發標記:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        AppDropdown(top_bar, variable=self.var_trigger, values=["無", "魂", "門", "褲", "風", "電", "金磚", "池"], width=75).pack(side=tk.LEFT, padx=(2, 10))

        ctk.CTkLabel(top_bar, text="觸發魂點:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
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

        ctk.CTkLabel(bot_row1, text="種類:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        AppDropdown(bot_row1, variable=self.var_type, values=["角色", "事件", "名場面"], width=75).pack(side=tk.LEFT, padx=(2, 8))

        ctk.CTkLabel(bot_row1, text="卡名:", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row1, textvariable=self.var_name, **preview_entry_opts).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        bot_row2 = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        bot_row2.pack(fill=tk.X, pady=1)

        ctk.CTkLabel(bot_row2, text="力量 (Power):", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row2, textvariable=self.var_power, width=80, **preview_entry_opts).pack(side=tk.LEFT, padx=(2, 12))

        ctk.CTkLabel(bot_row2, text="基礎魂點 (Soul):", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(bot_row2, textvariable=self.var_soul, width=40, **preview_entry_opts).pack(side=tk.LEFT, padx=2)

        # 2.2 右下：7 大攻擊節點編輯器卡片
        editor_card = ctk.CTkFrame(
            right_card, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=12, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        editor_card.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        ctk.CTkLabel(editor_card, text="角色攻擊階段效果配置面板", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"]).pack(anchor="w", padx=10, pady=(4, 1))

        # 1. 綁定 command=self._update_tab_text_colors，在點擊切換頁籤時動態更新文字顏色
        self.phase_tabview = ctk.CTkTabview(
            editor_card,
            command=self._update_tab_text_colors,
            fg_color="transparent",
            segmented_button_fg_color=PALETTE["secondary"],
            segmented_button_selected_color=PALETTE["primary"],             # 選中藍底
            segmented_button_selected_hover_color=PALETTE["primary_hover"], # 選中懸停
            segmented_button_unselected_color=PALETTE["secondary"],         # 未選中灰底
            segmented_button_unselected_hover_color=PALETTE["secondary_hover"]
        )
        self.phase_tabview._segmented_button.configure(font=FONT_GLOBAL_BOLD)

        self.phase_tabview.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))

        self.phase_names = [
            ("pre_attack", "(1) 攻擊前"),
            ("attack_type", "(2) 攻擊方式"),
            ("on_attack", "(3) 攻擊時"),
            ("trigger_step", "(4) 判定階段"),
            ("deal_damage", "(5) 傷害結算"),
            ("on_reverse", "(6) 擊倒對手時"),
            ("post_attack", "(7) 攻擊結束"),
        ]

        self.phase_tabs: Dict[str, ctk.CTkFrame] = {}
        for phase_key, phase_label in self.phase_names:
            tab = self.phase_tabview.add(phase_label)
            self.phase_tabs[phase_key] = tab
            self._build_phase_tab_ui(tab, phase_key)

        # 2. 7 個頁籤添加完成後，初始化調用一次，設置初始狀態顏色
        self._update_tab_text_colors()
        self._refresh_card_listbox()
 
    def _update_tab_text_colors(self, selected_tab=None):
        """🌟 保持與 RightColumnView / MiddleColumnView 完全一致的按鈕顏色引用模式"""
        if not hasattr(self, "phase_tabview") or not hasattr(self.phase_tabview, "_segmented_button"):
            return
        current_tab = selected_tab or self.phase_tabview.get()
        buttons_dict = getattr(self.phase_tabview._segmented_button, "_buttons_dict", {})
        
        for tab_name, btn in buttons_dict.items():
            if tab_name == current_tab:
                # 🌟 選中態：參考 right_column.py，使用 ("#FFFFFF", "#0B0F19")
                btn.configure(text_color=("#FFFFFF", "#0B0F19"))
            else:
                # 🌟 未選中常態：參考 right_column.py，直接引用 PALETTE["text_main"]
                btn.configure(text_color=PALETTE["text_main"])

    def _build_phase_tab_ui(self, parent: ctk.CTkFrame, phase_key: str):
        """🌟 統一提示行字體為 5 號字 FONT_GLOBAL (-14px)"""
        top_row = ctk.CTkFrame(parent, fg_color="transparent", height=26)
        top_row.pack(fill=tk.X, pady=(0, 2), padx=2)

        phase_tip_map = {
            "pre_attack": "【(1) 攻擊前】附加效果：",
            "attack_type": "【(2) 攻擊方式】附加效果：",
            "on_attack": "【(3) 攻擊時】附加效果：",
            "trigger_step": "【(4) 判定階段】附加效果：",
            "deal_damage": "【(5) 傷害結算】附加效果：",
            "on_reverse": "【(6) 擊倒對手時】附加效果：",
            "post_attack": "【(7) 攻擊結束】附加效果："
        }
        tip_text = phase_tip_map.get(phase_key, f"【{phase_key}】附加效果：")

        # 🌟 統一為 FONT_GLOBAL (五號字 -14px)
        ctk.CTkLabel(
            top_row, 
            text=tip_text, 
            font=FONT_GLOBAL, 
            text_color=PALETTE["text_sub"],
            height=24
        ).pack(side=tk.LEFT, padx=0)

        # 🌟 統一為 FONT_GLOBAL (五號字 -14px)
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
        """🌟 處理卡片列表點擊選擇與高亮切換"""
        if not (0 <= index < len(self.cards_data)):
            return

        if self.current_card_index != index:
            self._save_editor_to_card(self.current_card_index)
            self.current_card_index = index
            self._load_card_to_editor(self.current_card_index)

        # 刷新所有按鈕高亮樣式
        for i, btn in enumerate(self.card_buttons):
            is_selected = (i == self.current_card_index)
            btn.configure(
                fg_color=PALETTE["primary"] if is_selected else PALETTE["secondary"],
                hover_color=PALETTE["primary_hover"] if is_selected else PALETTE["secondary_hover"],
                text_color=("#FFFFFF", "#0B0F19") if is_selected else PALETTE["text_main"]
            )

    def _refresh_card_listbox(self):
        """🌟 刷新 CTk 卡片按鈕列表"""
        self.card_buttons.clear()
        for child in self.card_scroll_list.winfo_children():
            child.destroy()

        if not self.cards_data:
            ctk.CTkLabel(
                self.card_scroll_list, 
                text="當前卡庫為空", 
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
        """兼容接口：向下兼容原有選擇回調"""
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
        self.var_trigger.set(card.get("trigger", "無"))
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
        """🌟 根治版頁籤渲染：清空 DOM 時同步解綁死變量 Trace，防止野指針回調"""
        tab = self.phase_tabs[phase_key]
        ops_list = self.phase_ops[phase_key]
        container = tab.ops_container

        # 1. 徹底銷燬舊的 DOM 控件
        for widget in container.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        # 2. 🌟 關鍵修復：清空舊 UI 句柄並解綁殘留的 Trace，防範 bad window path name 崩潰
        for op in ops_list:
            if "_trace_ids" in op and op["_trace_ids"]:
                # 解綁已記錄的所有舊 Trace 監聽
                for key, tid in list(op["_trace_ids"].items()):
                    var_name = f"{key}_var"
                    if var_name in op["params"]:
                        try:
                            op["params"][var_name].trace_vdelete("w", tid)
                        except Exception:
                            pass
                op["_trace_ids"].clear()

            # 清理已被銷燬的 UI 句柄
            op.pop("params_frame", None)
            op.pop("linkage_frame", None)
            op.pop("cancel_detail_frame", None)
            op.pop("steps_frame", None)
            op.pop("row_frame", None)

        # 3. 重新物理構建 UI 控件
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
        default_type = "普通傷害"
        if phase_key == "attack_type":
            default_type = "攻擊方式"
        elif phase_key == "trigger_step":
            default_type = "工況判定"
        elif phase_key == "deal_damage":
            default_type = "角色傷害"

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
        """🌟 遞歸遍歷算卡操作及其衍生/嵌套操作，自動綁定所有變量的實時卡文更新"""
        if not isinstance(op, dict):
            return

        trace_dict = op.setdefault("_preview_trace_ids", {})

        # 防刷頻與時序同步：延遲 10ms 執行預覽刷新，確保 UI 重繪（如衍生子步驟 DOM 生成）徹底完成
        def _deferred_update(*args):
            self.after(10, self._update_card_preview)

        # 1. 綁定操作自身的 type_var（包含主操作與衍生子操作類型下拉框）
        if "type_var" in op and isinstance(op["type_var"], tk.Variable):
            safe_trace(
                op["type_var"],
                "w",
                _deferred_update,
                trace_dict,
                "type_var"
            )

        # 2. 綁定 params 中的所有參數變量
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
            # 3. 遞歸綁定“多步驟操作”子步驟
            elif p_name == "steps_ops" and isinstance(p_val, list):
                for sub in p_val:
                    self._bind_op_param_traces(sub)
            # 4. 遞歸綁定“多次觸發”嵌套操作
            elif p_name == "nested_ops" and isinstance(p_val, list):
                for sub in p_val:
                    self._bind_op_param_traces(sub)
            # 5. 遞歸綁定“單次觸發/傳火”嵌套操作
            elif p_name == "nested_op" and isinstance(p_val, dict):
                self._bind_op_param_traces(p_val)

    def _update_card_preview(self):
        """🌟 實時刷新 WS 卡文格式化預覽（含左側列表文本與衍生子操作實時感知）"""
        # 🌟 0. 實時同步刷新左側卡庫列表中當前卡片的按鈕文本（如輸入新卡名時）
        if hasattr(self, "card_buttons") and 0 <= self.current_card_index < len(self.card_buttons):
            c_type = self.var_type.get()
            c_name = self.var_name.get() or "未命名卡片"
            self.card_buttons[self.current_card_index].configure(text=f"[{c_type}] {c_name}")

        # 1. 自動為當前卡片所有 Phase 中的算卡操作及其衍生子操作變量綁定實時 Trace
        for phase_key, _ in self.phase_names:
            for op in self.phase_ops.get(phase_key, []):
                self._bind_op_param_traces(op)

        # 2. 清空並重新格式化生成預覽文案
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)

        ctype = self.var_type.get()
        lines = []

        if ctype != "角色":
            lines.append(f"【{ctype}卡效果佔位】")
            lines.append("（事件與名場面卡片的效果定義界面暫留空，將在後續版本上線）")
        else:
            has_effect = False
            phase_desc_map = {
                "pre_attack": "(1) 攻擊前",
                "attack_type": "(2) 攻擊方式",
                "on_attack": "(3) 攻擊時",
                "trigger_step": "(4) 判定階段",
                "deal_damage": "(5) 傷害結算",
                "on_reverse": "(6) 擊倒對手時",
                "post_attack": "(7) 攻擊結束"
            }

            for phase_key, label in phase_desc_map.items():
                ops = self.phase_ops.get(phase_key, [])
                if ops:
                    has_effect = True
                    op_descs = [format_operation(op) for op in ops]
                    lines.append(f"【自】[{label}]：" + "；".join(op_descs) + "。")

            if not has_effect:
                lines.append("【通常】（無特殊效果文本）")

        self.preview_text.insert(tk.END, "\n".join(lines))
        self.preview_text.configure(state="disabled")

    def _add_new_card(self):
        new_card = {
            "name": f"新自定義卡片 {len(self.cards_data)+1}",
            "type": "角色",
            "level": 0, "cost": 0, "power": 3000, "soul": 1,
            "trigger": "無", "trigger_soul": 0,
            "effects": {pk: [] for pk, _ in self.phase_names}
        }
        self.cards_data.append(new_card)
        self.current_card_index = len(self.cards_data) - 1
        self._sync_to_app()
        self._refresh_card_listbox()
        self._load_card_to_editor(self.current_card_index)

    def _delete_card(self):
        if len(self.cards_data) <= 1:
            messagebox.showwarning("提示", "卡庫中至少需要保留一張卡牌！", parent=self)
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
                messagebox.showinfo("導出成功", "自定義卡庫已成功導出為 JSON 文件。", parent=self)
            except Exception as e:
                messagebox.showerror("導出失敗", f"導出失敗：\n{e}", parent=self)

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
                messagebox.showinfo("導入成功", f"成功導入卡庫，共 {len(data)} 張卡片。", parent=self)

            elif isinstance(data, dict) and ("name" in data or "type" in data or "effects" in data):
                self.cards_data.append(data)
                self.current_card_index = len(self.cards_data) - 1
                self._sync_to_app()
                self._refresh_card_listbox()
                self._load_card_to_editor(self.current_card_index)
                messagebox.showinfo("導入成功", f"成功導入單張卡片：【{data.get('name', '未命名')}】。", parent=self)

            else:
                messagebox.showwarning("導入失敗", "導入的文件格式不符合卡片或卡庫 JSON 規範。", parent=self)

        except Exception as e:
            messagebox.showerror("導入失敗", f"讀取卡庫文件失敗：\n{e}", parent=self)

    def _export_single_card_json(self):
        self._save_editor_to_card(self.current_card_index)
        if not (0 <= self.current_card_index < len(self.cards_data)):
            return

        card = self.cards_data[self.current_card_index]
        card_name = card.get("name", "自定義卡片")

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
                messagebox.showinfo("導出成功", f"單卡【{card_name}】已成功導出為 JSON 文件。", parent=self)
            except Exception as e:
                messagebox.showerror("導出失敗", f"導出單卡失敗：\n{e}", parent=self)

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
                messagebox.showinfo("導入成功", f"成功導入單張卡片：【{card_data.get('name', '未命名')}】。", parent=self)
            else:
                messagebox.showwarning("導入失敗", "選擇的文件不包含有效的單卡 JSON 數據。", parent=self)
        except Exception as e:
            messagebox.showerror("導入失敗", f"讀取單卡文件失敗：\n{e}", parent=self)