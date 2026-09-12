# -*- coding: utf-8 -*-
"""
二次確認按鈕組件 (Confirm Button)
用「點一次進入確認狀態、限時內再點一次才真正觸發」取代彈窗確認，
避免刪除/清空這類危險操作因為位置靠近其他按鈕而被誤按。
"""

import customtkinter as ctk
from typing import Any, Callable, Optional

from ui.theme import PALETTE


class ConfirmButton(ctk.CTkButton):
    """危險操作用二次確認按鈕：第一次點擊進入「確認中」狀態，限時內再點一次才執行"""

    def __init__(
        self,
        master: Any,
        text: str,
        on_confirm: Callable[[], None],
        confirm_text: str = "確定？",
        arm_seconds: float = 3.0,
        **kwargs
    ):
        self._normal_text = text
        self._confirm_text = confirm_text
        self._on_confirm = on_confirm
        self._arm_seconds = arm_seconds
        self._armed = False
        self._disarm_job: Optional[str] = None

        self._normal_fg = kwargs.pop("fg_color", PALETTE["secondary"])
        self._normal_hover = kwargs.pop("hover_color", PALETTE["secondary_hover"])
        self._confirm_fg = PALETTE["danger"]

        super().__init__(
            master, text=text, command=self._handle_click,
            fg_color=self._normal_fg, hover_color=self._normal_hover,
            **kwargs
        )

    def _handle_click(self):
        if not self._armed:
            self._arm()
            return
        self._disarm()
        self._on_confirm()

    def _arm(self):
        self._armed = True
        self.configure(text=self._confirm_text, fg_color=self._confirm_fg, hover_color=self._confirm_fg)
        if self._disarm_job:
            self.after_cancel(self._disarm_job)
        self._disarm_job = self.after(int(self._arm_seconds * 1000), self._disarm)

    def _disarm(self):
        self._armed = False
        self._disarm_job = None
        try:
            self.configure(text=self._normal_text, fg_color=self._normal_fg, hover_color=self._normal_hover)
        except Exception:
            pass
