# -*- coding: utf-8 -*-
"""
通用具名存檔持久化倉儲 (Preset Store)
負責把「名稱 -> 任意可序列化資料」的具名存檔對照表讀寫到本地 JSON 文件。
"""

import os
import json
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PresetStore:
    """單一 JSON 文件的具名存檔管理類（每個文件各自獨立實例，不共用單例）"""

    def __init__(self, filename: str):
        self.file_path = os.path.join(BASE_DIR, filename)
        self.presets: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        self.presets = {}
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.presets = data
            except Exception as e:
                print(f"[WARN] 讀取本地 {os.path.basename(self.file_path)} 失敗: {e}")
        return self.presets

    def save(self) -> bool:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] 保存 {os.path.basename(self.file_path)} 失敗: {e}")
            return False

    def get_names(self) -> List[str]:
        return list(self.presets.keys())

    def get_preset(self, name: str) -> Optional[Any]:
        return self.presets.get(name)

    def set_preset(self, name: str, data: Any) -> bool:
        self.presets[name] = data
        return self.save()

    def delete_preset(self, name: str) -> bool:
        if name in self.presets:
            del self.presets[name]
            return self.save()
        return False
