"""Control Plane 단계적 전환 재현: shadow → control_with_direct_fallback → control → intent.

숨은 버그: blocks_search 호출부는 옛 메커니즘(`use_control` 파라미터)으로 Control 라우팅을
'선택'하게 되어 있었고, 라우트 테이블 주석은 그 때문에 카탈로그 등록이 필요 없다고 가정했다.
하지만 use_control을 넘기는 호출자는 없었다 → 계속 조용히 direct로 갔다.
"""

CATALOG = {  # 업무 intent → (service, action)
    "rules.code.lookup": ("rules-svc", "fcode"),
    "web.search": ("search-svc", "search"),
    "document.render": ("render-svc", "render"),
}
ROUTES = {  # (service, path) → intent
    ("rules-svc", "/codes/fcode"): "rules.code.lookup",
    ("search-svc", "/search"): "web.search",
    ("render-svc", "/v1/render"): "document.render",
    # ("analyze-svc", "/v1/blocks/search") — "use_control 파라미터가 처리하므로 등록 불필요" (낡은 가정)
}


class RouteNotInCatalog(Exception):
    pass


def direct(service: str, path: str) -> dict:
    return {"via": "direct", "service": service, "path": path, "items": 3}


def via_control(intent: str) -> dict:
    service, action = CATALOG[intent]
    return {"via": "control", "service": service, "action": action, "items": 3}


class Adapter:
    def __init__(self, mode: str):
        assert mode in {"shadow", "control_with_direct_fallback", "control"}
        self.mode, self.events = mode, []

    def call(self, service: str, path: str, use_control: bool = False) -> dict:
        intent = ROUTES.get((service, path))
        if intent is None and use_control:
            intent = f"{service}{path}"  # 옛 메커니즘 — 실제로 이 분기를 타는 호출자는 없다
        if self.mode == "shadow":
            real = direct(service, path)
            if intent in CATALOG:
                shadow = via_control(intent)
                if shadow["items"] != real["items"]:
                    self.events.append(f"shadow mismatch {path}")
            else:
                self.events.append(f"(shadow 대상 아님 — 조용히 넘어감) {path}")
            return real
        if intent not in CATALOG:
            if self.mode == "control_with_direct_fallback":
                self.events.append(f"(fallback으로 direct — 조용히 넘어감) {path}")
                return direct(service, path)
            raise RouteNotInCatalog(f"카탈로그에 없는 라우트: {service} {path}")
        return via_control(intent)


TRAFFIC = [
    ("rules-svc", "/codes/fcode"),
    ("search-svc", "/search"),
    ("analyze-svc", "/v1/blocks/search"),  # research 경로 — use_control을 넘기지 않는다
    ("render-svc", "/v1/render"),
]


def run(mode: str) -> None:
    a = Adapter(mode)
    errors = 0
    for service, path in TRAFFIC:
        try:
            a.call(service, path)
        except RouteNotInCatalog as e:
            errors += 1
            a.events.append(f"❌ {e}")
    print(f"[{mode}] 요청 {len(TRAFFIC)}건, 오류 {errors}건")
    for ev in a.events:
        print("    ", ev)


def test_blocks_search_routes_through_control() -> None:
    result = Adapter("control").call("analyze-svc", "/v1/blocks/search")
    assert result["via"] == "control", result


def main() -> None:
    run("shadow")
    run("control_with_direct_fallback")
    run("control")

    print("\n수정: 실제 트래픽이 지나는 한 곳(범용 라우트 테이블)에 정식 등록 + 회귀 테스트")
    CATALOG["knowledge.blocks.search"] = ("analyze-svc", "blocks_search")
    ROUTES[("analyze-svc", "/v1/blocks/search")] = "knowledge.blocks.search"
    test_blocks_search_routes_through_control()
    print("   회귀 테스트 통과 ✅")
    run("control")

    print("\n④ 선언형 intent — 호출자는 서비스·경로를 모른다")
    print("   ", via_control("knowledge.blocks.search"))


if __name__ == "__main__":
    main()
