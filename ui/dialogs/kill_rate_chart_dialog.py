# -*- coding: utf-8 -*-
"""
斬殺率比較圖對話框 (Kill Rate Comparison Chart Dialog)
從已命名存檔的矩陣批量統計結果中挑選多組，攤平成「等級-血量」檢查點序列，
畫成同一張折線比較圖：Y 軸為機率(%)，每組資料獨立顏色並在圖例標示名稱。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Any, Optional

import matplotlib
matplotlib.use("TkAgg")
matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti TC", "Arial Unicode MS", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD
from ui.chart_theme import assign_series_colors
from services.batch_matrix_service import batch_matrix_service


def _flatten_matrix(data: dict):
    """把矩陣依 (軸1, 軸2) 逐列展開成一串「val1-val2」檢查點序列"""
    range1 = data.get("range1", [])
    range2 = data.get("range2", [])
    matrix = data.get("winrate_matrix", [])
    labels, values = [], []
    for i, v1 in enumerate(range1):
        for j, v2 in enumerate(range2):
            v1_label = v1 if v1 is not None else "-"
            v2_label = v2 if v2 is not None else "-"
            labels.append(f"{v1_label}-{v2_label}")
            try:
                values.append(matrix[i][j])
            except (IndexError, TypeError):
                values.append(None)
    return labels, values


class KillRateChartDialog(ctk.CTkToplevel):
    """斬殺率矩陣比較折線圖對話框"""

    def __init__(self, parent: tk.Widget, app_controller: Optional[Any] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("斬殺率比較圖")
        self.geometry("1120x680+100+80")
        self.configure(fg_color=PALETTE["bg_main"])

        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self.check_vars = {}
        self.canvas = None
        self._build_ui()

    def _build_ui(self):
        left_col = ctk.CTkFrame(self, fg_color=("#F1F5F9", "#111827"), corner_radius=8, width=230)
        left_col.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 4), pady=8)
        left_col.pack_propagate(False)

        right_col = ctk.CTkFrame(self, fg_color=("#F1F5F9", "#111827"), corner_radius=8)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        ctk.CTkLabel(
            left_col, text="選擇要比較的存檔", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(10, 6))

        self.list_scroll = ctk.CTkScrollableFrame(left_col, fg_color="transparent")
        self.list_scroll.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._rebuild_checklist()

        ctk.CTkButton(
            left_col, text="↻ 重新整理清單", command=self._rebuild_checklist,
            fg_color=PALETTE["secondary"], hover_color=PALETTE["secondary_hover"],
            text_color=PALETTE["text_main"], font=FONT_GLOBAL, height=28
        ).pack(fill=tk.X, padx=6, pady=(0, 4))

        ctk.CTkButton(
            left_col, text="生成比較圖", command=self._render_chart,
            fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"],
            text_color=("#FFFFFF", "#0B0F19"), font=FONT_GLOBAL_BOLD, height=34
        ).pack(fill=tk.X, padx=6, pady=(0, 10))

        self.chart_frame = ctk.CTkFrame(
            right_col, fg_color=PALETTE["card_bg"], corner_radius=8,
            border_width=1, border_color=PALETTE["card_border"]
        )
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        ctk.CTkLabel(
            self.chart_frame, text="勾選左側存檔後按「生成比較圖」",
            font=FONT_GLOBAL, text_color=PALETTE["text_sub"]
        ).pack(expand=True)

    def _rebuild_checklist(self):
        for w in self.list_scroll.winfo_children():
            w.destroy()

        names = batch_matrix_service.get_names()
        old_checked = {name for name, var in self.check_vars.items() if var.get()}
        self.check_vars = {}

        if not names:
            ctk.CTkLabel(
                self.list_scroll, text="目前沒有任何存檔的矩陣結果。\n請先在「矩陣批量統計分析」跑出結果後存檔。",
                font=FONT_GLOBAL, text_color=PALETTE["text_sub"], justify="left"
            ).pack(anchor="w", padx=6, pady=10)
            return

        for name in names:
            var = tk.BooleanVar(value=name in old_checked)
            self.check_vars[name] = var
            ctk.CTkCheckBox(
                self.list_scroll, text=name, variable=var,
                font=FONT_GLOBAL, text_color=PALETTE["text_main"],
                fg_color=PALETTE["primary"], hover_color=PALETTE["primary_hover"]
            ).pack(anchor="w", padx=4, pady=3)

    def _render_chart(self):
        selected = [name for name, var in self.check_vars.items() if var.get()]

        for w in self.chart_frame.winfo_children():
            w.destroy()

        if not selected:
            ctk.CTkLabel(
                self.chart_frame, text="請至少勾選一組存檔", font=FONT_GLOBAL, text_color=PALETTE["text_sub"]
            ).pack(expand=True)
            return

        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = PALETTE["card_bg"][1 if is_dark else 0]
        text_color = PALETTE["text_main"][1 if is_dark else 0]
        grid_color = PALETTE["card_border"][1 if is_dark else 0]
        color_map = assign_series_colors(batch_matrix_service.get_names(), is_dark=is_dark)

        # 蒐集各組資料，X 軸標籤以最長的那組為準，其餘依相同「val1-val2」標籤對齊
        all_labels: list = []
        series_data = []
        for name in selected:
            data = batch_matrix_service.get_preset(name)
            if not data:
                continue
            labels, values = _flatten_matrix(data)
            series_data.append((name, labels, values))
            if len(labels) > len(all_labels):
                all_labels = labels

        if not all_labels:
            ctk.CTkLabel(
                self.chart_frame, text="所選存檔沒有可用的矩陣資料", font=FONT_GLOBAL, text_color=PALETTE["text_sub"]
            ).pack(expand=True)
            return

        label_index = {lbl: i for i, lbl in enumerate(all_labels)}

        fig = Figure(figsize=(7.6, 5.3), dpi=100, facecolor=bg)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        for name, labels, values in series_data:
            y = [None] * len(all_labels)
            for lbl, v in zip(labels, values):
                if lbl in label_index:
                    y[label_index[lbl]] = v
            color = color_map.get(name, "#2a78d6")
            ax.plot(
                range(len(all_labels)), y,
                label=name, color=color, linewidth=2.2,
                marker="o", markersize=5, markerfacecolor=color,
                markeredgecolor=bg, markeredgewidth=1, solid_capstyle="round"
            )

        ax.set_xticks(range(len(all_labels)))
        ax.set_xticklabels(all_labels, rotation=45, ha="right", fontsize=8, color=text_color)
        ax.set_ylabel("機率 (%)", color=text_color, fontsize=11)
        ax.set_xlabel("等級-血量檢查點", color=text_color, fontsize=11)
        ax.set_title("斬殺率比較", color=text_color, fontsize=13, fontweight="bold")
        ax.set_ylim(bottom=0)

        ax.tick_params(axis="y", colors=text_color, labelsize=9)
        ax.grid(True, axis="y", color=grid_color, linewidth=0.6, alpha=0.6)
        ax.set_axisbelow(True)
        for spine_name in ("top", "right"):
            ax.spines[spine_name].set_visible(False)
        for spine_name in ("left", "bottom"):
            ax.spines[spine_name].set_color(grid_color)

        ax.legend(
            loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=min(4, len(series_data)),
            frameon=False, fontsize=9, labelcolor=text_color
        )

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.canvas = canvas
