#!/usr/bin/env bash
# R-4 회귀 검증 — catalog 파일들의 기존 항목이 변경되지 않았는지 확인.
#
# 사용:
#   bash scripts/modernize-check-catalog-unchanged.sh [BASE_REF]
#
# BASE_REF 미지정 시 main. 신규 항목 추가는 OK, 기존 항목의 id/category/fields 수정·삭제는 차단.
set -euo pipefail

BASE_REF="${1:-main}"
CATALOG_DIRS=(
    "clickeye-api/app/data/catalog"
    "clickeye-web/src/lib/engine/catalog"
)

echo "═══════════════════════════════════════════════════"
echo "  R-4 카탈로그 무변경 검사 (base=$BASE_REF)"
echo "═══════════════════════════════════════════════════"

violations=0
for dir in "${CATALOG_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        continue
    fi
    while IFS= read -r file; do
        # base 에 없던 신규 파일은 OK
        if ! git cat-file -e "$BASE_REF:$file" 2>/dev/null; then
            echo "  ⊕ 신규 파일 (허용): $file"
            continue
        fi
        # 삭제된 라인 검사 — 기존 항목 수정/삭제 의심
        deleted=$(git diff "$BASE_REF" -- "$file" | grep -c "^-[^-]" || true)
        if [[ $deleted -gt 0 ]]; then
            echo "  ✗ 변경 감지: $file ($deleted 라인 삭제/수정)"
            git diff --stat "$BASE_REF" -- "$file" | head -5
            violations=$((violations + 1))
        else
            echo "  ✓ $file (추가만 또는 무변경)"
        fi
    done < <(find "$dir" -type f \( -name "*.json" -o -name "*.yaml" -o -name "*.yml" \))
done

echo
if [[ $violations -gt 0 ]]; then
    echo "✗ R-4 실패: 카탈로그 기존 항목 변경 $violations 건 감지"
    echo "  비침습성 원칙: 기존 항목 id/category/필드 수정·삭제 금지. 추가만 허용."
    exit 1
fi

echo "✓ R-4 통과: 모든 카탈로그 파일 추가만 또는 무변경"
exit 0
