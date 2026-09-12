# -*- coding: utf-8 -*-
"""單次操作評估選項卡組件"""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from ui.components.right_column.init_state_card import InitStateCard
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class SingleOpTab(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)

        # 初始局勢卡片
        self.init_card = InitStateCard(self.scroll_frame, default_summary="單次操作評估結果：未執行")
        self.init_card.pack(fill=tk.X, pady=(4, 6), padx=2)

        # 動態結果展示區
        self.result_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.result_frame.pack(fill=tk.BOTH, expand=True)