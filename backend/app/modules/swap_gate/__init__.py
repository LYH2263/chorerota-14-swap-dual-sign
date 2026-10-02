"""确认门禁:纯函数,只回答「此刻能不能确认改表」。

门禁只吃签名齐备(status + 应签双方 + 已签集合),不做票面重算——
即使将来与预演票路径并存,放行依据也只是双签齐,而不是重算对调内容。
格位的实际交换与合法性兜底发生在 confirm 的写路径(apply_swap),与门禁无关。
"""

REJECTED = "rejected"
PENDING = "pending"


def confirm_allowed(status: str, required: tuple, signed: set) -> dict:
    """status=rejected 是终态;pending 须 required 双方都在 signed 中才放行。"""
    if status == REJECTED:
        return {"ok": False, "reason": "rejected", "missing": []}
    if status != PENDING:
        return {"ok": False, "reason": "not_pending", "missing": []}
    missing = [m for m in required if m not in signed]
    if missing:
        return {"ok": False, "reason": "missing_signatures", "missing": missing}
    return {"ok": True, "reason": "", "missing": []}
