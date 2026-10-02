"""列表投影:把 swap_requests 行 + 签名记录投影成对调列表视图,展示双签状态。

每行附带 sign_a/sign_b(对应 a_member/b_member 各自的签署态:
signed / rejected / pending)与 dual_signed 汇总位,前端直接渲染。
纯函数,不碰数据库。
"""

PENDING = "pending"


def project_swap(swap: dict, signatures: list[dict]) -> dict:
    by_member = {s["member_id"]: s["decision"] for s in signatures}
    out = dict(swap)
    out["sign_a"] = by_member.get(swap.get("a_member"), PENDING)
    out["sign_b"] = by_member.get(swap.get("b_member"), PENDING)
    out["dual_signed"] = out["sign_a"] == "signed" and out["sign_b"] == "signed"
    return out


def project_swaps(swaps: list[dict], sigs_by_swap: dict[int, list[dict]]) -> list[dict]:
    return [project_swap(s, sigs_by_swap.get(s["id"], [])) for s in swaps]
