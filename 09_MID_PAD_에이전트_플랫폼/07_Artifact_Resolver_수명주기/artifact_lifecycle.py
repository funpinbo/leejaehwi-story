"""Artifact Resolver 수명주기 · 접근 제어 재현 (인메모리).

- BUILDING → VALIDATING → READY 를 거쳐야만 alias(latest)로 보인다
- checksum 불일치면 FAILED, 이전 latest는 그대로
- 권한 없는 호출자에게는 403이 아니라 404 (존재 숨김)
- owner_service는 호출자 identity와 같아야 함 (proxy identity만 예외)
- 기본 공개 범위가 선언되지 않은 kind는 ACL이 없으면 거부
"""

import hashlib
from dataclasses import dataclass, field

DEFAULT_ACL_BY_KIND = {"pad_document": {"pad-team"}}  # 선언된 kind만 기본 범위 적용
IDENTITIES = {  # 호출자 토큰 → identity (실제로는 토큰 해시로 저장)
    "tok-render-svc": {"name": "render-svc", "scopes": {"pad-team"}, "proxy": False},
    "tok-chatbot": {"name": "chatbot", "scopes": {"pad-team"}, "proxy": False},
    "tok-search-svc": {"name": "search-svc", "scopes": {"public"}, "proxy": False},
    "tok-control": {"name": "control", "scopes": set(), "proxy": True},
}


class HTTPError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(f"{status} {code}")


@dataclass
class Revision:
    rid: int
    entity: str
    kind: str
    owner: str
    expected_sha: str
    state: str = "BUILDING"
    content: bytes = b""
    acl: set[str] = field(default_factory=set)
    parents: list[int] = field(default_factory=list)


class Resolver:
    def __init__(self):
        self.revisions: dict[int, Revision] = {}
        self.alias: dict[str, int] = {}  # entity → latest revision id
        self._next = 1

    def _who(self, token: str) -> dict:
        if token not in IDENTITIES:
            raise HTTPError(401, "TOKEN_REQUIRED")
        return IDENTITIES[token]

    def create_upload(self, token: str, entity: str, kind: str, owner: str, sha: str,
                      acl: set[str] | None = None, parents: list[int] | None = None) -> int:
        who = self._who(token)
        if owner != who["name"] and not who["proxy"]:
            raise HTTPError(403, "OWNER_MISMATCH")  # 다른 서비스 이름으로 등록 불가
        rev = Revision(self._next, entity, kind, owner, sha, acl=acl or set(), parents=parents or [])
        self.revisions[rev.rid] = rev
        self._next += 1
        return rev.rid

    def put_and_commit(self, token: str, rid: int, data: bytes) -> str:
        rev = self.revisions[rid]
        rev.content, rev.state = data, "VALIDATING"
        if hashlib.sha256(data).hexdigest() != rev.expected_sha:
            rev.state = "FAILED"
            return "FAILED (checksum 불일치) — latest는 그대로"
        # commit: READY 전환 + alias 전환 + 이전 revision SUPERSEDED (실제로는 한 트랜잭션)
        prev = self.alias.get(rev.entity)
        if prev:
            self.revisions[prev].state = "SUPERSEDED"
        rev.state = "READY"
        self.alias[rev.entity] = rid
        return f"READY, latest → rev{rid}"

    def _visible(self, who: dict, rev: Revision) -> bool:
        if who["name"] == rev.owner or who["proxy"]:
            return True
        scopes = rev.acl or DEFAULT_ACL_BY_KIND.get(rev.kind, set())  # 미선언 kind → 빈 집합 → 거부
        return bool(scopes & who["scopes"])

    def resolve(self, token: str, entity: str) -> str:
        who = self._who(token)
        rid = self.alias.get(entity)
        if rid is None or not self._visible(who, self.revisions[rid]):
            raise HTTPError(404, "NOT_FOUND")  # 없음과 권한 없음을 구분하지 않는다
        rev = self.revisions[rid]
        return f"artifact://{entity}@rev{rid} ({rev.state}, {len(rev.content)} bytes)"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def attempt(label: str, fn) -> None:
    try:
        print(f"{label:<44} → {fn()}")
    except HTTPError as e:
        print(f"{label:<44} → ✖ {e}")


def main() -> None:
    r = Resolver()
    v1, v2_bad, v2 = b"PAD docx v1", b"PAD docx v2 (corrupted)", b"PAD docx v2"
    E = "pad/PN-2026-0412/docx"

    a = r.create_upload("tok-render-svc", E, "pad_document", "render-svc", sha(v1))
    attempt("업로드 중 조회 (BUILDING)", lambda: r.resolve("tok-chatbot", E))
    attempt("v1 commit", lambda: r.put_and_commit("tok-render-svc", a, v1))
    attempt("chatbot 조회 (같은 pad-team 범위)", lambda: r.resolve("tok-chatbot", E))

    b = r.create_upload("tok-render-svc", E, "pad_document", "render-svc", sha(v2), parents=[a])
    attempt("v2 업로드 — 손상된 내용", lambda: r.put_and_commit("tok-render-svc", b, v2_bad))
    attempt("조회 (여전히 v1이어야 함)", lambda: r.resolve("tok-chatbot", E))
    c = r.create_upload("tok-render-svc", E, "pad_document", "render-svc", sha(v2), parents=[a])
    attempt("v2 재업로드", lambda: r.put_and_commit("tok-render-svc", c, v2))
    attempt("조회", lambda: r.resolve("tok-chatbot", E))

    attempt("search-svc 조회 (범위 밖)", lambda: r.resolve("tok-search-svc", E))
    attempt("search-svc 조회 (존재하지 않는 entity)", lambda: r.resolve("tok-search-svc", "pad/none"))
    attempt("chatbot이 render-svc 이름으로 등록", lambda: r.create_upload(
        "tok-chatbot", "pad/x", "pad_document", "render-svc", sha(b"x")))
    attempt("control(proxy)이 render-svc 대신 등록", lambda: "허용 (rev%d BUILDING)" % r.create_upload(
        "tok-control", "pad/y", "pad_document", "render-svc", sha(b"y")))

    d = r.create_upload("tok-search-svc", "ocr/tmp", "ocr_scratch", "search-svc", sha(b"o"))
    r.put_and_commit("tok-search-svc", d, b"o")
    attempt("미선언 kind(ocr_scratch)를 chatbot이 조회", lambda: r.resolve("tok-chatbot", "ocr/tmp"))


if __name__ == "__main__":
    main()
