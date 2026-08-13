# -*- coding: utf-8 -*-
"""
工况模式战场画布组件 (Condition Field Canvas Component) - CTk 浅色重构版
负责 8列 6行 正方形网格战场的响应式绘制、对方前列力量/等级配置与区域点击事件派发。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, Callable, Optional, Any
from ui.components.app_dropdown import AppDropdown
from ui.components.app_dropdown import PALETTE, FONT_GLOBAL
FONT_GLOBAL_BOLD = ("微软雅黑", -14, "bold")

class ConditionFieldCanvas(ctk.CTkFrame):
    """工况模式可视化网格画布（CTk 浅色高颜值版）"""

    def _set_appearance_mode(self, mode_string):
        """重写底层监听：当主题改变时，同步强制刷新 Canvas 及内部控件的底色"""
        super()._set_appearance_mode(mode_string)
        self._update_canvas_theme()

    def _update_canvas_theme(self):
        """实时将 Canvas 背景、分割线和内部嵌入控件的直角底色染成一致，消除白边"""
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
            
        # 1. 提取当前模式底下的调色盘色值
        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        bg_color = PALETTE["card_bg"][mode_idx]
        text_color = PALETTE["text_main"][mode_idx]
        border_color = PALETTE["card_border"][mode_idx]

        # 2. 将 Canvas 画布背景色和文字色与主题拉平
        self.canvas.configure(bg=bg_color)
        self.canvas.itemconfig(self.top_text_id, fill=text_color)
        
        # 网格分割线也改用 card_border 配色，保持极简高级感
        self.canvas.itemconfig("grid_line", fill=border_color)

        # 3. 强制更新所有常驻按钮的 bg_color，将多余直角彻底隐藏
        for btn in self.zone_buttons.values():
            if btn.winfo_exists():
                btn.configure(bg_color=bg_color)
        
        if self.hand_btn.winfo_exists():
            self.hand_btn.configure(bg_color=bg_color)
            
        # 🌟 新增下面这几行，强行粉碎“我方”文本框区域的白色直角方框
        if self.hand_bottom_frame.winfo_exists():
            self.hand_bottom_frame.configure(bg_color=bg_color)
        if hasattr(self, "bottom_label") and self.bottom_label.winfo_exists():
            self.bottom_label.configure(bg_color=bg_color)
        if hasattr(self, "overview_btn") and self.overview_btn.winfo_exists():
            self.overview_btn.configure(bg_color=bg_color)

        # 4. 强制更新对方前列属性卡片（CTkFrame）的 bg_color
        if hasattr(self, "enemy_boxes"):
            for box in self.enemy_boxes:
                if box.winfo_exists():
                    box.configure(bg_color=bg_color)

    def __init__(
        self,
        parent: tk.Widget,
        on_zone_click: Callable[[str], None],
        on_overview_click: Callable[[], None],
        enemy_front_roles: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.on_zone_click = on_zone_click
        self.on_overview_click = on_overview_click

        # 对方前列力量与等级数据映射
        self.enemy_front_roles = enemy_front_roles or {
            "前列1": {"level": tk.StringVar(value="0"), "power": tk.IntVar(value=500)},
            "前列2": {"level": tk.StringVar(value="0"), "power": tk.IntVar(value=500)},
            "前列3": {"level": tk.StringVar(value="0"), "power": tk.IntVar(value=500)},
        }

        self.button_windows: Dict[str, int] = {}
        self.zone_buttons: Dict[str, ctk.CTkButton] = {}
        self.enemy_front_windows: Dict[str, int] = {}

        self._init_ui()

    def _init_ui(self):
        # 采用紧凑型五号字
        label_font = FONT_GLOBAL
        bold_font = FONT_GLOBAL_BOLD

        # 1. 战场 Canvas 容器，背景色通过 _update_canvas_theme 动态刷新
        self.canvas = tk.Canvas(self, height=360, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.top_text_id = self.canvas.create_text(
            10, 10, text="对方", font=bold_font, anchor="center"
        )

        # 2. 我方底部控制行
        self.hand_bottom_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")

        self.hand_btn = ctk.CTkButton(
            self.hand_bottom_frame, text="手牌", width=55, height=28, corner_radius=4,
            font=label_font,
            fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
            command=lambda: self.on_zone_click("手牌")
        )
        self.hand_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.bottom_label = ctk.CTkLabel(self.hand_bottom_frame, text="我方", font=FONT_GLOBAL_BOLD, text_color=PALETTE["text_main"])
        self.bottom_label.pack(side=tk.LEFT, padx=6)

        self.overview_btn = ctk.CTkButton(
            self.hand_bottom_frame, text="概览", width=55, height=28, corner_radius=4,
            font=bold_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=self.on_overview_click
        )
        self.overview_btn.pack(side=tk.LEFT, padx=6)

        self.hand_bottom_id = self.canvas.create_window(
            0, 0, window=self.hand_bottom_frame, anchor="center"
        )

        # 3. 注册标准卡区按钮
        button_configs = [
            ("卡组", "卡组"), ("控制室", "控室"), ("思出", "思出"), ("库存", "库存"), ("CX", "CX"),
            ("等级1", "等级1"), ("等级2", "等级2"), ("等级3", "等级3"), ("等级4", "等级4"),
            ("前列1", "前列1"), ("前列2", "前列2"), ("前列3", "前列3"),
            ("后列1", "后列1"), ("后列2", "后列2"),
        ]
        for i in range(1, 8):
            button_configs.append((f"计时{i}", f"计时{i}"))

        for zone_name, text in button_configs:
            btn = ctk.CTkButton(
                self.canvas, text=text, width=55, height=28, corner_radius=4,
                font=label_font,
                fg_color=PALETTE["secondary"], text_color=PALETTE["text_main"], hover_color=PALETTE["secondary_hover"],
                command=lambda zn=zone_name: self.on_zone_click(zn)
            )
            win_id = self.canvas.create_window(0, 0, window=btn, anchor="center")
            self.zone_buttons[zone_name] = btn
            self.button_windows[zone_name] = win_id

        # 4. 创建对方前列属性卡片并保存引用（用来动态清除直角白边）
        self.enemy_boxes = []
        for front_key in ["前列1", "前列2", "前列3"]:
            role_data = self.enemy_front_roles[front_key]
            lvl_var = role_data["level"]
            pwr_var = role_data["power"]

            # 将对方卡片框架的边框调配到 card_border 极客蓝
            box = ctk.CTkFrame(
                self.canvas, 
                fg_color=PALETTE["card_bg"], 
                corner_radius=6, 
                border_width=1, 
                border_color=PALETTE["card_border"]
            )

            ctk.CTkLabel(box, text=f"敌{front_key}", font=("微软雅黑", -11, "bold"), text_color=PALETTE["text_main"]).pack(anchor="center", pady=(2, 0))

            top_f = ctk.CTkFrame(box, fg_color="transparent")
            top_f.pack(fill=tk.X, padx=4, pady=1)
            ctk.CTkLabel(top_f, text="等级:", font=label_font, text_color=PALETTE["text_sub"]).pack(side=tk.LEFT, padx=1)
            lvl_combo = AppDropdown(top_f, variable=lvl_var, values=["空", "0", "1", "2", "3"], width=52)
            lvl_combo.pack(side=tk.LEFT, padx=1)

            bot_f = ctk.CTkFrame(box, fg_color="transparent")
            bot_f.pack(fill=tk.X, padx=4, pady=(1, 4))
            ctk.CTkLabel(bot_f, text="力量:", font=label_font, text_color=PALETTE["text_sub"]).pack(side=tk.LEFT, padx=1)
            
            pwr_entry = ctk.CTkEntry(
                bot_f, 
                textvariable=pwr_var, 
                width=50, 
                height=24, 
                font=label_font,
                fg_color=PALETTE["secondary"],
                border_color=PALETTE["card_border"],
                text_color=PALETTE["text_main"]
            )
            pwr_entry.pack(side=tk.LEFT, padx=1)

            def make_pwr_toggler(lvar, entry):
                def _toggle(*args):
                    if lvar.get() == "空":
                        entry.configure(state="disabled")
                    else:
                        entry.configure(state="normal")
                return _toggle

            toggler = make_pwr_toggler(lvl_var, pwr_entry)
            lvl_var.trace("w", toggler)
            toggler()

            win_id = self.canvas.create_window(0, 0, window=box, anchor="center")
            self.enemy_front_windows[front_key] = win_id
            self.enemy_boxes.append(box)

        self.canvas.bind("<Configure>", self._redraw_grid)
        
        # 强制在初始化时执行一次底色渲染
        self._update_canvas_theme()

    def _redraw_grid(self, event=None):
        cw = event.width if event else self.canvas.winfo_width()
        if cw < 10:
            return

        cell_size = cw / 8
        # 网格包含 5 行主体对战区域 (Row 0~4)
        grid_rows = 5
        grid_height = cell_size * grid_rows
        top_margin = 30
        bottom_margin = 35
        total_height = top_margin + grid_height + bottom_margin

        # 🌟【核心修复】：实时将等比例计算出的 total_height 设置给 Canvas 画布
        # 确保画布高度随宽度自适应伸缩，彻底解决宽度变大时我方底部卡区（后列/计时区/控制室/手牌栏）被截断的 Bug！
        self.canvas.configure(height=int(total_height))

        self.canvas.delete("grid")

        # 1. 绘制纵向网格线 (将 tags="grid" 升级为双标签，增加 "grid_line")
        for i in range(9):
            x = i * cell_size
            self.canvas.create_line(x, top_margin, x, top_margin + grid_height, fill=PALETTE["card_border"][0], tags=("grid", "grid_line"))

        # 2. 绘制横向网格线 (同样打上 "grid_line" 标签)
        for j in range(grid_rows + 1):
            y = top_margin + j * cell_size
            self.canvas.create_line(0, y, cw, y, fill=PALETTE["card_border"][0], tags=("grid", "grid_line"))

        # 3. 敌我分割红线
        y_sep = top_margin + 2 * cell_size
        self.canvas.create_line(0, y_sep, cw, y_sep, fill="#EF4444", width=2, tags="grid")
        
        # 4. 重建线条后，立即重刷一次颜色状态
        self._update_canvas_theme()

        # 4. 更新顶部“对方”文本与底部“我方/手牌/概览”控制行坐标
        self.canvas.coords(self.top_text_id, cw / 2, top_margin / 2)
        self.canvas.coords(self.hand_bottom_id, cw / 2, top_margin + grid_height + bottom_margin / 2)

        # 5. 重新映射对战垫标准坐标
        button_positions = {
            # 对方前列 (Row 1, 红线上方)
            "敌前列1": (1, 2), "敌前列2": (1, 4), "敌前列3": (1, 6),

            # 我方顶部/攻击前列 (Row 2, 红线下方)
            "等级3": (2, 0), "库存": (2, 1), "前列1": (2, 2), "前列2": (2, 4), "前列3": (2, 6), "思出": (2, 7),

            # 后列/支持区 (Row 3)
            "等级2": (3, 0),
            "CX": (3, 1),
            "等级4": (3, 2),
            "后列1": (3, 3),
            "后列2": (3, 5),
            "计时7": (3, 6),
            "卡组": (3, 7),

            # 底部/计时升级区 (Row 4)
            "等级1": (4, 0),
            "计时1": (4, 1), "计时2": (4, 2), "计时3": (4, 3),
            "计时4": (4, 4), "计时5": (4, 5), "计时6": (4, 6),
            "控制室": (4, 7),
        }

        for zone_name, (row, col) in button_positions.items():
            x = (col + 0.5) * cell_size
            y = top_margin + (row + 0.5) * cell_size
            if zone_name in self.button_windows:
                self.canvas.coords(self.button_windows[zone_name], x, y)
            elif zone_name.replace("敌", "") in self.enemy_front_windows:
                f_key = zone_name.replace("敌", "")
                self.canvas.coords(self.enemy_front_windows[f_key], x, y)