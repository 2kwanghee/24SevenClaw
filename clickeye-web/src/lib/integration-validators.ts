/**
 * 외부 통합(Linear/Notion 등) API 키 입력의 클라이언트 사전 검증.
 *
 * Linear/Notion 토큰은 영문/숫자/일부 기호로 구성된 ASCII 문자열이다.
 * 한글·이모지·제어문자가 섞이면 백엔드까지 보낼 가치가 없고 fetch 자체가
 * 실패할 수 있으므로 호출 전에 차단한다.
 */

// ASCII printable (0x20~0x7E) 외 문자 검출.
// 토큰에는 보통 줄바꿈/탭이 들어갈 일이 없으므로 제어문자도 거른다.
const NON_PRINTABLE_ASCII = /[^\x20-\x7E]/;
const NON_PRINTABLE_ASCII_GLOBAL = /[^\x20-\x7E]/g;

/**
 * 통합 키 input 의 onChange 단계에서 사용. 비-printable ASCII (한글/이모지/제어문자)를
 * 모두 제거한 문자열을 반환한다. IME 합성 결과로 한글이 한꺼번에 들어오는 경우에도
 * state 에 한글이 절대 저장되지 않도록 가장 안쪽 layer 에서 차단한다.
 */
export function sanitizeIntegrationInput(value: string): string {
  return value.replace(NON_PRINTABLE_ASCII_GLOBAL, "");
}

export interface IntegrationInputCheck {
  ok: boolean;
  /** ok=false 인 경우 사용자에게 노출할 invalid 메시지 */
  message: string;
}

export function checkIntegrationInput(
  value: string,
  fieldLabel: string,
): IntegrationInputCheck {
  if (NON_PRINTABLE_ASCII.test(value)) {
    return {
      ok: false,
      message: `${fieldLabel}에 한글/이모지 등 비-ASCII 문자는 사용할 수 없습니다. 영문·숫자만 입력하세요.`,
    };
  }
  return { ok: true, message: "" };
}

/**
 * Linear API Key + Team ID 입력 검증.
 * 둘 중 하나라도 invalid 면 첫 invalid 메시지 반환.
 */
export function checkLinearInputs(
  apiKey: string,
  teamId: string,
): IntegrationInputCheck {
  const a = checkIntegrationInput(apiKey, "Linear API Key");
  if (!a.ok) return a;
  const t = checkIntegrationInput(teamId, "Linear Team ID");
  if (!t.ok) return t;
  return { ok: true, message: "" };
}

/**
 * Notion API Key + Database ID 입력 검증.
 */
export function checkNotionInputs(
  apiKey: string,
  databaseId: string,
): IntegrationInputCheck {
  const a = checkIntegrationInput(apiKey, "Notion API Key");
  if (!a.ok) return a;
  const d = checkIntegrationInput(databaseId, "Notion Database ID");
  if (!d.ok) return d;
  return { ok: true, message: "" };
}

/**
 * fetch 실패 시 사용자 친화 메시지 추출.
 * "Failed to fetch" 같은 네트워크 에러는 안내 메시지로 치환한다.
 */
export function describeIntegrationError(err: unknown): string {
  if (err instanceof Error) {
    if (err.message === "Failed to fetch" || err.name === "TypeError") {
      return "검증 서버에 연결할 수 없습니다. 네트워크 또는 입력값을 확인하세요.";
    }
    return `검증 요청 실패: ${err.message}`;
  }
  return "검증 요청 실패. 네트워크를 확인하세요.";
}
