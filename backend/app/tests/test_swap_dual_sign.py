"""双签确认链路测例:签写模块 + 确认门禁 + 列表投影,内存 sqlite,不依赖 fastapi。"""
import sqlite3
import pytest

from app.modules.swap_sign import record_signature, SignError
from app.modules.swap_gate import confirm_allowed
from app.modules.swap_projection import project_swap
from app.engines.rota import apply_swap

A, B = 1, 2  # 双方成员


def fresh_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE assignments(id INTEGER PRIMARY KEY AUTOINCREMENT, week_id INT, day INT, task_id INT, member_id INT);
    CREATE TABLE swap_requests(id INTEGER PRIMARY KEY AUTOINCREMENT, week_id INT, a_day INT, a_task INT,
                               b_day INT, b_task INT, status TEXT, note TEXT, a_member INT, b_member INT);
    CREATE TABLE swap_signatures(id INTEGER PRIMARY KEY AUTOINCREMENT, swap_id INT, member_id INT,
                                 decision TEXT, created_at TEXT);
    CREATE UNIQUE INDEX idx_swap_signatures_once ON swap_signatures(swap_id, member_id);
    """)
    c.execute("INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (1,0,10,?),(1,1,10,?)", (A, B))
    c.execute("INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note,a_member,b_member)"
              " VALUES (1,0,10,1,10,'pending','',?,?)", (A, B))
    c.commit()
    return c


def gate_of(c, swap_id=1):
    sw = c.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    signed = {r["member_id"] for r in c.execute(
        "SELECT member_id FROM swap_signatures WHERE swap_id=? AND decision='signed'", (swap_id,))}
    return sw, confirm_allowed(sw["status"], (sw["a_member"], sw["b_member"]), signed)


def board(c):
    return [dict(r) for r in c.execute("SELECT day,task_id,member_id FROM assignments WHERE week_id=1 ORDER BY day")]


def test_single_signature_blocks_confirm_and_keeps_cells():
    c = fresh_db()
    before = board(c)
    record_signature(c, 1, A, "sign")
    sw, gate = gate_of(c)
    assert gate["ok"] is False
    assert gate["reason"] == "missing_signatures"
    assert gate["missing"] == [B]
    assert sw["status"] == "pending"      # 单签不改状态
    assert board(c) == before             # 签名动作本身不改格


def test_dual_signature_opens_gate_then_confirm_swaps_cells():
    c = fresh_db()
    record_signature(c, 1, A, "sign")
    assert board(c)[0]["member_id"] == A  # 签完一侧,格仍未动
    record_signature(c, 1, B, "sign")
    sw, gate = gate_of(c)
    assert gate["ok"] is True
    # 门禁放行后才走 confirm 写路径:交换格位 + 置 confirmed
    new_slots = apply_swap(board(c), sw["a_day"], sw["a_task"], sw["b_day"], sw["b_task"])
    for s in new_slots:
        c.execute("UPDATE assignments SET member_id=? WHERE week_id=1 AND day=? AND task_id=?",
                  (s["member_id"], s["day"], s["task_id"]))
    c.execute("UPDATE swap_requests SET status='confirmed' WHERE id=1")
    c.commit()
    assert [r["member_id"] for r in board(c)] == [B, A]
    _, gate_after = gate_of(c)
    assert gate_after["ok"] is False and gate_after["reason"] == "not_pending"


def test_reject_is_terminal_and_never_confirmable():
    c = fresh_db()
    before = board(c)
    out = record_signature(c, 1, A, "reject")
    assert out["status"] == "rejected"
    sw, gate = gate_of(c)
    assert sw["status"] == "rejected"
    assert gate["ok"] is False and gate["reason"] == "rejected"
    assert board(c) == before
    with pytest.raises(SignError) as e:  # 终态后另一侧无法再签
        record_signature(c, 1, B, "sign")
    assert e.value.reason == "not_pending"
    _, gate2 = gate_of(c)
    assert gate2["ok"] is False           # 依旧不可确认


def test_non_party_and_duplicate_sign_rejected():
    c = fresh_db()
    with pytest.raises(SignError) as e:
        record_signature(c, 1, 999, "sign")
    assert e.value.reason == "not_a_party"
    record_signature(c, 1, A, "sign")
    with pytest.raises(SignError) as e2:
        record_signature(c, 1, A, "sign")
    assert e2.value.reason == "already_signed"


def test_projection_shows_dual_sign_state():
    c = fresh_db()
    record_signature(c, 1, A, "sign")
    sw = dict(c.execute("SELECT * FROM swap_requests WHERE id=1").fetchone())
    sigs = [dict(r) for r in c.execute("SELECT swap_id,member_id,decision FROM swap_signatures")]
    view = project_swap(sw, sigs)
    assert view["sign_a"] == "signed" and view["sign_b"] == "pending"
    assert view["dual_signed"] is False
    record_signature(c, 1, B, "sign")
    sigs = [dict(r) for r in c.execute("SELECT swap_id,member_id,decision FROM swap_signatures")]
    view = project_swap(sw, sigs)
    assert view["dual_signed"] is True
