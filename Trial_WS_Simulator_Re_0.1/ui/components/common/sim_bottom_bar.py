# -*- coding: utf-8 -*-
"""
通用模擬控制底欄組件 (Simulation Bottom Bar Component)
統一管理模擬次數輸入框、多次模擬執行按鈕、進度條與附加動作區域。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional, Callable

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class SimBottomBar(ctk.CTkFrame):
    """通用模擬控制底欄組件"""

    def __init__(
        self, 
        master: Any, 
        on_run_sim: Optional[Callable[[], None]] = None,
        sim_times_default: int = 10000,
        sim_row_callback: Optional[Callable[[ctk.CTkFrame], None]] = None,
        **kwargs
    ):
        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }

        super().__init__(master=master, fg_color="transparent", **ctk_kwargs)

        self.on_run_sim = on_run_sim
        self.sim_row_callback = sim_row_callback
        self.sim_times = tk.IntVar(value=sim_times_default)

        self._build_ui()

    def _build_ui(self):
        # 1. 模擬次數輸入行（單層平鋪，徹底防止多層 Frame 嵌套引發對齊錯位）
        self.sim_row = ctk.CTkFrame(self, fg_color="transparent")
        self.sim_row.pack(fill=tk.X, pady=2)

        ctk.CTkLabel(self.sim_row, text="模擬次數:", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=2)

        ctk.CTkEntry(
            self.sim_row, 
            textvariable=self.sim_times, 
            width=65, 
            height=26,
            font=FONT_GLOBAL,
            fg_color=PALETTE["secondary"],
            border_color=PALETTE["input_border"],
            border_width=1.5,
            text_color=PALETTE["text_main"]
        ).pack(side=tk.LEFT, padx=2)

        # 🌟 鉤子回調：將模式特有的按鈕直接平鋪掛載在 sim_row 同一行上
        if self.sim_row_callback:
            self.sim_row_callback(self.sim_row)

        # 2. 模擬按鈕
        ctk.CTkButton(
            self, 
            text="多次傷害模擬", 
            command=self._handle_run_sim,
            fg_color=PALETTE["primary"], 
            hover_color=PALETTE["primary_hover"], 
            text_color=("#FFFFFF", "#0B0F19"),
            font=FONT_GLOBAL_BOLD,
            height=30
        ).pack(pady=6, fill=tk.X)

        # 3. 進度條與百分比
        self.progress_bar = ctk.CTkProgressBar(self, progress_color=PALETTE["primary"], height=8)
        self.progress_bar.pack(fill=tk.X, pady=2)
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(self, text="0%", text_color=PALETTE["text_sub"], font=FONT_GLOBAL)
        self.progress_label.pack(pady=2)

    def _handle_run_sim(self):
        if self.on_run_sim:
            self.on_run_sim()

    def get_sim_times(self) -> int:
        return self.sim_times.get()