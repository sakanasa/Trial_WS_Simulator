# -*- coding: utf-8 -*-
"""
具名存檔／匯入工具列組件 (Preset Toolbar)
用內嵌控件（輸入框＋下拉選單）取代彈窗，提供「命名存檔」與「下拉選擇匯入」的通用 UI。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Callable, List, Optional

from ui.theme import PALETTE, FONT_GLOBAL
from ui.components.app_dropdown import AppDropdown
from ui.components.common.confirm_button import ConfirmButton

NO_PRESET_LABEL = "(無存檔)"


class PresetToolbar(ctk.CTkFrame):
    """存檔／匯入具名紀錄的內嵌工具列（不使用彈窗）"""

    def __init__(
        self,
        master: Any,
        get_names: Callable[[], List[str]],
        on_save: Callable[[str], None],
        on_import: Callable[[str], None],
        on_delete: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.get_names = get_names
        self.on_save = on_save
        self.on_import = on_import
        self.on_delete = on_delete

        self.name_var = tk.StringVar()
        self.selected_var = tk.StringVar()
        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self.refresh_names()

    def _build_ui(self):
        entry_opts = {
            "height": 26,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"],
            "border_width": 1.5,
            "text_color": PALETTE["text_main"]
        }
        btn_opts = {
            "height": 26,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "text_color": PALETTE["text_main"],
            "hover_color": PALETTE["secondary_hover"]
        }

        save_row = ctk.CTkFrame(self, fg_color="transparent")
        save_row.pack(side=tk.TOP, fill=tk.X, pady=(0, 3))

        ctk.CTkEntry(
            save_row, textvariable=self.name_var, placeholder_text="輸入存檔名稱...",
            width=130, **entry_opts
        ).pack(side=tk.LEFT, padx=(0, 4))

        ctk.CTkButton(save_row, text="存檔", command=self._handle_save, width=48, **btn_opts).pack(side=tk.LEFT)

        import_row = ctk.CTkFrame(self, fg_color="transparent")
        import_row.pack(side=tk.TOP, fill=tk.X)

        self.dropdown = AppDropdown(
            import_row, variable=self.selected_var, values=[NO_PRESET_LABEL], width=130
        )
        self.dropdown.pack(side=tk.LEFT, padx=(0, 4))

        ctk.CTkButton(import_row, text="匯入", command=self._handle_import, width=48, **btn_opts).pack(side=tk.LEFT, padx=(0, 4))

        if self.on_delete:
            # 🌟 二次確認按鈕：避免緊鄰「匯入」導致誤刪存檔
            ConfirmButton(
                import_row, text="刪除", confirm_text="確定？",
                on_confirm=self._handle_delete, width=48,
                height=26, font=FONT_GLOBAL, text_color=PALETTE["text_main"]
            ).pack(side=tk.LEFT)

        ctk.CTkLabel(
            self, textvariable=self.status_var, text_color=PALETTE["text_sub"], font=FONT_GLOBAL
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

    def refresh_names(self):
        names = self.get_names() or []
        self.dropdown.configure(values=names if names else [NO_PRESET_LABEL])
        self.selected_var.set(names[0] if names else NO_PRESET_LABEL)

    def _handle_save(self):
        name = self.name_var.get().strip()
        if not name:
            return
        self.on_save(name)
        self.name_var.set("")
        self.refresh_names()
        self.status_var.set(f"已存檔「{name}」")

    def _handle_import(self):
        name = self.selected_var.get()
        if not name or name == NO_PRESET_LABEL:
            return
        self.on_import(name)
        self.status_var.set(f"已匯入「{name}」")

    def _handle_delete(self):
        name = self.selected_var.get()
        if not name or name == NO_PRESET_LABEL or not self.on_delete:
            return
        self.on_delete(name)
        self.refresh_names()
        self.status_var.set(f"已刪除「{name}」")
