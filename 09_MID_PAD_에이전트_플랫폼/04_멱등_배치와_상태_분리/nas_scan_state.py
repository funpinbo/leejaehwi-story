"""NAS 스캔 · 임베딩 배치의 두 상태(status / rag_status)와 복원 시 좌초 사고 재현.

RESET_ON_RESTORE=False → 복원 시 rag_status를 리셋하지 않아 문서가 RAG에서 영구 누락(실제 사고)
RESET_ON_RESTORE=True  → 복원 시 rag_status=PENDING으로 함께 리셋(수정 후)
"""

import hashlib
import sys
from dataclasses import dataclass

RESET_ON_RESTORE = "--bug" not in sys.argv
FULL_HASH_LIMIT = 512 * 1024 * 1024
MAX_FAILS = 3


@dataclass
class Asset:
    path: str
    size: int
    mtime: int
    content_hash: str
    status: str = "REGISTERED"   # 원장 상태
    rag_status: str = "PENDING"  # RAG 반영 상태 (별개 생명주기)
    fails: int = 0
    deleted: bool = False


def content_hash(data: bytes) -> str:
    if len(data) <= FULL_HASH_LIMIT:
        return hashlib.sha256(data).hexdigest()[:12]
    mb = 1024 * 1024
    return "partial-" + hashlib.sha256(data[:mb] + data[-mb:]).hexdigest()[:12]


class Pipeline:
    def __init__(self):
        self.assets: dict[str, Asset] = {}
        self.rag: dict[str, int] = {}  # chatbot 쪽: doc_id → 청크 수

    def scan(self, nas: dict[str, tuple[int, bytes]]) -> list[str]:
        log = []
        for path, (mtime, data) in nas.items():
            a = self.assets.get(path)
            if a and not a.deleted and (a.mtime, a.size) == (mtime, len(data)):
                continue  # 변경 없음 → 다운로드·해시 생략
            h = content_hash(data)
            if a is None:
                self.assets[path] = Asset(path, len(data), mtime, h)
                log.append(f"CREATED  {path}")
            elif a.deleted:
                a.deleted, a.status, a.mtime, a.size, a.content_hash = False, "REGISTERED", mtime, len(data), h
                if RESET_ON_RESTORE:
                    a.rag_status = "PENDING"  # ← 사고 후 추가된 한 줄
                log.append(f"RESTORED {path}")
            elif h != a.content_hash:
                a.mtime, a.size, a.content_hash, a.rag_status = mtime, len(data), h, "PENDING"
                log.append(f"MODIFIED {path}")
        for path, a in self.assets.items():
            if path not in nas and not a.deleted:
                a.deleted, a.status = True, "MISSING"
                log.append(f"MISSING  {path}")
        return log

    def embed(self, fail_paths: set[str] = frozenset()) -> list[str]:
        log = []
        for a in self.assets.values():  # 1) 삭제 전파
            if a.deleted and a.rag_status == "EMBEDDED" and a.path in self.rag:
                del self.rag[a.path]
                log.append(f"delete-by-doc {a.path}")
        for a in self.assets.values():  # 2) PENDING 처리 (항목 단위 실패 격리)
            if a.deleted or a.rag_status != "PENDING" or a.status == "QUARANTINED":
                continue
            if a.path in fail_paths:
                a.fails += 1  # 이 항목만 실패, 나머지는 계속 진행
                if a.fails >= MAX_FAILS:
                    a.status, a.rag_status = "QUARANTINED", "FAILED"  # 더 이상 매 배치를 잡아먹지 않게 격리
                log.append(f"FAILED   {a.path} (#{a.fails}){' → QUARANTINED' if a.fails >= MAX_FAILS else ''}")
                continue
            self.rag[a.path] = max(1, a.size // 100)  # 문서 단위 통째 교체
            a.rag_status = "EMBEDDED"
            log.append(f"EMBEDDED {a.path}")
        return log

    def consistency_check(self) -> list[str]:
        return [a.path for a in self.assets.values()
                if a.status == "REGISTERED" and not a.deleted and a.rag_status == "EMBEDDED" and a.path not in self.rag]


def main() -> None:
    print(f"RESET_ON_RESTORE = {RESET_ON_RESTORE}  (--bug 옵션으로 사고 재현)\n")
    p = Pipeline()
    timeline = [
        ("t1 생성", {"/MID/spec_a.pdf": (1, b"a" * 500), "/MID/spec_b.pdf": (1, b"b" * 300),
                     "/MID/broken.pdf": (1, b"x" * 50)}),
        ("t2 a 수정", {"/MID/spec_a.pdf": (2, b"A" * 520), "/MID/spec_b.pdf": (1, b"b" * 300),
                      "/MID/broken.pdf": (1, b"x" * 50)}),
        ("t3 b 삭제", {"/MID/spec_a.pdf": (2, b"A" * 520), "/MID/broken.pdf": (1, b"x" * 50)}),
        ("t4 b 복원", {"/MID/spec_a.pdf": (2, b"A" * 520), "/MID/spec_b.pdf": (3, b"b" * 300),
                      "/MID/broken.pdf": (1, b"x" * 50)}),
    ]
    for label, nas in timeline:
        print(f"[{label}]")
        for line in p.scan(nas) + p.embed(fail_paths={"/MID/broken.pdf"}):
            print("   ", line)
    print("\n최종 상태")
    for a in p.assets.values():
        print(f"   {a.path:<18} status={a.status:<12} rag_status={a.rag_status:<9} RAG청크={'있음' if a.path in p.rag else '없음'}")
    stranded = p.consistency_check()
    print(f"\n정합성 점검: {'⚠ 원장은 정상인데 RAG에 없음 → ' + str(stranded) if stranded else '이상 없음 ✅'}")


if __name__ == "__main__":
    main()
