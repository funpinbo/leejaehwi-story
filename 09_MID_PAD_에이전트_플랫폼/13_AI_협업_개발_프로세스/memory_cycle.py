"""AI 협업 개발의 memory cycle 재현 (임시 디렉터리에 파일로).

task / long-term memory / short-term memory / log 를 만들고
  에이전트: short-term만 읽고 1건 수행 → log append → task 한 줄 → short-term '비어 있음'
  hook   : 다음 항목을 '지금 할 일'로 / 소진되면 완료 / 사람 판단 필요하면 '막힘'을 쓰고 멈춤
"""

import re
import tempfile
from pathlib import Path

LONG_TERM = """# chatbot long-term memory — TASK-1
1. [ ] adapter 모드를 control_with_direct_fallback → control 로 전환 — 완료 기준: 카탈로그 밖 라우트 fail-closed
2. [ ] 각 다운스트림 대표 Action이 Control 경유로 성공하는지 재검증 — 완료 기준: 실트래픽 성공
3. [ ] (사람 결정) 남은 비동기 action의 안전망 제거 시점 결정 — 완료 기준: 제거 일정 승인
"""


def agent_run(item: str) -> str:
    """에이전트 대역: 실제로는 코드 수정 + 테스트. 결과와 '어떻게 확인했는지'를 함께 반환."""
    return {"1": "모드 전환, 회귀 테스트 추가 — 확인: 전체 테스트 통과",
            "2": "대표 Action 4종 실트래픽 호출 — 확인: 운영 로그 오류 0건"}[item]


def hook(d: Path) -> str:
    """턴 종료 hook: long-term을 읽고 다음 short-term 상태를 결정한다."""
    items = re.findall(r"^(\d+)\. \[( |x)\] (.+)$", (d / "long_term.md").read_text(), re.M)
    pending = [(n, text) for n, done, text in items if done == " "]
    if not pending:
        (d / "short_term.md").write_text("## 비어 있음\nlong-term 소진 — 이 서비스 몫 완료\n")
        with (d / "task.md").open("a") as f:
            f.write("- chatbot: 완료\n")
        return "done"
    n, text = pending[0]
    if text.startswith("(사람 결정)"):
        (d / "short_term.md").write_text(
            f"## 막힘 — 사람의 결정 필요\n- 항목: #{n} {text}\n- 묻고 싶은 것: 안전망 제거 시점을 언제로 할까요?\n")
        return "blocked"
    (d / "short_term.md").write_text(f"## 지금 할 일\n- long-term 항목: #{n} — {text}\n")
    return "next"


def agent_turn(d: Path) -> None:
    short = (d / "short_term.md").read_text()  # 에이전트는 short-term만 읽는다
    m = re.search(r"#(\d+)", short)
    n = m.group(1)
    result = agent_run(n)
    with (d / "log.md").open("a") as f:
        f.write(f"- #{n}: {result}\n")
    with (d / "task.md").open("a") as f:
        f.write(f"- chatbot #{n} 완료\n")
    lt = (d / "long_term.md").read_text().replace(f"{n}. [ ]", f"{n}. [x]")
    (d / "long_term.md").write_text(lt)
    (d / "short_term.md").write_text("## 비어 있음\n")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "task.md").write_text("## TASK-1: 서비스 간 호출을 Control Plane으로 이전\n- 진행 로그:\n")
        (d / "long_term.md").write_text(LONG_TERM)
        (d / "log.md").write_text("# chatbot log\n")
        state, turn = hook(d), 0
        while state == "next":
            turn += 1
            print(f"[turn {turn}] short-term → {(d / 'short_term.md').read_text().splitlines()[1]}")
            agent_turn(d)
            state = hook(d)
        print(f"\nhook 결과: {state}")
        print((d / "short_term.md").read_text())
        print((d / "log.md").read_text())


if __name__ == "__main__":
    main()
