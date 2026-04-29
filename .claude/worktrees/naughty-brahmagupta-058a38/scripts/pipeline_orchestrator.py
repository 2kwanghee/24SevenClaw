#!/usr/bin/env python3
"""파이프라인 단일 진입점 오케스트레이터.

전체 라이프사이클을 단일 프로세스에서 관리:
  1. Linear Queued 이슈 감지 (linear_watcher)
  2. 기획 → 구현 → 리뷰 (auto_dev_pipeline.sh)
  3. 결과 보고 (linear_reporter) — 이미 pipeline 내 포함
  4. Confirm 이슈 머지 (linear_confirmer)
  5. Telegram 알림

Usage:
  python3 scripts/pipeline_orchestrator.py              # 전체 실행
  python3 scripts/pipeline_orchestrator.py --once       # 1개만 처리
  python3 scripts/pipeline_orchestrator.py --watch      # 지속 감시 모드 (30초 간격)
  python3 scripts/pipeline_orchestrator.py --dry-run    # 로그만 출력
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from pipeline_config import is_enabled

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [orchestrator] {msg}", flush=True)


def run_script(cmd: list[str], label: str, dry_run: bool = False) -> int:
    """스크립트 실행 후 종료 코드 반환."""
    if dry_run:
        log(f"[DRY-RUN] {label}: {' '.join(cmd)}")
        return 0

    log(f"START: {label}")
    result = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        text=True,
    )
    log(f"END: {label} (exit={result.returncode})")
    return result.returncode


def run_pipeline(once: bool = False, max_turns: str | None = None, dry_run: bool = False) -> int:
    """auto_dev_pipeline.sh 실행."""
    cmd = ["bash", "scripts/auto_dev_pipeline.sh"]
    if once:
        cmd.append("--once")
    if max_turns:
        cmd.extend(["--max-turns", max_turns])
    return run_script(cmd, "파이프라인 (Queued → 구현 → 리뷰 → PR)", dry_run)


def run_confirmer(dry_run: bool = False) -> int:
    """linear_confirmer.py 실행."""
    if not is_enabled("FLOWOPS_LINEAR_CONFIRM"):
        log("SKIP: Linear Confirm 비활성화됨")
        return 0
    return run_script(
        ["python3", "scripts/linear_confirmer.py"],
        "Confirm 이슈 머지",
        dry_run,
    )


def run_telegram_report(message: str, dry_run: bool = False) -> int:
    """Telegram 알림."""
    if not is_enabled("FLOWOPS_TELEGRAM"):
        return 0
    return run_script(
        ["python3", "scripts/telegram_notify.py", "--message", message],
        "Telegram 알림",
        dry_run,
    )


def orchestrate(once: bool = False, max_turns: str | None = None, dry_run: bool = False):
    """전체 라이프사이클 1회 실행."""
    log("=" * 50)
    log("  파이프라인 오케스트레이터 시작")
    log("=" * 50)

    # Step 1: 파이프라인 (Queued 감지 → 구현 → 리뷰 → reporter → PR)
    pipeline_exit = run_pipeline(once=once, max_turns=max_turns, dry_run=dry_run)

    # Step 2: Confirm 이슈 머지
    confirm_exit = run_confirmer(dry_run=dry_run)

    # Step 3: 최종 보고
    if pipeline_exit == 0 and confirm_exit == 0:
        run_telegram_report("오케스트레이터 완료: 정상 종료", dry_run)
    else:
        errors = []
        if pipeline_exit != 0:
            errors.append(f"파이프라인(exit={pipeline_exit})")
        if confirm_exit != 0:
            errors.append(f"Confirmer(exit={confirm_exit})")
        run_telegram_report(f"오케스트레이터 완료 (에러: {', '.join(errors)})", dry_run)

    log("=" * 50)
    log("  오케스트레이터 종료")
    log("=" * 50)

    return max(pipeline_exit, confirm_exit)


def watch_loop(interval: int = 30, max_turns: str | None = None, dry_run: bool = False):
    """지속 감시 모드: interval초마다 오케스트레이터 실행."""
    log(f"감시 모드 시작 (간격: {interval}초)")
    log("Ctrl+C로 종료")

    while True:
        try:
            orchestrate(once=False, max_turns=max_turns, dry_run=dry_run)
            log(f"다음 실행까지 {interval}초 대기...")
            time.sleep(interval)
        except KeyboardInterrupt:
            log("감시 모드 종료")
            break


def main():
    parser = argparse.ArgumentParser(description="파이프라인 단일 진입점 오케스트레이터")
    parser.add_argument("--once", action="store_true", help="이슈 1개만 처리 후 종료")
    parser.add_argument("--watch", action="store_true", help="지속 감시 모드")
    parser.add_argument("--interval", type=int, default=30, help="감시 간격 (초, 기본: 30)")
    parser.add_argument("--max-turns", help="Claude 최대 턴 수")
    parser.add_argument("--dry-run", action="store_true", help="실행 안 함 (로그만)")
    args = parser.parse_args()

    if args.watch:
        watch_loop(interval=args.interval, max_turns=args.max_turns, dry_run=args.dry_run)
    else:
        exit_code = orchestrate(once=args.once, max_turns=args.max_turns, dry_run=args.dry_run)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
