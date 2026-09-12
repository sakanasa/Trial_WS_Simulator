# -*- coding: utf-8 -*-
"""
WS 卡牌效果文本生成器 (Effect Formatter) - 玩家精簡快看版
將算卡操作與參數轉化為符合 WS 牌手習慣的短語概括。
"""

from typing import Dict, Any


def format_operation(op: Dict[str, Any]) -> str:
    """根據操作字典生成玩家精簡版的概括文本"""
    if not isinstance(op, dict):
        return "未知操作"

    # 若傳入的是 UI 暫態操作對象，利用 registry 提取當前 UI 參數
    if "type_var" in op:
        try:
            from utils.registry import registry
            params = registry.extract_params(op)
        except Exception:
            params = {"type": op["type_var"].get()}
    else:
        params = op

    op_type = params.get("type", "未知操作")
    formatter = FORMATTERS.get(op_type, _default_formatter)
    return formatter(params)


# ==================== 玩家精簡快看格式化邏輯 ====================

def _fmt_normal_damage(p: dict) -> str:
    dmg = p.get("damage", 3)
    trig = p.get("trigger_rate", 0.0)
    extra = f" (觸發率{trig:.0f}%)" if trig > 0 else ""
    return f"普通傷害: {dmg}點{extra}"


def _fmt_cancel_damage(p: dict) -> str:
    base = p.get("cancel_damage_base", 1)
    bonus = p.get("cancel_damage_bonus", "0")
    bonus_str = f"+{bonus}" if bonus != "0" else ""
    return f"取消傷害: 基礎{base}{bonus_str}"


def _fmt_role_damage(p: dict) -> str:
    base = p.get("role_damage_base", 0)
    bonus = p.get("role_bonus_type", "魂點")
    trig = p.get("trigger_rate", 30.0)
    extra = f" (觸發率{trig:.0f}%)" if trig > 0 else ""
    return f"角色傷害: 基礎{base}+{bonus}{extra}"


def _fmt_attack_type(p: dict) -> str:
    atype = p.get("attack_type", "正面")
    return f"攻擊方式: {atype}"


def _fmt_push(p: dict) -> str:
    count = p.get("push_count", 1)
    return f"推{count}張"


def _fmt_drain_climax(p: dict) -> str:
    count = p.get("count", 1)
    return f"按潮反洗: 按{count}潮"


def _fmt_normal_wash(p: dict) -> str:
    count = p.get("normal_wash_count", 1)
    return f"普通反洗: {count}張"


def _fmt_shake(p: dict) -> str:
    return "搖勻"


def _fmt_wash_stock(p: dict) -> str:
    return "洗費"


def _fmt_bottom_drain(p: dict) -> str:
    x = p.get("X", 1)
    ltype = p.get("linkage_type", "有潮")
    if ltype == "有潮":
        bdmg = p.get("burn_damage", 1)
        btimes = p.get("burn_times", 1)
        return f"拔底{x}張: 燒{bdmg}點{btimes}次"
    else:
        base_d = p.get("base_damage", 3)
        bonus_d = p.get("damage_bonus", "0")
        base_t = p.get("base_times", 0)
        bonus_t = p.get("times_bonus", "潮數")
        return f"拔底{x}張: 燒({base_d}+{bonus_d})點({base_t}+{bonus_t})次"


def _fmt_dragon_star(p: dict) -> str:
    mode = p.get("dragon_mode", "公開")
    count = p.get("dragon_count", 1)
    return f"龍星擴散爆: {mode}{count}張"


def _fmt_mocha(p: dict) -> str:
    mode = p.get("mocha_mode", "原位")
    count = p.get("mocha_count", 1)
    return f"摩{count}卡，{mode}"


def _fmt_shoot(p: dict) -> str:
    mode = p.get("shoot_mode", "牌組")
    count = p.get("shoot_count", 1) if mode == "牌組" else 1
    return f"射血: {mode}{count}張"


def _fmt_top_deck(p: dict) -> str:
    mode = p.get("top_deck_mode", "控室")
    count = p.get("top_deck_count", 1) if mode == "控室" else 1
    return f"上頂: {mode}{count}張"


def _fmt_multi_climax_cancel(p: dict) -> str:
    dmg = p.get("damage", 3)
    req = p.get("required_climax", 1)
    return f"多潮取消: 傷害{dmg} (需{req}潮)"


def _fmt_special_linkage(p: dict) -> str:
    char = p.get("special_char", "早川秋")
    if char == "早川秋":
        smoke = p.get("hayakawa_count", 0)
        return f"特殊聯動: 早川秋 ({smoke}煙)"
    return f"特殊聯動: {char}"


def _fmt_reduce_soul(p: dict) -> str:
    amount = p.get("reduce_amount", 1)
    return f"減{amount}魂"


def _fmt_ice_armor(p: dict) -> str:
    return "冰甲"


def _fmt_condition_check(p: dict) -> str:
    return "工況判定"


def _fmt_top_check_burn(p: dict) -> str:
    fkind = p.get("filter_kind", "任意")
    flvl = p.get("filter_level", "等級")
    bdmg = p.get("burn_damage", 1)
    btype = p.get("burn_bonus_type", "0")
    btimes = p.get("burn_times", 1)

    cond_parts = []
    if fkind != "任意": cond_parts.append(fkind)
    if flvl != "等級": cond_parts.append(f"Lv.{flvl}")
    cond_str = f" [{','.join(cond_parts)}]" if cond_parts else ""

    return f"翻頂燒: 燒({bdmg}+{btype})點{btimes}次{cond_str}"


def _fmt_top_push_burn(p: dict) -> str:
    pcount = p.get("push_count", 1)
    bdmg = p.get("base_damage", 1)
    dbonus = p.get("damage_bonus", "0")
    btimes = p.get("base_times", 1)
    tbonus = p.get("times_bonus", "0")

    return f"推頂燒: 推{pcount}張，燒({bdmg}+{dbonus})點({btimes}+{tbonus})次"


def _fmt_look_reorder(p: dict) -> str:
    lcount = p.get("look_count", 3)
    mstock = p.get("max_stock", 1)
    return f"羽未: 看頂{lcount}張，充庫至多{mstock}張"


def _fmt_look_select(p: dict) -> str:
    return "選判"


def _fmt_cancel_trigger(p: dict) -> str:
    smode = p.get("sub_mode", "單次觸發")
    if smode == "單次觸發":
        nested = p.get("nested_op")
        nested_str = format_operation(nested) if nested else "無"
        return f"取消觸發 ➔ {nested_str}"
    elif smode == "多次觸發":
        nested_ops = p.get("nested_ops", [])
        tot = p.get("total_triggers", len(nested_ops))
        sub_strs = [format_operation(s) for s in nested_ops]
        return f"取消觸發(至多{tot}次) ➔ [" + ", ".join(sub_strs) + "]"
    elif smode == "傳火":
        target = p.get("pass_target", 1)
        nested = p.get("nested_op")
        nested_str = format_operation(nested) if nested else "無"
        return f"取消觸發 ➔ 傳給#{target}: {nested_str}"
    return "取消觸發"


def _fmt_multi_step(p: dict) -> str:
    steps = p.get("steps", [])
    if not steps:
        return "多步驟: [空]"
    step_strs = [format_operation(s) for s in steps]
    return "多步驟: [" + " ➔ ".join(step_strs) + "]"


def _default_formatter(p: dict) -> str:
    return p.get("type", "未知操作")


# 註冊表字典
FORMATTERS = {
    "普通傷害": _fmt_normal_damage,
    "取消傷害": _fmt_cancel_damage,
    "角色傷害": _fmt_role_damage,
    "攻擊方式": _fmt_attack_type,
    "推牌": _fmt_push,
    "按潮反洗": _fmt_drain_climax,
    "普通反洗": _fmt_normal_wash,
    "搖勻": _fmt_shake,
    "洗費": _fmt_wash_stock,
    "拔底聯動": _fmt_bottom_drain,
    "龍星擴散爆": _fmt_dragon_star,
    "摩卡": _fmt_mocha,
    "射血": _fmt_shoot,
    "上頂": _fmt_top_deck,
    "多潮取消": _fmt_multi_climax_cancel,
    "特殊聯動": _fmt_special_linkage,
    "減魂": _fmt_reduce_soul,
    "冰甲": _fmt_ice_armor,
    "工況判定": _fmt_condition_check,
    "翻頂燒": _fmt_top_check_burn,
    "推頂燒": _fmt_top_push_burn,
    "羽未(決策用)": _fmt_look_reorder,
    "選判": _fmt_look_select,
    "取消觸發": _fmt_cancel_trigger,
    "多步驟操作": _fmt_multi_step,
}