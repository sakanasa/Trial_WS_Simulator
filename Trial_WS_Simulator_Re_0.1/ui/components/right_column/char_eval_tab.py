# -*- coding: utf-8 -*-
"""单角色评估选项卡组件"""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from ui.components.right_column.init_state_card import InitStateCard


class CharEvalTab(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs):
        super().__init__(master=master, fg_color="transparent", **kwargs)
        self._build_ui()

    def _build_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)

        self.init_card = InitStateCard(self.scroll_frame, default_summary="单角色评估结果：未评估")
        self.init_card.pack(fill=tk.X, pady=(4, 6), padx=2)

        self.result_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.result_frame.pack(fill=tk.BOTH, expand=True)