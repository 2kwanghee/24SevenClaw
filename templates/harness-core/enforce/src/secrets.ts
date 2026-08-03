/**
 * G-03 — 비밀정보 스캔
 *
 * 근거: GATE-SPEC.md §6 `G-03`, workflow.md §2-17,
 *       docs/Decision/DEC_20260726_BOOT_05.md (이 게이트가 막았어야 할 실제 사건)
 * 소유: S1 / TASK-GATE-002
 *
 * 설계 제약
 *  - 순수 함수. 파일시스템·네트워크 접근 없음.
 *    `.harness/secrets-deny.txt` / `secrets-allow.txt` 의 **내용은 호출자가 주입**한다.
 *  - 오탐이 의심되면 `deny`가 아니라 `ask`(GATE-SPEC §3.3, CYCLE §5 R-5).
 *  - reason 에 **탐지된 비밀 값 자체를 절대 싣지 않는다.** 거부 메시지도 로그·프롬프트다.
 *
 * BOOT_05 가 통과한 이유: 유출 형태가 `password: <값>` 이 아니라
 * **마크다운 표 셀**(`| \`password\` | \`<값>\` |`)이었다. 키-값 정규식만으로는 잡히지 않는다.
 * 표 행 검사(§3)가 그 회귀를 막는 장치다.
 */

export type Verdict =
  | { decision: 'allow' }
  | { decision: 'deny'; rule: string; reason: string; next: string }
  | { decision: 'ask'; rule: string; reason: string };

export interface SecretsContext {
  /** `.harness/secrets-deny.txt` 의 각 줄. 알려진 실제 비밀 값. 호출자가 읽어서 주입한다. */
  denyValues?: string[];
  /** `.harness/secrets-allow.txt` 의 각 줄. 근거와 함께 등록된 예외. */
  allowValues?: string[];
}

const RULE = 'G-03';

interface Finding {
  line: number; // 1-based
  label: string; // 사람이 읽는 탐지 사유. 값은 포함하지 않는다.
  severity: 'deny' | 'ask';
}

/* ------------------------------------------------------------------ *
 * 0. 값 판별 보조
 * ------------------------------------------------------------------ */

/** 자리표시자·마스킹·환경변수 참조 — 비밀이 아니다. */
const PLACEHOLDER = new RegExp(
  [
    '^<[^>]*>$', // <REDACTED:DB_PASSWORD>, <your-password>
    '^\\$\\{?[A-Za-z_][A-Za-z0-9_]*\\}?$', // $PASSWORD, ${DB_PASSWORD}
    '^\\{\\{.*\\}\\}$', // {{ password }}
    '^%[A-Za-z_]+%$', // %PASSWORD%
    '^ENC\\(.*\\)$', // jasypt
    '^[*x•·.\\-_?]+$', // ****, xxxx, ----, ...., ???
    '^(REDACTED|MASKED|PLACEHOLDER|CHANGEME|CHANGE_ME|TODO|TBD|N/?A|NONE|NULL|NIL|EMPTY|OMITTED|생략|미상|없음|비공개)$',
  ].join('|'),
  'i',
);

/** 표/스키마 문서에서 값 자리에 흔히 오는 비-비밀 토큰. */
const NON_SECRET_VALUE = new RegExp(
  [
    '^(varchar|nvarchar|char|text|longtext|mediumtext|tinytext|int|integer|bigint|smallint|tinyint|decimal|numeric|float|double|date|datetime|timestamp|time|year|blob|json|bool|boolean|enum|set|binary|uuid|serial)\\b',
    '^(string|number|object|array|true|false|yes|no|on|off|null|undefined)$',
    '^(not|primary|unique|index|default|auto_increment|nullable|required|optional)$',
    '^(password|passwd|pwd|secret|token|credential|자격증명|비밀번호|평문)$', // 키 이름이 값 자리에 온 경우
    '^\\d+$', // 순수 숫자 (길이·행수 등)
    '^\\d+(\\.\\d+)+$', // 버전
    '^(spring|jdbc|mysql|mariadb|oracle|postgres)\\.', // 설정 키 이름
    // `datasource.password` 같은 키 경로. **각 구성요소가 문자로 시작할 때만.**
    // 초판은 뒤쪽을 `[A-Za-z0-9_.]*` 로 열어 둬 숫자로 시작하는
    // 구성요소를 가진 값까지 삼켰다 (리뷰어 D "13자 점"). `log4j.appender` 는 여전히 통과한다.
    '^[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)+$',
    // 소스 참조: `context-db.xml:13-14`, `:65-66`, `App.java:120`
    '^[\\w./-]+\\.(xml|java|ts|tsx|jsx?|json|ya?ml|md|properties|sql|jsp|html?|css|scss|sh|py|go|kt|gradle|txt|cfg|conf|ini)(:[\\d,\\s:-]+)?$',
    '^:?\\d+([-,:]\\s*\\d+)*$', // 행 참조 `:13-14`, `13,65`
    '^\\d{1,3}(\\.\\d{1,3}){3}(:\\d+)?$', // IP·IP:PORT (별도 규칙이 담당)
    '^[a-z][a-z0-9+.-]*:\\/\\/', // URL·JDBC DSN (별도 규칙이 담당)
    '^[A-Za-z_][A-Za-z0-9_]*\\(\\)$', // 함수 표기 foo()
    '^§?[\\d.-]+$', // 절 번호
  ].join('|'),
  'i',
);

/**
 * 문맥 없이 값만 보고 "자격증명 리터럴"이라고 말할 수 있는가.
 *
 * 이 판정은 **매우 보수적이어야 한다.** 산문·표 안의 백틱 리터럴 대부분은
 * 식별자·파일참조·클래스명이고, 그것들을 막기 시작하면 문서 작업이 마비된다(R-5).
 * 실측 기준: `docs/**` 59개 파일에 돌려 오탐 0이 되도록 조정했다.
 *
 * 통과시키는 신호는 둘뿐이다.
 *  1. 비밀번호형 기호(`! @ # $ % ^ & * + = ~`)를 포함한다 — 식별자에는 거의 없다
 *  2. 구분자 없이 영문+숫자가 붙은 8자 이상 (`<8자 영숫자>` 형태)
 *
 * ⚠️ **이 파일의 주석·예시에 실제 자격증명 값을 절대 쓰지 않는다** (workflow §2-17).
 *    검출기가 잡는 것은 값이 아니라 **형태**이므로 `<13자 기호포함>` 같은 형태 표기로
 *    설명이 충분히 성립한다. 유출을 설명하다 유출을 재생산하는 것이 이 사이클에서
 *    세 번 반복된 실패 패턴이다 (리뷰어 D).
 */
function isCredentialLiteral(v: string, depth = 0): boolean {
  if (depth > 2) return false;
  if (v.length < 6 || v.length > 64) return false;
  if (/\s/.test(v)) return false;
  if (PLACEHOLDER.test(v) || NON_SECRET_VALUE.test(v)) return false;
  // 구조 문자 — 코드·정규식·마크업이지 비밀번호가 아니다
  if (/[()[\]{}<>\\;]/.test(v)) return false;
  if (/^[\w.+-]+@[\w-]+\.[\w.]+$/.test(v)) return false; // 이메일
  if (/^@[A-Za-z]/.test(v)) return false; // 애노테이션 `@RequirePriv`
  if (/^[A-Za-z_][A-Za-z0-9_]*#[A-Za-z_][A-Za-z0-9_]*(:\d+)?$/.test(v)) return false; // `Foo#bar`, `Foo#bar:96`
  if (/^#[A-Za-z_]/.test(v)) return false; // `#method` 축약 참조·앵커
  if (/^[/~][\w/*.:@-]*$/.test(v)) return false; // URL·경로 `/system/**`, `/tmpl/terminal/*`
  // 경로·소스참조 `WEB-INF/classes/*.properties`, `Foo.java:113-114`.
  // ⚠️ **구분자를 하나 이상 요구한다.** 초판은 `/^[\w][\w/*.:-]*$/` 였는데, 이 집합이
  //    순수 영숫자까지 삼켜 아래 `<8자 영숫자>` 검사를 **도달 불가능한 죽은 코드**로 만들었다.
  //    그 결과 기호 없는 값이 43% 무통보 통과했다 (리뷰어 D 발견).
  //    ⚠️ 2차 사각: 구분자 집합이 `[/.:-]` 라 `_` 포함 값은 이 가드를 통과하는데,
  //    아래 신호는 *순수* 영숫자만 인정해 **어느 쪽에도 안 걸렸다.**
  //    AES 고정키 계열 미탐 5/6이 여기 있었다 (리뷰어 D).
  //    가드를 "진짜 경로·소스참조처럼 보이는 것"으로 좁히고, 아래에 신호를 하나 더 둔다.
  if (
    /^[\w][\w/*.:-]*$/.test(v) &&
    (/\//.test(v) || // 경로
      // 파일 확장자꼴 — **숫자가 없을 때만.** 실제 확장자를 가진 소스 참조는
      // `NON_SECRET_VALUE` 가 확장자 목록으로 이미 걸러내므로, 여기서 숫자 포함까지
      // 삼키면 점 구분 자격증명이 통째로 빠진다 (리뷰어 D "13자 점").
      (/\.[A-Za-z]{1,10}(:[\d,-]+)?$/.test(v) && !/\d/.test(v)) ||
      /:\d/.test(v) || // 행 번호
      /-/.test(v)) // 버전·하이픈 식별자
  ) {
    return false;
  }
  if (/^[A-Z]+\d+$/.test(v)) return false; // 메시지·감사 코드 `NMC00715`
  if (/^[\w.]+\.\*$/.test(v)) return false; // 패키지 글롭 `com.example.auth.*`
  if (/^[A-Za-z_][A-Za-z0-9_]*\*$/.test(v)) return false; // 식별자 글롭 `LIC_V2_*`
  // 식별자 안에 박힌 와일드카드 `get*List`, `RPT_*`, `V_PRIV_*`.
  // `*` 는 비밀번호형 기호 집합에 있지만 이 문서군에서는 압도적으로 글롭 표기다.
  if (/\*/.test(v) && /^[A-Za-z_][A-Za-z0-9_*]*$/.test(v)) return false;
  // `key=value` 는 값 쪽만 다시 본다 (`nms.login.p=<비밀번호>` 를 잡기 위해)
  const kv = v.match(/^[\w.-]+=(.+)$/);
  if (kv) return isCredentialLiteral(kv[1], depth + 1);
  // `~` 는 한국어 문서의 범위 표기(`W29~W38`, `CG-1~CG-10`)에 압도적으로 많아 신호에서 뺀다.
  if (/[!@#$%^&*+=]/.test(v)) return true;
  if (/^[A-Za-z]+\d[A-Za-z0-9]*$/.test(v) && v.length >= 8) return true;
  // 구분자(`_` `.`)를 품은 영숫자 혼합 값 — AES 고정키·라이선스 키가 이 형태다.
  // SQL 식별자(`RPT_CUSTOM_00036`)와 가르는 신호는 **소문자 포함 여부**다:
  // 대문자+숫자+밑줄만이면 테이블·코드 이름이고, 소문자가 섞이면 값일 가능성이 높다.
  if (/^[A-Za-z0-9][A-Za-z0-9_.]{7,}$/.test(v) && /[a-z]/.test(v) && /\d/.test(v)) return true;
  return false;
}

function stripDecoration(cell: string): string {
  return cell
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .replace(/^\s+|\s+$/g, '');
}

/** 문자 종류 다양성 — 자격증명다움의 대용 지표. */
function classCount(v: string): number {
  let n = 0;
  if (/[a-z]/.test(v)) n += 1;
  if (/[A-Z]/.test(v)) n += 1;
  if (/[0-9]/.test(v)) n += 1;
  if (/[^A-Za-z0-9]/.test(v)) n += 1;
  return n;
}

type ValueVerdict = 'secret' | 'suspect' | 'benign';

/** 값 하나가 비밀로 보이는지 판정한다. */
function classifyValue(raw: string): ValueVerdict {
  const v = stripDecoration(raw);
  if (v.length < 4) return 'benign';
  if (/\s/.test(v)) return 'benign'; // 산문
  if (!/[A-Za-z0-9]/.test(v)) return 'benign'; // 기호·한글만
  if (/[()[\]{}<>\\;]/.test(v)) return 'benign'; // 코드 조각 (`makeToken(reqVO);`)
  if (PLACEHOLDER.test(v)) return 'benign';
  if (NON_SECRET_VALUE.test(v)) return 'benign';
  if (/^https?:\/\//i.test(v) && !/\/\/[^/\s:@]+:[^/\s@]+@/.test(v)) return 'benign';

  const classes = classCount(v);
  if (classes >= 3) return 'secret'; // dummy!#$000 → 소문자+숫자+기호
  if (v.length >= 12 && classes >= 2) return 'secret';
  if (v.length >= 8) return 'suspect';
  return 'suspect';
}

/* ------------------------------------------------------------------ *
 * 1. 고정 토큰 패턴
 * ------------------------------------------------------------------ */

interface PatternRule {
  label: string;
  re: RegExp;
  severity: 'deny' | 'ask';
  /**
   * 이 부분문자열이 줄에 없으면 정규식을 아예 돌리지 않는다.
   * `String.includes` 는 선형이고 정규식 역추적을 통째로 건너뛴다.
   */
  pre?: string;
}

const TOKEN_PATTERNS: PatternRule[] = [
  { label: 'AWS Access Key ID', re: /\b(?:AKIA|ASIA|ABIA|ACCA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|A3T[A-Z0-9])[A-Z0-9]{16}\b/, severity: 'deny' },
  {
    label: 'AWS Secret Access Key',
    re: /aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['"]?[A-Za-z0-9/+=]{40}/i,
    severity: 'deny',
  },
  { label: 'GitHub 토큰', re: /\bgh[pousr]_[A-Za-z0-9]{36,}\b/, severity: 'deny' },
  { label: 'GitHub fine-grained PAT', re: /\bgithub_pat_[A-Za-z0-9_]{60,}\b/, severity: 'deny' },
  { label: 'Slack 토큰', re: /\bxox[abposr]-[A-Za-z0-9-]{10,}\b/, severity: 'deny' },
  { label: 'Google API Key', re: /\bAIza[0-9A-Za-z_-]{35}\b/, severity: 'deny' },
  { label: 'Stripe 키', re: /\b[sr]k_(live|test)_[A-Za-z0-9]{16,}\b/, severity: 'deny' },
  { label: 'npm 토큰', re: /\bnpm_[A-Za-z0-9]{36}\b/, severity: 'deny' },
  { label: '개인키 블록', re: /-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP|ENCRYPTED)?\s*PRIVATE KEY-----/, severity: 'deny' },
  {
    // ⚠️ 초판 `/[a-zA-Z][a-zA-Z0-9+.-]*:\/\/…/` 는 **O(n²)** 였다. `://` 가 없는 긴 줄에서
    //    모든 시작 위치마다 `[a-zA-Z0-9+.-]*` 가 끝까지 삼켰다가 역추적한다.
    //    100KB 한 줄에 3225ms — §8 예산 50ms를 G-03 혼자 60배 초과했다 (리뷰어 D 측정).
    //    ① `pre` 로 `://` 없는 줄을 통째로 건너뛰고 ② 수량자에 상한을 둔다.
    label: 'URL 내 basic-auth 자격증명',
    // 선행 경계는 "스킴 문자가 아닌 것" 전부다. `DATABASE_URL=mysql://…` 처럼
    // `=` 뒤에 오는 형태를 놓치지 않으면서, 긴 영숫자 런에서는 즉시 실패한다.
    re: /(?:^|[^A-Za-z0-9+.-])[a-zA-Z][a-zA-Z0-9+.-]{0,15}:\/\/[^/\s:@]{1,64}:[^/\s@]{3,64}@/,
    severity: 'deny',
    pre: '://',
  },
  { label: 'JWT 추정 문자열', re: /\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/, severity: 'ask' },
  { label: 'Bearer 토큰', re: /\bBearer\s+[A-Za-z0-9\-._~+/]{20,}=*/, severity: 'ask' },
];

/**
 * GATE-SPEC §6 G-03 이 명시한 `password` 키-값 형태.
 *
 * 키 뒤의 `["']?` 가 핵심이다. 초판은 이게 없어서 **`{"password": "…"}` 를 놓쳤다** —
 * 키가 따옴표로 닫히면 `\s*[:=]` 가 매칭에 실패한다 (리뷰어 D 발견).
 */
const PASSWORD_KV =
  // `\.p` 는 `nms.login.p=…` 같은 **점 구분 설정 키의 축약형**만 노린다.
  // 맨 `\bp` 로 넓히면 코드의 `p = value` 를 전부 물어 오탐이 된다.
  /(?:password|passwd|passphrase|pwd|\bpw|\bpass|\.p|비밀번호|암호)["']?\s*[:=]\s*(['"]?)([^\s'"`,;<>]{4,})\1?/gi;

/**
 * Spring XML 형태 — **`BOOT_05` 의 원본이 `context-db.xml` 이다.**
 * 문서에 인용된 XML 조각이나 실제 설정 파일 쓰기를 잡는다.
 */
const XML_ATTR_SECRET =
  /name\s*=\s*["'][\w.]*(?:password|passwd|pwd|secret)["'][^>]{0,120}?value\s*=\s*["']([^"']{4,})["']/gi;
const XML_ELEM_SECRET = /<([\w.:-]{0,40}(?:password|passwd|pwd|secret))\s*>\s*([^<\s][^<]{3,})<\/\1>/gi;

/** 그 밖의 비밀 키-값. 오탐이 많아 값 판정을 한 번 더 거친다. */
const GENERIC_KV = /(?:secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential|auth[_-]?key)\s*[:=]\s*(['"]?)([^\s'"`,;]{8,})\1?/gi;

/* ------------------------------------------------------------------ *
 * 2. 사설 IP + 포트 + 계정
 * ------------------------------------------------------------------ */

const PRIVATE_IP_PORT =
  /\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2})\s*:\s*(\d{2,5})\b/;
const LOOPBACK_IP_PORT = /\b(?:127(?:\.\d{1,3}){3}|localhost)\s*:\s*(\d{2,5})\b/i;
const ACCOUNT_KV = /\b(?:user|username|uid|userid|account|login|id|계정|사용자)\s*[:=]\s*['"]?([A-Za-z0-9._-]{2,})/i;
/** CLI 형태의 계정 지정: `mysql -u dummyuser`, `psql --username=svc`. */
const ACCOUNT_CLI = /(?:^|\s)(?:-u|--user|--username)(?:[=\s]+)['"]?([A-Za-z0-9._-]{2,})/;
/** `mysql -p<비밀번호>` 붙여쓰기 형태. DB 클라이언트 줄에서만 본다 — 다른 도구의 `-p` 와 충돌하므로. */
const DB_CLIENT_LINE = /\b(?:mysql|mysqldump|mariadb|psql|mongo|mongosh|redis-cli|sqlplus)\b/i;
const DB_CLIENT_PASSWORD = /(?:^|\s)-p(?!\s)([^\s'"]{4,})/;

/** 한 줄에서 계정 식별자를 찾는다 (키-값 형태 또는 CLI 플래그 형태). */
function findAccount(line: string): string | null {
  const kv = line.match(ACCOUNT_KV);
  if (kv) return kv[1];
  const cli = line.match(ACCOUNT_CLI);
  if (cli) return cli[1];
  return null;
}

/* ------------------------------------------------------------------ *
 * 2-2. 산문 속 자격증명 — BOOT_05 의 실제 다수 형태
 *
 * BOOT_05 의 23개소 중 `password: <값>` 형태는 소수였다. 대부분은
 *   `<계정> / <13자 기호포함>`
 *   DB(`<13자 기호포함>`), 메일(`<9자 기호포함>`)
 * 처럼 **산문·표 셀 안의 계정/비밀번호 쌍** 또는 **비밀 키워드가 있는 줄의 백틱 리터럴**이었다.
 * 키-값 정규식만으로는 전부 놓친다.
 * ------------------------------------------------------------------ */

/** `<계정> / <자격증명>` — 공백으로 감싼 슬래시 쌍. 경로(`a/b`)와 구분된다. */
const ACCOUNT_SLASH_SECRET = /(?:^|[\s`(\[|])`?([A-Za-z][A-Za-z0-9._-]{2,})`?\s+\/\s+`?([^\s`|,)\]]{4,})/g;

/**
 * 같은 줄에 비밀 키워드가 있으면 그 줄의 백틱 리터럴을 값 후보로 본다.
 *
 * `키` 단독은 넣지 않는다 — `키워드`·`키보드`·`모니터링키` 에 전부 걸린다.
 * 대신 실제 유출 문맥에서 쓰이는 **합성어만** 명시한다(`AES 고정키`·`라이선스 임시키`).
 * 리뷰어 D 미탐 표의 "AES-256 고정키 6건 중 5건 미탐 / 라이선스 임시키 9건 중 8건 미탐"이
 * 이 키워드 부족에서 나왔다.
 */
const SECRET_CONTEXT =
  /(비밀번호|암호|자격증명|계정|시크릿|(?:고정|임시|암호화|인증|비밀|공개|개인|마스터|대칭|세션)\s*키|password|passwd|pwd|passphrase|credential|secret|토큰|token|api[_-]?key|\bAES\b|\bRSA\b|\bDES\b|\bHMAC\b|\bpw\b|\bpass\b)/i;

/* ------------------------------------------------------------------ *
 * 3. 마크다운 표 행 — BOOT_05 회귀 방지
 * ------------------------------------------------------------------ */

const SECRET_KEY_NAME =
  /^(password|passwd|pwd|비밀번호|secret|token|api[_-]?key|access[_-]?key|secret[_-]?key|credential|자격증명)$/i;

/** 셀 안에 `` `password` `` 처럼 키 이름이 들어 있는가. */
function cellNamesSecret(cell: string): boolean {
  const plain = stripDecoration(cell);
  if (SECRET_KEY_NAME.test(plain)) return true;
  for (const m of cell.matchAll(/`([^`]+)`/g)) {
    if (SECRET_KEY_NAME.test(m[1].trim())) return true;
  }
  // `spring.datasource.password` 같은 설정 키 경로도 키 이름으로 본다.
  // 단 `TERMINAL_ACCOUNT_POLICY_PASSWORD` 같은 SQL 식별자(UPPER_SNAKE)는 제외한다 —
  // 테이블·컬럼 이름이지 비밀 키가 아니다.
  for (const m of cell.matchAll(/`([^`]+)`/g)) {
    const t = m[1].trim();
    if (/^[A-Z0-9_.]+$/.test(t)) continue;
    if (/(?:^|[._-])(password|passwd|pwd|secret)$/i.test(t)) return true;
  }
  return false;
}

/** 값 셀에서 후보 값을 뽑는다. 백틱 안이 있으면 그것, 없으면 셀 전체. */
function cellValue(cell: string): string {
  const m = cell.match(/`([^`]+)`/);
  return stripDecoration(m ? m[1] : cell);
}

/**
 * @param isAllowed `secrets-allow.txt` 대조. **BOOT_05 핵심 규칙에도 예외가 통해야 한다** —
 *        초판은 이 함수만 예외를 조회하지 않아 오탐 구제 수단이 무력했다 (리뷰어 D 발견).
 */
function scanTableRow(line: string, isAllowed: (v: string) => boolean): Finding['severity'] | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|')) return null;
  if (/^\|[\s:|-]+\|$/.test(trimmed)) return null; // 구분선

  const cells = trimmed.split('|').slice(1, -1);
  if (cells.length < 2) return null;

  for (let i = 0; i < cells.length; i++) {
    if (!cellNamesSecret(cells[i])) continue;
    for (let j = i + 1; j < Math.min(i + 3, cells.length); j++) {
      const v = cellValue(cells[j]);
      if (v === '') continue;
      if (isAllowed(v)) continue;
      if (isCredentialLiteral(v)) return 'deny';
      // 자격증명 리터럴은 아니지만 숫자를 포함해 값일 가능성이 남는 경우 → 사용자 판단.
      // 순수 알파벳 식별자(`DelegatingPasswordEncoder`)는 값이 아니라 설명이므로 넘긴다.
      if (/[0-9]/.test(v) && classifyValue(v) !== 'benign') return 'ask';
      // benign 이면 다음 셀을 한 칸 더 본다 (키 셀 바로 뒤가 타입·설명인 경우)
    }
  }
  return null;
}

/* ------------------------------------------------------------------ *
 * 4. 진입점
 * ------------------------------------------------------------------ */

/**
 * 테스트 자원인가.
 *
 * 픽스처와 테스트 소스는 **비밀 형태의 문자열을 의도적으로 담는다** — G-03 의
 * 회귀 테스트가 바로 그것이다. 여기에 하드 거부를 걸면 게이트가 자기 테스트를
 * 쓰지 못하게 되고, 그러면 구현자가 패턴을 우회하도록 값을 난독화하게 된다.
 * 그래서 거부를 **`ask` 로만 완화**한다. 통과가 아니라 사용자 판단으로 넘기는 것이다.
 *
 * ⚠️ 리뷰 지점: 이 완화는 `foo.test.ts` 로 이름 지어 실제 비밀을 넣는 경로를 연다.
 *    다만 그 경우에도 사용자에게 사유가 그대로 제시되므로 조용한 통과는 아니다.
 */
function isTestAsset(path: string): boolean {
  const p = (path || '').replace(/\\/g, '/');
  if (/(^|\/)(test|tests|spec|__tests__)\/fixtures?\//.test(p)) return true;
  if (/(^|\/)__fixtures__\//.test(p)) return true;
  if (/\.fixture\.[A-Za-z0-9]+$/.test(p)) return true;
  if (/(^|\/)(test|tests|spec|__tests__)\//.test(p) && /\.(test|spec)\.[A-Za-z0-9]+$/.test(p)) return true;
  return false;
}

function cleanList(list?: string[]): string[] {
  if (!Array.isArray(list)) return [];
  return list
    .map((s) => (typeof s === 'string' ? s.trim() : ''))
    .filter((s) => s !== '' && !s.startsWith('#') && s.length >= 4);
}

const SEVERITY: Record<Verdict['decision'], number> = { allow: 0, ask: 1, deny: 2 };

/**
 * 쓰기 내용에서 비밀정보를 찾는다.
 *
 * @param content `tool_input.content` 또는 `new_string`
 * @param path    `tool_input.file_path` — 픽스처 경로 완화 판정과 메시지에만 쓴다
 * @param ctx     deny/allow 목록 (호출자가 `.harness/` 에서 읽어 주입)
 */
export function scanSecrets(content: string, path: string, ctx: SecretsContext = {}): Verdict {
  if (typeof content !== 'string' || content === '') return { decision: 'allow' };

  const allow = cleanList(ctx.allowValues);
  const denyList = cleanList(ctx.denyValues);
  const lines = content.split(/\r?\n/);
  const findings: Finding[] = [];

  /**
   * 예외 목록 대조 — **완전 일치만.**
   *
   * 초판은 `v.includes(a)` 부분문자열 매칭이라 `secrets-allow.txt` 에 `dumm` 한 줄이면
   * `dummy!#$000` 이 통과했다 (리뷰어 D 발견). 예외는 등록한 그 값에만 적용된다.
   */
  const isAllowed = (v: string) => allow.includes(v) || allow.includes(stripDecoration(v));

  for (let idx = 0; idx < lines.length; idx++) {
    const line = lines[idx];
    const no = idx + 1;
    if (line.trim() === '') continue;

    // (a) 알려진 값 목록 — 최우선. 형태를 따지지 않는다.
    for (const known of denyList) {
      if (line.includes(known)) {
        findings.push({ line: no, label: '알려진 비밀 값 목록(.harness/secrets-deny.txt) 일치', severity: 'deny' });
        break;
      }
    }

    // (b) 고정 토큰 패턴
    for (const rule of TOKEN_PATTERNS) {
      if (rule.pre !== undefined && !line.includes(rule.pre)) continue;
      const m = line.match(rule.re);
      if (m && !isAllowed(m[0])) {
        findings.push({ line: no, label: rule.label, severity: rule.severity });
      }
    }

    // (c) password 키-값
    PASSWORD_KV.lastIndex = 0;
    for (const m of line.matchAll(PASSWORD_KV)) {
      const value = m[2];
      if (isAllowed(value)) continue;
      const cls = classifyValue(value);
      if (cls === 'benign') continue;
      // `isCredentialLiteral` 을 최종 판정에 쓴다 — `classifyValue` 만으로는
      // 기호 없는 값(`dummy000abc`)이 ask 로 내려간다 (리뷰어 D 미탐 계열).
      findings.push({
        line: no,
        label: `password 키-값 형태 (값 ${value.length}자)`,
        severity: isCredentialLiteral(value) || cls === 'secret' ? 'deny' : 'ask',
      });
    }

    // (c-2) Spring XML — BOOT_05 원본 형태
    XML_ATTR_SECRET.lastIndex = 0;
    for (const m of line.matchAll(XML_ATTR_SECRET)) {
      const value = m[1].trim();
      if (isAllowed(value) || classifyValue(value) === 'benign') continue;
      findings.push({
        line: no,
        label: `XML 속성 형태 \`name="…password" value="…"\` (값 ${value.length}자)`,
        severity: 'deny',
      });
    }
    XML_ELEM_SECRET.lastIndex = 0;
    for (const m of line.matchAll(XML_ELEM_SECRET)) {
      const value = m[2].trim();
      if (isAllowed(value) || classifyValue(value) === 'benign') continue;
      findings.push({
        line: no,
        label: `XML 요소 형태 \`<${m[1]}>…</${m[1]}>\` (값 ${value.length}자)`,
        severity: 'deny',
      });
    }

    // (d) 그 밖의 비밀 키-값 — 오탐이 많아 기본 ask
    GENERIC_KV.lastIndex = 0;
    for (const m of line.matchAll(GENERIC_KV)) {
      const value = m[2];
      if (isAllowed(value)) continue;
      const cls = classifyValue(value);
      if (cls === 'benign') continue;
      // `length >= 16` 문턱을 뺀다 — 실제 유출값 6종 중 5종이 16자 미만이었고,
      // `credential:`/`secret:` 키 아래 있었다면 전부 ask 로 흘렀다 (리뷰어 D).
      // 판정은 (c)와 동일하게 `isCredentialLiteral` 로 일원화한다.
      findings.push({
        line: no,
        label: `secret/token/api_key 키-값 형태 (값 ${value.length}자)`,
        severity: isCredentialLiteral(value) || cls === 'secret' ? 'deny' : 'ask',
      });
    }

    // (e) 사설 IP + 포트 + 계정이 한 줄에
    const priv = PRIVATE_IP_PORT.test(line);
    const acct = findAccount(line);
    if (priv && acct !== null && !isAllowed(acct)) {
      findings.push({ line: no, label: '한 줄에 사설 IP + 포트 + 계정 동시 출현 (접속정보 3요소)', severity: 'deny' });
    } else if (LOOPBACK_IP_PORT.test(line) && acct !== null) {
      findings.push({ line: no, label: '루프백 주소 + 포트 + 계정 동시 출현', severity: 'ask' });
    }

    // (e-2) DB 클라이언트 줄의 `-pPASSWORD`
    if (DB_CLIENT_LINE.test(line)) {
      const m = line.match(DB_CLIENT_PASSWORD);
      if (m && !isAllowed(m[1]) && classifyValue(m[1]) !== 'benign') {
        findings.push({ line: no, label: `DB 클라이언트 인라인 비밀번호 (-p, 값 ${m[1].length}자)`, severity: 'deny' });
      }
    }

    // (f) 마크다운 표 행 — BOOT_05 형태
    const table = scanTableRow(line, isAllowed);
    if (table) {
      findings.push({ line: no, label: '마크다운 표에 비밀 키 셀과 평문 값 셀이 인접 (BOOT_05 형태)', severity: table });
    }

    // (h) `계정 / 비밀번호` 쌍 — 키워드 없이도 성립하는 형태
    ACCOUNT_SLASH_SECRET.lastIndex = 0;
    for (const m of line.matchAll(ACCOUNT_SLASH_SECRET)) {
      const value = stripDecoration(m[2]); // `S10 / **R-59**` 같은 마크다운 강조를 벗긴다
      if (isAllowed(value)) continue;
      // `isCredentialLiteral` 이 이미 보수적인 관문이다. 그 뒤에 `classifyValue` 를
      // 한 번 더 걸면 **더 약한 검사가 최종 판정을 뒤집는다** — 기호 없는 값
      // (`<8자 영숫자>` 형태)이 deny 대신 ask 로 내려가던 원인이다 (리뷰어 D 미탐 표).
      if (!isCredentialLiteral(value)) continue;
      findings.push({
        line: no,
        label: `\`계정 / 자격증명\` 쌍 형태 (값 ${value.length}자)`,
        severity: 'deny',
      });
    }

    // (i) 비밀 키워드가 있는 줄의 백틱 리터럴
    if (SECRET_CONTEXT.test(line)) {
      for (const m of line.matchAll(/`([^`\n]{4,64})`/g)) {
        const value = m[1].trim();
        if (isAllowed(value)) continue;
        if (!isCredentialLiteral(value)) continue;
        findings.push({
          line: no,
          label: `비밀 키워드가 있는 줄의 백틱 리터럴이 자격증명 형태 (값 ${value.length}자)`,
          severity: 'deny',
        });
      }
    }
  }

  // (g) 근접 규칙 — 사설 IP+포트 줄과 계정 줄이 ±5행 안에 함께 있으면 접속정보가 조립된다.
  //     같은 줄이 아니므로 deny 가 아니라 ask (BOOT_05 문서의 실제 배치가 이 형태다).
  const ipLines: number[] = [];
  const acctLines: number[] = [];
  for (let idx = 0; idx < lines.length; idx++) {
    if (PRIVATE_IP_PORT.test(lines[idx])) ipLines.push(idx + 1);
    const a = findAccount(lines[idx]);
    if (a !== null && classifyValue(a) !== 'benign') acctLines.push(idx + 1);
  }
  for (const ip of ipLines) {
    const near = acctLines.find((a) => a !== ip && Math.abs(a - ip) <= 5);
    if (near !== undefined) {
      findings.push({
        line: ip,
        label: `사설 IP+포트(${ip}행)와 계정(${near}행)이 근접 — 접속정보가 조립 가능`,
        severity: 'ask',
      });
      break;
    }
  }

  if (findings.length === 0) return { decision: 'allow' };

  const fixture = isTestAsset(path);
  let severity: Verdict['decision'] = findings.some((f) => f.severity === 'deny') ? 'deny' : 'ask';
  if (fixture && severity === 'deny') severity = 'ask';

  const shown = findings.slice(0, 8);
  const detail = shown.map((f) => `  - ${f.line}행: ${f.label}`).join('\n');
  const more = findings.length > shown.length ? `\n  … 외 ${findings.length - shown.length}건` : '';
  const head = `${path || '(경로 미상)'} 에서 비밀정보 추정 ${findings.length}건 발견`;
  const reason = `${head}\n${detail}${more}${fixture ? '\n  (테스트 자원 경로이므로 거부 대신 사용자 판단으로 넘긴다)' : ''}`;

  if (severity === 'ask') {
    return { decision: 'ask', rule: RULE, reason };
  }
  return {
    decision: 'deny',
    rule: RULE,
    reason,
    next:
      '값을 `<REDACTED:...>` 로 치환하고 실제 값은 저장소 밖(운영팀 채널)으로만 전달하라. ' +
      '오탐이면 `.harness/secrets-allow.txt` 에 **근거와 함께** 등록하라 — 무근거 예외는 금지다 (GATE-SPEC §6 G-03).',
  };
}

export const __internal = { classifyValue, scanTableRow, tokenPatterns: TOKEN_PATTERNS };
export { SEVERITY as __severity };
