# -*- coding: utf-8 -*-
"""
工况模式模拟面板组件 (Condition Simulation Tab Component)
独立封装中间列“工况模式”的战场画布、角色定义、执行计划、存档/自定义卡片控制与多次模拟。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.components.common.collapsible_card import CollapsibleCard
from ui.components.common.sim_bottom_bar import SimBottomBar
from ui.components.field_canvas import ConditionFieldCanvas
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class CondSimTab(ctk.CTkFrame):
    """工况模式独立 UI 面板组件"""

    def __init__(
        self, 
        master: Any, 
        app_controller: Any = None, 
        on_run_sim: Optional[Callable[[], None]] = None,
        on_single_test: Optional[Callable[[], None]] = None,
        on_save_state: Optional[Callable[[], None]] = None,
        on_load_state: Optional[Callable[[], None]] = None,
        on_open_custom_cards: Optional[Callable[[], None]] = None,
        on_add_plan_step: Optional[Callable[[], None]] = None,
        on_clear_plan: Optional[Callable[[], None]] = None,
        on_zone_click: Optional[Callable[[str], None]] = None,
        on_overview_click: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.app = app_controller
        self.on_run_sim = on_run_sim or kwargs.get("on_run_sim")
        self.on_single_test = on_single_test or kwargs.get("on_single_test")
        self.on_save_state = on_save_state or kwargs.get("on_save_state")
        self.on_load_state = on_load_state or kwargs.get("on_load_state")
        self.on_open_custom_cards = on_open_custom_cards or kwargs.get("on_open_custom_cards")
        self.on_add_plan_step = on_add_plan_step or kwargs.get("on_add_plan_step")
        self.on_clear_plan = on_clear_plan or kwargs.get("on_clear_plan")
        self.on_zone_click = on_zone_click or kwargs.get("on_zone_click")
        self.on_overview_click = on_overview_click or kwargs.get("on_overview_click")

        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(master=master, fg_color="transparent", **ctk_kwargs)
        self._build_ui()

    def _build_ui(self):
        # 1. 🌟 底部控制区（通过 sim_row_callback 单层平铺，完美对齐）
        def build_cond_extra_buttons(sim_row):
            btn_aux_opts = {
                "font": FONT_GLOBAL,
                "fg_color": PALETTE["secondary"],
                "text_color": PALETTE["text_main"],
                "hover_color": PALETTE["secondary_hover"],
                "height": 26
            }
            ctk.CTkButton(sim_row, text="单次测试", command=self._handle_single_test, width=65, **btn_aux_opts).pack(side=tk.LEFT, padx=2)
            ctk.CTkLabel(sim_row, text="存档:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=(4, 2))
            ctk.CTkButton(sim_row, text="保存", command=self._handle_save_state, width=45, **btn_aux_opts).pack(side=tk.LEFT, padx=1)
            ctk.CTkButton(sim_row, text="导入", command=self._handle_load_state, width=45, **btn_aux_opts).pack(side=tk.LEFT, padx=1)
            ctk.CTkButton(sim_row, text="自定义卡片", command=self._handle_open_custom_cards, width=75, **btn_aux_opts).pack(side=tk.RIGHT, padx=2)

        self.bottom_bar = SimBottomBar(
            self, 
            on_run_sim=self._handle_run_sim,
            sim_row_callback=build_cond_extra_buttons
        )
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=6, padx=8)

        # 2. 中间可滚动区
        self.cond_scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.cond_scroll_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=2, padx=4)

        # 3. 场上情况卡片
        self.field_card = CollapsibleCard(self.cond_scroll_frame, title="场上情况")
        self.field_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=4)

        self.field_component = ConditionFieldCanvas(
            self.field_card.content_frame,
            on_zone_click=self._handle_zone_click,
            on_overview_click=self._handle_overview_click
        )
        self.field_component.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 4. 角色定义卡片
        self.roles_card = CollapsibleCard(self.cond_scroll_frame, title="角色定义")
        self.roles_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=4)
        self.condition_roles_container = self.roles_card.content_frame

        # 5. 执行计划卡片
        self.plan_card = CollapsibleCard(self.cond_scroll_frame, title="执行计划（可选）")
        self.plan_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=4)
        self.plan_card.add_header_button("+", command=self._handle_add_plan_step, width=24)
        self.plan_card.add_header_button("清空", command=self._handle_clear_plan, width=45)
        self.condition_plan_list_frame = self.plan_card.content_frame

    def _handle_run_sim(self):
        if self.on_run_sim:
            self.on_run_sim()
        elif hasattr(self.app, "run_condition_simulation"):
            self.app.run_condition_simulation()

    def _handle_single_test(self):
        if self.on_single_test:
            self.on_single_test()
        elif hasattr(self.app, "run_condition_single_test"):
            self.app.run_condition_single_test()

    def _handle_save_state(self):
        if self.on_save_state:
            self.on_save_state()
        elif hasattr(self.app, "save_condition_state"):
            self.app.save_condition_state()

    def _handle_load_state(self):
        if self.on_load_state:
            self.on_load_state()
        elif hasattr(self.app, "load_condition_state"):
            self.app.load_condition_state()

    def _handle_open_custom_cards(self):
        if self.on_open_custom_cards:
            self.on_open_custom_cards()
        elif hasattr(self.app, "open_custom_cards_dialog"):
            self.app.open_custom_cards_dialog()

    def _handle_add_plan_step(self):
        if self.on_add_plan_step:
            self.on_add_plan_step()
        elif hasattr(self.app, "add_condition_plan_step"):
            self.app.add_condition_plan_step()

    def _handle_clear_plan(self):
        if self.on_clear_plan:
            self.on_clear_plan()
        elif hasattr(self.app, "clear_condition_plan"):
            self.app.clear_condition_plan()

    def _handle_zone_click(self, zone_name: str):
        if self.on_zone_click:
            self.on_zone_click(zone_name)
        elif hasattr(self.app, "open_card_detail_window"):
            self.app.open_card_detail_window(zone_name)

    def _handle_overview_click(self):
        if self.on_overview_click:
            self.on_overview_click()
        elif hasattr(self.app, "show_condition_overview"):
            self.app.show_condition_overview()

    @property
    def cond_sim_times(self): return self.bottom_bar.sim_times
    @property
    def cond_progress_bar(self): return self.bottom_bar.progress_bar
    @property
    def cond_progress_label(self): return self.bottom_bar.progress_label