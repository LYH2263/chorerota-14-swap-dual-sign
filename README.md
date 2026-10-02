# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 申请对调 → 双方签名 → 确认改表。

对调双签：pending 对调须 a/b 两方成员各签一次（`POST /api/swaps/{id}/sign`,decision=sign|reject)；缺任一侧签名时 confirm 失败且周格原样；任一方拒签即 `rejected` 终态不可再确认。签名只登记不改格，看板仅在确认成功后交换格位。签写/门禁/投影分模块：`app/modules/swap_sign`、`swap_gate`（纯函数，只吃签名齐备，不做票面重算）、`swap_projection`。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。
