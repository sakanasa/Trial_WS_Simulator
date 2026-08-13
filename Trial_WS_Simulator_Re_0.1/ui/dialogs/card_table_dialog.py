# -*- coding: utf-8 -*-
"""
卡区卡牌明细编辑弹窗 (Card Table Dialog)
"""

import copy
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from typing import Any, List, Optional

from core.models import card_is_normal, card_is_climax
from ui.components.app_dropdown import AppDropdown
from ui.dialogs.select_from_library_dialog import SelectFromLibraryDialog
from ui.components.common.animations import animate_widget_bg, animate_delete_red_glow  # 🌟 引入通用动画
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class CardTableDialog(ctk.CTkToplevel):
    def __init__(self, parent: tk.Widget, source_name: str, app_controller: Any, **kwargs):
        ctk_kwargs = {
            k: v for k, v in kwargs.items() 
            if k in ("width", "height", "fg_color", "bg_color", "corner_radius", "border_width", "border_color")
        }
        super().__init__(parent, **ctk_kwargs)

        self.app = app_controller
        self.source_name = source_name
        self.cards = self.app.condition_zones.get(source_name, [])
        self.max_cards = self.app.zone_max_cards.get(source_name, None)

        self.title(f"【{source_name}】卡牌列表编辑")
        self.geometry("1100x580+80+60")
        self.configure(fg_color=PALETTE["bg_main"])

        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _on_close(self):
        if hasattr(self.app, "refresh_field_canvas_stats"):
            self.app.refresh_field_canvas_stats()
        self.destroy()

    def _build_ui(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._draw_card_table(table_frame)

    def _draw_card_table(self, parent: ttk.Frame):
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        if not hasattr(parent, "_table_initialized") or not parent._table_initialized:
            for widget in parent.winfo_children():
                widget.destroy()

            mode_idx = 1 if ctk.get_appearance_mode() == "Dark" else 0
            bg_col = PALETTE["card_bg"][mode_idx]

            canvas = tk.Canvas(parent, bg=bg_col, highlightthickness=0)
            scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
            scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            top_bar_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            top_bar_frame.pack(side=tk.TOP, fill=tk.X, pady=(10, 6), padx=4)

            btn_new = ctk.CTkButton(
                top_bar_frame, text="新建", width=70, height=28, font=header_font,
                fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19")
            )
            btn_new.pack(side=tk.LEFT, padx=2)

            btn_import_zone = ctk.CTkButton(
                top_bar_frame, text="导入卡牌", width=90, height=28, font=label_font,
                fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"]
            )
            btn_import_zone.pack(side=tk.LEFT, padx=2)

            count_lbl = ctk.CTkLabel(top_bar_frame, text="", font=label_font, text_color=PALETTE["text_sub"])
            count_lbl.pack(side=tk.LEFT, padx=6)

            header_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))
            
            headers = [
                ("位置", 35), ("种类", 75), ("等级", 55), ("费用", 55),
                ("触发魂", 55), ("触发类", 55), ("基础魂", 55), ("力量", 55),
                ("调整与增删", 220), ("跨区移动", 220)
            ]
            for h_text, h_width in headers:
                ctk.CTkLabel(
                    header_frame, text=h_text, width=h_width, font=FONT_GLOBAL_BOLD,
                    text_color=PALETTE["text_main"], fg_color=PALETTE["secondary"], corner_radius=4, height=28
                ).pack(side=tk.LEFT, padx=1)

            list_container = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            list_container.pack(side=tk.TOP, fill=tk.X)

            parent._canvas = canvas
            parent._scrollable_frame = scrollable_frame
            parent._top_bar_frame = top_bar_frame
            parent._header_frame = header_frame
            parent._list_container = list_container
            parent._btn_new = btn_new
            parent._btn_import_zone = btn_import_zone
            parent._count_lbl = count_lbl
            parent._table_initialized = True

        list_container = parent._list_container
        target_zone_names = [n for n in self.app.condition_zones.keys() if n != self.source_name]

        is_disabled = (self.max_cards is not None and len(self.cards) >= self.max_cards)
        state_str = "disabled" if is_disabled else "normal"

        parent._btn_new.configure(command=lambda: self._add_card(parent), state=state_str)
        parent._btn_import_zone.configure(command=lambda: self._import_custom_card_to_zone(parent), state=state_str)
        parent._count_lbl.configure(text=f"（共 {len(self.cards)} 张卡牌）")

        for card in self.cards:
            if "card_container" in card and card["card_container"].winfo_exists():
                try: card["card_container"].pack_forget()
                except Exception: pass

        valid_containers = set()

        if not self.cards:
            empty_lbl = ctk.CTkLabel(list_container, text="当前卡区为空，点击上方 [新建] 或 [导入卡牌] 增加卡牌", font=label_font, text_color=PALETTE["text_sub"])
            empty_lbl.pack(side=tk.TOP, anchor="w", padx=10, pady=16)
        else:
            for child in list_container.winfo_children():
                if isinstance(child, ctk.CTkLabel): child.destroy()

            for orig_idx, card in enumerate(self.cards):
                pos_str = f"{orig_idx + 1}"

                if "card_container" in card and card["card_container"].winfo_exists():
                    card_container = card["card_container"]
                    valid_containers.add(card_container)

                    if "pos_label" in card and card["pos_label"].winfo_exists():
                        card["pos_label"].configure(text=pos_str)

                    self._update_card_row_commands(card, orig_idx, parent, target_zone_names)
                    card_container.pack(side=tk.TOP, fill=tk.X, pady=2)
                else:
                    card_container = ctk.CTkFrame(list_container, fg_color="transparent")
                    card_container.pack(side=tk.TOP, fill=tk.X, pady=2)
                    card["card_container"] = card_container

                    self._build_card_row_widgets(
                        card_container, card, pos_str, orig_idx, parent, target_zone_names, label_font, header_font
                    )
                    valid_containers.add(card_container)

        for child in list_container.winfo_children():
            if child not in valid_containers and not isinstance(child, ctk.CTkLabel):
                child.destroy()

        parent._scrollable_frame.update_idletasks()
        parent._canvas.configure(scrollregion=parent._canvas.bbox("all"))

        if hasattr(self.app, "refresh_field_canvas_stats"):
            self.app.refresh_field_canvas_stats()

    def _notify_canvas_refresh(self):
        if hasattr(self.app, "refresh_field_canvas_stats"):
            self.app.refresh_field_canvas_stats()

    def _update_card_positions(self, parent: ttk.Frame):
        target_zone_names = [n for n in self.app.condition_zones.keys() if n != self.source_name]
        for idx, card in enumerate(self.cards):
            pos_str = str(idx + 1)
            if "pos_label" in card and card["pos_label"].winfo_exists():
                card["pos_label"].configure(text=pos_str)
            self._update_card_row_commands(card, idx, parent, target_zone_names)

        if hasattr(parent, "_count_lbl") and parent._count_lbl.winfo_exists():
            parent._count_lbl.configure(text=f"（共 {len(self.cards)} 张卡牌）")

        self._notify_canvas_refresh()

    def _build_card_row_widgets(
        self, card_container: ctk.CTkFrame, card: dict, pos_str: str, orig_idx: int,
        parent: ttk.Frame, target_zone_names: list, label_font: tuple, header_font: tuple
    ):
        row_frame = ctk.CTkFrame(card_container, fg_color="transparent")
        row_frame.pack(fill=tk.X)

        pos_label = ctk.CTkLabel(row_frame, text=pos_str, width=35, font=label_font, text_color=PALETTE["text_main"])
        pos_label.pack(side=tk.LEFT, padx=1)
        card["pos_label"] = pos_label

        kind_var = tk.StringVar(value=card.get("kind", "角色"))
        kind_var.trace("w", lambda *a, c=card, v=kind_var: (c.update({"kind": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=kind_var, values=["角色", "事件", "高潮"], width=75).pack(side=tk.LEFT, padx=1)
        card["kind_var"] = kind_var

        level_var = tk.StringVar(value=str(card.get("level", "0")))
        level_var.trace("w", lambda *a, c=card, v=level_var: (c.update({"level": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=level_var, values=["0", "1", "2", "3"], width=55).pack(side=tk.LEFT, padx=1)
        card["level_var"] = level_var

        cost_var = tk.StringVar(value=str(card.get("cost", "0")))
        cost_var.trace("w", lambda *a, c=card, v=cost_var: (c.update({"cost": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=cost_var, values=[str(i) for i in range(10)], width=55).pack(side=tk.LEFT, padx=1)
        card["cost_var"] = cost_var

        trigger_soul_var = tk.StringVar(value=str(card.get("trigger_soul", "0")))
        trigger_soul_var.trace("w", lambda *a, c=card, v=trigger_soul_var: (c.update({"trigger_soul": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=trigger_soul_var, values=["0", "1", "2"], width=55).pack(side=tk.LEFT, padx=1)
        card["trigger_soul_var"] = trigger_soul_var

        trigger_var = tk.StringVar(value=str(card.get("trigger", "无")))
        trigger_var.trace("w", lambda *a, c=card, v=trigger_var: (c.update({"trigger": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=trigger_var, values=["无", "魂", "门", "裤", "风", "电"], width=55).pack(side=tk.LEFT, padx=1)
        card["trigger_var"] = trigger_var

        base_soul_var = tk.StringVar(value=str(card.get("soul", card.get("base_soul", "1"))))
        base_soul_var.trace("w", lambda *a, c=card, v=base_soul_var: (c.update({"soul": v.get(), "base_soul": v.get()}), self._notify_canvas_refresh()))
        AppDropdown(row_frame, variable=base_soul_var, values=["1", "2", "3", "4", "5"], width=55).pack(side=tk.LEFT, padx=1)
        card["base_soul_var"] = base_soul_var

        power_var = tk.StringVar(value=str(card.get("power", "500")))
        power_var.trace("w", lambda *a, c=card, v=power_var: (c.update({"power": v.get()}), self._notify_canvas_refresh()))
        ctk.CTkEntry(row_frame, textvariable=power_var, width=55, height=28, font=label_font, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=1)
        card["power_var"] = power_var

        ops_box = ctk.CTkFrame(row_frame, fg_color="transparent", width=220)
        ops_box.pack(side=tk.LEFT, padx=1)

        btn_delete = ctk.CTkButton(
            ops_box, text="-", width=24, height=26, corner_radius=4, font=header_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=lambda c=card: self._delete_card(c, parent)
        )
        btn_delete.pack(side=tk.LEFT, padx=1)
        card["btn_delete"] = btn_delete

        copy_var = tk.IntVar(value=1)
        card["copy_var"] = copy_var

        btn_add = ctk.CTkButton(
            ops_box, text="复制", width=38, height=26, corner_radius=4, font=header_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=lambda c=card, cv=copy_var: self._copy_card(c, cv.get(), parent)
        )
        btn_add.pack(side=tk.LEFT, padx=1)
        card["btn_add"] = btn_add

        ctk.CTkEntry(ops_box, textvariable=copy_var, width=32, height=26, font=label_font, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=1)

        btn_import = ctk.CTkButton(
            ops_box, text="导入卡牌", width=75, height=26, font=label_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=lambda c=card: self._import_custom_card_to_item(c, parent)
        )
        btn_import.pack(side=tk.LEFT, padx=2)
        card["btn_import"] = btn_import

        if self.max_cards is None:
            btn_up = ctk.CTkButton(ops_box, text="▲", width=24, height=26, corner_radius=4, font=header_font, fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"], command=lambda i=orig_idx: self._move_card_up(i, parent))
            btn_up.pack(side=tk.LEFT, padx=1)
            card["btn_up"] = btn_up

            btn_down = ctk.CTkButton(ops_box, text="▼", width=24, height=26, corner_radius=4, font=header_font, fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"], command=lambda i=orig_idx: self._move_card_down(i, parent))
            btn_down.pack(side=tk.LEFT, padx=1)
            card["btn_down"] = btn_down
        else:
            card["btn_up"] = None
            card["btn_down"] = None

        move_box = ctk.CTkFrame(row_frame, fg_color="transparent", width=220)
        move_box.pack(side=tk.LEFT, padx=1)

        target_var = tk.StringVar(value=target_zone_names[0] if target_zone_names else "")
        pos_var = tk.IntVar(value=0)
        card["target_var"] = target_var
        card["pos_var"] = pos_var

        btn_move = ctk.CTkButton(
            move_box, text="移动", width=45, height=26, font=label_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=lambda c=card, tv=target_var, pv=pos_var: self._move_card_to(c, parent, tv.get(), pv.get())
        )
        btn_move.pack(side=tk.LEFT, padx=1)
        card["btn_move"] = btn_move

        AppDropdown(move_box, variable=target_var, values=target_zone_names, width=75).pack(side=tk.LEFT, padx=1)

        pos_f = ctk.CTkFrame(move_box, fg_color="transparent")
        pos_f.pack(side=tk.LEFT, padx=1)
        ctk.CTkLabel(pos_f, text="顶起", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)
        ctk.CTkEntry(pos_f, textvariable=pos_var, width=32, height=26, font=label_font, fg_color=PALETTE["secondary"], border_color=PALETTE["input_border"], border_width=1.5, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=1)
        ctk.CTkLabel(pos_f, text="张", font=label_font, text_color=PALETTE["text_main"]).pack(side=tk.LEFT)

        eff_summary = self._get_card_effects_summary(card)
        if eff_summary:
            desc_box = ctk.CTkFrame(card_container, fg_color=PALETTE["card_bg"], corner_radius=6, border_width=1, border_color=PALETTE["card_border"])
            desc_box.pack(fill=tk.X, padx=2, pady=(2, 4))
            ctk.CTkLabel(desc_box, text=f"卡牌详细能力 ({card.get('name', '自定义卡片')}): {eff_summary}", font=label_font, text_color=PALETTE["primary"], justify="left").pack(anchor="w", padx=6, pady=2)

    def _update_card_row_commands(self, card: dict, orig_idx: int, parent: ttk.Frame, target_zone_names: list):
        if "btn_delete" in card and card["btn_delete"] and card["btn_delete"].winfo_exists():
            card["btn_delete"].configure(command=lambda c=card: self._delete_card(c, parent))
        if "btn_add" in card and card["btn_add"] and card["btn_add"].winfo_exists():
            card["btn_add"].configure(command=lambda c=card, cv=card.get("copy_var"): self._copy_card(c, cv.get() if cv else 1, parent))
        if "btn_import" in card and card["btn_import"] and card["btn_import"].winfo_exists():
            card["btn_import"].configure(command=lambda c=card: self._import_custom_card_to_item(c, parent))
        if "btn_up" in card and card["btn_up"] and card["btn_up"].winfo_exists():
            card["btn_up"].configure(command=lambda i=orig_idx: self._move_card_up(i, parent))
        if "btn_down" in card and card["btn_down"] and card["btn_down"].winfo_exists():
            card["btn_down"].configure(command=lambda i=orig_idx: self._move_card_down(i, parent))
        if "btn_move" in card and card["btn_move"] and card["btn_move"].winfo_exists():
            card["btn_move"].configure(command=lambda c=card, tv=card.get("target_var"), pv=card.get("pos_var"): self._move_card_to(c, parent, tv.get() if tv else "", pv.get() if pv else 0))

    def _get_card_effects_summary(self, card: dict) -> str:
        effects = card.get("effects", {})
        if not effects or not isinstance(effects, dict):
            return ""
        phase_map = [
            ("pre_attack", "(1) 攻击前"), ("attack_type", "(2) 攻击方式"),
            ("on_attack", "(3) 攻击时"), ("trigger_step", "(4) 判定阶段"),
            ("deal_damage", "(5) 伤害结算"), ("on_reverse", "(6) 击倒对手时"),
            ("post_attack", "(7) 攻击结束")
        ]
        parts = []
        for pk, p_label in phase_map:
            ops = effects.get(pk, [])
            if ops:
                op_names = [op.get("type", op.get("type_var", "操作")) for op in ops if isinstance(op, dict)]
                if op_names:
                    parts.append(f"{p_label}: {', '.join(op_names)}")
        return " | ".join(parts) if parts else ""

    def _import_custom_card_to_item(self, card: dict, parent: ttk.Frame):
        def on_selected(selected_card: dict):
            card.clear()
            card_copy = copy.deepcopy(selected_card)
            card_copy["kind"] = card_copy.get("type", "角色")
            card.update(card_copy)
            self._draw_card_table(parent)
            messagebox.showinfo("导入成功", f"卡牌【{card.get('name', '自定义卡')}】能力已加载。", parent=self)

        SelectFromLibraryDialog(self, app_controller=self.app, on_select=on_selected)

    def _import_custom_card_to_zone(self, parent: ttk.Frame):
        if self.max_cards is not None and len(self.cards) >= self.max_cards:
            messagebox.showwarning("无法导入", f"卡区【{self.source_name}】已达到最大张数限制（{self.max_cards}张）！", parent=self)
            return

        def on_selected(selected_card: dict):
            card_copy = copy.deepcopy(selected_card)
            card_copy["kind"] = card_copy.get("type", "角色")
            self.cards.append(card_copy)

            list_container = parent._list_container
            target_zone_names = [n for n in self.app.condition_zones.keys() if n != self.source_name]
            label_font = FONT_GLOBAL
            header_font = FONT_GLOBAL_BOLD

            card_container = ctk.CTkFrame(list_container, fg_color="transparent", height=1)
            card_copy["card_container"] = card_container

            idx = len(self.cards) - 1
            self._build_card_row_widgets(
                card_container, card_copy, str(idx + 1), idx,
                parent, target_zone_names, label_font, header_font
            )
            card_container.pack(side=tk.TOP, fill=tk.X, pady=2)
            
            animate_widget_bg(card_container, start_color=("#D1FAE5", "#064E3B"), end_color="transparent")
            self._update_card_positions(parent)

            messagebox.showinfo("导入成功", f"卡牌【{selected_card.get('name', '自定义卡')}】已加入卡区。", parent=self)

        SelectFromLibraryDialog(self, app_controller=self.app, on_select=on_selected)

    def _add_card(self, parent: ttk.Frame):
        if self.max_cards is not None and len(self.cards) >= self.max_cards:
            return
            
        new_card = {
            "kind": "角色", "level": "0", "cost": "0", "soul": "1",
            "trigger": "无", "trigger_soul": "0", "base_soul": "1", "power": "500"
        }
        self.cards.append(new_card)

        list_container = parent._list_container
        target_zone_names = [n for n in self.app.condition_zones.keys() if n != self.source_name]
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        card_container = ctk.CTkFrame(list_container, fg_color="transparent", height=1)
        new_card["card_container"] = card_container

        idx = len(self.cards) - 1
        self._build_card_row_widgets(
            card_container, new_card, str(idx + 1), idx,
            parent, target_zone_names, label_font, header_font
        )
        card_container.pack(side=tk.TOP, fill=tk.X, pady=2)

        animate_widget_bg(card_container, start_color=("#D1FAE5", "#064E3B"), end_color="transparent")
        self._update_card_positions(parent)

    def _delete_card(self, card: dict, parent: ttk.Frame):
        if card not in self.cards:
            return

        if "btn_delete" in card and card["btn_delete"] and card["btn_delete"].winfo_exists():
            card["btn_delete"].configure(state="disabled")

        card_container = card.get("card_container")

        def do_destroy():
            if card in self.cards:
                self.cards.remove(card)
            if card_container and card_container.winfo_exists():
                card_container.destroy()
            self._update_card_positions(parent)

        if card_container and card_container.winfo_exists():
            animate_delete_red_glow(card_container, on_complete=do_destroy)
        else:
            do_destroy()

    def _clone_card_data(self, card: dict) -> dict:
        cleaned = {}
        for k, v in card.items():
            if isinstance(v, (tk.Variable, tk.Widget, ctk.CTkBaseClass)):
                continue
            if k.endswith("_var") or k.startswith("btn_") or k in ("card_container", "pos_label", "desc_box"):
                continue
            cleaned[k] = v
        return copy.deepcopy(cleaned)

    # 🌟 沿用你指定的 _copy_card 版本
    def _copy_card(self, card: dict, count: int, parent: ttk.Frame):
        if count <= 0:
            return
        if self.max_cards is not None and len(self.cards) + count > self.max_cards:
            count = self.max_cards - len(self.cards)
            if count <= 0:
                return

        idx = self.cards.index(card)
        prev_container = card.get("card_container")
        target_zone_names = [n for n in self.app.condition_zones.keys() if n != self.source_name]
        label_font = FONT_GLOBAL
        header_font = FONT_GLOBAL_BOLD

        list_container = parent._list_container

        for i in range(count):
            new_card = self._clone_card_data(card)
            self.cards.insert(idx + 1 + i, new_card)

            card_container = ctk.CTkFrame(list_container, fg_color="transparent", height=1)
            new_card["card_container"] = card_container

            self._build_card_row_widgets(
                card_container, new_card, str(idx + 2 + i), idx + 1 + i,
                parent, target_zone_names, label_font, header_font
            )

            if prev_container and prev_container.winfo_exists():
                card_container.pack(side=tk.TOP, fill=tk.X, pady=2, after=prev_container)
            else:
                card_container.pack(side=tk.TOP, fill=tk.X, pady=2)

            prev_container = card_container
            animate_widget_bg(card_container, start_color=("#D1FAE5", "#064E3B"), end_color="transparent")

        self._update_card_positions(parent)

    def _move_card_up(self, index: int, parent: ttk.Frame):
        if index > 0 and index < len(self.cards):
            curr_card = self.cards[index]
            target_card = self.cards[index - 1]

            self.cards[index], self.cards[index - 1] = self.cards[index - 1], self.cards[index]

            curr_container = curr_card.get("card_container")
            target_container = target_card.get("card_container")

            if curr_container and target_container and curr_container.winfo_exists() and target_container.winfo_exists():
                curr_container.pack(before=target_container)

                animate_widget_bg(curr_container, start_color=("#D1FAE5", "#064E3B"), end_color="transparent")
                animate_widget_bg(target_container, start_color=("#DBEAFE", "#172554"), end_color="transparent")

            self._update_card_positions(parent)

    def _move_card_down(self, index: int, parent: ttk.Frame):
        if index < len(self.cards) - 1:
            curr_card = self.cards[index]
            target_card = self.cards[index + 1]

            self.cards[index], self.cards[index + 1] = self.cards[index + 1], self.cards[index]

            curr_container = curr_card.get("card_container")
            target_container = target_card.get("card_container")

            if curr_container and target_container and curr_container.winfo_exists() and target_container.winfo_exists():
                curr_container.pack(after=target_container)

                animate_widget_bg(curr_container, start_color=("#DBEAFE", "#172554"), end_color="transparent")
                animate_widget_bg(target_container, start_color=("#D1FAE5", "#064E3B"), end_color="transparent")

            self._update_card_positions(parent)

    def _move_card_to(self, card: dict, parent: ttk.Frame, target_zone_name: str, position: int):
        if card not in self.cards or target_zone_name not in self.app.condition_zones:
            return
        target_cards = self.app.condition_zones[target_zone_name]
        if target_cards is self.cards:
            return

        target_max = self.app.zone_max_cards.get(target_zone_name, None)
        if target_max is not None and len(target_cards) >= target_max:
            messagebox.showwarning("无法移动", f"目标卡区【{target_zone_name}】已达到容量上限（{target_max}张）！", parent=self)
            return

        self.cards.remove(card)
        card_container = card.get("card_container")
        if card_container and card_container.winfo_exists():
            card_container.destroy()

        insert_idx = len(target_cards) if position == 0 else max(0, len(target_cards) - position)
        target_cards.insert(insert_idx, card)

        self._draw_card_table(parent)