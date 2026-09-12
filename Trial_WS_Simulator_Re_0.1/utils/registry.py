# -*- coding: utf-8 -*-
"""
操作註冊中心 (Operation Registry) - CustomTkinter 適配版
統一管理所有算卡操作類型的元數據、UI 構建、參數提取與執行邏輯。
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Dict, List, Tuple, Any, Callable, Optional
from ui.components.app_dropdown import AppDropdown
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


def safe_trace(var: tk.Variable, mode: str, callback: Callable, store_dict: dict, key: str) -> str:
    """安全 Trace 綁定函數，防止頻繁重繪 UI 時回調函數不斷疊加導致的內存洩漏"""
    if key in store_dict and store_dict[key]:
        try:
            var.trace_vdelete(mode, store_dict[key])
        except Exception:
            pass
    tid = var.trace(mode, callback)
    store_dict[key] = tid
    return tid


class OperationRegistry:
    """統一操作註冊表類"""

    def __init__(self):
        self.types: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        type_name: str,
        params_def: Optional[List[Dict[str, Any]]] = None,
        build_extra: Optional[Callable] = None,
        extract_extra: Optional[Callable] = None,
        execute: Optional[Callable] = None,
        modes: Optional[List[str]] = None,
    ):
        """註冊一個新的操作類型"""
        self.types[type_name] = {
            "params": params_def or [],
            "build_extra": build_extra,
            "extract_extra": extract_extra,
            "execute": execute,
            "modes": modes or ["single", "regular", "char", "advanced"],
        }

    def get_type_names(self, mode: str, context: str = "") -> List[str]:
        """返回指定模式與上下文下所有可用的操作類型名稱"""
        names = []
        for name, info in self.types.items():
            if name == "取消傷害" and context != "cancel_trigger":
                continue
            if mode in info["modes"]:
                names.append(name)
        return names

    def build_widgets(
        self,
        op: dict,
        params_frame: ttk.Frame,
        linkage_frame: Optional[ttk.Frame],
        cancel_detail_frame: Optional[ttk.Frame],
        mode: str,
        steps_frame: Optional[ttk.Frame] = None,
        context: str = ""
    ):
        type_name = op["type_var"].get()
        if type_name not in self.types:
            return

        info = self.types[type_name]

        # 保底機制：若 build_extra 為空，自動觸發 OpWidgetFactory 進行補掛
        if not info.get("build_extra"):
            try:
                from ui.builders.op_widget_factory import OpWidgetFactory
                OpWidgetFactory.register_all_ui_builders()
                info = self.types[type_name]
            except Exception:
                pass

        params_def = info["params"]

        # 清除舊控件
        for widget in params_frame.winfo_children():
            widget.destroy()

        for extra_frame in (linkage_frame, cancel_detail_frame, steps_frame):
            if extra_frame:
                try:
                    extra_frame.grid_remove()
                except Exception:
                    pass
                try:
                    extra_frame.pack_forget()
                except Exception:
                    pass
                for widget in extra_frame.winfo_children():
                    widget.destroy()
                    
        op["controls"] = {}
        op["params"] = op.get("params", {})

        # 構建基礎控件
        for p in params_def:
            name = p["name"]
            default = p.get("default", 0)
            var_name = f"{name}_var"

            # 🌟 智能類型推導：若未顯式指定 var_type，根據 default 的 Python 類型自動綁定正確的 tk 變量類
            var_type = p.get("var_type")
            if var_type is None:
                if isinstance(default, bool):
                    var_type = tk.BooleanVar
                elif isinstance(default, float):
                    var_type = tk.DoubleVar
                elif isinstance(default, int) and not isinstance(default, bool):
                    var_type = tk.IntVar
                elif isinstance(default, str):
                    var_type = tk.StringVar
                else:
                    var_type = tk.StringVar

            if var_name not in op["params"]:
                op["params"][var_name] = var_type(value=default)
            var = op["params"][var_name]
            op["controls"][name] = var

            label_text = p.get("label", "")
            widget_type = p.get("widget", "entry")
            width = p.get("width", 4)
            values = p.get("values", None)

            if label_text:
                ctk.CTkLabel(
                    params_frame, 
                    text=label_text, 
                    text_color=PALETTE["text_main"],
                    font=FONT_GLOBAL
                ).pack(side=tk.LEFT, padx=2)

            if widget_type == "entry":
                entry = ctk.CTkEntry(
                    params_frame, 
                    textvariable=var, 
                    width=width * 10, 
                    height=26,
                    font=FONT_GLOBAL,
                    fg_color=PALETTE["secondary"],
                    border_color=PALETTE["input_border"],
                    border_width=1.5,
                    text_color=PALETTE["text_main"]
                )
                entry.pack(side=tk.LEFT, padx=2)
                op["controls"][name + "_entry"] = entry

            elif widget_type == "combobox":
                combo = AppDropdown(
                    params_frame,
                    variable=var,
                    values=values,
                    width=width * 14,
                )
                combo.pack(side=tk.LEFT, padx=2)
                op["controls"][name + "_combo"] = combo

            suffix = p.get("suffix", "")
            if suffix:
                suffix_label = ctk.CTkLabel(
                    params_frame, 
                    text=suffix, 
                    text_color=PALETTE["text_sub"],
                    font=FONT_GLOBAL
                )
                suffix_label.pack(side=tk.LEFT, padx=2)
                op["controls"][name + "_suffix_label"] = suffix_label

        if info.get("build_extra"):
            try:
                info["build_extra"](op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=context)
            except TypeError:
                info["build_extra"](op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame)

    def extract_params(self, op: dict) -> Dict[str, Any]:
        """從操作對象及其控件提取參數字典"""
        type_name = op["type_var"].get()
        if type_name not in self.types:
            return {"type": type_name}

        info = self.types[type_name]
        result = {"type": type_name}

        for p in info["params"]:
            name = p["name"]
            var_name = f"{name}_var"
            if var_name in op["params"]:
                result[name] = op["params"][var_name].get()

        if info.get("extract_extra"):
            extra = info["extract_extra"](op)
            result.update(extra)

        return result

    def execute(
        self,
        type_name: str,
        deck: list,
        control: list,
        stock: list,
        level: list,
        clock: list,
        op_params: dict,
        stabilize_func: Callable[[], bool],
        **kwargs,
    ) -> Tuple[bool, str, dict]:
        """執行指定操作類型"""
        if type_name not in self.types or not self.types[type_name]["execute"]:
            return False, "未知操作類型", {}
        return self.types[type_name]["execute"](
            deck, control, stock, level, clock, op_params, stabilize_func, **kwargs
        )


# 創建全局單例註冊表
registry = OperationRegistry()