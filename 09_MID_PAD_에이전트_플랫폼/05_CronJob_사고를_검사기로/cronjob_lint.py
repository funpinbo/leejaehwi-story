"""CronJob 표준 린터 — 실제 사고에서 나온 규칙을 코드로 검사한다.

검사 항목
  R1 timeZone: Asia/Seoul 필수 (타임존 사고)
  R2 concurrencyPolicy: Forbid
  R3 backoffLimit: 0
  R4 activeDeadlineSeconds < 다음 실행까지의 간격
  R5 파드 라벨 app.kubernetes.io/name 이 NetworkPolicy 허용 라벨과 일치 (라벨 누락 사고)
  R6 GPU 전환 CronJob 시각이 워커 코드의 시간대 상수와 일치 (중복 정의 불일치)
매니페스트는 예시이며, 실제 YAML 대신 dict로 표현했다.
"""

GPU_WINDOW = {"night_start": "20:00", "day_start": "07:00"}  # 워커 코드 쪽 정의 (예시 시각)
NETPOL_ALLOWED = {"pipeline-svc", "analyze-svc"}  # NetworkPolicy podSelector가 허용하는 라벨

CRONJOBS = [
    {"name": "embed-hourly", "schedule": "15 * * * *", "timeZone": "Asia/Seoul",
     "concurrencyPolicy": "Forbid", "backoffLimit": 0, "activeDeadlineSeconds": 3300,
     "labels": {"app.kubernetes.io/name": "pipeline-svc", "app.kubernetes.io/component": "embed"}},
    {"name": "gpu-window-stop (사고 ①)", "schedule": "0 22 * * *",  # UTC 환산을 의도했지만 KST로 해석됨
     "concurrencyPolicy": "Forbid", "backoffLimit": 0, "activeDeadlineSeconds": 1800,
     "labels": {"app.kubernetes.io/name": "analyze-svc"}, "gpu_switch": "day_start"},
    {"name": "gpu-window-start (사고 ②)", "schedule": "0 20 * * *", "timeZone": "Asia/Seoul",
     "concurrencyPolicy": "Forbid", "backoffLimit": 0, "activeDeadlineSeconds": 49800,
     "labels": {}, "gpu_switch": "night_start"},  # 라벨 누락 → default-deny에 막힘
    {"name": "embed-bad (규칙 위반 예시)", "schedule": "15 * * * *", "timeZone": "Asia/Seoul",
     "concurrencyPolicy": "Allow", "backoffLimit": 3, "activeDeadlineSeconds": 5400,
     "labels": {"app.kubernetes.io/name": "pipeline-svc"}},
]


def period_seconds(schedule: str) -> int:
    minute, hour, *_ = schedule.split()
    if hour == "*":
        return 3600
    return 86400  # 이 예제는 매시 / 매일 두 형태만 다룬다


def wall_clock(schedule: str) -> str:
    minute, hour, *_ = schedule.split()
    return f"{int(hour):02d}:{int(minute):02d}"


def lint(job: dict) -> list[str]:
    errs = []
    if job.get("timeZone") != "Asia/Seoul":
        errs.append("R1 timeZone 누락 — 서버 로컬 시각으로 해석되어 의도와 다른 시각에 실행될 수 있음")
    if job.get("concurrencyPolicy") != "Forbid":
        errs.append(f"R2 concurrencyPolicy={job.get('concurrencyPolicy')} — 이전 실행과 겹칠 수 있음")
    if job.get("backoffLimit") != 0:
        errs.append(f"R3 backoffLimit={job.get('backoffLimit')} — 재시도는 다음 주기가 담당해야 함")
    period = period_seconds(job["schedule"])
    if job.get("activeDeadlineSeconds", period) >= period:
        errs.append(f"R4 activeDeadlineSeconds={job.get('activeDeadlineSeconds')} ≥ 주기 {period}s — 다음 실행 침범")
    name = job.get("labels", {}).get("app.kubernetes.io/name")
    if name not in NETPOL_ALLOWED:
        errs.append(f"R5 파드 라벨 '{name}' — NetworkPolicy에 허용되지 않아 모든 통신 차단")
    if "gpu_switch" in job:
        expected = GPU_WINDOW[job["gpu_switch"]]
        if wall_clock(job["schedule"]) != expected:
            errs.append(f"R6 GPU 전환 시각 {wall_clock(job['schedule'])} ≠ 워커 코드 {expected} — 시간대 불일치")
    return errs


def main() -> None:
    total = 0
    for job in CRONJOBS:
        errs = lint(job)
        total += len(errs)
        print(f"{'[O]' if not errs else '[X]'} {job['name']}  [{job['schedule']}]")
        for e in errs:
            print(f"     {e}")
    print(f"\n위반 {total}건")


if __name__ == "__main__":
    main()
