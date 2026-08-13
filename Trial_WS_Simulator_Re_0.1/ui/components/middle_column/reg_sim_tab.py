# -*- coding: utf-8 -*-
"""
常规模式模拟面板组件 (Regular Simulation Tab Component)
独立封装中间列“常规模式”的操作列表、折叠交互、模拟次数与运行控制。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.components.common.collapsible_card import CollapsibleCard
from ui.components.common.sim_bottom_bar import SimBottomBar


class RegSimTab(ctk.CTkFrame):
    """常规模式独立 UI 面板组件"""

    def __init__(
        self, 
        master: Any, 
        app_controller: Any = None, 
        on_run_sim: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        self.app = app_controller
        self.on_run_sim = on_run_sim or kwargs.get("on_run_sim")

        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(master=master, fg_color="transparent", **ctk_kwargs)
        self._build_ui()

    def _build_ui(self):
        # 1. 🌟 底部控制栏
        self.bottom_bar = SimBottomBar(self, on_run_sim=self._handle_run_sim)
        self.bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=6, padx=8)

        # 2. 中间可滚动区
        self.reg_ops_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.reg_ops_scroll.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=2, padx=4)

        # 3. 🌟 使用 CollapsibleCard 自动构建卡片与折叠功能
        self.ops_card = CollapsibleCard(self.reg_ops_scroll, title="常规操作列表")
        self.ops_card.pack(side=tk.TOP, fill=tk.X, anchor="n", padx=2, pady=2)
        self.reg_ops_frame = self.ops_card.content_frame

    def _handle_run_sim(self):
        if self.on_run_sim:
            self.on_run_sim()
        elif hasattr(self.app, "run_regular_simulation"):
            self.app.run_regular_simulation()

    # 向下兼容属性
    @property
    def reg_sim_times(self): return self.bottom_bar.sim_times
    @property
    def reg_progress_bar(self): return self.bottom_bar.progress_bar
    @property
    def reg_progress_label(self): return self.bottom_bar.progress_label