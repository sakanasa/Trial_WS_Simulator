# -*- coding: utf-8 -*-
"""
工況模式戰場畫布組件 (Condition Field Canvas Component) - CTk 淺色重構版
負責 8列 6行 正方形網格戰場的響應式繪製、對方前列力量/等級配置與區域點擊事件派發。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, Callable, Optional, Any
from ui.components.app_dropdown import AppDropdown
from ui.components.app_dropdown import PALETTE, FONT_GLOBAL
FONT_GLOBAL_BOLD = ("微軟雅黑", -14, "bold")

class ConditionFieldCanvas(ctk.CTkFrame):
    """工況模式可視化網格畫布（CTk 淺色高顏值版）"""

    def _set_appearance_mode(self, mode_string):
        """重寫底層監聽：當主題改變時，同步強制刷新 Canvas 及內部控件的底色"""
        super()._set_appearance_mode(mode_string)
        self._update_canvas_theme()

    def _update_canvas_theme(self):
        """實時將 Canvas 背景、分割線和內部嵌入控件的直角底色染成一致，消除白邊"""
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
            
        # 1. 提取當前模式底下的調色盤色值
        mode_idx = 0 if ctk.get_appearance_mode() == "Light" else 1
        bg_color = PALETTE["card_bg"][mode_idx]
        text_color = PALETTE["text_main"][mode_idx]
        border_color = PALETTE["card_border"][mode_idx]

        # 2. 將 Canvas 畫布背景色和文字色與主題拉平
        self.canvas.configure(bg=bg_color)
        self.canvas.itemconfig(self.top_text_id, fill=text_color)
        
        # 網格分割線也改用 card_border 配色，保持極簡高級感
        self.canvas.itemconfig("grid_line", fill=border_color)

        # 3. 強制更新所有常駐按鈕的 bg_color，將多餘直角徹底隱藏
        for btn in self.zone_buttons.values():
            if btn.winfo_exists():
                btn.configure(bg_color=bg_color)
        
        if self.hand_btn.winfo_exists():
            self.hand_btn.configure(bg_color=bg_color)
            
        # 🌟 新增下面這幾行，強行粉碎“我方”文本框區域的白色直角方框
        if self.hand_bottom_frame.winfo_exists():
            self.hand_bottom_frame.configure(bg_color=bg_color)
        if hasattr(self, "bottom_label") and self.bottom_label.winfo_exists():
            self.bottom_label.configure(bg_color=bg_color)
        if hasattr(self, "overview_btn") and self.overview_btn.winfo_exists():
            self.overview_btn.configure(bg_color=bg_color)

        # 4. 強制更新對方前列屬性卡片（CTkFrame）的 bg_color
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

        # 對方前列力量與等級數據映射
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
        # 採用緊湊型五號字
        label_font = FONT_GLOBAL
        bold_font = FONT_GLOBAL_BOLD

        # 1. 戰場 Canvas 容器，背景色通過 _update_canvas_theme 動態刷新
        self.canvas = tk.Canvas(self, height=360, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.top_text_id = self.canvas.create_text(
            10, 10, text="對方", font=bold_font, anchor="center"
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
            self.hand_bottom_frame, text="概覽", width=55, height=28, corner_radius=4,
            font=bold_font,
            fg_color=PALETTE["primary"], text_color=("#FFFFFF", "#0B0F19"), hover_color=PALETTE["primary_hover"],
            command=self.on_overview_click
        )
        self.overview_btn.pack(side=tk.LEFT, padx=6)

        self.hand_bottom_id = self.canvas.create_window(
            0, 0, window=self.hand_bottom_frame, anchor="center"
        )

        # 3. 註冊標準卡區按鈕
        button_configs = [
            ("牌組", "牌組"), ("控制室", "控室"), ("思出", "思出"), ("能量", "能量"), ("CX", "CX"),
            ("等級1", "等級1"), ("等級2", "等級2"), ("等級3", "等級3"), ("等級4", "等級4"),
            ("前列1", "前列1"), ("前列2", "前列2"), ("前列3", "前列3"),
            ("後列1", "後列1"), ("後列2", "後列2"),
        ]
        for i in range(1, 8):
            button_configs.append((f"傷害{i}", f"傷害{i}"))

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

        # 4. 創建對方前列屬性卡片並保存引用（用來動態清除直角白邊）
        self.enemy_boxes = []
        for front_key in ["前列1", "前列2", "前列3"]:
            role_data = self.enemy_front_roles[front_key]
            lvl_var = role_data["level"]
            pwr_var = role_data["power"]

            # 將對方卡片框架的邊框調配到 card_border 極客藍
            box = ctk.CTkFrame(
                self.canvas, 
                fg_color=PALETTE["card_bg"], 
                corner_radius=6, 
                border_width=1, 
                border_color=PALETTE["card_border"]
            )

            ctk.CTkLabel(box, text=f"敵{front_key}", font=("微軟雅黑", -11, "bold"), text_color=PALETTE["text_main"]).pack(anchor="center", pady=(2, 0))

            top_f = ctk.CTkFrame(box, fg_color="transparent")
            top_f.pack(fill=tk.X, padx=4, pady=1)
            ctk.CTkLabel(top_f, text="等級:", font=label_font, text_color=PALETTE["text_sub"]).pack(side=tk.LEFT, padx=1)
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
        
        # 強制在初始化時執行一次底色渲染
        self._update_canvas_theme()

    def _redraw_grid(self, event=None):
        cw = event.width if event else self.canvas.winfo_width()
        if cw < 10:
            return

        cell_size = cw / 8
        # 網格包含 5 行主體對戰區域 (Row 0~4)
        grid_rows = 5
        grid_height = cell_size * grid_rows
        top_margin = 30
        bottom_margin = 35
        total_height = top_margin + grid_height + bottom_margin

        # 🌟【核心修復】：實時將等比例計算出的 total_height 設置給 Canvas 畫布
        # 確保畫布高度隨寬度自適應伸縮，徹底解決寬度變大時我方底部卡區（後列/傷害區/控制室/手牌欄）被截斷的 Bug！
        self.canvas.configure(height=int(total_height))

        self.canvas.delete("grid")

        # 1. 繪製縱向網格線 (將 tags="grid" 升級為雙標籤，增加 "grid_line")
        for i in range(9):
            x = i * cell_size
            self.canvas.create_line(x, top_margin, x, top_margin + grid_height, fill=PALETTE["card_border"][0], tags=("grid", "grid_line"))

        # 2. 繪製橫向網格線 (同樣打上 "grid_line" 標籤)
        for j in range(grid_rows + 1):
            y = top_margin + j * cell_size
            self.canvas.create_line(0, y, cw, y, fill=PALETTE["card_border"][0], tags=("grid", "grid_line"))

        # 3. 敵我分割紅線
        y_sep = top_margin + 2 * cell_size
        self.canvas.create_line(0, y_sep, cw, y_sep, fill="#EF4444", width=2, tags="grid")
        
        # 4. 重建線條後，立即重刷一次顏色狀態
        self._update_canvas_theme()

        # 4. 更新頂部“對方”文本與底部“我方/手牌/概覽”控制行座標
        self.canvas.coords(self.top_text_id, cw / 2, top_margin / 2)
        self.canvas.coords(self.hand_bottom_id, cw / 2, top_margin + grid_height + bottom_margin / 2)

        # 5. 重新映射對戰墊標準座標
        button_positions = {
            # 對方前列 (Row 1, 紅線上方)
            "敵前列1": (1, 2), "敵前列2": (1, 4), "敵前列3": (1, 6),

            # 我方頂部/攻擊前列 (Row 2, 紅線下方)
            "等級3": (2, 0), "能量": (2, 1), "前列1": (2, 2), "前列2": (2, 4), "前列3": (2, 6), "思出": (2, 7),

            # 後列/支持區 (Row 3)
            "等級2": (3, 0),
            "CX": (3, 1),
            "等級4": (3, 2),
            "後列1": (3, 3),
            "後列2": (3, 5),
            "傷害7": (3, 6),
            "牌組": (3, 7),

            # 底部/傷害升級區 (Row 4)
            "等級1": (4, 0),
            "傷害1": (4, 1), "傷害2": (4, 2), "傷害3": (4, 3),
            "傷害4": (4, 4), "傷害5": (4, 5), "傷害6": (4, 6),
            "控制室": (4, 7),
        }

        for zone_name, (row, col) in button_positions.items():
            x = (col + 0.5) * cell_size
            y = top_margin + (row + 0.5) * cell_size
            if zone_name in self.button_windows:
                self.canvas.coords(self.button_windows[zone_name], x, y)
            elif zone_name.replace("敵", "") in self.enemy_front_windows:
                f_key = zone_name.replace("敵", "")
                self.canvas.coords(self.enemy_front_windows[f_key], x, y)