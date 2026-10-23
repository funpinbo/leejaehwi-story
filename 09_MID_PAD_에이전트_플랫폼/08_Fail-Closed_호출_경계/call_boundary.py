"""Fail-closed 호출 경계 — 표준 라이브러리만으로 재현 (네트워크 요청 없음).

1) 경로 정규화(percent-decode → dot-segment 제거) 후 allowlist 검사
2) 계약 digest: Control이 보낸 값과 Worker가 로컬 승인 spec에서 재계산한 값의 exact match
3) SSRF 가드: 사설/루프백/링크로컬 IP, *.cluster.local 차단
4) site 필터: label 경계 일치만 허용 (suffix 공격 차단)
"""

import hashlib
import ipaddress
import json
import posixpath
from urllib.parse import unquote, urlsplit

ALLOWED = {  # service → 허용 endpoint (method, canonical path)
    "render-svc": {("POST", "/v1/validate"), ("POST", "/v1/render")},
}
APPROVED_SPECS = {
    ("render-svc", "validate"): {"version": "1.2.0", "endpoint": "/v1/validate", "method": "POST",
                                   "timeout": 30, "request_schema": {"type": "object", "required": ["slots"]}},
}


# ---------- 1. 경로 정규화 + allowlist ----------
def canonical_path(raw: str) -> str:
    path = raw
    for _ in range(3):  # 이중 인코딩(%252e)까지 풀릴 때까지
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    norm = posixpath.normpath("/" + path.lstrip("/"))
    return norm if norm != "." else "/"


def check_endpoint(service: str, method: str, raw_path: str) -> str:
    allowed = ALLOWED.get(service)
    if not allowed:
        return "[X] ENDPOINT_NOT_ALLOWED (서비스 설정 없음 → fail-closed)"
    path = canonical_path(raw_path)
    if (method, path) not in allowed:
        return f"[X] ENDPOINT_NOT_ALLOWED (정규화 결과 {path})"
    return f"[O] 허용 ({path})"


# ---------- 2. 계약 digest ----------
def digest(spec: dict) -> str:
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def check_contract(service: str, action: str, sent_digest: str) -> str:
    spec = APPROVED_SPECS.get((service, action))
    if spec is None:
        return "[X] ACTION_NOT_APPROVED (fail-closed)"
    local = digest(spec)
    return "[O] 계약 일치" if sent_digest == local else f"[X] ACTION_CONTRACT_MISMATCH (보냄 {sent_digest} ≠ 로컬 {local})"


# ---------- 3. SSRF 가드 ----------
def check_fetch_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        return f"[X] 스킴 {parts.scheme} 거부"
    host = (parts.hostname or "").rstrip(".").lower()
    if host == "localhost" or host.endswith(".cluster.local") or host.endswith(".svc"):
        return f"[X] 내부 호스트 {host} 거부"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return f"[X] 사설/내부 IP {ip} 거부"
    except ValueError:
        pass  # 도메인: 실제 구현은 DNS 해석 결과 IP도 다시 검사한다
    return "[O] 허용"


# ---------- 4. site 필터 ----------
def site_match(url_host: str, site: str) -> bool:
    host = url_host.encode("idna").decode().lower().rstrip(".")
    site = site.encode("idna").decode().lower().rstrip(".")
    return host == site or host.endswith("." + site)  # label 경계


def main() -> None:
    print("[1] 경로 정규화 + allowlist")
    for m, p in [("POST", "/v1/validate"), ("POST", "/v1/../admin/delete"),
                 ("POST", "/v1/%2e%2e/admin"), ("POST", "/v1/%252e%252e/admin"),
                 ("POST", "/v1/./render")]:
        print(f"   {p:<32} {check_endpoint('render-svc', m, p)}")
    print(f"   {'(설정 없는 서비스)':<32} {check_endpoint('unknown-svc', 'GET', '/')}")

    print("\n[2] 계약 digest")
    good = digest(APPROVED_SPECS[("render-svc", "validate")])
    stale = digest({**APPROVED_SPECS[("render-svc", "validate")], "timeout": 60})
    print(f"   최신 카탈로그       {check_contract('render-svc', 'validate', good)}")
    print(f"   timeout만 바뀐 계약 {check_contract('render-svc', 'validate', stale)}")
    print(f"   미승인 action       {check_contract('render-svc', 'delete_all', good)}")

    print("\n[3] SSRF 가드")
    for u in ["https://escies.org/spec.pdf", "http://10.0.0.5/admin", "http://127.0.0.1:8080/",
              "http://chatbot.chatbot.svc.cluster.local/api", "http://169.254.169.254/latest", "file:///etc/passwd"]:
        print(f"   {u:<46} {check_fetch_url(u)}")

    print("\n[4] site 필터 (site=ecss.nl)")
    for h in ["ecss.nl", "docs.ecss.nl", "fakeecss.nl", "ecss.nl.evil.com"]:
        print(f"   {h:<20} {'[O] 통과' if site_match(h, 'ecss.nl') else '[X] 차단'}")


if __name__ == "__main__":
    main()
