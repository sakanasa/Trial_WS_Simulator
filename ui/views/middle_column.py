# -*- coding: utf-8 -*-
"""
主界面中欄面板視圖 (Middle Column View) - 統一淺色高顏值適配版
包含了多次模擬配置、模式切換（常規/高級/殘局）、動態角色管理、計劃列表與執行控制。
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Any, List, Dict

from utils.registry import registry
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD, RADIUS, SPACING, BORDER_THIN
from ui.components.middle_column.reg_sim_tab import RegSimTab
from ui.components.middle_column.adv_sim_tab import AdvSimTab
from ui.components.middle_column.cond_sim_tab import CondSimTab  # 🌟 1. 引入殘局模式組件


class MiddleColumnView(ctk.CTkFrame):
    """中欄多模式模擬配置視圖"""

    # 常規模式透傳屬性
    @property
    def reg_sim_times(self): return self.reg_tab.reg_sim_times
    @property
    def reg_progress_bar(self): return self.reg_tab.reg_progress_bar
    @property
    def reg_progress_label(self): return self.reg_tab.reg_progress_label
    @property
    def reg_ops_frame(self): return self.reg_tab.reg_ops_frame

    # 高級模式透傳屬性
    @property
    def adv_sim_times(self): return self.adv_tab.adv_sim_times
    @property
    def adv_progress_bar(self): return self.adv_tab.adv_progress_bar
    @property
    def adv_progress_label(self): return self.adv_tab.adv_progress_label
    @property
    def adv_roles_container(self): return self.adv_tab.adv_roles_container
    @property
    def plan_list_frame(self): return self.adv_tab.plan_list_frame

    # 🌟 2. 殘局模式透傳屬性
    @property
    def cond_sim_times(self): return self.cond_tab.cond_sim_times
    @property
    def cond_progress_bar(self): return self.cond_tab.cond_progress_bar
    @property
    def cond_progress_label(self): return self.cond_tab.cond_progress_label
    @property
    def field_component(self): return self.cond_tab.field_component
    @property
    def condition_roles_container(self): return self.cond_tab.condition_roles_container
    @property
    def condition_plan_list_frame(self): return self.cond_tab.condition_plan_list_frame

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, fg_color=("#F1F5F9", "#111827"), **kwargs)
        self.app = app_controller

        self.multi_mode_var = tk.StringVar(value="常規")
        self._build_ui()

    def _build_ui(self):
        multi_frame = ctk.CTkFrame(
            self, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=12, 
            border_width=0
        )
        multi_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        title_row = ctk.CTkFrame(multi_frame, fg_color="transparent")
        title_row.pack(fill=tk.X, pady=(8, 4), padx=8)

        btn_aux_opts = {
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"],
            "height": 26,
            "corner_radius": RADIUS["sm"]
        }

        self.batch_btn = ctk.CTkButton(
            title_row, 
            text="批量統計", 
            command=lambda: self.app.open_batch_statistics(),
            width=75,
            **btn_aux_opts
        )
        self.batch_btn.pack(side=tk.LEFT, padx=2)

        self.dt_btn = ctk.CTkButton(
            title_row, 
            text="決策樹", 
            command=lambda: self.app.open_decision_tree_dialog(),
            width=65,
            **btn_aux_opts
        )

        self.mode_btn_frame = ctk.CTkFrame(title_row, fg_color="transparent")
        self.mode_btn_frame.pack(side=tk.RIGHT)

        tab_opts = {
            "font": FONT_GLOBAL_BOLD,
            "width": 64,
            "height": 28,
            "corner_radius": RADIUS["sm"]
        }

        self.btn_reg = ctk.CTkButton(self.mode_btn_frame, text="常規", command=lambda: self.select_mode("常規"), **tab_opts)
        self.btn_reg.pack(side=tk.LEFT, padx=2)

        self.btn_adv = ctk.CTkButton(self.mode_btn_frame, text="高級", command=lambda: self.select_mode("高級"), **tab_opts)
        self.btn_adv.pack(side=tk.LEFT, padx=2)

        self.btn_cond = ctk.CTkButton(self.mode_btn_frame, text="殘局", command=lambda: self.select_mode("殘局"), **tab_opts)
        self.btn_cond.pack(side=tk.LEFT, padx=2)

        self.mode_buttons_dict = {
            "常規": self.btn_reg,
            "高級": self.btn_adv,
            "殘局": self.btn_cond
        }

        # 1. 常規模式子容器
        self.regular_frame = ctk.CTkFrame(multi_frame, fg_color="transparent")
        self.regular_frame.pack(fill=tk.BOTH, expand=True)

        self.reg_tab = RegSimTab(
            self.regular_frame,
            app_controller=self.app,
            on_run_sim=self.app.run_regular_simulation
        )
        self.reg_tab.pack(fill=tk.BOTH, expand=True)

        # 2. 高級模式子容器
        self.advanced_frame = ctk.CTkFrame(multi_frame, fg_color="transparent")
        self.advanced_frame.pack(fill=tk.BOTH, expand=True)
        self.advanced_frame.pack_forget()

        self.adv_tab = AdvSimTab(
            self.advanced_frame,
            app_controller=self.app,
            on_run_sim=self.app.run_advanced_simulation,
            on_single_test=self.app.run_advanced_single_test,
            on_add_plan_step=self.app.add_plan_step,
            on_clear_plan=self.app.clear_plan
        )
        self.adv_tab.pack(fill=tk.BOTH, expand=True)

        # 3. 🌟 殘局模式子容器：實例化 CondSimTab
        self.condition_frame = ctk.CTkFrame(multi_frame, fg_color="transparent")
        self.condition_frame.pack(fill=tk.BOTH, expand=True)
        self.condition_frame.pack_forget()

        self.cond_tab = CondSimTab(
            self.condition_frame,
            app_controller=self.app,
            on_run_sim=self.app.run_condition_simulation,
            on_single_test=self.app.run_condition_single_test,
            on_save_state=self.app.save_condition_state,
            on_load_state=self.app.load_condition_state,
            on_open_custom_cards=self.app.open_custom_cards_dialog,
            on_add_plan_step=self.app.add_condition_plan_step,
            on_clear_plan=self.app.clear_condition_plan,
            on_zone_click=self.app.open_card_detail_window,
            on_overview_click=self.app.show_condition_overview
        )
        self.cond_tab.pack(fill=tk.BOTH, expand=True)

        self.select_mode("高級")

    def select_mode(self, mode_name: str):
        self.multi_mode_var.set(mode_name)

        self.regular_frame.pack_forget()
        self.advanced_frame.pack_forget()
        self.condition_frame.pack_forget()
        self.dt_btn.pack_forget()

        if mode_name == "常規":
            self.regular_frame.pack(fill=tk.BOTH, expand=True)
        elif mode_name == "高級":
            self.advanced_frame.pack(fill=tk.BOTH, expand=True)
        elif mode_name == "殘局":
            self.condition_frame.pack(fill=tk.BOTH, expand=True)
            self.dt_btn.pack(side=tk.LEFT, padx=4)

        for name, btn in self.mode_buttons_dict.items():
            if name == mode_name:
                btn.configure(
                    fg_color=PALETTE["primary"], 
                    hover_color=PALETTE["primary_hover"], 
                    text_color=("#FFFFFF", "#0B0F19")
                )
            else:
                btn.configure(
                    fg_color=PALETTE["secondary"], 
                    hover_color=PALETTE["secondary_hover"], 
                    text_color=PALETTE["text_main"]
                )

    def toggle_multi_mode(self):
        modes = ["常規", "高級", "殘局"]
        current = self.multi_mode_var.get()
        next_mode = modes[(modes.index(current) + 1) % len(modes)]
        self.select_mode(next_mode)