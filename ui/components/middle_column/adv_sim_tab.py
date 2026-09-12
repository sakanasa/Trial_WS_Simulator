# -*- coding: utf-8 -*-
"""
高級模式模擬面板組件 (Advanced Simulation Tab Component)
獨立封裝中間列“高級模式”的角色定義、執行計劃、單次測試與多次模擬控制。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.components.common.collapsible_card import CollapsibleCard
from ui.components.common.sim_bottom_bar import SimBottomBar
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class AdvSimTab(ctk.CTkFrame):
    """高級模式獨立 UI 面板組件"""

    def __init__(
        self, 
        master: Any, 
        app_controller: Any = None, 
        on_run_sim: Optional[Callable[[], None]] = None,
        on_single_test: Optional[Callable[[], None]] = None,
        on_add_plan_step: Optional[Callable[[], None]] = None,
        on_clear_plan: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.app = app_controller
        self.on_run_sim = on_run_sim or kwargs.get("on_run_sim")
        self.on_single_test = on_single_test or kwargs.get("on_single_test")
        self.on_add_plan_step = on_add_plan_step or kwargs.get("on_add_plan_step")
        self.on_clear_plan = on_clear_plan or kwargs.get("on_clear_plan")

        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(master=master, fg_color="transparent", **ctk_kwargs)
        self._build_ui()

    def _build_ui(self):
        # 1. 🌟 底部控制欄（通過 sim_row_callback 平鋪插入“單次測試”按鈕）
        def build_adv_extra_buttons(sim_row):
            ctk.CTkButton(
                sim_row, 
                text="單次測試", 
                command=self._handle_single_test, 
                fg_color=PALETTE["secondary"], 
                text_color=PALETTE["text_main"], 
                hover_color=PALETTE["secondary_hover"], 
                font=FONT_GLOBAL, 
                width=70, 
                height=26
            ).pack(side=tk.LEFT, padx=8)

        self.bottom_bar = SimBottomBar(
            self, 
            on_run_sim=self._handle_run_sim,
            sim_row_callback=build_adv_extra_buttons
        )
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=6, padx=8)

        # 2. 中間可滾動區
        self.adv_scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.adv_scroll_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=2, padx=4)

        # 3. 角色定義卡片
        self.roles_card = CollapsibleCard(self.adv_scroll_frame, title="角色定義")
        self.roles_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=4)
        self.adv_roles_container = self.roles_card.content_frame

        # 4. 執行計劃卡片
        self.plan_card = CollapsibleCard(self.adv_scroll_frame, title="執行計劃（可選）")
        self.plan_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=4)
        self.plan_card.add_header_button("+", command=self._handle_add_plan_step, width=24)
        self.plan_card.add_header_button("清空", command=self._handle_clear_plan, width=45)
        self.plan_list_frame = self.plan_card.content_frame

    def _handle_run_sim(self):
        if self.on_run_sim:
            self.on_run_sim()
        elif hasattr(self.app, "run_advanced_simulation"):
            self.app.run_advanced_simulation()

    def _handle_single_test(self):
        if self.on_single_test:
            self.on_single_test()
        elif hasattr(self.app, "run_advanced_single_test"):
            self.app.run_advanced_single_test()

    def _handle_add_plan_step(self):
        if self.on_add_plan_step:
            self.on_add_plan_step()
        elif hasattr(self.app, "add_plan_step"):
            self.app.add_plan_step()

    def _handle_clear_plan(self):
        if self.on_clear_plan:
            self.on_clear_plan()
        elif hasattr(self.app, "clear_plan"):
            self.app.clear_plan()

    @property
    def adv_sim_times(self): return self.bottom_bar.sim_times
    @property
    def adv_progress_bar(self): return self.bottom_bar.progress_bar
    @property
    def adv_progress_label(self): return self.bottom_bar.progress_label