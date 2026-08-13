# -*- coding: utf-8 -*-
"""
主界面中栏面板视图 (Middle Column View) - 统一浅色高颜值适配版
包含了多次模拟配置、模式切换（常规/高级/工况）、动态角色管理、计划列表与执行控制。
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Any, List, Dict

from utils.registry import registry
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD
from ui.components.middle_column.reg_sim_tab import RegSimTab
from ui.components.middle_column.adv_sim_tab import AdvSimTab
from ui.components.middle_column.cond_sim_tab import CondSimTab  # 🌟 1. 引入工况模式组件


class MiddleColumnView(ctk.CTkFrame):
    """中栏多模式模拟配置视图"""

    # 常规模式透传属性
    @property
    def reg_sim_times(self): return self.reg_tab.reg_sim_times
    @property
    def reg_progress_bar(self): return self.reg_tab.reg_progress_bar
    @property
    def reg_progress_label(self): return self.reg_tab.reg_progress_label
    @property
    def reg_ops_frame(self): return self.reg_tab.reg_ops_frame

    # 高级模式透传属性
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

    # 🌟 2. 工况模式透传属性
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

        self.multi_mode_var = tk.StringVar(value="常规")
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
            "height": 26
        }

        self.batch_btn = ctk.CTkButton(
            title_row, 
            text="批量统计", 
            command=lambda: self.app.open_batch_statistics(),
            width=75,
            **btn_aux_opts
        )
        self.batch_btn.pack(side=tk.LEFT, padx=2)

        self.dt_btn = ctk.CTkButton(
            title_row, 
            text="决策树", 
            command=lambda: self.app.open_decision_tree_dialog(),
            width=65,
            **btn_aux_opts
        )

        self.mode_btn_frame = ctk.CTkFrame(title_row, fg_color="transparent")
        self.mode_btn_frame.pack(side=tk.RIGHT)

        tab_opts = {
            "font": FONT_GLOBAL,
            "width": 60,
            "height": 26,
            "corner_radius": 6
        }

        self.btn_reg = ctk.CTkButton(self.mode_btn_frame, text="常规", command=lambda: self.select_mode("常规"), **tab_opts)
        self.btn_reg.pack(side=tk.LEFT, padx=1)

        self.btn_adv = ctk.CTkButton(self.mode_btn_frame, text="高级", command=lambda: self.select_mode("高级"), **tab_opts)
        self.btn_adv.pack(side=tk.LEFT, padx=1)

        self.btn_cond = ctk.CTkButton(self.mode_btn_frame, text="工况", command=lambda: self.select_mode("工况"), **tab_opts)
        self.btn_cond.pack(side=tk.LEFT, padx=1)

        self.mode_buttons_dict = {
            "常规": self.btn_reg,
            "高级": self.btn_adv,
            "工况": self.btn_cond
        }

        # 1. 常规模式子容器
        self.regular_frame = ctk.CTkFrame(multi_frame, fg_color="transparent")
        self.regular_frame.pack(fill=tk.BOTH, expand=True)

        self.reg_tab = RegSimTab(
            self.regular_frame,
            app_controller=self.app,
            on_run_sim=self.app.run_regular_simulation
        )
        self.reg_tab.pack(fill=tk.BOTH, expand=True)

        # 2. 高级模式子容器
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

        # 3. 🌟 工况模式子容器：实例化 CondSimTab
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

        self.select_mode("常规")

    def select_mode(self, mode_name: str):
        self.multi_mode_var.set(mode_name)

        self.regular_frame.pack_forget()
        self.advanced_frame.pack_forget()
        self.condition_frame.pack_forget()
        self.dt_btn.pack_forget()

        if mode_name == "常规":
            self.regular_frame.pack(fill=tk.BOTH, expand=True)
        elif mode_name == "高级":
            self.advanced_frame.pack(fill=tk.BOTH, expand=True)
        elif mode_name == "工况":
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
        modes = ["常规", "高级", "工况"]
        current = self.multi_mode_var.get()
        next_mode = modes[(modes.index(current) + 1) % len(modes)]
        self.select_mode(next_mode)