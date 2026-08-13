# -*- coding: utf-8 -*-
"""
工况局势数据与 JSON 存档服务 (Condition State Service)
负责工况模式下我方/敌方各个卡区数据管理、容量上限配置以及局势配置的 JSON 导出与导入。
"""

import tkinter as tk
import customtkinter as ctk
from typing import Dict, List, Any, Optional


def clean_card_for_json(card: Any) -> Any:
    """🌟 核心清洗函数：过滤掉卡牌字典中的 UI 控件句柄 (CTkFrame/CTkButton/tk.Variable)，提取纯数据"""
    if isinstance(card, str):
        return card
    if not isinstance(card, dict):
        return str(card)

    cleaned = {}
    for k, v in card.items():
        # 1. 过滤掉所有 Tkinter/CustomTkinter 控件与 Variable 对象
        if isinstance(v, (tk.Variable, tk.Widget, ctk.CTkBaseClass)):
            continue
        # 2. 过滤掉 UI 临时挂载的控件键名
        if k.endswith("_var") or k.startswith("btn_") or k in ("card_container", "pos_label", "desc_box", "row_frame"):
            continue
        cleaned[k] = v
    return cleaned


def clean_zone_cards(zone_data: Any) -> Any:
    """递归清理列表或字典卡区里的卡牌数据"""
    if isinstance(zone_data, list):
        return [clean_card_for_json(c) for c in zone_data]
    elif isinstance(zone_data, dict):
        return {k: [clean_card_for_json(c) for c in v] for k, v in zone_data.items()}
    return zone_data


class ConditionStateService:
    """工况局势状态与存档服务类（单例服务）"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.init_state()

    def init_state(self):
        """初始化/重置所有工况卡区列表与上限配置"""
        self.deck_cards: List[Any] = []
        self.control_cards: List[Any] = []
        self.memory_cards: List[Any] = []
        self.stock_cards: List[Any] = []
        self.cx_cards: List[Any] = []
        self.hand_cards: List[Any] = []

        self.level_cards: Dict[str, List[Any]] = {f"等级{i}": [] for i in range(1, 5)}
        self.clock_cards: Dict[str, List[Any]] = {f"计时{i}": [] for i in range(1, 8)}
        self.front_cards: Dict[str, List[Any]] = {f"前列{i}": [] for i in range(1, 4)}
        self.back_cards: Dict[str, List[Any]] = {f"后列{i}": [] for i in range(1, 3)}
        self.enemy_front_cards: Dict[str, List[Any]] = {f"敌前列{i}": [] for i in range(1, 4)}

        self.zones: Dict[str, List[Any]] = {
            "卡组": self.deck_cards, "控制室": self.control_cards,
            "思出": self.memory_cards, "库存": self.stock_cards,
            "CX": self.cx_cards, "手牌": self.hand_cards,
        }
        self.zones.update(self.level_cards)
        self.zones.update(self.clock_cards)
        self.zones.update(self.front_cards)
        self.zones.update(self.back_cards)
        self.zones.update(self.enemy_front_cards)

        self.zone_max_cards: Dict[str, Optional[int]] = {
            "卡组": None, "控制室": None, "思出": None, "库存": None, "CX": 1, "手牌": None,
        }
        for k in self.level_cards: self.zone_max_cards[k] = 1
        for k in self.clock_cards: self.zone_max_cards[k] = 1
        for k in self.front_cards: self.zone_max_cards[k] = 1
        for k in self.back_cards: self.zone_max_cards[k] = 1
        for k in self.enemy_front_cards: self.zone_max_cards[k] = 1

        self.adv_roles: List[dict] = []
        self.plan_steps: List[dict] = []
        self.condition_roles: List[dict] = []
        self.condition_plan_steps: List[dict] = []

    def serialize_data(
        self, 
        enemy_front_roles: dict, 
        roles_serialized: list, 
        plan_serialized: list
    ) -> dict:
        """序列化工况局势为字典（自动清洗剔除 UI 控件对象，确保 JSON 序列化无报错）"""
        return {
            "deck": clean_zone_cards(self.deck_cards),
            "control": clean_zone_cards(self.control_cards),
            "stock": clean_zone_cards(self.stock_cards),
            "memory": clean_zone_cards(self.memory_cards),
            "level": clean_zone_cards(self.level_cards),
            "clock": clean_zone_cards(self.clock_cards),
            "front": clean_zone_cards(self.front_cards),
            "back": clean_zone_cards(self.back_cards),
            "cx": clean_zone_cards(self.cx_cards),
            "hand": clean_zone_cards(self.hand_cards),
            "enemy_front_cards": clean_zone_cards(self.enemy_front_cards),
            "enemy_front_roles": enemy_front_roles,
            "roles": roles_serialized,
            "plan": plan_serialized,
        }

    def deserialize_data(self, data: dict):
        """从字典反序列化恢复卡区内容"""
        self.deck_cards[:] = data.get("deck", [])
        self.control_cards[:] = data.get("control", [])
        self.stock_cards[:] = data.get("stock", [])
        self.memory_cards[:] = data.get("memory", [])
        if "cx" in data and isinstance(data["cx"], list):
            self.cx_cards[:] = data["cx"]
        if "hand" in data and isinstance(data["hand"], list):
            self.hand_cards[:] = data["hand"]

        for key_name, target_dict in [
            ("front", self.front_cards),
            ("back", self.back_cards),
            ("level", self.level_cards),
            ("clock", self.clock_cards),
            ("enemy_front_cards", self.enemy_front_cards)
        ]:
            if key_name in data and isinstance(data[key_name], dict):
                for k, v in data[key_name].items():
                    if k in target_dict:
                        target_dict[k][:] = v


condition_state_service = ConditionStateService()