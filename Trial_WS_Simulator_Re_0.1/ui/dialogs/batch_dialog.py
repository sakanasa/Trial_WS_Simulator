# -*- coding: utf-8 -*-
"""
矩阵批量统计弹窗 (Batch Statistics Dialog) - Geek Indigo 统一样式高颜值版
1. 全量采用 FONT_GLOBAL (-14px 五号字) 与 FONT_GLOBAL_BOLD。
2. 配置底座与卡片完全对应 Geek Indigo / GitHub 黑碳灰规范，消除直角白边。
3. 文本框字体统一为等宽 Consolas (-13px)，保证矩阵结果输出完美对齐。
"""

import time
import random
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Any, List

from core.engine import build_deck, stabilize
from simulator.runner import SimulationRunner
from simulator.statistics import format_elapsed_time, calc_winrate, calc_avg_damage
from utils.registry import registry
from ui.components.app_dropdown import AppDropdown

# 统一自中央主题库引入配色与字体规范
from ui.theme import PALETTE, FONT_GLOBAL, FONT_GLOBAL_BOLD


class BatchStatisticsDialog(ctk.CTkToplevel):
    """矩阵批量统计分析对话框类"""

    def __init__(self, parent: tk.Widget, app_controller: Any, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app_controller
        self.title("矩阵批量统计分析")
        self.geometry("1000x700+80+60")

        # 🌟 配置窗口大底色，防止深色模式下闪白
        self.configure(fg_color=PALETTE["bg_main"])

        self.after(10, lambda: self.lift())
        self.after(50, lambda: self.focus_force())

        self._init_variables()
        self._build_ui()

    def _init_variables(self):
        self.var_options = ["无", "卡组潮数", "卡组肉数", "计时区肉数", "等级区肉数"]

        # 纵列 (轴1) 变量
        self.batch_var1 = tk.StringVar(value="等级区肉数")
        self.batch_from1 = tk.IntVar(value=0)
        self.batch_to1 = tk.IntVar(value=3)

        # 横行 (轴2) 变量
        self.batch_var2 = tk.StringVar(value="计时区肉数")
        self.batch_from2 = tk.IntVar(value=0)
        self.batch_to2 = tk.IntVar(value=6)

    def _build_ui(self):
        """🌟 三级色彩结构重构：消除多余嵌套，对齐 left_column 统一样式"""
        
        # ==========================================
        # 二级结构：左列与右列面板 (背景色: #F1F5F9 / #111827)
        # ==========================================
        left_col = ctk.CTkFrame(
            self, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=8, 
            width=380
        )
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, padx=(8, 4), pady=8)
        left_col.pack_propagate(False)

        right_col = ctk.CTkFrame(
            self, 
            fg_color=("#F1F5F9", "#111827"), 
            corner_radius=8
        )
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 8), pady=8)

        # 输入框统一样式配置（对齐 left_column 控件）
        entry_opts = {
            "width": 45,
            "height": 28,
            "font": FONT_GLOBAL,
            "fg_color": PALETTE["secondary"],
            "border_color": PALETTE["input_border"], # 🌟 统一高对比度描边
            "border_width": 1.5,                     # 🌟 统一 1.5px 描边
            "text_color": PALETTE["text_main"]
        }

        # ==========================================
        # 三级结构 (左列内部)：独立配置卡片 (背景色: card_bg)
        # ==========================================

        # --- 卡片 1：横行 (轴2) 配置 ---
        row2_card = ctk.CTkFrame(
            left_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        row2_card.pack(fill=tk.X, padx=6, pady=6)

        ctk.CTkLabel(
            row2_card, 
            text="横行 (轴2) 配置", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        r2 = ctk.CTkFrame(row2_card, fg_color="transparent")
        r2.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(r2, text="变量:", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(0, 2))
        AppDropdown(r2, variable=self.batch_var2, values=self.var_options, width=110).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r2, text="从", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r2, textvariable=self.batch_from2, **entry_opts).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r2, text="到", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r2, textvariable=self.batch_to2, **entry_opts).pack(side=tk.LEFT, padx=2)

        # --- 卡片 2：纵列 (轴1) 配置 ---
        row1_card = ctk.CTkFrame(
            left_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        row1_card.pack(fill=tk.X, padx=6, pady=6)

        ctk.CTkLabel(
            row1_card, 
            text="纵列 (轴1) 配置", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        r1 = ctk.CTkFrame(row1_card, fg_color="transparent")
        r1.pack(fill=tk.X, padx=10, pady=(0, 8))

        ctk.CTkLabel(r1, text="变量:", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(0, 2))
        AppDropdown(r1, variable=self.batch_var1, values=self.var_options, width=110).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r1, text="从", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r1, textvariable=self.batch_from1, **entry_opts).pack(side=tk.LEFT, padx=2)

        ctk.CTkLabel(r1, text="到", font=FONT_GLOBAL, text_color=PALETTE["text_main"]).pack(side=tk.LEFT, padx=(6, 2))
        ctk.CTkEntry(r1, textvariable=self.batch_to1, **entry_opts).pack(side=tk.LEFT, padx=2)

        # --- 左列底部的控制按键与进度条 ---
        self.start_btn = ctk.CTkButton(
            left_col,
            text="开始矩阵批量统计",
            command=self.run_batch_statistics,
            fg_color=PALETTE["primary"],
            hover_color=PALETTE["primary_hover"],
            text_color=("#FFFFFF", "#0B0F19"),
            font=FONT_GLOBAL_BOLD,
            height=36
        )
        self.start_btn.pack(fill=tk.X, padx=6, pady=(12, 6))

        self.progress_bar = ctk.CTkProgressBar(left_col, progress_color=PALETTE["primary"], height=8)
        self.progress_bar.pack(fill=tk.X, padx=6, pady=4)
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(left_col, text="总进度：0%", font=FONT_GLOBAL, text_color=PALETTE["text_sub"])
        self.progress_label.pack(pady=(0, 8))

        # ==========================================
        # 三级结构 (右列内部)：结果展示卡片 (背景色: card_bg)
        # ==========================================
        right_card = ctk.CTkFrame(
            right_col, 
            fg_color=PALETTE["card_bg"], 
            corner_radius=8, 
            border_width=1, 
            border_color=PALETTE["card_border"]
        )
        right_card.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        ctk.CTkLabel(
            right_card, 
            text="=== 矩阵统计分析结果 ===", 
            font=FONT_GLOBAL_BOLD, 
            text_color=PALETTE["text_main"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        # 结果输出框（保持原有的 secondary 配色与等宽字体，不影响功能）
        self.result_text = ctk.CTkTextbox(
            right_card, 
            wrap="none", 
            font=("Consolas", -13), 
            fg_color=PALETTE["secondary"], 
            text_color=PALETTE["text_main"]
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

    def run_batch_statistics(self):
        var1 = self.batch_var1.get()
        var2 = self.batch_var2.get()

        if var1 == "无" and var2 == "无":
            messagebox.showwarning("警告", "必须至少选择一个有效的矩阵变量！", parent=self)
            return

        mode = self.app.middle_col.multi_mode_var.get()
        if mode == "常规":
            sim_times = self.app.middle_col.reg_sim_times.get()
            ops_params = [registry.extract_params(op) for op in self.app.reg_ops]
            execution_plan, roles_params = None, None
        elif mode == "高级":
            sim_times = self.app.middle_col.adv_sim_times.get()
            execution_plan, roles_params = self.app._get_advanced_execution_plan()
            ops_params = None
        else:  # 工况模式
            sim_times = self.app.middle_col.cond_sim_times.get()
            execution_plan, roles_params = self.app._get_condition_execution_plan()
            ops_params = None

        def get_range(var_name, f_val, t_val):
            if var_name == "无":
                return [None]
            s, e = f_val.get(), t_val.get()
            return list(range(s, e + 1)) if s <= e else list(range(s, e - 1, -1))

        range1 = get_range(var1, self.batch_from1, self.batch_to1)
        range2 = get_range(var2, self.batch_from2, self.batch_to2)
        total_combinations = len(range1) * len(range2)

        self.progress_bar.set(0.0)
        self.start_btn.configure(state="disabled")

        fixed = self.app._get_fixed_state_params()
        level_meat_def = sum(1 for v in self.app.left_col.level_vars if v.get() == "肉")
        clock_meat_def = sum(1 for v in self.app.left_col.clock_vars if v.get() == "肉")

        def _batch_thread():
            start_time = time.time()
            winrate_matrix = [[0.0] * len(range2) for _ in range(len(range1))]
            avg_dmg_matrix = [[0.0] * len(range2) for _ in range(len(range1))]

            combination_count = 0

            for i, val1 in enumerate(range1):
                for j, val2 in enumerate(range2):
                    wins = 0
                    total_dmg = 0

                    for k in range(sim_times):
                        d, c, s, l, cl = self._build_batch_cell_state(
                            var1, val1, var2, val2, fixed, level_meat_def, clock_meat_def
                        )
                        stabilize_func = lambda: stabilize(d, c, l, cl)

                        if mode == "常规":
                            game_over = False
                            dmg = 0
                            for op in ops_params:
                                opt = op["type"]
                                if opt in registry.types and registry.types[opt]["execute"]:
                                    over, _, extra = registry.execute(opt, d, c, s, l, cl, op, stabilize_func)
                                    dmg += extra.get("total_damage", 0)
                                    if over:
                                        game_over = True
                                        break
                        else:
                            game_over = False
                            dmg = 0
                            pending_pass = {}
                            global_ice_armors = []
                            role_states = [{"soul": rp["soul"], "abilities": [], "ops": rp["ops"]} for rp in roles_params]

                            for role_idx, start_idx, end_idx in execution_plan:
                                if game_over:
                                    break
                                rstate = role_states[role_idx]
                                over, seg_dmg, _ = SimulationRunner.simulate_role_ops_segment(
                                    d, c, s, l, cl, rstate, rstate["ops"],
                                    start_idx, end_idx, pending_pass, role_idx, len(roles_params),
                                    collect_steps=False, global_ice_armors=global_ice_armors
                                )
                                dmg += seg_dmg
                                if over:
                                    game_over = True

                        total_dmg += dmg
                        if game_over:
                            wins += 1

                    winrate_matrix[i][j] = calc_winrate(wins, sim_times)
                    avg_dmg_matrix[i][j] = calc_avg_damage(total_dmg, sim_times)

                    combination_count += 1
                    pct = int((combination_count / total_combinations) * 100)
                    self.after(0, lambda c=combination_count, p=pct: self._update_progress(c, p))

            elapsed = time.time() - start_time
            self.after(0, lambda: self._render_results(winrate_matrix, avg_dmg_matrix, range1, range2, var1, var2, elapsed))

        threading.Thread(target=_batch_thread, daemon=True).start()

    def _build_batch_cell_state(self, var1, val1, var2, val2, fixed, level_meat_def, clock_meat_def):
        d_normal = fixed["deck_normal"]
        d_climax = fixed["deck_climax"]
        c_normal = fixed["control_normal"]
        c_climax = fixed["control_climax"]

        clock_meat = None
        level_meat = None

        if var1 == "卡组潮数" and val1 is not None: d_climax = val1
        elif var1 == "卡组肉数" and val1 is not None: d_normal = val1
        elif var1 == "计时区肉数" and val1 is not None: clock_meat = val1
        elif var1 == "等级区肉数" and val1 is not None: level_meat = val1

        if var2 == "卡组潮数" and val2 is not None: d_climax = val2
        elif var2 == "卡组肉数" and val2 is not None: d_normal = val2
        elif var2 == "计时区肉数" and val2 is not None: clock_meat = val2
        elif var2 == "等级区肉数" and val2 is not None: level_meat = val2

        deck = build_deck(d_normal, d_climax)
        control = ["普通"] * c_normal + ["高潮"] * c_climax
        stock = ["普通"] * fixed["stock_normal"] + ["高潮"] * fixed["stock_climax"]

        l_climax = fixed["level_climax_count"]
        l_meat = level_meat if level_meat is not None else level_meat_def
        level = ["高潮"] * l_climax + ["普通"] * min(l_meat, 4 - l_climax)
        random.shuffle(level)

        cl_climax = fixed["clock_climax_count"]
        cl_meat = clock_meat if clock_meat is not None else clock_meat_def
        clock = ["高潮"] * cl_climax + ["普通"] * min(cl_meat, 6 - cl_climax)
        random.shuffle(clock)

        return deck, control, stock, level, clock

    def _update_progress(self, current, pct):
        """🌟 进度条自适应刷新"""
        self.progress_bar.set(pct / 100.0)
        self.progress_label.configure(text=f"总进度：{pct}%")

    def _render_results(self, winrate_matrix, avg_dmg_matrix, range1, range2, var1, var2, elapsed):
        self.start_btn.configure(state="normal")
        self.result_text.delete("1.0", tk.END)

        def build_table(matrix, title):
            lines = [title]
            cols = [str(v) if v is not None else "-" for v in range2]
            lines.append("\t" + "\t".join(cols))
            for i, r_val in enumerate(range1):
                r_label = str(r_val) if r_val is not None else "-"
                row_vals = [f"{matrix[i][j]:.2f}" for j in range(len(range2))]
                lines.append(f"{r_label}\t" + "\t".join(row_vals))
            return "\n".join(lines)

        txt = build_table(winrate_matrix, f"=== 斩杀率矩阵 (%) [纵轴: {var1} \\ 横轴: {var2}] ===")
        txt += "\n\n" + build_table(avg_dmg_matrix, f"=== 平均伤害矩阵 [纵轴: {var1} \\ 横轴: {var2}] ===")
        txt += f"\n\n总计算耗时: {format_elapsed_time(elapsed)}"

        self.result_text.insert("1.0", txt)