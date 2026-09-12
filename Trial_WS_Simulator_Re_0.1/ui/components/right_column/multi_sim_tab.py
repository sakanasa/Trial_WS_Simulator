# -*- coding: utf-8 -*-
"""多次模擬統計結果選項卡組件"""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class MultiSimTab(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.winrate_label = ctk.CTkLabel(self, text="斬殺率: ", font=FONT_GLOBAL_BOLD, text_color=PALETTE["primary"])
        self.winrate_label.pack(anchor="w", pady=6, padx=6)

        self.avg_damage_label = ctk.CTkLabel(self, text="平均傷害: ", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"])
        self.avg_damage_label.pack(anchor="w", pady=6, padx=6)

        ctk.CTkFrame(self, height=1, fg_color=PALETTE["card_border"]).pack(fill=tk.X, pady=8, padx=6)

        self.ci_label = ctk.CTkLabel(self, text="95%置信區間: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.ci_label.pack(anchor="w", pady=3, padx=6)

        self.diff_label = ctk.CTkLabel(self, text="顯著差異所需最小差值: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.diff_label.pack(anchor="w", pady=3, padx=6)

        self.time_label = ctk.CTkLabel(self, text="運行時間: ", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.time_label.pack(anchor="w", pady=3, padx=6)