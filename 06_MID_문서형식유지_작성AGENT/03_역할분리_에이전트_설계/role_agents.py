"""MID-AGENT 역할 분리 설계 예제.

Report Agent        : 목적 분석 · 데이터 검색 · 규격 참조 · 내용(JSON) 생성
Layout Agent        : 템플릿 구조 분석 · placeholder와 내용 키의 정합성 확인 · (렌더링은 02 템플릿 엔진)
Verification Agent  : 규격 번호 · Revision 확인, 각 값의 근거 데이터 추적

LLM 호출과 사내 데이터는 대역으로 대체했다. 규격 번호·Revision은 예시 값이다.
"""

import re
from dataclasses import dataclass, field

# 사내 데이터 대역
PART_DB = {"PN-2026-0412": {"manufacturer": "ACME Space Components", "family": "Capacitor"}}
SPEC_REGISTRY = {  # 규격별 최신 Revision (예시)
    "ESCC-3009": "Issue 5",
    "ECSS-Q-ST-60": "Rev 3",
}
TEMPLATE_KEYS = {"part_number", "manufacturer", "spec_ref", "spec_revision", "test_summary"}


@dataclass
class Field_:
    value: str
    source: str  # 근거: 어디서 가져온 값인가


@dataclass
class Report:
    fields: dict[str, Field_] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)


def report_agent(part_number: str) -> Report:
    part = PART_DB[part_number]
    r = Report()
    r.fields["part_number"] = Field_(part_number, "입력값")
    r.fields["manufacturer"] = Field_(part["manufacturer"], f"PART_DB[{part_number}]")
    # LLM이 규격을 참조해 작성한 부분 — Revision을 오래된 값으로 적은 상황을 재현
    r.fields["spec_ref"] = Field_("ESCC-3009", "LLM: 부품군 Capacitor → 적용 규격 추론")
    r.fields["spec_revision"] = Field_("Issue 4", "LLM: 학습 지식")
    r.fields["test_summary"] = Field_("열진공 · 진동 시험 통과", "시험 보고서 TR-118")
    return r


def layout_agent(report: Report) -> Report:
    missing = TEMPLATE_KEYS - report.fields.keys()
    extra = report.fields.keys() - TEMPLATE_KEYS
    if missing:
        report.issues.append(f"[Layout] 템플릿에 필요한 값 누락: {sorted(missing)}")
    if extra:
        report.issues.append(f"[Layout] 템플릿에 자리가 없는 값: {sorted(extra)}")
    return report


def verification_agent(report: Report) -> Report:
    spec = report.fields["spec_ref"].value
    rev = report.fields["spec_revision"].value
    latest = SPEC_REGISTRY.get(spec)
    if latest is None:
        report.issues.append(f"[Verify] 규격 '{spec}'가 레지스트리에 없음 → 사람 검토 필요")
    elif rev != latest:
        report.issues.append(f"[Verify] {spec} Revision 불일치: 작성 {rev} / 최신 {latest} → 자동 수정")
        report.fields["spec_revision"] = Field_(latest, "SPEC_REGISTRY (검증 에이전트가 수정)")
    for k, f in report.fields.items():
        if f.source.startswith("LLM") and k != "spec_ref":
            report.issues.append(f"[Verify] '{k}'는 LLM 지식에만 근거함 → 근거 데이터 확인 필요")
    return report


def main() -> None:
    report = verification_agent(layout_agent(report_agent("PN-2026-0412")))
    print("=== 검증 결과 ===")
    for issue in report.issues or ["문제 없음"]:
        print(" •", issue)
    print("\n=== 최종 값과 근거 ===")
    for k, f in report.fields.items():
        print(f" {k:<14} {f.value:<24} ← {f.source}")


if __name__ == "__main__":
    main()
