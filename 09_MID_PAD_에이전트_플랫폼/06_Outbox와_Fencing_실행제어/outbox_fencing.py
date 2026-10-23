"""Control Layer 핵심 동작 재현 (SQLite).

① Idempotency      : 같은 request_id는 다시 실행하지 않는다
② Outbox           : step 상태 변경과 이벤트 기록을 한 트랜잭션에
③ Fencing          : step을 재할당할 때마다 claim_epoch 증가, 옛 epoch의 결과는 거부
④ Partial retry    : FAILED step만 재실행
⑤ Dedup            : outbox는 at-least-once, 구독자가 dedup_key로 중복 제거
"""

import json
import sqlite3

DAG = ["validate", "render_docx", "render_pdf"]


class Control:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(
            """
            CREATE TABLE execution (request_id TEXT PRIMARY KEY, status TEXT);
            CREATE TABLE step (request_id TEXT, name TEXT, status TEXT, claim_epoch INTEGER, result TEXT,
                               PRIMARY KEY (request_id, name));
            CREATE TABLE event (id INTEGER PRIMARY KEY, ordering_key TEXT, dedup_key TEXT UNIQUE,
                                type TEXT, payload TEXT, published INTEGER DEFAULT 0);
            """
        )

    def _event(self, request_id: str, etype: str, payload: dict, dedup: str) -> None:
        self.db.execute("INSERT INTO event (ordering_key, dedup_key, type, payload) VALUES (?,?,?,?)",
                        (f"execution:{request_id}", dedup, etype, json.dumps(payload)))

    def submit(self, request_id: str) -> str:
        row = self.db.execute("SELECT status FROM execution WHERE request_id=?", (request_id,)).fetchone()
        if row:
            return f"기존 실행 반환 (status={row[0]}) — 재실행 안 함"
        with self.db:  # 한 트랜잭션
            self.db.execute("INSERT INTO execution VALUES (?, 'RUNNING')", (request_id,))
            self.db.executemany("INSERT INTO step VALUES (?,?,'PENDING',0,NULL)", [(request_id, s) for s in DAG])
            self._event(request_id, "execution.created", {}, f"{request_id}:created")
        return "새 실행 생성"

    def claim(self, request_id: str, name: str) -> int:
        with self.db:
            self.db.execute("UPDATE step SET claim_epoch=claim_epoch+1, status='RUNNING' "
                            "WHERE request_id=? AND name=?", (request_id, name))
            epoch = self.db.execute("SELECT claim_epoch FROM step WHERE request_id=? AND name=?",
                                    (request_id, name)).fetchone()[0]
            self._event(request_id, "step.claimed", {"step": name, "epoch": epoch}, f"{request_id}:{name}:claim:{epoch}")
        return epoch

    def report(self, request_id: str, name: str, epoch: int, ok: bool, result: str = "") -> str:
        with self.db:  # 상태 변경 + 이벤트 = 한 트랜잭션
            cur = self.db.execute(
                "UPDATE step SET status=?, result=? WHERE request_id=? AND name=? AND claim_epoch=? AND status='RUNNING'",
                ("SUCCEEDED" if ok else "FAILED", result, request_id, name, epoch))
            if cur.rowcount == 0:
                return f"거부 (epoch={epoch} — 이미 재할당된 step의 늦은 결과)"
            self._event(request_id, f"step.{'succeeded' if ok else 'failed'}", {"step": name},
                        f"{request_id}:{name}:done:{epoch}")
            self._aggregate(request_id)
        return "반영"

    def _aggregate(self, request_id: str) -> None:
        statuses = {s for (s,) in self.db.execute("SELECT status FROM step WHERE request_id=?", (request_id,))}
        if statuses <= {"SUCCEEDED"}:
            agg = "SUCCEEDED"
        elif statuses <= {"FAILED"}:
            agg = "FAILED"
        elif statuses & {"PENDING", "RUNNING"}:
            agg = "RUNNING"
        else:
            agg = "PARTIAL_SUCCESS"
        self.db.execute("UPDATE execution SET status=? WHERE request_id=?", (agg, request_id))

    def retry_targets(self, request_id: str) -> list[str]:
        return [n for (n,) in self.db.execute(
            "SELECT name FROM step WHERE request_id=? AND status='FAILED'", (request_id,))]

    def status(self, request_id: str) -> str:
        return self.db.execute("SELECT status FROM execution WHERE request_id=?", (request_id,)).fetchone()[0]

    def outbox_batch(self) -> list[tuple]:
        return self.db.execute("SELECT dedup_key, type FROM event WHERE published=0 ORDER BY id").fetchall()


def main() -> None:
    c, rid = Control(), "req-pad-0412"
    print("① submit:", c.submit(rid))
    print("① 재전송:", c.submit(rid))

    e = c.claim(rid, "validate")
    print("\n   validate:", c.report(rid, "validate", e, ok=True))

    old = c.claim(rid, "render_docx")      # Worker A가 맡음
    new = c.claim(rid, "render_docx")      # 타임아웃 → Worker B에 재할당 (epoch 증가)
    print(f"③ render_docx 재할당 epoch {old} → {new}")
    print("   Worker B 결과:", c.report(rid, "render_docx", new, ok=True, result="docx#2"))
    print("   Worker A 결과(늦게 도착):", c.report(rid, "render_docx", old, ok=True, result="docx#1"))

    e = c.claim(rid, "render_pdf")
    print("\n   render_pdf:", c.report(rid, "render_pdf", e, ok=False))
    print("   execution 상태:", c.status(rid))
    targets = c.retry_targets(rid)
    print(f"④ retry 대상: {targets}  (SUCCEEDED step은 재사용)")
    for name in targets:
        e = c.claim(rid, name)
        print(f"   {name} 재시도:", c.report(rid, name, e, ok=True))
    print("   execution 상태:", c.status(rid))

    # ⑤ 발행기가 같은 배치를 두 번 보냈다고 가정 (at-least-once)
    batch = c.outbox_batch()
    delivered, seen = batch + batch[:3], set()
    applied = [k for k, _ in delivered if not (k in seen or seen.add(k))]
    print(f"\n⑤ outbox 전달 {len(delivered)}건 → 구독자 반영 {len(applied)}건 (중복 {len(delivered) - len(applied)}건 제거)")


if __name__ == "__main__":
    main()
