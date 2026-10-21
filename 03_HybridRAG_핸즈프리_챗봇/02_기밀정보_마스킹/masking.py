"""가역 마스킹: LLM으로 보내기 전에 기밀을 토큰으로 치환하고, 응답에서 원래 값으로 복원한다."""

import re
from dataclasses import dataclass, field

# 패턴 순서가 곧 우선순위 (구체적인 것부터)
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("PHONE", re.compile(r"01[0-9]-?\d{3,4}-?\d{4}")),
    ("EQUIP", re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+){2,}\b")),
]
# 정규식으로 못 잡는 고유명사는 사전으로 관리
DICTIONARY = {"CUSTOMER": ["하늘반도체", "바다전자"]}


@dataclass
class Masker:
    forward: dict[str, str] = field(default_factory=dict)  # 원문 → 토큰
    counters: dict[str, int] = field(default_factory=dict)

    def _token(self, kind: str, value: str) -> str:
        if value not in self.forward:  # 같은 값은 항상 같은 토큰 → 문맥 유지
            self.counters[kind] = self.counters.get(kind, 0) + 1
            self.forward[value] = f"[{kind}_{self.counters[kind]}]"
        return self.forward[value]

    def mask(self, text: str) -> str:
        for kind, words in DICTIONARY.items():
            for w in words:
                if w in text:
                    text = text.replace(w, self._token(kind, w))
        for kind, pattern in PATTERNS:
            text = pattern.sub(lambda m, k=kind: self._token(k, m.group()), text)
        return text

    def unmask(self, text: str) -> str:
        for value, token in self.forward.items():
            text = text.replace(token, value)
        return text


SYSTEM_PROMPT = (
    "검색된 컨텍스트에 있는 내용만 사용해 답하라. 없으면 '문서에서 찾을 수 없습니다'라고 답하라.\n"
    "[EQUIP_1] 같은 대괄호 토큰은 마스킹된 값이다. 원래 값을 추측하거나 새 토큰을 만들지 말고 그대로 사용하라."
)


def fake_llm(prompt: str) -> str:
    """LLM 대역. 받은 텍스트에 기밀 원문이 없는지 확인할 수 있도록 토큰만 사용해 답한다."""
    return "[CUSTOMER_1] 납품 장비 [EQUIP_1]은 조명 캘리브레이션 후 GrayValue 180을 기준으로 합니다. 문의: [EMAIL_1]"


def main() -> None:
    question = "하늘반도체에 납품한 EBR-3D-OPT-V2 캘리브레이션 기준이 뭐야?"
    context = "하늘반도체 납품 EBR-3D-OPT-V2: 캘리브레이션 GrayValue 180. 담당 kim.op@ati-example.com / 010-1234-5678"

    masker = Masker()
    prompt = f"{SYSTEM_PROMPT}\n\n[컨텍스트]\n{masker.mask(context)}\n\n[질문]\n{masker.mask(question)}"

    print("=== LLM으로 나가는 프롬프트 ===")
    print(prompt)
    leaked = [v for v in masker.forward if v in prompt]
    print(f"\n기밀 원문 포함 여부: {'⚠ ' + str(leaked) if leaked else '없음 ✅'}")

    answer = fake_llm(prompt)
    print("\n=== LLM 응답 (마스킹 상태) ===\n" + answer)
    print("\n=== 사용자에게 보여주는 답변 (사내에서 복원) ===\n" + masker.unmask(answer))


if __name__ == "__main__":
    main()
