"""토큰 만료가 401이 아니라 502로 오는 API에 대한 재시도 정책 비교.

FakeKisApi: 토큰이 만료되면 502를 반환하고, 가끔 일시적인 503도 반환한다.
"""

import itertools
import random
from dataclasses import dataclass


@dataclass
class Response:
    status: int
    body: dict


class FakeKisApi:
    TOKEN_TTL = 3  # 토큰 하나로 처리 가능한 요청 수 (만료를 빠르게 재현)

    def __init__(self):
        self._serial = itertools.count(1)
        self.valid: dict[str, int] = {}

    def issue_token(self) -> str:
        token = f"tok-{next(self._serial)}"
        self.valid[token] = self.TOKEN_TTL
        return token

    def order(self, token: str, code: str, qty: int) -> Response:
        if self.valid.get(token, 0) <= 0:
            return Response(502, {"msg": "Bad Gateway"})  # 만료인데 401이 아니라 502
        self.valid[token] -= 1
        if random.random() < 0.15:
            return Response(503, {"msg": "Service Unavailable"})  # 진짜 일시 장애
        return Response(200, {"order_no": f"{code}-{qty}"})


class Client:
    def __init__(self, api: FakeKisApi, refresh_on_502: bool, max_retry: int = 3):
        self.api, self.refresh_on_502, self.max_retry = api, refresh_on_502, max_retry
        self.token = api.issue_token()
        self.refreshes = 0

    def _refresh(self) -> None:
        self.token = self.api.issue_token()
        self.refreshes += 1

    def order(self, code: str, qty: int) -> Response:
        res = Response(0, {})
        for attempt in range(self.max_retry + 1):
            res = self.api.order(self.token, code, qty)
            if res.status == 200:
                return res
            if res.status == 401 or (res.status == 502 and self.refresh_on_502):
                self._refresh()  # 상태를 바꾸는 재시도
            # 그 외 5xx: 같은 요청 재시도 (실제 코드는 지수 백오프 sleep)
        return res


def run(refresh_on_502: bool) -> None:
    random.seed(0)
    client = Client(FakeKisApi(), refresh_on_502)
    results = [client.order(f"{i:06d}", 10).status for i in range(12)]
    ok = results.count(200)
    label = "개선: 502 → 토큰 강제 갱신" if refresh_on_502 else "기존: 5xx는 같은 요청 반복"
    print(f"[{label}]")
    print(f"   응답 코드: {results}")
    print(f"   주문 성공 {ok}/12, 토큰 갱신 {client.refreshes}회\n")


if __name__ == "__main__":
    run(refresh_on_502=False)
    run(refresh_on_502=True)
