/**
 * 클라이언트 사이드 feature flag 조회.
 *
 * `NEXT_PUBLIC_*` 환경변수는 Next.js 가 빌드 타임에 코드에 인라인하므로 브라우저에서 접근 가능.
 * 모든 flag 는 default OFF — 명시적으로 "true" 인 경우에만 활성화된다.
 *
 * 서버 측에서는 `clickeye-api/app/config.py` 의 `feature_modernize_enabled` 필드를 사용한다.
 */

/**
 * ClickEye Modernize (기존 코드 현대화 파이프라인) 활성화 여부.
 * MVP-2-A 진행 중. 기본 OFF — 화이트리스트 베타 사용자만 노출.
 */
export function isModernizeEnabled(): boolean {
  return process.env.NEXT_PUBLIC_FEATURE_MODERNIZE_ENABLED === "true";
}
