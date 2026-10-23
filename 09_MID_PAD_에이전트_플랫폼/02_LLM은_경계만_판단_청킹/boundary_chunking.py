"""LLM은 '어디서 자를지'만 고르고, 텍스트는 절대 다시 쓰지 않는 청킹.

- 윈도우 단위로 문단 목록을 보여주고, LLM은 경계가 될 문단 번호(JSON 배열)만 응답
- 응답 검증: JSON 배열인가, 범위 안인가, 오름차순인가
- 연속 MAX_FAILS회 실패하면 문자 수 규칙으로 폴백
- 불변 조건: "".join(chunks) == 원문
"""

import itertools
import json

WINDOW_CHARS = 3500
MAX_FAILS = 3
FALLBACK_CHARS = 1200


def make_document() -> str:
    paras = []
    for sec in range(1, 7):
        paras.append(f"{sec}. 조항 제목 {sec}\n")
        for i in range(1, 6):
            paras.append(f"{sec}.{i} 이 조항은 부품 조달 및 시험 요구사항을 설명한다. " * 8 + "\n")
    return "".join(paras)


def split_paragraphs(text: str) -> list[str]:
    return text.splitlines(keepends=True)


# LLM 대역: 정상 응답 사이사이에 잘못된 응답을 섞는다
_responses = itertools.cycle(["[0, 6]", "not json", "[0, 999]", "[3, 1]", "[0, 5]"])


def fake_llm(numbered: list[str]) -> str:
    return next(_responses)


def validate(resp: str, n: int) -> list[int] | None:
    try:
        idx = json.loads(resp)
    except json.JSONDecodeError:
        return None
    if not (isinstance(idx, list) and all(isinstance(i, int) for i in idx)):
        return None
    if any(i < 0 or i >= n for i in idx) or idx != sorted(set(idx)):
        return None
    return idx


def chunk(text: str) -> tuple[list[str], dict]:
    paras = split_paragraphs(text)
    chunks, stats = [], {"llm_ok": 0, "llm_bad": 0, "fallback": 0}
    fails, i = 0, 0
    while i < len(paras):
        window, size = [], 0
        while i + len(window) < len(paras) and size < WINDOW_CHARS:
            window.append(paras[i + len(window)])
            size += len(window[-1])

        bounds = validate(fake_llm([f"[{k}] {p[:30]}" for k, p in enumerate(window)]), len(window))
        if bounds is None:
            stats["llm_bad"] += 1
            fails += 1
            if fails < MAX_FAILS:
                continue  # 같은 윈도우 재시도
            # 연속 MAX_FAILS회 실패 → 이 윈도우는 문자 수 규칙으로 폴백
            stats["fallback"] += 1
            bounds, acc = [0], 0
            for k, p in enumerate(window):
                if acc >= FALLBACK_CHARS:
                    bounds.append(k)
                    acc = 0
                acc += len(p)
        else:
            stats["llm_ok"] += 1
        fails = 0
        if 0 not in bounds:
            bounds = [0] + bounds
        for a, b in zip(bounds, bounds[1:] + [len(window)]):
            chunks.append("".join(window[a:b]))  # 원문 그대로 이어 붙이기만 한다
        i += len(window)
    return chunks, stats


def main() -> None:
    original = make_document()
    chunks, stats = chunk(original)
    print(f"원문 {len(original):,}자 → 청크 {len(chunks)}개")
    print(f"LLM 정상 응답 {stats['llm_ok']}회 / 잘못된 응답 {stats['llm_bad']}회 / 규칙 폴백 {stats['fallback']}회")
    print(f"청크 길이: {[len(c) for c in chunks]}")
    assert "".join(chunks) == original
    print('불변 조건 "".join(chunks) == 원문 ✅  (LLM이 텍스트를 바꾼 곳 없음)')


if __name__ == "__main__":
    main()
