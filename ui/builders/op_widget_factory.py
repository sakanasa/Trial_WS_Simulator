# -*- coding: utf-8 -*-
"""
操作 UI 控件工廠 (Operation Widget Factory) - 全量排查防溢出版
負責所有複雜算卡操作二級 UI 控件的生成與聯動渲染。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any

from utils.registry import registry, safe_trace
from ui.components.app_dropdown import AppDropdown
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


def _build_role_damage_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=""):
    bonus_values = ["魂點", "0", "取消傷害"] if context == "cancel_trigger" else ["魂點", "0"]
    combo = op["controls"].get("role_bonus_type_combo")
    if combo and hasattr(combo, "configure"):
        combo.configure(values=bonus_values)


def _build_shoot_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame):
    mode_var = op["params"]["shoot_mode_var"]
    shoot_label = op["controls"].get("shoot_mode_suffix_label")
    count_entry = op["controls"].get("shoot_count_entry")
    count_suffix = op["controls"].get("shoot_count_suffix_label")

    def update_visibility(*args):
        if mode_var.get() == "牌組":
            if shoot_label: shoot_label.pack(side=tk.LEFT, padx=2)
            if count_entry: count_entry.pack(side=tk.LEFT, padx=2)
            if count_suffix: count_suffix.pack(side=tk.LEFT, padx=2)
        else:
            if shoot_label: shoot_label.pack_forget()
            if count_entry: count_entry.pack_forget()
            if count_suffix: count_suffix.pack_forget()

    safe_trace(mode_var, "w", update_visibility, op.setdefault("_trace_ids", {}), "shoot_mode")
    update_visibility()


def _build_top_deck_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame):
    mode_var = op["params"]["top_deck_mode_var"]
    count_entry = op["controls"].get("top_deck_count_entry")
    count_label = op["controls"].get("top_deck_count_suffix_label")

    def update_visibility(*args):
        if mode_var.get() == "控室":
            if count_entry: count_entry.pack(side=tk.LEFT, padx=2)
            if count_label: count_label.pack(side=tk.LEFT)
        else:
            if count_entry: count_entry.pack_forget()
            if count_label: count_label.pack_forget()

    safe_trace(mode_var, "w", update_visibility, op.setdefault("_trace_ids", {}), "top_deck_mode")
    update_visibility()


def _build_special_linkage_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame):
    char_var = op["params"]["special_char_var"]
    entry = op["controls"].get("hayakawa_count_entry")
    suffix_label = op["controls"].get("hayakawa_count_suffix_label")
    combo = op["controls"].get("special_char_combo")

    if combo and hasattr(combo, "configure"):
        if mode == "condition":
            combo.configure(values=["早川秋", "源櫻", "藍頭盔", "泳裝千束", "泳裝瀧奈"])
        else:
            combo.configure(values=["早川秋", "源櫻"])
            if char_var.get() in ("藍頭盔", "泳裝千束", "泳裝瀧奈"):
                char_var.set("早川秋")

    def update_visibility(*args):
        if char_var.get() == "早川秋":
            if entry: entry.pack(side=tk.LEFT, padx=2)
            if suffix_label: suffix_label.pack(side=tk.LEFT, padx=2)
        else:
            if entry: entry.pack_forget()
            if suffix_label: suffix_label.pack_forget()

    safe_trace(char_var, "w", update_visibility, op.setdefault("_trace_ids", {}), "special_char")
    update_visibility()


def _extract_special_linkage_extra(op):
    return {
        "special_char": op["params"].get("special_char_var", tk.StringVar(value="早川秋")).get(),
        "hayakawa_count": op["params"].get("hayakawa_count_var", tk.IntVar(value=0)).get()
    }


def _rebuild_sub_op_ui(params_frame, linkage_frame, cancel_detail_frame, steps_frame, sub_op, m):
    registry.build_widgets(
        sub_op, 
        params_frame, 
        linkage_frame, 
        cancel_detail_frame, 
        m, 
        steps_frame=steps_frame, 
        context="cancel_trigger"
    )


def _build_cancel_trigger_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=""):
    if "sub_mode_var" not in op["params"]:
        op["params"]["sub_mode_var"] = tk.StringVar(value="單次觸發")
    sub_mode_var = op["params"]["sub_mode_var"]

    values = ["單次觸發", "多次觸發"]
    if mode in ("advanced", "condition"):
        values.append("傳火")

    sub_mode_combo = AppDropdown(
        params_frame, 
        variable=sub_mode_var, 
        values=values, 
        width=100,
        command=lambda val: update_detail_ui()
    )
    sub_mode_combo.pack(side=tk.LEFT, padx=2)

    if "total_triggers_var" not in op["params"]:
        op["params"]["total_triggers_var"] = tk.IntVar(value=1)
    total_var = op["params"]["total_triggers_var"]

    if "pass_target_var" not in op["params"]:
        op["params"]["pass_target_var"] = tk.IntVar(value=1)

    if "nested_ops" not in op["params"]:
        op["params"]["nested_ops"] = []

    total_frame = ctk.CTkFrame(params_frame, fg_color="transparent", height=28)
    ctk.CTkLabel(total_frame, text="共計觸發", text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=26).pack(side=tk.LEFT, padx=2)
    ctk.CTkEntry(
        total_frame, 
        textvariable=total_var, 
        width=40, 
        height=26, 
        font=FONT_GLOBAL, 
        fg_color=PALETTE["secondary"], 
        border_color=PALETTE["input_border"],
        border_width=1.5,
        text_color=PALETTE["text_main"]
    ).pack(side=tk.LEFT, padx=2)
    ctk.CTkLabel(total_frame, text="次", text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=26).pack(side=tk.LEFT, padx=2)

    pass_target_frame = ctk.CTkFrame(params_frame, fg_color="transparent", height=28)
    ctk.CTkLabel(pass_target_frame, text="傳給角色", text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=26).pack(side=tk.LEFT, padx=2)
    ctk.CTkEntry(
        pass_target_frame, 
        textvariable=op["params"]["pass_target_var"], 
        width=40, 
        height=26, 
        font=FONT_GLOBAL, 
        fg_color=PALETTE["secondary"], 
        border_color=PALETTE["input_border"],
        border_width=1.5,
        text_color=PALETTE["text_main"]
    ).pack(side=tk.LEFT, padx=2)

    bold_font = FONT_GLOBAL_BOLD
    op["_last_sub_mode"] = None

    def update_detail_ui(*args):
        if not cancel_detail_frame or not cancel_detail_frame.winfo_exists():
            return

        smode = sub_mode_var.get()

        if smode == "多次觸發":
            try:
                n = total_var.get()
            except (tk.TclError, ValueError):
                return
            n = max(1, min(int(n), 10))
        else:
            n = 1

        if smode == "多次觸發":
            total_frame.pack(side=tk.LEFT, padx=2)
            pass_target_frame.pack_forget()
        elif smode == "傳火":
            total_frame.pack_forget()
            pass_target_frame.pack(side=tk.LEFT, padx=2)
        else:
            total_frame.pack_forget()
            pass_target_frame.pack_forget()

        if op.get("_last_sub_mode") != smode:
            op["_last_sub_mode"] = smode
            for widget in cancel_detail_frame.winfo_children():
                widget.destroy()
            op["params"]["nested_ops"].clear()

        if hasattr(cancel_detail_frame, "grid_info") and cancel_detail_frame.grid_info():
            cancel_detail_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            try:
                cancel_detail_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
            except tk.TclError:
                cancel_detail_frame.pack(side=tk.TOP, fill=tk.X, padx=(16, 0), pady=(2, 0))

        nested_list = op["params"]["nested_ops"]

        while len(nested_list) > n:
            removed_op = nested_list.pop()
            row_frame = removed_op.get("row_frame")
            if row_frame and row_frame.winfo_exists():
                row_frame.destroy()

        for idx in range(n):
            if idx < len(nested_list):
                sub_op = nested_list[idx]
                row_frame = sub_op.get("row_frame")
                if row_frame and row_frame.winfo_exists():
                    continue
            else:
                sub_op = {
                    "type_var": tk.StringVar(value="普通傷害"),
                    "controls": {}, "params": {}
                }
                nested_list.append(sub_op)

            try:
                sub_op_container = ctk.CTkFrame(cancel_detail_frame, fg_color="transparent")
                sub_op_container.pack(side=tk.TOP, fill=tk.X, pady=2, padx=2)
                sub_op["row_frame"] = sub_op_container

                row_frame = ctk.CTkFrame(sub_op_container, fg_color="transparent", height=28)
                row_frame.pack(side=tk.TOP, fill=tk.X)

                label_txt = f"第{idx+1}次取消觸發:" if smode == "多次觸發" else "取消觸發效果:"
                lbl = ctk.CTkLabel(
                    row_frame, 
                    text=label_txt, 
                    font=bold_font, 
                    text_color=PALETTE["text_main"], 
                    height=26
                )
                lbl.pack(side=tk.LEFT, padx=(0, 4))
                sub_op["label_widget"] = lbl

                type_values = registry.get_type_names(mode, context="cancel_trigger")
                sub_params_frame = ctk.CTkFrame(row_frame, fg_color="transparent", height=28)

                sub_linkage_frame = ctk.CTkFrame(sub_op_container, fg_color="transparent")
                sub_cancel_detail_frame = ctk.CTkFrame(sub_op_container, fg_color="transparent")
                sub_steps_frame = ctk.CTkFrame(sub_op_container, fg_color="transparent")

                def _make_change_cmd(so, sf, slf, scdf, ssf):
                    return lambda val: _rebuild_sub_op_ui(sf, slf, scdf, ssf, so, mode)

                sub_combo = AppDropdown(
                    row_frame, 
                    variable=sub_op["type_var"], 
                    values=type_values, 
                    width=110,
                    command=_make_change_cmd(sub_op, sub_params_frame, sub_linkage_frame, sub_cancel_detail_frame, sub_steps_frame)
                )
                sub_combo.pack(side=tk.LEFT, padx=2)

                sub_params_frame.pack(side=tk.LEFT, padx=2)
                
                _rebuild_sub_op_ui(
                    sub_params_frame, 
                    sub_linkage_frame, 
                    sub_cancel_detail_frame, 
                    sub_steps_frame, 
                    sub_op, 
                    mode
                )
            except Exception as err:
                print(f"[WARN] 追加取消觸發第 {idx+1} 行暫態警告: {err}")

    safe_trace(sub_mode_var, "w", update_detail_ui, op.setdefault("_trace_ids", {}), "sub_mode")
    safe_trace(total_var, "w", update_detail_ui, op.setdefault("_trace_ids", {}), "total_triggers")
    update_detail_ui()


def _extract_cancel_trigger_extra(op):
    result = {}
    if "sub_mode_var" in op["params"]:
        result["sub_mode"] = op["params"]["sub_mode_var"].get()

    smode = result.get("sub_mode")
    nested_list = op["params"].get("nested_ops", [])

    if smode in ("單次觸發", "傳火"):
        if nested_list:
            result["nested_op"] = registry.extract_params(nested_list[0])
        if smode == "傳火":
            result["pass_target"] = op["params"].get("pass_target_var", tk.IntVar(value=1)).get()

    elif smode == "多次觸發":
        result["total_triggers"] = op["params"].get("total_triggers_var", tk.IntVar(value=1)).get()
        result["nested_ops"] = [registry.extract_params(sub_op) for sub_op in nested_list]

    return result


def _build_bottom_drain_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame):
    if linkage_frame:
        if hasattr(linkage_frame, "grid_info") and linkage_frame.grid_info():
            linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            try:
                linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
            except tk.TclError:
                linkage_frame.pack(side=tk.TOP, fill=tk.X, padx=(16, 0), pady=(2, 0))
        
        for widget in linkage_frame.winfo_children():
            widget.destroy()

        if "linkage_type_var" not in op["params"]:
            op["params"]["linkage_type_var"] = tk.StringVar(value="有潮")
        linkage_type_var = op["params"]["linkage_type_var"]

        combo = AppDropdown(
            linkage_frame,
            variable=linkage_type_var,
            values=["有潮", "潮數"],
            width=70,
            command=lambda val: _update_linkage_params(op)
        )
        combo.grid(row=0, column=2, sticky="w", padx=2)

        linkage_params_frame = ctk.CTkFrame(linkage_frame, fg_color="transparent")
        linkage_params_frame.grid(row=0, column=3, sticky="w", padx=5)
        op["controls"]["linkage_params_frame"] = linkage_params_frame

        _update_linkage_params(op)


def _update_linkage_params(op):
    linkage_type = op["params"]["linkage_type_var"].get()
    frame = op["controls"]["linkage_params_frame"]
    
    for widget in frame.winfo_children():
        widget.destroy()

    entry_opts = {
        "width": 30,
        "height": 26,
        "font": FONT_GLOBAL,
        "fg_color": PALETTE["secondary"],
        "border_color": PALETTE["input_border"],
        "border_width": 1.5,
        "text_color": PALETTE["text_main"]
    }

    if linkage_type == "有潮":
        if "burn_damage_var" not in op["params"]:
            op["params"]["burn_damage_var"] = tk.IntVar(value=1)
        if "burn_times_var" not in op["params"]:
            op["params"]["burn_times_var"] = tk.IntVar(value=1)

        ctk.CTkLabel(frame, text="燒", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=2)
        ctk.CTkEntry(frame, textvariable=op["params"]["burn_damage_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(frame, text="點傷害", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=2)
        ctk.CTkEntry(frame, textvariable=op["params"]["burn_times_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(frame, text="次", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=2)
    else:
        if "base_damage_var" not in op["params"]:
            op["params"]["base_damage_var"] = tk.IntVar(value=3)
        if "damage_bonus_var" not in op["params"]:
            op["params"]["damage_bonus_var"] = tk.StringVar(value="0")
        if "base_times_var" not in op["params"]:
            op["params"]["base_times_var"] = tk.IntVar(value=0)
        if "times_bonus_var" not in op["params"]:
            op["params"]["times_bonus_var"] = tk.StringVar(value="潮數")

        ctk.CTkLabel(frame, text="燒(", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(frame, textvariable=op["params"]["base_damage_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(frame, text="+", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        
        AppDropdown(frame, variable=op["params"]["damage_bonus_var"], values=["0", "潮數"], width=65).pack(side=tk.LEFT, padx=2)
        
        ctk.CTkLabel(frame, text=")點傷害(", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(frame, textvariable=op["params"]["base_times_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(frame, text="+", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        
        AppDropdown(frame, variable=op["params"]["times_bonus_var"], values=["0", "潮數"], width=65).pack(side=tk.LEFT, padx=2)
        
        ctk.CTkLabel(frame, text=")次", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)


def _extract_bottom_drain_extra(op):
    result = {}
    if "linkage_type_var" in op["params"]:
        result["linkage_type"] = op["params"]["linkage_type_var"].get()
    if result.get("linkage_type") == "有潮":
        result["burn_damage"] = op["params"].get("burn_damage_var", tk.IntVar(value=1)).get()
        result["burn_times"] = op["params"].get("burn_times_var", tk.IntVar(value=1)).get()
    else:
        result["base_damage"] = op["params"].get("base_damage_var", tk.IntVar(value=3)).get()
        result["damage_bonus"] = op["params"].get("damage_bonus_var", tk.StringVar(value="0")).get()
        result["base_times"] = op["params"].get("base_times_var", tk.IntVar(value=0)).get()
        result["times_bonus"] = op["params"].get("times_bonus_var", tk.StringVar(value="潮數")).get()
    return result

def _build_multi_step_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=""):
    """🌟 修復版多步驟 UI 構建器：優先複用已反序列化好的 steps_ops"""
    if "steps_ops" in op["params"] and op["params"]["steps_ops"]:
        if "step_count_var" not in op["params"]:
            op["params"]["step_count_var"] = tk.IntVar(value=len(op["params"]["steps_ops"]))
        else:
            op["params"]["step_count_var"].set(len(op["params"]["steps_ops"]))
    else:
        if "step_count_var" not in op["params"]:
            op["params"]["step_count_var"] = tk.IntVar(value=1)
        if "steps_ops" not in op["params"]:
            op["params"]["steps_ops"] = []

    step_count_var = op["params"]["step_count_var"]

    entry_opts = {
        "width": 30,
        "height": 26,
        "font": FONT_GLOBAL,
        "fg_color": PALETTE["secondary"],
        "border_color": PALETTE.get("input_border", PALETTE["card_border"]),
        "border_width": 1.5,
        "text_color": PALETTE["text_main"]
    }

    count_frame = ctk.CTkFrame(params_frame, fg_color="transparent", height=28)
    count_frame.pack(side=tk.LEFT, padx=2)
    ctk.CTkLabel(count_frame, text="步數:", text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=26).pack(side=tk.LEFT, padx=2)
    ctk.CTkEntry(count_frame, textvariable=step_count_var, **entry_opts).pack(side=tk.LEFT, padx=2)

    if steps_frame is not None:
        if hasattr(steps_frame, "grid_info") and steps_frame.grid_info():
            steps_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            try:
                steps_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
            except tk.TclError:
                steps_frame.pack(side=tk.TOP, fill=tk.X, padx=(16, 0), pady=(2, 0))

    container = steps_frame if steps_frame is not None else params_frame

    def update_steps_ui(*args):
        try:
            n = step_count_var.get()
        except (tk.TclError, ValueError):
            return
        n = max(1, min(int(n), 10))

        steps_list = op["params"]["steps_ops"]

        while len(steps_list) > n:
            removed_op = steps_list.pop()
            row_frame = removed_op.get("row_frame")
            if row_frame and row_frame.winfo_exists():
                row_frame.destroy()

        for idx in range(n):
            if idx < len(steps_list):
                sub_op = steps_list[idx]
                row_frame = sub_op.get("row_frame")
                if row_frame and row_frame.winfo_exists():
                    continue
            else:
                sub_op = {
                    "type_var": tk.StringVar(value="普通傷害"),
                    "controls": {}, "params": {}
                }
                steps_list.append(sub_op)

            step_container = ctk.CTkFrame(container, fg_color="transparent")
            step_container.pack(side=tk.TOP, fill=tk.X, pady=2)
            sub_op["row_frame"] = step_container

            row_frame = ctk.CTkFrame(step_container, fg_color="transparent", height=28)
            row_frame.pack(side=tk.TOP, fill=tk.X)

            ctk.CTkLabel(row_frame, text=f"第{idx+1}步:", text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=26).pack(side=tk.LEFT, padx=2)

            sub_params_frame = ctk.CTkFrame(row_frame, fg_color="transparent", height=28)

            sub_linkage_frame = ctk.CTkFrame(step_container, fg_color="transparent")
            sub_cancel_detail_frame = ctk.CTkFrame(step_container, fg_color="transparent")
            sub_steps_frame = ctk.CTkFrame(step_container, fg_color="transparent")

            def _make_change_cmd(so, sf, slf, scdf, ssf):
                return lambda val: _rebuild_sub_op_ui(sf, slf, scdf, ssf, so, mode)

            type_values = registry.get_type_names(mode)
            type_combo = AppDropdown(
                row_frame,
                variable=sub_op["type_var"],
                values=type_values,
                width=110,
                command=_make_change_cmd(sub_op, sub_params_frame, sub_linkage_frame, sub_cancel_detail_frame, sub_steps_frame)
            )
            type_combo.pack(side=tk.LEFT, padx=2)
            sub_params_frame.pack(side=tk.LEFT, padx=2)

            registry.build_widgets(
                sub_op,
                sub_params_frame,
                sub_linkage_frame,
                sub_cancel_detail_frame,
                mode,
                steps_frame=sub_steps_frame,
                context=context
            )

    safe_trace(step_count_var, "w", update_steps_ui, op.setdefault("_trace_ids", {}), "step_count")
    update_steps_ui()


def _extract_multi_step_extra(op):
    result = {}
    if "step_count_var" in op["params"]:
        result["step_count"] = op["params"]["step_count_var"].get()
        steps_list = op["params"].get("steps_ops", [])
        result["steps"] = [registry.extract_params(sub_op) for sub_op in steps_list[:result["step_count"]]]
    return result


def _build_top_check_burn_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=""):
    """翻頂燒二級 UI 構建：在第二行渲染燒(傷害+加成)點傷害X次"""
    if linkage_frame:
        if hasattr(linkage_frame, "grid_info") and linkage_frame.grid_info():
            linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            try:
                linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
            except tk.TclError:
                linkage_frame.pack(side=tk.TOP, fill=tk.X, padx=(16, 0), pady=(2, 0))

        for widget in linkage_frame.winfo_children():
            widget.destroy()

        if "burn_damage_var" not in op["params"]:
            op["params"]["burn_damage_var"] = tk.IntVar(value=1)
        if "burn_bonus_type_var" not in op["params"]:
            op["params"]["burn_bonus_type_var"] = tk.StringVar(value="0")
        if "burn_times_var" not in op["params"]:
            op["params"]["burn_times_var"] = tk.IntVar(value=1)

        entry_opts = {
            "width": 30,
            "height": 26,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"],
            "border_width": 1.5,
            "text_color": PALETTE["text_main"]
        }

        ctk.CTkLabel(linkage_frame, text="燒(", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(linkage_frame, textvariable=op["params"]["burn_damage_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text="+", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        AppDropdown(linkage_frame, variable=op["params"]["burn_bonus_type_var"], values=["0", "等級", "基礎魂點"], width=75).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text=")點傷害", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(linkage_frame, textvariable=op["params"]["burn_times_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text="次", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)


def _extract_top_check_burn_extra(op):
    return {
        "burn_damage": op["params"].get("burn_damage_var", tk.IntVar(value=1)).get(),
        "burn_bonus_type": op["params"].get("burn_bonus_type_var", tk.StringVar(value="0")).get(),
        "burn_times": op["params"].get("burn_times_var", tk.IntVar(value=1)).get(),
    }


def _build_top_push_burn_extra(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame, context=""):
    """🌟 修復：推頂燒二級 UI 構建，把超寬的燒點數與次數移到第二行，防止水平遮擋隱形"""
    if linkage_frame:
        if hasattr(linkage_frame, "grid_info") and linkage_frame.grid_info():
            linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        else:
            try:
                linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
            except tk.TclError:
                linkage_frame.pack(side=tk.TOP, fill=tk.X, padx=(16, 0), pady=(2, 0))

        for widget in linkage_frame.winfo_children():
            widget.destroy()

        if "base_damage_var" not in op["params"]:
            op["params"]["base_damage_var"] = tk.IntVar(value=1)
        if "damage_bonus_var" not in op["params"]:
            op["params"]["damage_bonus_var"] = tk.StringVar(value="0")
        if "base_times_var" not in op["params"]:
            op["params"]["base_times_var"] = tk.IntVar(value=1)
        if "times_bonus_var" not in op["params"]:
            op["params"]["times_bonus_var"] = tk.StringVar(value="0")

        entry_opts = {
            "width": 30,
            "height": 26,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"],
            "border_width": 1.5,
            "text_color": PALETTE["text_main"]
        }

        ctk.CTkLabel(linkage_frame, text="燒(", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(linkage_frame, textvariable=op["params"]["base_damage_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text="+", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        AppDropdown(linkage_frame, variable=op["params"]["damage_bonus_var"], values=["0", "潮數", "觸發魂點", "等級"], width=100).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text=")點(", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        ctk.CTkEntry(linkage_frame, textvariable=op["params"]["base_times_var"], **entry_opts).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text="+", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)
        AppDropdown(linkage_frame, variable=op["params"]["times_bonus_var"], values=["0", "潮數", "觸發魂點", "等級"], width=100).pack(side=tk.LEFT, padx=2)
        ctk.CTkLabel(linkage_frame, text=")次", text_color=PALETTE["text_main"], font=FONT_GLOBAL).pack(side=tk.LEFT, padx=1)


def _extract_top_push_burn_extra(op):
    return {
        "push_count": op["params"].get("push_count_var", tk.IntVar(value=1)).get(),
        "base_damage": op["params"].get("base_damage_var", tk.IntVar(value=1)).get(),
        "damage_bonus": op["params"].get("damage_bonus_var", tk.StringVar(value="0")).get(),
        "base_times": op["params"].get("base_times_var", tk.IntVar(value=1)).get(),
        "times_bonus": op["params"].get("times_bonus_var", tk.StringVar(value="0")).get(),
    }


class OpWidgetFactory:
    """註冊並綁定所有算卡操作的 UI 繪製工廠類"""

    @classmethod
    def register_all_ui_builders(cls):
        """統一將界面構建器與參數提取器掛載到 registry"""
        import core.operations
        import core.condition_operations

        builder_map = {
            "角色傷害": (_build_role_damage_extra, None),
            "射血": (_build_shoot_extra, None),
            "上頂": (_build_top_deck_extra, None),
            "特殊聯動": (_build_special_linkage_extra, _extract_special_linkage_extra),
            "取消觸發": (_build_cancel_trigger_extra, _extract_cancel_trigger_extra),
            "拔底聯動": (_build_bottom_drain_extra, _extract_bottom_drain_extra),
            "多步驟操作": (_build_multi_step_extra, _extract_multi_step_extra),
            "翻頂燒": (_build_top_check_burn_extra, _extract_top_check_burn_extra),
            "推頂燒": (_build_top_push_burn_extra, _extract_top_push_burn_extra), # 🌟 新增推頂燒構建器
        }

        for type_name, (b_extra, e_extra) in builder_map.items():
            if type_name in registry.types:
                if b_extra:
                    registry.types[type_name]["build_extra"] = b_extra
                if e_extra:
                    registry.types[type_name]["extract_extra"] = e_extra


OpWidgetFactory.register_all_ui_builders()