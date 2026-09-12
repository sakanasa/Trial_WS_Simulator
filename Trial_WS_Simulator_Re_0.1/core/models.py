# -*- coding: utf-8 -*-
"""
核心領域模型 (Core Domain Models)
包含了卡牌、卡牌區域、遊戲全局狀態與角色狀態的定義。
"""

import copy
from typing import List, Dict, Union, Any, Optional


# ==================== 鴨子類型輔助函數 ====================

def card_is_climax(card: Union[str, dict, "Card"]) -> bool:
    if isinstance(card, str):
        return card == "名場面"
    elif isinstance(card, dict):
        kind = card.get("kind") or card.get("type")
        return kind == "名場面"
    elif hasattr(card, "is_climax"):
        return card.is_climax()
    return False


def card_is_normal(card: Union[str, dict, "Card"]) -> bool:
    if isinstance(card, str):
        return card == "普通"
    elif isinstance(card, dict):
        kind = card.get("kind") or card.get("type")
        return kind in ("角色", "事件")
    elif hasattr(card, "is_normal"):
        return card.is_normal()
    return False


def get_card_kind(card: Union[str, dict, "Card"]) -> str:
    if isinstance(card, str):
        return "名場面" if card == "名場面" else "角色"
    elif isinstance(card, dict):
        return card.get("kind") or card.get("type") or "角色"
    elif hasattr(card, "kind"):
        return card.kind
    return "角色"


def get_card_level(card: Union[str, dict, "Card"]) -> int:
    if isinstance(card, str):
        return 0
    elif isinstance(card, dict):
        try:
            return int(card.get("level", 0) or 0)
        except (ValueError, TypeError):
            return 0
    elif hasattr(card, "level"):
        return card.level
    return 0


def get_card_soul(card: Union[str, dict, "Card"]) -> int:
    """獲取卡牌的基礎魂點（默認為 1）"""
    if isinstance(card, str):
        return 1 if card == "普通" else 0
    elif isinstance(card, dict):
        try:
            return int(card.get("soul", card.get("base_soul", 1)) or 1)
        except (ValueError, TypeError):
            return 1
    elif hasattr(card, "soul"):
        return card.soul
    return 1


def get_card_base_soul(card: Union[str, dict, "Card"]) -> int:
    """獲取卡牌的基礎魂點（與 get_card_soul 保持一致）"""
    return get_card_soul(card)

def get_card_trigger_soul(card: Union[str, dict, "Card"]) -> int:
    """獲取卡牌判定翻頂牌時的觸發魂加成（默認為 0）"""
    if isinstance(card, str):
        return 0
    elif isinstance(card, dict):
        try:
            val = card.get("trigger_soul", 0)
            return int(val) if val is not None and str(val).isdigit() else 0
        except (ValueError, TypeError):
            return 0
    elif hasattr(card, "trigger_soul"):
        try:
            return int(card.trigger_soul)
        except (ValueError, TypeError):
            return 0
    return 0

def clone_card_list(cards: List[Any]) -> List[Any]:
    if not cards:
        return []
    first = cards[0]
    if isinstance(first, str):
        return cards.copy()
    elif isinstance(first, dict):
        return [c.copy() for c in cards]
    elif hasattr(first, "clone"):
        return [c.clone() for c in cards]
    else:
        return copy.copy(cards)


# ==================== 卡牌對象 ====================

class Card:
    def __init__(
        self,
        kind: str = "角色",
        level: Union[int, str] = 0,
        cost: Union[int, str] = 0,
        soul: Union[int, str] = 1,           # 基礎魂 (Base Soul, 默認 1)
        trigger: str = "無",
        trigger_soul: Union[int, str] = 0,   # 觸發魂 (Trigger Soul, 默認 0)
        base_soul: Optional[Union[int, str]] = None,
    ):
        self.kind = str(kind)
        self.level = int(level) if str(level).isdigit() else 0
        self.cost = int(cost) if str(cost).isdigit() else 0
        self.soul = int(base_soul if base_soul is not None else soul)
        self.base_soul = self.soul
        self.trigger = str(trigger)
        self.trigger_soul = int(trigger_soul) if str(trigger_soul).isdigit() else 0

    def clone(self) -> "Card":
        return Card(
            kind=self.kind,
            level=self.level,
            cost=self.cost,
            soul=self.soul,
            trigger=self.trigger,
            trigger_soul=self.trigger_soul,
            base_soul=self.base_soul,
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "kind": self.kind,
            "level": str(self.level),
            "cost": str(self.cost),
            "soul": str(self.soul),
            "trigger": self.trigger,
            "trigger_soul": str(self.trigger_soul),
            "base_soul": str(self.base_soul),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Card":
        return cls(
            kind=d.get("kind", "角色"),
            level=d.get("level", 0),
            cost=d.get("cost", 0),
            soul=d.get("soul", d.get("base_soul", 1)),
            trigger=d.get("trigger", "無"),
            trigger_soul=d.get("trigger_soul", 0),
            base_soul=d.get("base_soul", 1),
        )

# ==================== 遊戲狀態 ====================

class GameState:
    def __init__(
        self,
        deck: Optional[List[Any]] = None,
        control: Optional[List[Any]] = None,
        stock: Optional[List[Any]] = None,
        level: Optional[Union[List[Any], Dict[str, List[Any]]]] = None,
        clock: Optional[Union[List[Any], Dict[str, List[Any]]]] = None,
        memory: Optional[List[Any]] = None,
        hand: Optional[List[Any]] = None,
        cx: Optional[List[Any]] = None,
        front: Optional[Dict[str, List[Any]]] = None,
        back: Optional[Dict[str, List[Any]]] = None,
    ):
        self.deck = deck if deck is not None else []
        self.control = control if control is not None else []
        self.stock = stock if stock is not None else []
        self.level = level if level is not None else []
        self.clock = clock if clock is not None else []
        self.memory = memory if memory is not None else []
        self.hand = hand if hand is not None else []
        self.cx = cx if cx is not None else []
        self.front = front if front is not None else {f"前列{i}": [] for i in range(1, 4)}
        self.back = back if back is not None else {f"後列{i}": [] for i in range(1, 3)}
        self.failed = False

    def count_climax(self, zone_name: str = "deck") -> int:
        zone = getattr(self, zone_name, [])
        cards = [card for slot in zone.values() for card in slot] if isinstance(zone, dict) else zone
        return sum(1 for c in cards if card_is_climax(c))

    def count_normal(self, zone_name: str = "deck") -> int:
        zone = getattr(self, zone_name, [])
        cards = [card for slot in zone.values() for card in slot] if isinstance(zone, dict) else zone
        return sum(1 for c in cards if card_is_normal(c))

    def clone(self) -> "GameState":
        new_state = GameState()
        new_state.deck = clone_card_list(self.deck)
        new_state.control = clone_card_list(self.control)
        new_state.stock = clone_card_list(self.stock)
        new_state.memory = clone_card_list(self.memory)
        new_state.hand = clone_card_list(self.hand)
        new_state.cx = clone_card_list(self.cx)

        if isinstance(self.level, dict):
            new_state.level = {k: clone_card_list(v) for k, v in self.level.items()}
        else:
            new_state.level = clone_card_list(self.level)

        if isinstance(self.clock, dict):
            new_state.clock = {k: clone_card_list(v) for k, v in self.clock.items()}
        else:
            new_state.clock = clone_card_list(self.clock)

        new_state.front = {k: clone_card_list(v) for k, v in self.front.items()}
        new_state.back = {k: clone_card_list(v) for k, v in self.back.items()}
        new_state.failed = self.failed
        return new_state


# ==================== 角色狀態 ====================

class RoleState:
    def __init__(
        self,
        role_id: int = 1,
        soul: int = 3,
        abilities: Optional[List[Dict[str, Any]]] = None,
        ice_armors: Optional[List[Dict[str, Any]]] = None,
    ):
        self.role_id = role_id
        self.soul = soul
        self.abilities = abilities if abilities is not None else []
        self.ice_armors = ice_armors if ice_armors is not None else []
        self.ice_armor_hits = 0

    def clone(self) -> "RoleState":
        cloned_abilities = [a.copy() for a in self.abilities]
        cloned_ice = [i.copy() for i in self.ice_armors]
        new_role = RoleState(
            role_id=self.role_id,
            soul=self.soul,
            abilities=cloned_abilities,
            ice_armors=cloned_ice,
        )
        new_role.ice_armor_hits = self.ice_armor_hits
        return new_role