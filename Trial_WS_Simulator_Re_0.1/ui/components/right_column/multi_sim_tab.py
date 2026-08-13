# -*- coding: utf-8 -*-
"""多次模拟统计结果选项卡组件"""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class MultiSimTab(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.winrate_label = ctk.CTkLabel(self, text="斩杀率: ", font=FONT_GLOBAL_BOLD, text_color=PALETTE["primary"])
        self.winrate_label.pack(anchor="w", pady=6, padx=6)

        self.avg_damage_label = ctk.CTkLabel(self, text="平均伤害: ", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"])
        self.avg_damage_label.pack(anchor="w", pady=6, padx=6)

        ctk.CTkFrame(self, height=1, fg_color=PALETTE["card_border"]).pack(fill=tk.X, pady=8, padx=6)

        self.ci_label = ctk.CTkLabel(self, text="95%置信区间: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.ci_label.pack(anchor="w", pady=3, padx=6)

        self.diff_label = ctk.CTkLabel(self, text="显著差异所需最小差值: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.diff_label.pack(anchor="w", pady=3, padx=6)

        self.time_label = ctk.CTkLabel(self, text="运行时间: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.time_label.pack(anchor="w", pady=3, padx=6)