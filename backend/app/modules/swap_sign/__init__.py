"""签写模块:登记对调双方成员的签名/拒签,只写 swap_signatures,绝不动周格。

- 仅 pending 对调可签;confirmed/rejected 一律拒绝(not_pending)。
- 仅 a_member/b_member 两位当事人可签,每人限签一次(UNIQUE 兜底)。
- decision='reject' 立即把对调置为 rejected 终态,之后不可再签、不可确认。
- 签名动作本身不改 assignments——格位只在 confirm 门禁放行后交换。
"""
import sqlite3
from datetime import datetime, timezone

SIGN = "sign"
REJECT = "reject"
DECISIONS = {SIGN: "signed", REJECT: "rejected"}


class SignError(Exception):
    def __init__(self, status: int, reason: str):
        super().__init__(reason)
        self.status = status
        self.reason = reason


def record_signature(conn: sqlite3.Connection, swap_id: int, member_id: int, decision: str) -> dict:
    """登记一侧签名,返回该对调当前的双签进度。不改任何周格。"""
    if decision not in DECISIONS:
        raise SignError(400, "bad_decision")
    swap = conn.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if swap is None:
        raise SignError(404, "swap_not_found")
    if swap["status"] != "pending":
        raise SignError(400, "not_pending")
    parties = (swap["a_member"], swap["b_member"])
    if member_id not in parties:
        raise SignError(400, "not_a_party")
    dup = conn.execute(
        "SELECT 1 FROM swap_signatures WHERE swap_id=? AND member_id=?",
        (swap_id, member_id)).fetchone()
    if dup:
        raise SignError(400, "already_signed")
    conn.execute(
        "INSERT INTO swap_signatures(swap_id,member_id,decision,created_at) VALUES (?,?,?,?)",
        (swap_id, member_id, DECISIONS[decision],
         datetime.now(timezone.utc).isoformat(timespec="seconds")))
    if decision == REJECT:
        conn.execute("UPDATE swap_requests SET status='rejected' WHERE id=?", (swap_id,))
    conn.commit()
    return progress(conn, swap_id)


def progress(conn: sqlite3.Connection, swap_id: int) -> dict:
    """某对调的签名进度快照,供签写接口回包与排障。"""
    swap = conn.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    signed = {r["member_id"] for r in conn.execute(
        "SELECT member_id FROM swap_signatures WHERE swap_id=? AND decision='signed'", (swap_id,))}
    return {
        "ok": True,
        "swap_id": swap_id,
        "status": swap["status"],
        "signed": sorted(m for m in (swap["a_member"], swap["b_member"]) if m in signed),
    }
