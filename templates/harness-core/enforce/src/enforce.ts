/**
 * P8 집행면 어댑터 — 워크스페이스 PreToolUse 훅 진입점 (CE-329)
 *
 * 무인·병렬 에이전트(`claude -p --dangerously-skip-permissions`)의 git/파일 조작을
 * 층 A 순수 판정기(`gitguard.ts` F1~F7 · `secrets.ts` S1~S4)에 물린다.
 * 두 판정기는 무수정 이식물이므로 이 파일이 하는 일은 **판정 조립뿐**이다:
 * stdin payload 해석 → 컨텍스트 주입 → 판정 → 종료코드 매핑.
 *
 * ── 설계 제약 (이 파일을 고칠 사람이 반드시 알아야 하는 것) ─────────────────
 *
 * 1. **exit 2 만 차단이다.** 실측 확인: PreToolUse 훅은 skip-permissions 에서도
 *    실행되지만 `exit 1` 은 자문형(non-blocking)이라 툴이 그대로 실행된다.
 *    그래서 이 파일에는 `exit 1` 로 가는 경로가 **하나도 없어야 한다**.
 *    통과는 `exit 0` 하나, 나머지 전부 `exit 2` 다.
 *
 * 2. **ask 도 거부다.** 무인 실행에는 사용자 확인 채널이 없으므로 `ask` 를
 *    허용으로 흘리면 판정 불능이 곧 우회가 된다. fail-closed 로 거부한다.
 *    에이전트의 정상 조작(`git add <파일>`·`git commit`)은 아래 3의 컨텍스트
 *    주입으로 이미 `allow` 이고, push·브랜치 조작은 파이프라인 impl_git 소관이라
 *    이 강경 매핑이 딜리버리 흐름을 끊지 않는다.
 *
 * 3. **`integrateRoots: [cwd]`** — clone 전체를 하나의 통합 작업면으로 선언한다.
 *    층 A 는 이 근거가 없으면 `git commit`·`apply` 를 거부하는 fail-closed 설계다.
 *    워크스페이스는 태스크 하나당 clone 하나이므로 clone 루트가 곧 작업면이고,
 *    같은 주입이 clone **밖** 경로(`git -C /tmp`, `cd ..`)를 경계 이탈로 만든다.
 *
 * 4. 층 B(config/identity/ownership/protect/approval/records)는 import 하지 않는다.
 *    CONTROL.yaml·assignment.json 같은 제어면이 워크스페이스에 없기 때문이다.
 *    다만 **작업면 경계 집행(E-01)은 예외로 가져왔다** — 원본은 쓰기 대상의
 *    `rel === null`(경계 밖) 판정을 층 B(ownership)에서 집행하는데, 층 B 가 없으면
 *    `Write ../../etc/evil.txt` 가 그대로 통과한다(실측). 판정식은 원본
 *    `gate.ts targetsFrom()` 을 그대로 옮겼고, 집행만 이 파일이 한다.
 *
 * 5. **Bash 명령 문자열도 비밀 스캔에 넣는다** — 원본 범위 밖이다(원본 G-03 은
 *    쓰기 툴만 본다). 무인 실행 결과가 고객 레포로 push 되는 이 환경에서는
 *    `echo <키> > .env` 가 쓰기 툴을 우회해 커밋까지 가므로 방어 깊이를 더한다.
 *    흔한 평문 경로(echo·printf·heredoc·tee)만 막고 인코딩·변수 조립은 못 잡는다.
 */

// 최상단 fail-closed 기본값 — 아래 어떤 코드가 죽어도 종료코드는 2다.
// (CJS 번들에서는 import 가 이 줄보다 앞으로 끌려가므로 모듈 로딩 단계는
//  esbuild 배너가 같은 규칙으로 덮는다 — esbuild.config.mjs 참조)
process.exitCode = 2;

import { appendFileSync, mkdirSync, readFileSync, realpathSync, writeSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, resolve } from 'node:path';

import { type GitGuardContext, checkGitCommand, tokenizeShell } from './gitguard.ts';
import { type SecretsContext, scanSecrets } from './secrets.ts';

/**
 * `gitguard.ts`·`secrets.ts` 가 각자 같은 이름으로 export 하는 판정 형태.
 * 구조 타입으로 받아 둘을 한 경로에서 처리한다.
 */
type Verdict =
  | { decision: 'allow' }
  | { decision: 'deny'; rule: string; reason: string; next: string }
  | { decision: 'ask'; rule: string; reason: string };

interface HookPayload {
  cwd?: unknown;
  tool_name?: unknown;
  tool_input?: unknown;
  session_id?: unknown;
}

const WRITE_TOOLS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const IN_SCOPE_TOOLS = new Set([...WRITE_TOOLS, 'Bash']);

/**
 * 대기 상태 상한.
 *
 * ⚠️ 이 타이머는 **판정을 선점하지 못한다** — 층 A 는 동기 순수 함수라 이벤트 루프를
 * 양보하지 않는다. 실제로 발동하는 경우는 stdin 이 닫히지 않아 `readStdin()` 이
 * 영원히 대기하는 것뿐이고, 그 상태를 훅 타임아웃(15s, 자문형 처리 가능)에 넘기지 않고
 * 거부로 떨어뜨리는 것이 목적이다. 동기 구간의 폭주에는 무력하다(10MB 입력 실측 수백 ms).
 */
const TIMEOUT_MS = 10_000;

/** 어댑터 자체 거부 — 층 A 판정이 아닌 형태·경계 위반 */
const RULE_ADAPTER = 'E-00';
/** 쓰기 대상이 clone(작업면) 밖 */
const RULE_BOUNDARY = 'E-01';
/** 게이트 자기보호 — 훅·설정·감사 경로 변조 */
const RULE_PROTECT = 'E-02';
/** 불투명 실행 경로 — 판정기가 볼 수 없는 우회 표면 */
const RULE_OPAQUE = 'E-03';

let watchdog: NodeJS.Timeout | null = null;
let auditCwd: string | null = null;
let auditTool = '(unknown)';

/* ------------------------------------------------------------------ *
 * 출력 · 감사 · 종료
 * ------------------------------------------------------------------ */

/**
 * 파이프에 대한 `process.stderr.write` 는 비동기라 곧바로 `process.exit` 하면
 * 거부 사유가 잘려 나간다. 사유 없는 거부는 에이전트가 우회를 시도하게 만든다.
 */
function writeErr(text: string): void {
  const buf = Buffer.from(text, 'utf8');
  let off = 0;
  for (let guard = 0; off < buf.length && guard < 1000; guard++) {
    try {
      off += writeSync(2, buf, off, buf.length - off);
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === 'EAGAIN') continue;
      return; // 출력 불가는 판정을 바꾸지 않는다
    }
  }
}

/**
 * best-effort 감사 1줄 — 차단된 판정만 남긴다. 실패는 무시한다(감사 실패가
 * 판정을 바꾸면 감사가 곧 우회 수단이 된다).
 * 탐지된 비밀 값은 층 A 가 reason 에 싣지 않으므로 그대로 기록해도 안전하다.
 */
function audit(decision: 'deny' | 'ask', rule: string, reason: string): void {
  try {
    if (auditCwd === null) return;
    const dir = join(auditCwd, '.harness');
    mkdirSync(dir, { recursive: true });
    const line =
      JSON.stringify({
        ts: new Date().toISOString(),
        tool: auditTool,
        decision,
        rule,
        reason: reason.split('\n')[0].slice(0, 300),
      }) + '\n';
    appendFileSync(join(dir, 'enforce-audit.jsonl'), line, 'utf8');
  } catch {
    /* best-effort */
  }
}

/** 차단 — 여기와 pass() 외에 process.exit 을 부르는 곳은 없다 */
function block(kind: 'deny' | 'ask', rule: string, reason: string, next: string): never {
  audit(kind, rule, reason);
  const head = kind === 'deny' ? '거부' : '거부(판정 불확정)';
  writeErr(`[집행면 게이트] ${head} — ${rule}\n  사유: ${reason}\n  조치: ${next}\n`);
  if (watchdog !== null) clearTimeout(watchdog);
  process.exit(2);
}

/** 통과 — exit 0 에 도달하는 유일한 경로 */
function pass(): never {
  if (watchdog !== null) clearTimeout(watchdog);
  process.exit(0);
}

/** 예외·타임아웃 — 허용이 아니라 거부로 떨어진다 */
function die(where: string, e: unknown): never {
  return block(
    'deny',
    RULE_ADAPTER,
    `집행면 게이트 내부 오류(${where}): ${(e as Error)?.stack ?? String(e)}`,
    '예외는 허용이 아니라 거부다(fail-closed). 게이트 결함이므로 운영자에게 보고하라.',
  );
}

process.on('uncaughtException', (e) => die('uncaughtException', e));
process.on('unhandledRejection', (e) => die('unhandledRejection', e));
// 번들 배너의 최후 방어선에게 "본체 핸들러가 살아 있다"고 알린다 — 이 시점부터
// 예외도 감사 기록을 남기고 거부된다 (esbuild.config.mjs 참조).
(globalThis as Record<string, unknown>)['__HARNESS_HANDLERS__'] = true;

/* ------------------------------------------------------------------ *
 * 입력
 * ------------------------------------------------------------------ */

function readStdin(): Promise<string> {
  return new Promise((res, rej) => {
    const chunks: Buffer[] = [];
    process.stdin.on('data', (c: Buffer) => chunks.push(c));
    process.stdin.on('end', () => res(Buffer.concat(chunks).toString('utf8')));
    process.stdin.on('error', rej);
  });
}

interface WriteTarget {
  /** payload 원문 경로 — 거부 사유에 그대로 보여준다 */
  raw: string;
  /** 정규화·심볼릭 해제까지 끝낸 절대경로 */
  abs: string;
  /** clone 안이면 POSIX 상대경로, 밖이면 null (원본 `WriteTarget.rel` 규약과 동일) */
  rel: string | null;
  content: string;
}

/** 원본 ownership.toPosix 와 동일 */
function toPosix(p: string): string {
  return p.replace(/\\/g, '/').replace(/^\.\//, '');
}

/**
 * 심볼릭 링크를 지나 실제 경로를 구한다.
 *
 * `resolve()` 는 `..` 만 정규화하므로 `<clone>/link → /etc` 같은 링크가 남으면
 * 경계 판정이 링크 이름 기준으로 통과한다. 존재하지 않는 경로(= 새로 만드는 파일)가
 * 정상 경우이므로 **존재하는 최상위 조상까지만** realpath 로 풀고 나머지는 붙여 되돌린다.
 * 해석 불가는 입력 그대로 돌려준다 — 경계 판정은 호출부에서 fail-closed 로 처리한다.
 */
function resolveThroughLinks(abs: string): string {
  const tail: string[] = [];
  let head = abs;
  for (let guard = 0; guard < 64; guard++) {
    try {
      const real = realpathSync(head);
      return tail.length === 0 ? real : join(real, ...tail.slice().reverse());
    } catch {
      const parent = dirname(head);
      if (parent === head) return abs; // 루트까지 올라갔다
      tail.push(basename(head));
      head = parent;
    }
  }
  return abs;
}

/**
 * 쓰기 대상 해석 — 원본 `gate.ts` `targetsFrom()` 의 판정식을 그대로 옮겼다:
 *   `abs = isAbsolute(raw) ? resolve(raw) : resolve(cwd, raw)`
 *   `rel = toPosix(relative(anchor, abs))`
 *   `inside = rel !== '' && !rel.startsWith('../')`
 *
 * ⚠️ 원본은 이 `rel === null`(경계 밖)을 **층 B(ownership)** 에서 집행한다. 층 B 를
 * 이식하지 않았으므로 집행이 비어 있었고, 실제로 `Write ../../etc/evil.txt` 가
 * 통과했다. 그래서 경계 집행은 이 어댑터의 책임으로 가져온다(E-01).
 */
function writeTargets(tool: string, ti: Record<string, unknown>, cwd: string): WriteTarget[] {
  const out: WriteTarget[] = [];
  const anchor = resolveThroughLinks(resolve(cwd));
  const add = (rawPath: unknown, content: unknown): void => {
    // 경로가 없으면 무엇을 쓰는지 알 수 없다 — 경계 판정도 불가하므로 밖으로 취급한다.
    const raw = typeof rawPath === 'string' ? rawPath : '';
    const text = typeof content === 'string' ? content : '';
    if (raw === '' && text === '') return;
    const abs = resolveThroughLinks(isAbsolute(raw) ? resolve(raw) : resolve(cwd, raw));
    const rel = toPosix(relative(anchor, abs));
    const inside = raw !== '' && rel !== '' && !rel.startsWith('../');
    out.push({ raw, abs, rel: inside ? rel : null, content: text });
  };

  switch (tool) {
    case 'Write':
      add(ti['file_path'], ti['content']);
      break;
    case 'Edit':
      add(ti['file_path'], ti['new_string']);
      break;
    case 'MultiEdit': {
      const edits = Array.isArray(ti['edits']) ? (ti['edits'] as Array<Record<string, unknown>>) : [];
      const merged = edits
        .map((e) => (typeof e?.['new_string'] === 'string' ? (e['new_string'] as string) : ''))
        .join('\n');
      add(ti['file_path'], merged);
      break;
    }
    case 'NotebookEdit':
      add(ti['notebook_path'] ?? ti['file_path'], ti['new_source']);
      break;
    default:
      break;
  }
  return out;
}

/**
 * 비밀 deny/allow 목록 주입 — 층 A 는 순수 함수라 파일을 읽지 않는다.
 * 워크스페이스 `.harness/` 에 목록이 없으면 빈 배열(= 패턴 판정만).
 */
function readValueLines(path: string): string[] {
  try {
    return readFileSync(path, 'utf8')
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l !== '' && !l.startsWith('#'));
  } catch {
    return [];
  }
}

function secretLists(cwd: string): SecretsContext {
  const dir = join(cwd, '.harness');
  return {
    denyValues: readValueLines(join(dir, 'secrets-deny.txt')),
    allowValues: readValueLines(join(dir, 'secrets-allow.txt')),
  };
}

/* ------------------------------------------------------------------ *
 * 게이트 자기보호 (E-02) · 불투명 실행 표면 (E-03)
 *
 * ⚠️ 이 두 검사는 **문자열·토큰 기반이라 적대적 우회를 막지 못한다.** 변수 조립
 * (`P=.claude/hooks; rm -f $P/x`)·인코딩·간접 실행이 그대로 남는다. 원본은 이 층을
 * `protect.ts`(보호 경로)와 G-11(Bash 화이트리스트)로 닫는데, 둘 다 층 B다
 * (`gitguard.ts:1476-1523` 주석이 이 위임을 명시한다). 여기 있는 것은 **값싼 구멍만
 * 닫는 얕은 방어**이고, 진짜 집행은 층 B 이식(v2) 없이는 성립하지 않는다.
 * ------------------------------------------------------------------ */

/** 변조되면 게이트 자체가 무력화되는 경로 (cwd 기준 상대경로) */
const PROTECTED_FILES = new Set(['.claude/settings.json']);
const PROTECTED_DIRS = ['.claude/hooks', '.harness'];

/**
 * 파괴 동사 — 대상이 보호 경로면 거부한다.
 * 읽기(`cat`·`grep`·`git diff`)는 막지 않는다. 감사·디버깅을 막을 이유가 없다.
 */
const DESTRUCTIVE = new Set([
  'rm', 'mv', 'cp', 'chmod', 'chown', 'truncate', 'tee', 'dd', 'ln', 'shred', 'unlink', 'rmdir',
]);
/** 대상이 보호 경로일 때 파괴적인 git 서브명령 */
const DESTRUCTIVE_GIT_SUB = new Set(['rm', 'clean', 'checkout', 'restore']);

const SHELL_NAMES = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'csh', 'tcsh']);
const INTERPRETERS = new Set(['python', 'python3', 'node', 'perl', 'ruby', 'php']);
const INLINE_FLAGS = new Set(['-c', '-e', '-p', '-E', '--eval', '--command']);
const REDIRECT_OPS = new Set(['>', '>>']);

function isProtectedRel(rel: string): boolean {
  if (rel === '') return false;
  if (PROTECTED_FILES.has(rel)) return true;
  return PROTECTED_DIRS.some((d) => rel === d || rel.startsWith(`${d}/`));
}

/** 토큰을 cwd 기준 상대경로로 정규화한다. 경로가 아니거나 작업면 밖이면 null */
function relOfToken(token: string, cwd: string): string | null {
  if (token === '' || token.startsWith('-')) return null;
  const abs = isAbsolute(token) ? resolve(token) : resolve(cwd, token);
  const rel = toPosix(relative(cwd, abs));
  return rel === '' || rel.startsWith('../') ? null : rel;
}

/** 세그먼트에서 `FOO=bar` 대입을 건너뛴 명령 이름과 인자 */
function segmentInfo(seg: string[]): { name: string; args: string[] } {
  let i = 0;
  while (i < seg.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(seg[i] as string)) i++;
  const rawName = seg[i] ?? '';
  const args = seg.slice(i + 1).filter((t) => !REDIRECT_OPS.has(t));
  return { name: basename(rawName), args };
}

function denyVerdict(rule: string, reason: string, next: string): Verdict {
  return { decision: 'deny', rule, reason, next };
}

/** 첫 번째 비플래그 인자 — git 서브명령 추출 */
function firstSub(args: string[]): string {
  return args.find((a) => !a.startsWith('-')) ?? '';
}

/** F1 — 훅·설정·감사 경로에 대한 파괴적 조작 (Bash 레인) */
function checkProtectedPaths(command: string, cwd: string): Verdict {
  for (const seg of tokenizeShell(command)) {
    if (seg.length === 0) continue;
    const hits = seg
      .map((t) => relOfToken(t, cwd))
      .filter((r): r is string => r !== null && isProtectedRel(r));
    if (hits.length === 0) continue;

    const { name, args } = segmentInfo(seg);
    let destructive = DESTRUCTIVE.has(name);
    // `sed -i` 는 제자리 편집이다
    if (name === 'sed' && args.some((a) => a === '-i' || a.startsWith('-i'))) destructive = true;
    if (name === 'git' && DESTRUCTIVE_GIT_SUB.has(firstSub(args))) destructive = true;
    // `> <보호경로>` 는 명령 이름과 무관하게 내용을 날린다(truncate 포함)
    const redirects = seg.some((t) => REDIRECT_OPS.has(t));

    if (destructive || redirects) {
      return denyVerdict(
        RULE_PROTECT,
        `게이트 자신을 겨냥한 조작이다 — 보호 경로: ${hits.join(', ')} (명령: ${name || '(리다이렉트)'})`,
        '집행면 훅(.claude/hooks/)·배선(.claude/settings.json)·감사와 예외목록(.harness/)은 ' +
          '피집행자가 바꿀 수 없다. 이 경로가 지워지거나 손상되면 훅이 자문형(exit 1)으로 ' +
          '떨어져 게이트가 조용히 열린다. 필요한 변경은 운영자가 조달 경로로 수행한다.',
      );
    }
  }
  return { decision: 'allow' };
}

/**
 * F4·F5·F6 — 판정기가 내용을 볼 수 없는 실행 표면.
 *
 * **좁은 표적만 막는다.** `npm run`·`make`·`pytest`·`uv run`·`./x.sh` 는 에이전트가
 * 정상 구현·테스트에 반드시 쓰므로 허용한다. 그 결과 "간접 실행을 통한 git 조작"은
 * v1 이 막지 못한다 — 그걸 닫는 것이 층 B G-11 화이트리스트다.
 */
function checkExecSurface(command: string, cwd: string): Verdict {
  for (const seg of tokenizeShell(command)) {
    if (seg.length === 0) continue;
    const { name, args } = segmentInfo(seg);
    if (name === '') continue;

    // F5 — `git-stash` 대시 디스패치. gitguard 는 `git` 이 아니라고 보아 통과시킨다.
    // 현대 git 은 대시 형태를 지원하지 않으므로 정상 사용례가 없다 → 거부(정규화 불필요).
    if (/^git-[A-Za-z0-9][A-Za-z0-9-]*$/.test(name)) {
      return denyVerdict(
        RULE_OPAQUE,
        `git 대시 디스패치(\`${name}\`)는 판정 우회 표면이다`,
        `\`git ${name.slice(4)}\` 형태로 쓰라 — 그래야 층 A 가 의미를 판정할 수 있다.`,
      );
    }

    // F4 ① 셸에 스크립트·표준입력을 먹이는 형태. `-c "<문자열>"` 은 층 A 가 재귀 검사하므로 넘긴다.
    if (SHELL_NAMES.has(name)) {
      if (args.includes('-c')) continue;
      return denyVerdict(
        RULE_OPAQUE,
        `셸에 스크립트/표준입력을 먹이는 형태다 (\`${name} ${args.join(' ')}\`.trim()) — 실행될 내용을 판정할 수 없다`,
        '`| bash`·`bash <파일>`·`sh -s` 는 게이트가 내용을 볼 수 없다. 실행할 명령을 ' +
          'Bash 툴에 직접 쓰거나, 스크립트를 파일로 두고 `./x.sh` 처럼 실행하라.',
      );
    }
    if (name === 'source' || name === '.') {
      return denyVerdict(
        RULE_OPAQUE,
        `\`${name}\` 은 현재 셸에서 파일 내용을 실행한다 — 판정할 수 없다`,
        '실행할 명령을 Bash 툴에 직접 쓰라.',
      );
    }

    // F4 ② 인터프리터 인라인 코드에 git 조작
    if (INTERPRETERS.has(name)) {
      const idx = args.findIndex((a) => INLINE_FLAGS.has(a));
      if (idx >= 0 && /\bgit\b/.test(args.slice(idx + 1).join(' '))) {
        return denyVerdict(
          RULE_OPAQUE,
          `인터프리터 인라인 코드(\`${name} ${args[idx]}\`)로 git 을 조작한다`,
          'git 명령은 Bash 툴에 직접 쓰라 — 인라인 코드 안의 git 은 층 A 가 판정할 수 없다.',
        );
      }
    }

    // F4 ③ find -exec git … / xargs … git …
    if (name === 'find' && args.includes('-exec') && args.some((a) => /\bgit\b/.test(a))) {
      return denyVerdict(
        RULE_OPAQUE,
        '`find -exec git …` 은 대상 수·인자를 정적으로 알 수 없다',
        'git 명령을 대상마다 명시적으로 쓰라.',
      );
    }
    if (name === 'xargs' && args.some((a) => /\bgit\b/.test(a))) {
      return denyVerdict(
        RULE_OPAQUE,
        '`xargs … git …` 은 대상 수·인자를 정적으로 알 수 없다',
        'git 명령을 대상마다 명시적으로 쓰라.',
      );
    }

    // F6 — `git apply`/`git am`. 어댑터가 `integrateRoots:[cwd]` 를 항진식으로 주입하므로
    // 층 A 의 통합 worktree 조건이 항상 참이 되어 이 둘이 열린다. 패치 **내용**은 어느
    // 스캐너도 보지 않으므로 임의 트리 변경 경로다. 에이전트는 Edit/Write 를 쓰면 되므로 막는다.
    if (name === 'git') {
      const sub = firstSub(args);
      if (sub === 'apply' || sub === 'am') {
        return denyVerdict(
          RULE_OPAQUE,
          `\`git ${sub}\` 은 패치 내용이 판정되지 않은 채 트리를 바꾼다`,
          '파일 변경은 Edit/Write 툴로 하라 — 그쪽은 경계·비밀 검사를 받는다.',
        );
      }
    }
  }
  return { decision: 'allow' };
}

/* ------------------------------------------------------------------ *
 * 판정 매핑
 * ------------------------------------------------------------------ */

/** allow 면 돌아오고, deny/ask 면 exit 2 로 끝난다 */
function decide(v: Verdict): void {
  if (v.decision === 'allow') return;
  if (v.decision === 'deny') {
    block('deny', v.rule || RULE_ADAPTER, v.reason, v.next);
  }
  block(
    'ask',
    v.rule || RULE_ADAPTER,
    v.reason,
    '무인 실행(skip-permissions)에는 사용자 확인 채널이 없어 판정 불확정을 거부로 처리한다(fail-closed). ' +
      '정상 작업이면 대상을 명시적으로 좁혀 다시 시도하고, 오탐이면 운영자가 ' +
      '.harness/secrets-allow.txt 에 근거와 함께 등록한다.',
  );
}

/* ------------------------------------------------------------------ *
 * 본체
 * ------------------------------------------------------------------ */

async function main(): Promise<never> {
  watchdog = setTimeout(
    () => die('타임아웃', new Error(`${TIMEOUT_MS}ms 안에 판정을 끝내지 못했다`)),
    TIMEOUT_MS,
  );

  const raw = await readStdin();

  let payload: HookPayload;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('최상위가 객체가 아니다');
    }
    payload = parsed as HookPayload;
  } catch (e) {
    block(
      'deny',
      RULE_ADAPTER,
      `훅 입력(stdin JSON)을 파싱할 수 없다: ${(e as Error).message} (입력 ${raw.length}B)`,
      '판정 근거를 읽지 못한 상태에서는 통과시킬 수 없다. 훅 계약이 바뀐 것이라면 운영자에게 보고하라.',
    );
  }

  // tool_name 부재는 "관할 밖 툴"이 아니라 **형태가 깨진 payload** 다. 관할 밖으로
  // 취급하면 tool_input 에 실제 조작이 담겨 있어도 그대로 통과한다.
  const rawTool = payload.tool_name;
  if (typeof rawTool !== 'string' || rawTool === '') {
    block(
      'deny',
      RULE_ADAPTER,
      `payload 에 tool_name 이 없거나 문자열이 아니다: ${JSON.stringify(rawTool ?? null).slice(0, 80)}`,
      '무엇을 하려는지 모르는 채로 통과시킬 수 없다. 훅 계약 변경이면 운영자에게 보고하라.',
    );
  }
  const tool = rawTool;
  auditTool = tool;

  // cwd 없이는 작업면 경계(경로 이탈·통합 worktree)를 판정할 근거가 없다.
  const rawCwd = payload.cwd;
  if (typeof rawCwd !== 'string' || rawCwd === '') {
    block(
      'deny',
      RULE_ADAPTER,
      'payload 에 cwd 가 없어 작업면 경계를 판정할 수 없다',
      '경계를 모르는 상태의 git·파일 조작은 허용하지 않는다(fail-closed).',
    );
  }
  const cwd = rawCwd;
  auditCwd = cwd;

  if (!IN_SCOPE_TOOLS.has(tool)) pass();

  const rawInput = payload.tool_input;
  if (rawInput === null || typeof rawInput !== 'object' || Array.isArray(rawInput)) {
    block(
      'deny',
      RULE_ADAPTER,
      `관할 툴(${tool})인데 tool_input 을 읽을 수 없다`,
      '무엇을 하려는지 모르는 채로 통과시킬 수 없다. 훅 계약 변경이면 운영자에게 보고하라.',
    );
  }
  const toolInput = rawInput as Record<string, unknown>;

  if (tool === 'Bash') {
    /**
     * 비문자열 command 는 **형태가 깨진 payload** 다 (F2).
     * 초판은 `''` 로 강등해 통과시켰는데, 그러면 `command: ["git","stash"]` 같은 입력이
     * 판정 없이 지나간다 — tool_name·tool_input 에는 "형태 깨짐 = 거부"를 적용하면서
     * 여기만 반대였다.
     */
    const rawCommand = toolInput['command'];
    if (typeof rawCommand !== 'string') {
      block(
        'deny',
        RULE_ADAPTER,
        `Bash 툴인데 command 가 문자열이 아니다: ${JSON.stringify(rawCommand ?? null).slice(0, 80)}`,
        '무엇을 실행하려는지 모르는 채로 통과시킬 수 없다. 훅 계약 변경이면 운영자에게 보고하라.',
      );
    }
    const command = rawCommand;
    if (command.trim() === '') pass();
    // 게이트 자기보호 — 판정기보다 먼저. 게이트가 지워지면 이후 판정 자체가 없다.
    decide(checkProtectedPaths(command, cwd));
    // 설계 제약 3 — clone 루트를 통합 작업면으로 주입한다
    const ctx: GitGuardContext = { cwd, integrateRoots: [cwd] };
    decide(checkGitCommand(command, ctx) as Verdict);
    /**
     * Bash 경유 비밀 기록 — 방어 깊이 보강 (설계 제약 5)
     *
     * 원본은 Bash 를 비밀 스캔 대상에서 제외한다(`gate.ts` 의 G-03 이 WRITE_TOOLS 만 본다).
     * 그러나 여기서는 skip-permissions 자율 실행 결과가 **고객 레포로 실제 push** 되므로,
     * `echo <키> > .env` 한 줄이 쓰기 툴을 거치지 않고 비밀을 커밋까지 태운다.
     * 명령 문자열 자체를 스캔해 흔한 평문 경로(echo·printf·heredoc·tee)를 막는다.
     * **완전 차단이 아니다** — 변수 조립·base64·외부 다운로드는 잡지 못한다.
     */
    decide(scanSecrets(command, '<bash-command>', secretLists(cwd)) as Verdict);
    // 불투명 실행 표면 — 좁은 표적만(F4·F5·F6). npm run·make·./x.sh 는 허용 유지.
    decide(checkExecSurface(command, cwd));
  } else {
    const lists = secretLists(cwd);
    for (const t of writeTargets(tool, toolInput, cwd)) {
      // ① 작업면 경계 (E-01) — 층 A 판정보다 먼저. clone 밖은 내용을 볼 필요도 없다.
      if (t.rel === null) {
        block(
          'deny',
          RULE_BOUNDARY,
          `쓰기 대상이 작업면(clone) 밖이다: ${t.raw || '(경로 없음)'} → ${t.abs}`,
          `작업면은 ${cwd} 하위뿐이다. Bash 의 경로 이탈(\`cd\`·\`git -C\`)과 같은 경계를 ` +
            '쓰기 툴에도 적용한다. 대상이 정말 저장소 안이라면 clone 루트 기준 상대경로로 다시 지정하라.',
        );
      }
      // ② 게이트 자기보호 (E-02) — 훅·배선·감사 경로는 쓰기 툴로도 못 바꾼다.
      //    `.claude/current-plan.md` 같은 정상 산출물은 보호 대상이 아니다.
      if (isProtectedRel(t.rel)) {
        block(
          'deny',
          RULE_PROTECT,
          `게이트 자신을 겨냥한 쓰기다 — 보호 경로: ${t.rel}`,
          '집행면 훅(.claude/hooks/)·배선(.claude/settings.json)·감사와 예외목록(.harness/)은 ' +
            '피집행자가 바꿀 수 없다. 자기 예외목록을 쓸 수 있으면 비밀 스캔이 무력해진다.',
        );
      }
      // ③ 비밀 스캔 (G-03) — 경로는 상대경로로 넘긴다(테스트 자원 완화 판정이 이걸 본다)
      decide(scanSecrets(t.content, t.rel, lists) as Verdict);
    }
  }

  pass();
}

void main();
