# -*- coding: utf-8 -*-
"""
操作列表 UI 構建工具 (Ops List Builder)
負責統一管理所有模式（single, regular, char, advanced, condition）的操作控件列表的創建、重排、類型切換與操作增刪上移下移。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, List, Optional

from utils.registry import registry
from ui.components.app_dropdown import AppDropdown, CTkControlButtons


class OpsListBuilder:
    """操作列表通用渲染與邏輯構建工具類"""

    @classmethod
    def create_ops_list_ui(
        cls,
        ops_list: list,
        parent_frame: Any,
        mode: str,
        role: Optional[dict] = None,
        app_controller: Any = None
    ):
        """按 ops_list 的最新順序重新物理裝載與掛載所有操作行 UI 控件"""
        valid_containers = set()

        # 重排前先對所有已有容器解包 (pack_forget)，強迫 Tkinter 按新順序重新物理堆疊
        for op in ops_list:
            if "op_container" in op and op["op_container"].winfo_exists():
                try:
                    op["op_container"].pack_forget()
                except Exception:
                    pass

        for i, op in enumerate(ops_list):
            if "op_container" in op and op["op_container"].winfo_exists():
                op_container = op["op_container"]
                valid_containers.add(op_container)

                if mode != "single" and "ctrl_group" in op and op["ctrl_group"].winfo_exists():
                    op["ctrl_group"].configure_commands(
                        on_remove=lambda o=op: cls.remove_op_by_ref(ops_list, o, mode, role, app_controller),
                        on_add=lambda o=op: cls.add_op_by_ref(ops_list, o, mode, role, app_controller),
                        on_up=lambda o=op: cls.move_op_up_by_ref(ops_list, o, mode, role, app_controller),
                        on_down=lambda o=op: cls.move_op_down_by_ref(ops_list, o, mode, role, app_controller)
                    )

                op_container.pack(fill=tk.X, pady=2)

            else:
                op_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
                op_container.pack(fill=tk.X, pady=2)
                op["op_container"] = op_container

                row_frame = ctk.CTkFrame(op_container, fg_color="transparent")
                row_frame.grid(row=0, column=0, sticky="w")
                op["row_frame"] = row_frame

                if mode != "single":
                    ctrl_group = CTkControlButtons(
                        row_frame,
                        on_remove=lambda o=op: cls.remove_op_by_ref(ops_list, o, mode, role, app_controller),
                        on_add=lambda o=op: cls.add_op_by_ref(ops_list, o, mode, role, app_controller),
                        on_up=lambda o=op: cls.move_op_up_by_ref(ops_list, o, mode, role, app_controller),
                        on_down=lambda o=op: cls.move_op_down_by_ref(ops_list, o, mode, role, app_controller)
                    )
                    ctrl_group.grid(row=0, column=0, columnspan=4, padx=1)
                    op["ctrl_group"] = ctrl_group

                type_values = registry.get_type_names(mode)
                type_combo = AppDropdown(
                    row_frame,
                    variable=op["type_var"],
                    values=type_values,
                    width=110,
                    command=lambda val, o=op: cls.on_op_type_change(o, mode, role=role)
                )
                type_combo.grid(row=0, column=4, padx=2)

                # 🌟 顯式設置 width=1/height=1，防止空參數操作（如假洗能）被 CTkFrame 默認 200px 撐出長空格
                params_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=1, height=1)
                params_frame.grid(row=0, column=5, sticky="w", padx=2)
                op["params_frame"] = params_frame

                linkage_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
                op["linkage_frame"] = linkage_frame
                linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
                linkage_frame.grid_remove()

                cancel_detail_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
                op["cancel_detail_frame"] = cancel_detail_frame
                cancel_detail_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
                cancel_detail_frame.grid_remove()

                steps_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
                op["steps_frame"] = steps_frame
                steps_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
                steps_frame.grid_remove()

                registry.build_widgets(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame)
                valid_containers.add(op_container)

        for child in parent_frame.winfo_children():
            if child not in valid_containers:
                child.destroy()

    @classmethod
    def on_op_type_change(cls, op: dict, mode: str, role: Optional[dict] = None):
        """切換操作類型時的清理與重建

        🌟 重新創建 params_frame/linkage_frame/cancel_detail_frame/steps_frame
        （而非清空舊控件後複用舊容器），避免舊類型較寬的參數把容器撐大後，
        換成無參數類型（如假洗能）時尺寸沒有跟著縮回去，留下一大段空格。
        """
        op["params"].clear()
        op["controls"].clear()

        row_frame = op["row_frame"]
        op_container = op["op_container"]

        old_params_frame = op.get("params_frame")
        if old_params_frame is not None:
            old_params_frame.destroy()
        params_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=1, height=1)
        params_frame.grid(row=0, column=5, sticky="w", padx=2)
        op["params_frame"] = params_frame

        old_linkage_frame = op.get("linkage_frame")
        if old_linkage_frame is not None:
            old_linkage_frame.destroy()
        linkage_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
        linkage_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        linkage_frame.grid_remove()
        op["linkage_frame"] = linkage_frame

        old_cancel_detail_frame = op.get("cancel_detail_frame")
        if old_cancel_detail_frame is not None:
            old_cancel_detail_frame.destroy()
        cancel_detail_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
        cancel_detail_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        cancel_detail_frame.grid_remove()
        op["cancel_detail_frame"] = cancel_detail_frame

        old_steps_frame = op.get("steps_frame")
        if old_steps_frame is not None:
            old_steps_frame.destroy()
        steps_frame = ctk.CTkFrame(op_container, fg_color="transparent", width=1, height=1)
        steps_frame.grid(row=1, column=0, sticky="w", pady=(2, 0))
        steps_frame.grid_remove()
        op["steps_frame"] = steps_frame

        registry.build_widgets(op, params_frame, linkage_frame, cancel_detail_frame, mode, steps_frame)

        # 🌟 剛切換成「角色傷害」時，基礎傷害預設值改成跟該角色目前的初始魂點一致（而非寫死的0）
        if op["type_var"].get() == "角色傷害" and role is not None:
            base_var = op["params"].get("role_damage_base_var")
            soul_var = role.get("soul_var")
            if base_var is not None and soul_var is not None:
                try:
                    base_var.set(soul_var.get())
                except Exception:
                    pass

    @classmethod
    def clone_op(cls, source_op: dict) -> dict:
        """複製一個操作行的類型與目前所有參數數值（不含 UI 控件句柄）"""
        new_op = {
            "type_var": tk.StringVar(value=source_op["type_var"].get()),
            "params_frame": None, "row_frame": None, "linkage_frame": None,
            "cancel_detail_frame": None, "controls": {}, "params": {}
        }
        for key, val in source_op.get("params", {}).items():
            if isinstance(val, tk.Variable):
                new_op["params"][key] = type(val)(value=val.get())
            elif key == "steps_ops" and isinstance(val, list):
                new_op["params"][key] = [cls.clone_op(sub_op) for sub_op in val]
            else:
                new_op["params"][key] = val
        return new_op

    @classmethod
    def add_op(
        cls, ops_list: list, index: int, mode: str,
        role: Optional[dict] = None, app_controller: Any = None,
        template_op: Optional[dict] = None
    ):
        if template_op is not None:
            new_op = cls.clone_op(template_op)
        else:
            new_op = {
                "type_var": tk.StringVar(value="普通傷害"),
                "params_frame": None, "row_frame": None, "linkage_frame": None,
                "cancel_detail_frame": None, "controls": {}, "params": {}
            }
        ops_list.insert(index + 1, new_op)
        cls.refresh_ops_ui(ops_list, mode, role, app_controller)

    @classmethod
    def remove_op(cls, ops_list: list, index: int, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if len(ops_list) <= 1:
            return
        del ops_list[index]
        cls.refresh_ops_ui(ops_list, mode, role, app_controller)

    @classmethod
    def move_op_up(cls, ops_list: list, index: int, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if index > 0:
            ops_list[index], ops_list[index - 1] = ops_list[index - 1], ops_list[index]
            cls.refresh_ops_ui(ops_list, mode, role, app_controller)

    @classmethod
    def move_op_down(cls, ops_list: list, index: int, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if index < len(ops_list) - 1:
            ops_list[index], ops_list[index + 1] = ops_list[index + 1], ops_list[index]
            cls.refresh_ops_ui(ops_list, mode, role, app_controller)

    @classmethod
    def remove_op_by_ref(cls, ops_list: list, op: dict, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if len(ops_list) <= 1 or op not in ops_list:
            return
        idx = ops_list.index(op)
        cls.remove_op(ops_list, idx, mode, role, app_controller)

    @classmethod
    def add_op_by_ref(cls, ops_list: list, op: dict, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        idx = ops_list.index(op) if op in ops_list else len(ops_list) - 1
        cls.add_op(ops_list, idx, mode, role, app_controller, template_op=op)

    @classmethod
    def move_op_up_by_ref(cls, ops_list: list, op: dict, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if op in ops_list:
            idx = ops_list.index(op)
            cls.move_op_up(ops_list, idx, mode, role, app_controller)

    @classmethod
    def move_op_down_by_ref(cls, ops_list: list, op: dict, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        if op in ops_list:
            idx = ops_list.index(op)
            cls.move_op_down(ops_list, idx, mode, role, app_controller)

    @classmethod
    def refresh_ops_ui(cls, ops_list: list, mode: str, role: Optional[dict] = None, app_controller: Any = None):
        """根據模式刷新對應容器的操作列表 UI"""
        if mode == "regular" and app_controller and hasattr(app_controller, "middle_col"):
            cls.create_ops_list_ui(ops_list, app_controller.middle_col.reg_ops_frame, mode="regular", app_controller=app_controller)
        elif mode == "char" and app_controller and hasattr(app_controller, "left_col"):
            cls.create_ops_list_ui(ops_list, app_controller.left_col.char_sim_card.char_ops_frame, mode="char", app_controller=app_controller)
        elif mode == "advanced" and role and "ops_frame" in role:
            cls.create_ops_list_ui(role["ops"], role["ops_frame"], mode="advanced", role=role, app_controller=app_controller)
        elif mode == "condition" and role and "ops_frame" in role:
            cls.create_ops_list_ui(role["ops"], role["ops_frame"], mode="condition", role=role, app_controller=app_controller)