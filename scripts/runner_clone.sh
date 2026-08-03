#!/usr/bin/env bash
# runner_clone.sh — 워크스페이스 전용 러너용 ClickEye 로컬 clone 프로비저닝 (P5/CE-346).
#
# 러너 N 개가 PRIMARY 체크아웃 하나를 공유하면 키 없는 스크래치(.ralph/fix_plan.md,
# .ralph/.task_mapping.json 등)가 레이스하고, 이터레이션 내내 공유 HEAD 를 점유해 서로를
# 깨뜨린다. 해법은 워크스페이스별 **로컬 clone** — 독립 refs + 독립 .ralph 로 자연 분리된다.
# (git worktree 는 같은 브랜치를 두 곳에 체크아웃할 수 없어 main 상시 충돌 → 기각.)
#
# 공유가 필요한 것만 PRIMARY 로 심볼릭한다:
#   .env(파이프라인 설정·API 키) · .ralph/seats.json · .ralph/seats/ · .ralph/workspaces.json
#   · workspaces/(키별 서브디렉터리라 러너 간 무충돌) · logs/(관측 일원화)
# 나머지 .ralph/ 는 clone-로컬로 남긴다 — 락·스크래치 격리가 이 스크립트의 본질이다.
#
# clone 의 origin 은 PRIMARY 가 아니라 **PRIMARY 의 origin(GitHub)** 으로 재지정한다.
# 그러지 않으면 러너의 push/브랜치 삭제가 PRIMARY 체크아웃을 겨냥한다(§①-b).
#
# 사용법:
#   bash scripts/runner_clone.sh <workspace_key>
#
# env:
#   RUNNER_CLONE_ROOT — clone 루트 (기본 $HOME/.clickeye-runners)
#
# 멱등: 두 번 실행해도 결과가 같다(이미 올바른 링크·clone 은 건드리지 않는다).
# 종료코드: 0 성공 / 2 인자 오류 / 1 프로비저닝 실패
set -euo pipefail

PRIMARY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() { echo "[runner-clone] ERROR: $*" >&2; exit 1; }
warn() { echo "[runner-clone] WARN: $*" >&2; }

KEY="${1:-}"
[ -n "$KEY" ] || { echo "사용법: $0 <workspace_key>" >&2; exit 2; }
# 키는 경로로 합성되므로 문자를 제한한다(seat_map.py 의 seat_id 규약과 동일).
[[ "$KEY" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "[runner-clone] ERROR: 허용되지 않는 workspace_key: $KEY" >&2; exit 2; }

CLONE_ROOT="${RUNNER_CLONE_ROOT:-$HOME/.clickeye-runners}"
CLONE_DIR="$CLONE_ROOT/$KEY"

# ── ① clone (멱등) ──────────────────────────────────────────────────────────
CLONE_ACTION="재사용"
if [ -d "$CLONE_DIR/.git" ]; then
  CLONE_ACTION="재사용"
elif [ -e "$CLONE_DIR" ]; then
  die "clone 경로에 git 저장소가 아닌 것이 있음: $CLONE_DIR"
else
  mkdir -p "$CLONE_ROOT"
  git clone "$PRIMARY_DIR" "$CLONE_DIR" >/dev/null 2>&1 || die "git clone 실패: $PRIMARY_DIR → $CLONE_DIR"
  CLONE_ACTION="신규 clone"
fi

# ── ①-b origin 재지정 (멱등) ────────────────────────────────────────────────
# clone 직후 origin 은 PRIMARY 체크아웃을 가리킨다. 그대로 두면 러너의 `git push origin main`
# 과 `git push origin --delete ralph/<KEY>` 가 **PRIMARY 를 겨냥한다**(브랜치 삭제까지 성사됨).
# PRIMARY 의 origin(GitHub)을 상속시켜 push/PR/pull 대상을 현행 단일 러너와 일치시키고,
# "PRIMARY git 무접촉" 불변식을 실질적으로 성립시킨다. main 최신성도 canonical 로 해결된다.
PRIMARY_ORIGIN="$(git -C "$PRIMARY_DIR" remote get-url origin 2>/dev/null || true)"
CLONE_ORIGIN="$(git -C "$CLONE_DIR" remote get-url origin 2>/dev/null || true)"
if [ -n "$PRIMARY_ORIGIN" ]; then
  if [ "$CLONE_ORIGIN" != "$PRIMARY_ORIGIN" ]; then
    if [ -n "$CLONE_ORIGIN" ]; then
      git -C "$CLONE_DIR" remote set-url origin "$PRIMARY_ORIGIN" || die "origin 재지정 실패"
    else
      git -C "$CLONE_DIR" remote add origin "$PRIMARY_ORIGIN" || die "origin 등록 실패"
    fi
    ORIGIN_ACTION="재지정"
  else
    ORIGIN_ACTION="유지"
  fi
elif [ -n "$CLONE_ORIGIN" ]; then
  # PRIMARY 에 origin 이 없다 = 올려보낼 canonical 원격이 없다. PRIMARY 를 겨냥한 채로 두는
  # 것보다 origin 을 없애는 편이 안전하다(그때 push 는 실패 WARN — 현행 파이프라인 관용 경로).
  git -C "$CLONE_DIR" remote remove origin || true
  warn "PRIMARY 에 origin 이 없어 clone 의 origin 을 제거함 — 러너의 push/PR 은 실패한다"
  ORIGIN_ACTION="제거"
else
  ORIGIN_ACTION="없음"
fi

# ── ② 심볼릭 배선 (멱등) ────────────────────────────────────────────────────
# 이미 올바른 링크면 무동작. 링크가 아닌 실체가 자리를 차지하고 있으면 덮어쓰지 않고 경고한다
# (러너가 만든 실제 산출물을 프로비저닝이 지우는 사고를 막는다).
LINKED=0
link_to() {  # link_to <PRIMARY 절대 타깃> <clone 내 링크 경로>
  local target="$1" link="$2" current=""
  if [ -L "$link" ]; then
    current="$(readlink "$link")"
    if [ "$current" = "$target" ]; then
      LINKED=$((LINKED + 1))
      return 0
    fi
    rm -f "$link"
  elif [ -e "$link" ]; then
    warn "링크 대상 자리에 실체가 있어 배선을 건너뜀: $link"
    return 1
  fi
  mkdir -p "$(dirname "$link")"
  ln -s "$target" "$link" || { warn "심볼릭 생성 실패: $link → $target"; return 1; }
  LINKED=$((LINKED + 1))
  return 0
}

mkdir -p "$CLONE_DIR/.ralph"

# .env — PRIMARY 에 없으면 링크하지 않는다(빈 dangling 링크는 설정 부재를 감춘다).
if [ -e "$PRIMARY_DIR/.env" ]; then
  link_to "$PRIMARY_DIR/.env" "$CLONE_DIR/.env" || true
else
  warn "PRIMARY 에 .env 없음 — 링크 생략(러너가 토글·키 없이 기동될 수 있음)"
fi

# 시트/매핑 원장 — 아직 없어도 dangling 링크로 걸어둔다(이후 PRIMARY 에 생기면 즉시 유효).
link_to "$PRIMARY_DIR/.ralph/seats.json" "$CLONE_DIR/.ralph/seats.json" || true
link_to "$PRIMARY_DIR/.ralph/seats" "$CLONE_DIR/.ralph/seats" || true
link_to "$PRIMARY_DIR/.ralph/workspaces.json" "$CLONE_DIR/.ralph/workspaces.json" || true

# workspaces/ — 키별 서브디렉터리라 러너 간 무충돌. PRIMARY 에 없으면 만들어 둔다.
mkdir -p "$PRIMARY_DIR/workspaces"
link_to "$PRIMARY_DIR/workspaces" "$CLONE_DIR/workspaces" || true

# logs/ — 관측 일원화. clone 에 이미 로그가 쌓여 있으면 지우지 않고 링크를 포기한다.
mkdir -p "$PRIMARY_DIR/logs"
if [ -d "$CLONE_DIR/logs" ] && [ ! -L "$CLONE_DIR/logs" ]; then
  if [ -z "$(ls -A "$CLONE_DIR/logs" 2>/dev/null)" ]; then
    rmdir "$CLONE_DIR/logs"
    link_to "$PRIMARY_DIR/logs" "$CLONE_DIR/logs" || true
  else
    warn "clone logs/ 에 내용이 있어 링크 생략(관측 분산): $CLONE_DIR/logs"
  fi
else
  link_to "$PRIMARY_DIR/logs" "$CLONE_DIR/logs" || true
fi

# ── ③ git 사용자 설정 확인 ──────────────────────────────────────────────────
# clone 은 전역/시스템 설정을 그대로 상속하므로 별도 조치는 필요 없다. 다만 커밋 주체가
# 비어 있으면 러너의 커밋 단계가 실패하므로 확인만 하고 알린다.
GIT_USER="$(git -C "$CLONE_DIR" config user.email 2>/dev/null || true)"
[ -n "$GIT_USER" ] || warn "clone 의 git user.email 이 비어 있음 — 러너 커밋이 실패할 수 있다"

echo "[runner-clone] $KEY: $CLONE_ACTION ($CLONE_DIR) origin=$ORIGIN_ACTION"
echo "[runner-clone] 심볼릭 배선 ${LINKED}건 (.env · seats.json · seats/ · workspaces.json · workspaces/ · logs/ 중)"
