# -*- coding: utf-8 -*-
"""
高級模式角色定義存檔持久化服務 (Advanced Roles Preset Service)
負責本地 advanced_roles_presets.json 文件的讀取、保存與具名存檔管理。
"""

from services.preset_store import PresetStore

# 全局單例服務實例
advanced_roles_service = PresetStore("advanced_roles_presets.json")
