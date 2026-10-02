"""双签确认链路测例：单签拒确认、双签后改表、拒签终态、签名不改格、非当事方拒签。"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="chorerota-dual-")
os.environ.setdefault("DATA_DIR", _tmp)

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _client():
    return TestClient(app)


def _grid(client, week_id=1):
    rows = client.get(f"/api/weeks/{week_id}/board").json()["assignments"]
    return {(a["day"], a["task_id"]): a["member_id"] for a in rows}


def _make_swap(client, a_day=0, a_task=1, b_day=0, b_task=2):
    """day0/task1=成员1(阿明) 与 day0/task2=成员2(小雨)，round-robin 相邻两格。"""
    r = client.post("/api/weeks/1/swaps", json={
        "a_day": a_day, "a_task": a_task, "b_day": b_day, "b_task": b_task})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _setup():
    client = _client()
    with client:  # 触发 startup -> seed.init_db
        client.post("/api/weeks/1/generate", json={"days": 7})
    return client


def test_single_sign_confirm_fails_grid_unchanged():
    client = _setup()
    before = _grid(client)
    sid = _make_swap(client)

    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "approve"})
    assert r.status_code == 200
    body = r.json()
    assert body["a"]["decision"] == "approved" and body["b"]["decision"] == "unsigned"
    assert body["ready_to_confirm"] is False
    # 签名动作本身不改格
    assert _grid(client) == before

    r = client.post(f"/api/swaps/{sid}/confirm")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["reason"] == "missing_signature" and detail["missing"] == ["b"]
    # 周格保持原样
    assert _grid(client) == before


def test_dual_sign_confirms_and_swaps_grid():
    client = _setup()
    before = _grid(client)
    sid = _make_swap(client)

    assert client.post(f"/api/swaps/{sid}/sign", json={"member_id": 2, "decision": "approve"}).status_code == 200
    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "approve"})
    assert r.json()["ready_to_confirm"] is True
    # 双签齐备但未确认前仍不改格
    assert _grid(client) == before

    r = client.post(f"/api/swaps/{sid}/confirm")
    assert r.status_code == 200 and r.json()["status"] == "confirmed"

    after = _grid(client)
    assert after[(0, 1)] == before[(0, 2)] == 2
    assert after[(0, 2)] == before[(0, 1)] == 1
    # 仅两格交换，其余不动
    for k, v in before.items():
        if k not in {(0, 1), (0, 2)}:
            assert after[k] == v


def test_reject_is_terminal():
    client = _setup()
    before = _grid(client)
    sid = _make_swap(client)

    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "reject"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert r.json()["a"]["decision"] == "rejected"

    # 终态不可再确认
    r = client.post(f"/api/swaps/{sid}/confirm")
    assert r.status_code == 400 and r.json()["detail"] == "not_pending"
    # 另一方也不能再补签
    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 2, "decision": "approve"})
    assert r.status_code == 400 and r.json()["detail"] == "not_pending"
    # 周格保持原样
    assert _grid(client) == before


def test_non_party_and_duplicate_sign_rejected():
    client = _setup()
    sid = _make_swap(client)

    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 3, "decision": "approve"})
    assert r.status_code == 400 and r.json()["detail"] == "not_a_party"

    client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "approve"})
    r = client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "approve"})
    assert r.status_code == 400 and r.json()["detail"] == "already_signed"


def test_list_projection_reflects_dual_sign_state():
    client = _setup()
    sid = _make_swap(client)
    rows = client.get("/api/swaps").json()
    row = next(r for r in rows if r["id"] == sid)
    assert row["a"]["member_id"] == 1 and row["b"]["member_id"] == 2
    assert row["a"]["member_name"] == "阿明" and row["b"]["member_name"] == "小雨"
    assert row["signed_count"] == 0 and row["ready_to_confirm"] is False

    client.post(f"/api/swaps/{sid}/sign", json={"member_id": 1, "decision": "approve"})
    row = next(r for r in client.get("/api/swaps").json() if r["id"] == sid)
    assert row["signed_count"] == 1 and row["ready_to_confirm"] is False
