/**
 * G-03 secrets 테스트 — CYCLE-20260726-00 / S1 / TASK-GATE-002
 *
 * 러너: node:test (`node --test test/secrets.test.ts`).
 *
 * ⚠️ 이 파일에는 **실제 비밀 값이 하나도 없다.** BOOT_05 회귀 픽스처는 형태만
 *    모사한 더미다: 13자 기호포함 → `dummy!#$000`, 8~9자 영숫자 → `dummy0001`,
 *    내부망 IP → `10.20.30.40`, 계정 → `dummyuser`.
 *    토큰 예시는 각 공급자의 공개 문서용 예시 형식만 따른 무효 문자열이다.
 *
 *    초판은 이 문장 안에 **실제 값을 인용해** 놓고 "더미다"라고 적었다(리뷰어 D 발견).
 *    치환 전후를 나란히 쓰려는 충동이 정확히 그 사고의 원인이다 —
 *    **원본 값은 형태로만 지칭한다.**
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import { scanSecrets, type Verdict } from '../src/secrets.ts';

const DOC = 'docs/Spec/02-database/04-schema-compatibility-policy.md';

function decide(content: string, path = DOC, ctx = {}): Verdict['decision'] {
  return scanSecrets(content, path, ctx).decision;
}

function assertDeny(content: string, path = DOC, ctx = {}) {
  const v = scanSecrets(content, path, ctx);
  assert.equal(v.decision, 'deny', `deny 를 기대했으나 ${v.decision}: ${JSON.stringify(content.slice(0, 80))}`);
  if (v.decision !== 'deny') return;
  // AC-6: 사유 + 규칙번호 + 다음 조치
  assert.equal(v.rule, 'G-03');
  assert.ok(v.reason.includes('행:'), '사유에 행 번호가 없다');
  assert.ok(v.next.length > 20, '다음 조치가 비어 있다');
}

function assertAllow(content: string, path = DOC, ctx = {}) {
  assert.equal(decide(content, path, ctx), 'allow', `allow 를 기대했으나 막혔다: ${JSON.stringify(content.slice(0, 80))}`);
}

function assertAsk(content: string, path = DOC, ctx = {}) {
  assert.equal(decide(content, path, ctx), 'ask', `ask 를 기대했으나 ${decide(content, path, ctx)}: ${JSON.stringify(content.slice(0, 80))}`);
}

/* ------------------------------------------------------------------ *
 * AC-5 — BOOT_05 회귀
 * ------------------------------------------------------------------ */

/**
 * `DEC_20260726_BOOT_05.md` 가 기술한 유출 형태를 그대로 모사한 것.
 * 값은 전부 더미다. 형태만 같다.
 *
 * 핵심: 유출이 `password: <값>` 이 아니라 **마크다운 표 셀**로 되어 있었다.
 * 키-값 정규식만 있는 스캐너는 이걸 통과시킨다 — 그게 BOOT_05 다.
 */
const BOOT05_SHAPE = [
  '### 8-6. 자격증명 인벤토리',
  '',
  '| 위치 | 값 | 분류 | 설정 키 | 처리 | 조치 |',
  '|---|---|---|---|---|---|',
  '| `:14` `password` | `dummy!#$000` | **평문 비밀번호** | spring.datasource.password | 승계 | **형상 제거 + 값 교체 필수** |',
  '',
  '레거시 접속 정보:',
  '',
  '```yaml',
  'spring:',
  '  datasource:',
  '    url: jdbc:mysql://10.20.30.40:3306/SAMPLE_DB',
  '    username: dummyuser',
  '```',
].join('\n');

test('AC-5: BOOT_05 형태(마크다운 표 셀 안의 평문 비밀번호)가 거부된다', () => {
  const v = scanSecrets(BOOT05_SHAPE, DOC);
  assert.equal(v.decision, 'deny');
  if (v.decision !== 'deny') return;
  assert.match(v.reason, /BOOT_05 형태/);
  assert.equal(v.rule, 'G-03');
});

test('AC-5: BOOT_05 회귀 — 거부 사유에 비밀 값 자체가 실리지 않는다', () => {
  const v = scanSecrets(BOOT05_SHAPE, DOC);
  assert.equal(v.decision, 'deny');
  if (v.decision !== 'deny') return;
  const dump = v.reason + v.next;
  assert.ok(!dump.includes('dummy!#$000'), '거부 메시지에 값이 그대로 실렸다. 메시지도 로그·프롬프트다.');
  assert.ok(!dump.includes('dummyuser'), '거부 메시지에 계정명이 그대로 실렸다.');
});

test('AC-5: BOOT_05 인근의 JDBC URL + 계정명 근접 배치가 최소 ask 로 잡힌다', () => {
  // 표 행을 뺀 접속정보만 남겨도 조용히 통과하면 안 된다.
  const onlyJdbc = ['```yaml', 'spring:', '  datasource:', '    url: jdbc:mysql://10.20.30.40:3306/SAMPLE_DB', '    username: dummyuser', '```'].join('\n');
  const v = scanSecrets(onlyJdbc, DOC);
  assert.notEqual(v.decision, 'allow');
  assert.equal(v.decision, 'ask'); // 한 줄이 아니라 근접이므로 사용자 판단
});

test('AC-5: 사설 IP + 포트 + 계정이 한 줄에 모이면 거부', () => {
  assertDeny('접속: 10.20.30.40:3306 username=dummyuser 로 붙는다');
  assertDeny('| 서버 | 192.168.10.7:5432 | account: svcuser |');
  assertDeny('mysql -h 172.16.5.9:3306 -u dummyuser');
});

/* ------------------------------------------------------------------ *
 * 거부 — 게이트별 3건 이상 (AC-2)
 * ------------------------------------------------------------------ */

test('G-03 거부: password 키-값 형태', () => {
  assertDeny('spring.datasource.password=dummy!#$000');
  assertDeny("password: 'dummy!#$000'");
  assertDeny('PASSWORD = Zx9#qL2m!Pv4');
  assertDeny('비밀번호: dummy!#$000');
});

test('G-03 거부: 알려진 값 목록(.harness/secrets-deny.txt) 일치', () => {
  const ctx = { denyValues: ['# 주석은 무시', '', 'KNOWN-LEAKED-VALUE-0001'] };
  assertDeny('이 문서 어딘가에 KNOWN-LEAKED-VALUE-0001 이 남아 있다', DOC, ctx);
  // 형태가 전혀 비밀 같지 않아도 목록에 있으면 무조건 거부한다
  assertDeny('value = KNOWN-LEAKED-VALUE-0001', 'src/config.ts', ctx);
});

test('G-03 거부: 일반 토큰 패턴', () => {
  assertDeny('aws_access_key_id = AKIAIOSFODNN7EXAMPLE');
  assertDeny('const t = "ghp_' + 'a'.repeat(36) + '";');
  assertDeny('slack: xoxb-1234567890-abcdefghij');
  assertDeny('key: AIza' + 'B'.repeat(35));
  assertDeny('-----BEGIN RSA PRIVATE KEY-----');
  assertDeny('DATABASE_URL=mysql://dummyuser:dummy!#$000@10.20.30.40:3306/SAMPLE_DB');
});

/* ------------------------------------------------------------------ *
 * 허용 — 오탐이 나면 안 되는 것 (AC-2, R-5)
 * ------------------------------------------------------------------ */

test('G-03 허용: 마스킹·자리표시자·환경변수 참조', () => {
  assertAllow('| `:14` `password` | `<REDACTED:DB_PASSWORD>` | **평문 비밀번호** | spring.datasource.password | 승계 | 처리됨 |');
  assertAllow('spring.datasource.password=${DB_PASSWORD}');
  assertAllow('password: <your-password-here>');
  assertAllow('password = ****');
  assertAllow('password: null');
});

test('G-03 허용: DB 스키마 문서의 password 컬럼 정의', () => {
  assertAllow(
    ['| 컬럼 | 타입 | 제약 | 설명 |', '|---|---|---|---|', '| password | varchar(64) | NOT NULL | 사용자 비밀번호 해시 |'].join('\n'),
  );
});

test('G-03 허용: 비밀과 무관한 일반 코드·산문', () => {
  assertAllow('export function checkGitCommand(command: string): Verdict {}', 'src/gitguard.ts');
  assertAllow('비밀번호를 평문으로 문서에 남기지 않는다 (workflow §2-17).');
  assertAllow('https://github.com/anthropics/claude-code 에서 확인하라.');
  assertAllow('접속 주소는 10.20.30.40:3306 이다.'); // 계정 없음 → 3요소 미완성
  assertAllow('');
});

test('G-03 허용: secrets-allow.txt 예외가 적용된다', () => {
  assertAllow('password: dummy!#$000', DOC, { allowValues: ['dummy!#$000'] });
});

/* ------------------------------------------------------------------ *
 * 리뷰어 D 지적 회귀 — 2026-07-27 재작업
 * ------------------------------------------------------------------ */

/**
 * `secrets.ts` 의 `isCredentialLiteral` 에 **도달 불가능한 죽은 코드**가 있었다.
 * 경로 제외 가드 `/^[\w][\w/*.:-]*$/` 가 순수 영숫자까지 삼켜, 그 아래의
 * "구분자 없는 영문+숫자 8자" 검사가 한 번도 실행되지 않았다.
 *
 * 결과: BOOT_05 DB 비밀번호는 값에 `!#$` 가 있어서 잡혔을 뿐이고,
 * **기호 없는 자격증명은 43%가 무통보 통과**했다(리뷰어 D 실측).
 * 아래는 그 계열 전체의 회귀 고정이다. 기호에 의존하지 않는 케이스만 모았다.
 */
test('G-03 거부: 기호 없는 자격증명 — 죽은 코드 회귀 (리뷰어 D)', () => {
  for (const v of ['dummy0001', 'abcdef12', 'Abcd1234', 'dummyacc1', 'admin1234']) {
    assertDeny(`| 로그인 기본 비밀번호(평문) | \`${v}\` | \`nms.properties:68\` |`);
    assertDeny(`로그인 기본 비밀번호는 \`${v}\` 로 하드코딩되어 있다.`);
  }
});

test('G-03: 기호 없는 값도 기호 있는 값과 같은 판정을 받는다', () => {
  // 이 두 줄이 갈리면 "형태가 아니라 값의 기호를 잡고 있다"는 뜻이다.
  const withSymbol = scanSecrets('메일 로그인 암호(평문) `dummy!#$000`', DOC).decision;
  const withoutSymbol = scanSecrets('메일 로그인 암호(평문) `dummy000abc`', DOC).decision;
  assert.equal(withSymbol, 'deny');
  assert.equal(withoutSymbol, 'deny', '기호 없는 값이 다른 판정을 받는다 — 죽은 코드가 되살아났다');
});

test('G-03: isAllowed 는 완전 일치만 인정한다 (부분문자열 금지)', () => {
  const line = '| `password` | `dummy!#$000` | 평문 |';
  // 부분문자열 예외가 통하면 `dumm` 한 줄로 모든 파생 값이 뚫린다
  assertDeny(line, DOC, { allowValues: ['dumm'] });
  assertDeny(line, DOC, { allowValues: ['dummy!#$00'] });
  assertDeny(line, DOC, { allowValues: ['ummy!#$000'] });
  // 완전 일치일 때만 통과
  assertAllow(line, DOC, { allowValues: ['dummy!#$000'] });
});

test('G-03: scanTableRow 도 allowValues 를 조회한다 (BOOT_05 핵심 규칙)', () => {
  // 예외 수단이 핵심 규칙에 안 통하면 오탐 구제가 불가능하다
  assertAllow('| `:14` `password` | `dummy!#$000` | **평문 비밀번호** | 승계 |', DOC, {
    allowValues: ['dummy!#$000'],
  });
});

/**
 * 밑줄·점 사각지대 — 라운드 1·2 모두 AES 고정키 계열 미탐이 5/6으로 무변화였다.
 * 키워드(`AES`)는 통과하는데 **값 관문**이 막고 있었다: 경로 제외 가드의 구분자
 * 집합에 `_` 가 없어 `_` 포함 값은 가드를 통과했고, 그 아래 신호는 *순수* 영숫자만
 * 인정해 어느 쪽에도 걸리지 않았다 (리뷰어 D 라운드 2).
 */
test('G-03 거부: 밑줄·점을 품은 자격증명 (AES 고정키 계열)', () => {
  for (const v of ['aes_key_17chars_x', 'aes_key_13a_x', 'aes.key.13a.x', 'k3y_f1xed_aes256']) {
    assertDeny(`AES 고정키는 \`${v}\` 로 하드코딩`);
    assertDeny(`| AES 고정키 | \`${v}\` | 하드코딩 |`);
    assertDeny(`password: ${v}`);
  }
});

test('G-03 거부: GENERIC_KV 도 같은 관문으로 일원화 (length>=16 문턱 제거)', () => {
  // 실제 유출값 6종 중 5종이 16자 미만이라 `credential:`/`secret:` 아래 있었다면 전부 ask 였다
  assertDeny('secret: dummy000abc');
  assertDeny('credential: dummy!#$000');
  assertDeny('token: dummy000abc');
  assertDeny('api_key: dummy000abc');
});

test('G-03 거부: 백틱 없는 평문 pw/pass 키-값', () => {
  for (const s of [
    'nms.mail.login.pw=dummy000abc',
    'ndi.api.pw=dummy!#$000',
    'nms.login.p=dummy!#$000',
    'pw = "dummy000abc"',
    'pass: dummy!#$000',
    'passphrase=dummy000abc',
  ]) {
    assertDeny(s);
  }
});

test('G-03 허용: 점 구분 설정 키 이름은 값이 아니다', () => {
  // `\.p` 보강이 과하게 넓어지면 여기가 먼저 깨진다
  assertAllow('설정 키는 `spring.datasource.password` 이다');
  assertAllow('로거는 `log4j.appender` 를 쓴다');
  assertAllow('const p = someValue;', 'src/x.ts');
});

/**
 * 자기 검사 — **검출기 소스 자신이 자격증명 형태를 담지 않는다.**
 *
 * 이 사이클에서 "유출을 설명하는 사람이 유출을 재생산한다"가 세 번 반복됐다
 * (PM Proceedings → 하네스 소스 주석 → 신규 픽스처). 주석의 예시 하나가
 * `mysql -p<값>` 형태로 자기 검출기에 걸린 적도 있다.
 * `src/**` 는 테스트 자원 완화(`isTestAsset`) 대상이 아니므로 여기서 `allow` 여야 한다.
 */
test('G-03 자기 검사: `src/**`·`bin/**` 전체에 자격증명 형태가 없다', () => {
  // 초판은 2개 파일 하드코딩이라 `src/config.ts`·`bin/harness.ts` 에 값을 넣어도
  // 깨지지 않았다 (리뷰어 D). 글롭으로 바꿔 **신규 파일이 자동 포함**되게 한다.
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const files: string[] = [];
  const walk = (dir: string, rel: string) => {
    for (const e of readdirSync(join(root, dir), { withFileTypes: true })) {
      const r = `${rel}/${e.name}`;
      if (e.isDirectory()) walk(join(dir, e.name), r);
      else if (/\.(ts|mjs|cjs|js)$/.test(e.name)) files.push(r.replace(/^\//, ''));
    }
  };
  for (const d of ['src', 'bin']) {
    if (existsSync(join(root, d))) walk(d, d);
  }
  // [CE-329 이식] 원본 하한은 8이었다(층 A+B 10파일 기준). 이 이식본의 src/ 는
  // 층 A 2파일 + 어댑터 1파일뿐이라 하한을 3으로 내린다. 글롭 정합성 가드라는
  // 역할은 그대로다 — 이 파일에서 이식 시 바꾼 곳은 이 한 줄이 전부다.
  assert.ok(files.length >= 3, `스캔 대상이 너무 적다 — 글롭이 깨졌다: ${files.length}개`);

  const flagged = files
    .map((f) => ({ f, v: scanSecrets(readFileSync(join(root, f), 'utf8'), f) }))
    .filter((x) => x.v.decision !== 'allow')
    .map((x) => `${x.f}: ${(x.v as { reason: string }).reason.split('\n').slice(0, 3).join(' / ')}`);
  assert.deepEqual(flagged, [], `소스에 자격증명 형태가 있다:\n${flagged.join('\n')}`);
});

test('G-03 허용: 식별자 안의 와일드카드는 비밀이 아니다 (실측 오탐)', () => {
  assertAllow('| PasswordChangeController | `/tmpl/password/excel` | `get*List` 호출 |');
  assertAllow('| 보고서 | `RPT` | `RPT_LIST`, `RPT_SCH_*`, `V_PRIV_*` | 자격증명 무관 |');
});

/* ------------------------------------------------------------------ *
 * ask — 경계 사례
 * ------------------------------------------------------------------ */

test('G-03 ask: 오탐 가능성이 있는 일반 키-값', () => {
  // 짧고 단일 문자종 — 예시 문자열일 수 있으므로 사용자 판단
  assertAsk('api_key: abcdefghijkl');
  assertAsk('token = abcdefghijkl');
});

test('G-03 거부: 길고 혼합 문자종인 일반 키-값은 예시로 보기 어렵다', () => {
  assertDeny('token = 0123456789abcdef');
  assertDeny('api_key: "Zx9qL2mPv4Ktr7Bn"');
});

test('G-03 거부: DB 클라이언트 줄의 인라인 비밀번호', () => {
  assertDeny('mysql -h 10.20.30.40 -u dummyuser -pdummy!#$000 SAMPLE_DB');
});

test('G-03 ask: JWT·Bearer 는 문서 예시일 수 있다', () => {
  assertAsk('Authorization: Bearer ' + 'a'.repeat(32));
  assertAsk('eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk');
});

test('G-03 ask: 루프백 주소 + 계정은 로컬 개발 설정일 수 있다', () => {
  assertAsk('url: jdbc:mysql://127.0.0.1:3306/dev  username: devuser');
});

test('G-03 ask: 표 셀 값이 비밀인지 확정할 수 없을 때', () => {
  assertAsk('| `secret` | `abc123` | 설명 |');
});

test('G-03 허용: 표의 비밀 키 셀 뒤가 값이 아니라 설명·식별자인 경우', () => {
  // 실측 오탐. `비밀번호` 행의 다음 셀이 구현 클래스명인 설계 문서.
  assertAllow('| 비밀번호 | `DelegatingPasswordEncoder` 로 교체 | 3.0 |');
  // SQL 식별자는 비밀 키 이름이 아니다
  assertAllow('| `TERMINAL_ACCOUNT_POLICY_PASSWORD` | `CORE-유지` | 미포함 |');
  assertAllow('| FUNC | `FC_NMS_GENERATE_RANDOM_PASSWORD` | 랜덤 패스워드 생성 | `x.sql:5414` |');
});

test('G-03 허용: 비밀 키워드가 있는 줄의 코드 식별자 (실측 오탐 회귀)', () => {
  assertAllow('- 토큰 매니저: `MainController#mainView`, `MainService#selectUserInfo`');
  assertAllow('인증/인가. `com.example.common.auth.*` — 로그인/세션/토큰 매니저');
  assertAllow('| 인증/인가 | 쿠키 토큰 | **Spring Security + `@RequirePriv`** |');
  assertAllow('DB 스키마 자격증명 관련: `PWD_FAIL`, `PWD_FAIL_HIST`, `LIC_V2_*`');
  assertAllow('String cryptoToken = makeToken(reqVO);', 'src/Login.java');
  assertAllow('- `AbstractLoginManager.java:203-224`(checkIdPw) — 비밀번호 검증 경로');
  assertAllow('`BOOT_05`(평문 비밀번호)·`BOOT_06`(Nexus URL)이 부트스트랩을 차단한다.');
  assertAllow('| 228 | `x/passwordChangeList.jsp` | `PasswordChangeController#contents:96` | 사용 |');
  assertAllow('> | CG-2 | 소스 내 평문 자격증명 **0건** | 동 + 시크릿 스캔 | S10 / **R-59** |');
  assertAllow('| 계정 잠금 해제 | `/user/unlock` | 보안 민감. 감사로그는 있음(`NMC00715`) |');
  assertAllow('`System.out`/평문자격증명 게이트 `CG-1~CG-10` — `W29~W38` 구간');
  assertAllow('→ `WEB-INF/classes/*.properties` 는 루트만 제외. `example/properties/nms.properties`(비밀번호 포함)는 포함된다.');
});

/**
 * 실측 회귀 — `infraeye3/docs/**` 59개 파일에 이 스캐너를 돌린 결과를 고정한다.
 *
 * BOOT_05 가 열거한 13개 파일이 **전부** deny 로 잡히고, 그 밖에 실제 자격증명이
 * 있는 3개 파일(AES 고정키·주석 평문 비밀번호·`nms.login.p=`)이 추가로 잡혔다.
 * `docs/Harness/**`·`docs/Proceedings/**`·`docs/LIFETIMES.tsv` 는 전부 allow —
 * 즉 게이트가 켜져도 PM 의 통상 기록 작업은 막히지 않는다.
 *
 * 위 `허용` 케이스들은 그 조사에서 실제로 나온 오탐을 하나씩 좁혀 만든 것이다.
 * 패턴을 넓힐 때 이 목록이 먼저 깨지는지 확인하라.
 */
test('G-03: 오탐 조사 기준선 — 문서 산문 표본이 통과한다', () => {
  const prose = [
    '| 5 | **auth** | jar | 1.0.0.180205-1-STD | example | 인증/인가. `com.example.common.auth.*` |',
    '| 1 | ANY | `/main` | `MainController#mainView`<br>`:59` | LoginUserVO(세션) |',
    '| 25 | **설정** | `nms_solution.properties` + `job.properties`. `{key}` 재귀 치환 |',
    '| 비밀번호 | `DelegatingPasswordEncoder`. 기존값은 `{legacy-sha256}` 아이디로 검증 |',
    '- DB 스키마: `USER_INFO`, `PWD_FAIL`, `PWD_FAIL_HIST`, `LIC_V2_*`(5), 사용자작업이력',
    '| INV-ACT-001 | SNMP 계정 템플릿 | `SNMP_ACCOUNT_TMPL` CRUD | `/tmpl/snmp/contents` |',
  ].join('\n');
  assertAllow(prose);
});

/* ------------------------------------------------------------------ *
 * 테스트 자원 경로 완화
 * ------------------------------------------------------------------ */

test('G-03: 테스트 자원 경로에서는 거부가 ask 로 완화된다 (통과가 아니다)', () => {
  assert.equal(decide(BOOT05_SHAPE, DOC), 'deny');
  assert.equal(decide(BOOT05_SHAPE, 'test/fixtures/bypass-attempts.txt'), 'ask');
  assert.equal(decide(BOOT05_SHAPE, 'test/secrets.test.ts'), 'ask');
  // 완화 대상이 아닌 경로는 그대로 거부
  assert.equal(decide(BOOT05_SHAPE, 'src/secrets.ts'), 'deny');
});

/* ------------------------------------------------------------------ *
 * 계약
 * ------------------------------------------------------------------ */

test('G-03: 순수 함수 계약 — 같은 입력이면 같은 판정', () => {
  const a = scanSecrets(BOOT05_SHAPE, DOC);
  const b = scanSecrets(BOOT05_SHAPE, DOC);
  assert.deepEqual(a, b);
});

test('G-03: 비문자열·빈 입력에서 예외를 던지지 않는다', () => {
  assert.equal(scanSecrets('', DOC).decision, 'allow');
  assert.equal(scanSecrets(undefined as unknown as string, DOC).decision, 'allow');
  assert.equal(scanSecrets('x', undefined as unknown as string).decision, 'allow');
});
