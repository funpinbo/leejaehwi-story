"""단일 WebSocket 공유 연결 + 종목별 콜백 라우팅 + 자동 재연결 · 재구독.

KIS 서버 대신 FakeKisServer를 사용한다.
  - 동시에 연결 1개만 허용 (approval_key 제약 재현)
  - 일정 메시지마다 연결을 강제로 끊음
"""

import asyncio
import random
from collections import defaultdict
from typing import Awaitable, Callable

Callback = Callable[[str, float], Awaitable[None]]


class ConnectionClosed(Exception):
    pass


class FakeKisServer:
    def __init__(self, drop_every: int = 7):
        self.active = 0
        self.drop_every = drop_every

    async def connect(self) -> "FakeConnection":
        if self.active >= 1:
            raise ConnectionError("approval_key당 연결은 1개만 허용됩니다")
        self.active += 1
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, server: FakeKisServer):
        self.server, self.subscribed, self.sent = server, set(), 0
        self.closed = False

    async def subscribe(self, code: str) -> None:
        self.subscribed.add(code)

    async def recv(self) -> tuple[str, float]:
        await asyncio.sleep(0.01)
        self.sent += 1
        if self.sent % self.server.drop_every == 0:
            await self.close()
            raise ConnectionClosed("서버가 연결을 끊었습니다")
        code = random.choice(sorted(self.subscribed))
        return code, round(random.uniform(6000, 7000), -1)

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.server.active -= 1


class SharedWebSocket:
    """연결은 하나, 종목별 처리는 콜백 딕셔너리로 라우팅."""

    def __init__(self, server: FakeKisServer, max_backoff: float = 0.2):
        self.server = server
        self.callbacks: dict[str, list[Callback]] = defaultdict(list)
        self.conn: FakeConnection | None = None
        self.max_backoff = max_backoff
        self.reconnects = 0

    async def subscribe(self, code: str, cb: Callback) -> None:
        self.callbacks[code].append(cb)
        if self.conn:
            await self.conn.subscribe(code)

    async def _connect(self) -> None:
        backoff = 0.01
        while True:
            try:
                self.conn = await self.server.connect()
                for code in self.callbacks:  # 재연결 후 전체 재구독
                    await self.conn.subscribe(code)
                return
            except ConnectionError:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.max_backoff)  # 지수 백오프

    async def run(self, n_messages: int) -> None:
        await self._connect()
        received = 0
        while received < n_messages:
            try:
                code, price = await self.conn.recv()
            except ConnectionClosed as e:
                self.reconnects += 1
                print(f"   ! {e} → 재연결 #{self.reconnects}")
                await self._connect()
                continue
            received += 1
            for cb in self.callbacks.get(code, []):
                await cb(code, price)
        await self.conn.close()


async def per_symbol_connections(server: FakeKisServer, codes: list[str]) -> None:
    """처음 구조: 종목마다 연결 → 두 번째 연결부터 거부된다."""
    for code in codes:
        try:
            conn = await server.connect()
            await conn.subscribe(code)
            print(f"   {code}: 연결 성공")
        except ConnectionError as e:
            print(f"   {code}: [X] {e}")
    server.active = 0


async def main() -> None:
    random.seed(1)
    codes = ["036540", "067310", "000660"]

    print("[Before] 종목별 개별 연결")
    await per_symbol_connections(FakeKisServer(), codes)

    print("\n[After] 단일 공유 연결 + 콜백 라우팅")
    ws = SharedWebSocket(FakeKisServer())
    counts: dict[str, int] = defaultdict(int)

    async def plan_monitor(code: str, price: float) -> None:
        counts[code] += 1

    for code in codes:
        await ws.subscribe(code, plan_monitor)
    await ws.run(n_messages=30)

    print(f"\n수신 30건, 재연결 {ws.reconnects}회 — 끊겨도 데이터 수신이 계속됨")
    for code in codes:
        print(f"   {code}: {counts[code]}건 콜백 처리")


if __name__ == "__main__":
    asyncio.run(main())
