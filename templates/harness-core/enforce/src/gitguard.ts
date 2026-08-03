/**
 * G-02 — 금지 git 명령 검사
 *
 * 근거: GATE-SPEC.md §6 `G-02` (a)~(d), §5(경로 이탈), workflow.md §12.1·§12.3
 * 소유: S1 / TASK-GATE-002
 *
 * 설계 제약
 *  - 순수 함수. 파일시스템·네트워크·환경변수·설정 접근 없음.
 *  - 문자열 매칭이 아니라 **셸 토크나이즈 후** 검사한다.
 *  - 판정이 애매하면 `deny`가 아니라 `ask`를 돌려준다(GATE-SPEC §3.3).
 *
 * ── 2판 (2026-07-27, 리뷰어 C 실증 반영) ────────────────────────────
 * 초판은 `git add .` 은 막으면서 등가 표현 10종을 통과시켰다. 원인은 하나다:
 * **문자열 집합 매칭은 등가 표현 앞에서 무력하다.** `BULK_PATHSPECS` 집합은
 * `./.`·`src/..`·`.//` 를 몰랐고 — `git add ./` 는 거부인데 `git add .//` 는
 * 통과하는 자기모순이었다 — `git -c alias.zz='!git add .' zz` 한 줄로
 * 금지 목록 전체가 우회됐다.
 *
 * 2판의 원칙:
 *  - 경로는 **정규화 후 포함관계**로 판정한다 (문자열 비교 금지)
 *  - 명령은 **의미**로 판정한다 (porcelain/plumbing 등가물을 같이 묶는다)
 *  - 코드 문자열을 받는 것은 전부 **재귀 검사하거나 `ask`** 로 올린다
 */

export type Verdict =
  | { decision: 'allow' }
  | { decision: 'deny'; rule: string; reason: string; next: string }
  | { decision: 'ask'; rule: string; reason: string };

export interface GitGuardContext {
  /**
   * PreToolUse payload의 `cwd`. 호출자가 주입한다(순수 함수 유지).
   * 커밋 권한·경로 이탈·pathspec 정규화 판정에 쓰인다.
   */
  cwd?: string;
  /**
   * 통합 worktree 를 식별하는 디렉터리 접미사. 기본 `['-integrate']`.
   * **하드코딩하지 않는다** — 호출자가 `CONTROL.yaml identity.map` 에서 읽어 주입한다
   * (GATE-SPEC §6 G-02 (c)).
   */
  integrateSuffixes?: string[];
  /**
   * 통합 worktree 의 **절대 경로**. 주어지면 접미사 heuristic 대신 이것으로
   * 진짜 경로 접두 판정을 한다 (GATE-SPEC §6 G-02 (c)).
   * 호출자가 `CONTROL.yaml identity.map` 에서 읽어 주입한다 — 이쪽이 정상 경로다.
   */
  integrateRoots?: string[];
}

const RULE = 'G-02';

/* ------------------------------------------------------------------ *
 * 1. 셸 토크나이저
 * ------------------------------------------------------------------ */

const REDIRECTS = new Set(['>', '>>', '<', '<<', '<<<']);

/**
 * 셸 명령 문자열을 "세그먼트(단순 명령) 배열"로 분해한다.
 *
 * 분해 기준: `&&` `||` `;` `|` `&` 개행, 서브셸 `$( )` `` ` `` `( )`.
 * 인용부호는 해제된 값으로 토큰화하므로 `git add "."` 의 인자는 `.` 이 된다.
 * 리다이렉션 연산자는 토큰으로 남기고 인자 추출 단계에서 제거한다.
 */
export function tokenizeShell(command: string): string[][] {
  const segments: string[][] = [];
  let cur: string[] = [];
  let tok = '';
  let hasTok = false;

  const flushTok = () => {
    if (hasTok) {
      cur.push(tok);
      tok = '';
      hasTok = false;
    }
  };
  const flushSeg = () => {
    flushTok();
    if (cur.length > 0) segments.push(cur);
    cur = [];
  };

  const n = command.length;
  let i = 0;

  while (i < n) {
    const c = command[i];

    // 백슬래시 이스케이프
    if (c === '\\') {
      if (i + 1 < n) {
        const nx = command[i + 1];
        if (nx === '\n') {
          i += 2; // 행 이음
          continue;
        }
        tok += nx;
        hasTok = true;
        i += 2;
      } else {
        i += 1;
      }
      continue;
    }

    // 작은따옴표 — 내부 이스케이프 없음
    if (c === "'") {
      hasTok = true;
      i += 1;
      while (i < n && command[i] !== "'") {
        tok += command[i];
        i += 1;
      }
      i += 1;
      continue;
    }

    // 큰따옴표
    if (c === '"') {
      hasTok = true;
      i += 1;
      while (i < n && command[i] !== '"') {
        if (command[i] === '\\' && i + 1 < n) {
          tok += command[i + 1];
          i += 2;
          continue;
        }
        tok += command[i];
        i += 1;
      }
      i += 1;
      continue;
    }

    // 주석 — 토큰 경계에서 시작하는 '#' 만
    if (c === '#' && !hasTok) {
      while (i < n && command[i] !== '\n') i += 1;
      continue;
    }

    // 명령 치환 / 서브셸 — 내부를 독립 세그먼트로 본다
    if (c === '$' && command[i + 1] === '(') {
      flushSeg();
      i += 2;
      continue;
    }
    if (c === '`' || c === '(' || c === ')') {
      flushSeg();
      i += 1;
      continue;
    }

    // 세그먼트 구분자
    if (c === ';' || c === '\n') {
      flushSeg();
      i += 1;
      continue;
    }
    if (c === '&') {
      flushSeg();
      i += command[i + 1] === '&' ? 2 : 1;
      continue;
    }
    if (c === '|') {
      flushSeg();
      i += command[i + 1] === '|' ? 2 : 1;
      continue;
    }

    // 리다이렉션
    if (c === '>' || c === '<') {
      flushTok();
      if (c === '>' && command[i + 1] === '>') {
        cur.push('>>');
        i += 2;
      } else if (c === '<' && command[i + 1] === '<') {
        if (command[i + 2] === '<') {
          cur.push('<<<');
          i += 3;
        } else {
          cur.push('<<');
          i += 2;
        }
      } else {
        cur.push(c);
        i += 1;
      }
      continue;
    }

    // 공백
    if (c === ' ' || c === '\t' || c === '\r') {
      flushTok();
      i += 1;
      continue;
    }

    tok += c;
    hasTok = true;
    i += 1;
  }

  flushSeg();
  return segments;
}

/** 리다이렉션 연산자와 그 대상 토큰을 인자 목록에서 제거한다. */
function stripRedirections(tokens: string[]): string[] {
  const out: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (REDIRECTS.has(t)) {
      i += 1; // 대상 토큰도 건너뛴다
      continue;
    }
    if (/^\d+$/.test(t) && tokens[i + 1] !== undefined && REDIRECTS.has(tokens[i + 1])) {
      i += 2; // `2> file`
      continue;
    }
    out.push(t);
  }
  return out;
}

/**
 * 실행 파일 이름을 정규화한다.
 *
 * 스크립트 확장자를 제거하는 이유: `./bin/harness.js approve` 와 `harness approve` 는
 * 같은 행위다. 초판은 확장자 제거를 런타임 언랩(`node x.cjs`) 안에서만 해서
 * **직접 실행하면 판정이 뒤집혔다** (GATE-SPEC §6 G-02 (d), 리뷰어 C 발견).
 */
function basename(p: string): string {
  const norm = p.replace(/\\/g, '/');
  const last = norm.slice(norm.lastIndexOf('/') + 1);
  return last.replace(/\.(exe|js|cjs|mjs|ts|cts|mts|sh|bash|py|rb|pl)$/i, '');
}

const WRAPPERS = new Set([
  'env',
  'sudo',
  'doas',
  'nohup',
  'time',
  'command',
  'builtin',
  'exec',
  'nice',
  'ionice',
  'stdbuf',
  'timeout',
  'xargs',
  'setsid',
]);

const RUNTIMES = new Set(['node', 'nodejs', 'npx', 'bunx', 'bun', 'tsx', 'ts-node', 'deno']);

/** 그룹화·제어구조 키워드. 명령 앞에 붙어도 실행되는 것은 그 뒤다. */
const SHELL_SYNTAX = new Set(['{', '}', '!', 'then', 'else', 'elif', 'do', 'done', 'fi', 'in']);

/** 명령 문자열을 받아 실행하는 셸. */
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'ash', 'busybox', 'script']);

/** 코드 문자열을 받아 실행하는 비셸 인터프리터 (GATE-SPEC §6 G-02 (d)). */
const INTERPRETERS = new Set(['python', 'python2', 'python3', 'perl', 'ruby', 'php', 'lua', 'awk', 'gawk']);

interface CommandInfo {
  /** 실행 파일 basename (소문자화 안 함 — 셸은 대소문자 구분) */
  name: string;
  /** 실행 파일 뒤의 인자들. 리다이렉션 제거됨. */
  args: string[];
  /**
   * 명령 앞에 붙은 `VAR=value` 접두들. **버리지 않는다.**
   *
   * 초판~3판은 이걸 내용도 보지 않고 건너뛰었다. 그래서 `-c`·`git config` 에 건
   * 모든 통제에 **환경변수라는 병렬 우회로**가 있었다 (리뷰어 C 라운드 3 실증):
   * `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0='!git add .' git zz`
   * 는 `git -c alias.zz='!git add .' zz` 와 완전 등가다.
   */
  env: string[];
}

/** 세그먼트에서 실제 실행되는 명령과 인자를 뽑는다. `VAR=x sudo git ...` 형태를 벗겨낸다. */
function commandInfo(rawTokens: string[]): CommandInfo {
  const tokens = stripRedirections(rawTokens);
  const env: string[] = [];
  let i = 0;

  while (i < tokens.length) {
    const t = tokens[i];
    if (/^[A-Za-z_][A-Za-z0-9_]*=/.test(t)) {
      env.push(t); // 버리지 않고 판정으로 넘긴다
      i += 1;
      continue;
    }
    if (SHELL_SYNTAX.has(t)) {
      i += 1;
      continue;
    }
    if (WRAPPERS.has(basename(t))) {
      i += 1;
      // 래퍼 자체의 플래그를 건너뛴다 (`timeout 10`, `xargs -I{}` 등)
      while (i < tokens.length && (tokens[i].startsWith('-') || /^\d+[smh]?$/.test(tokens[i]))) {
        i += 1;
      }
      continue;
    }
    break;
  }

  if (i >= tokens.length) return { name: '', args: [], env };

  let name = basename(tokens[i]);
  let args = tokens.slice(i + 1);

  // `node dist/harness.cjs approve`, `npx harness approve` 를 한 겹 벗긴다.
  // 단 `node -e "<code>"` 는 코드 실행이므로 벗기지 않고 인터프리터 분기로 넘긴다.
  const evalsCode = args.some((a) => a === '-e' || a === '--eval' || a === '-p' || a === '--print');
  if (RUNTIMES.has(name) && !evalsCode) {
    let j = 0;
    while (j < args.length && args[j].startsWith('-')) j += 1;
    if (j < args.length) {
      name = basename(args[j]);
      args = args.slice(j + 1);
    }
  }

  return { name, args, env };
}

/** `-am` 같은 단문자 클러스터를 고려해 특정 단문자 플래그 존재 여부를 본다. */
function hasShortFlag(args: string[], letter: string): boolean {
  for (const a of args) {
    if (a === '--') break;
    if (/^-[A-Za-z]+$/.test(a) && a.slice(1).includes(letter)) return true;
  }
  return false;
}

/* ------------------------------------------------------------------ *
 * 2. 경로 정규화 (GATE-SPEC §5, §6 G-02 (d) "경로 정규화")
 * ------------------------------------------------------------------ */

type Containment = 'inside' | 'outside' | 'unknown';

/**
 * 절대 경로를 정규화한다 — `.` `..` 를 **접는다**.
 *
 * ⚠️ 2판까지 이 함수는 후행 슬래시만 제거했다. 그래서 같은 파일 안에서
 * 정규화 강도가 두 갈래였다: 상대경로는 `normalizeRel` 로 접히는데 절대경로는
 * 원문 그대로 비교됐다. 결과로 `cd ../` 는 거부되는데
 * `cd /…/infraeye3-s1/../infraeye3-s0` 는 통과했다 (리뷰어 C 라운드 2).
 * 루트 위로 올라가는 `..` 는 루트에서 멈춘다(POSIX 동작).
 */
function normalizeAbs(p: string): string {
  const s = p.replace(/\\/g, '/');
  const m = s.match(/^([A-Za-z]:)?\//);
  const prefix = m ? m[0] : '';
  const stack: string[] = [];
  for (const part of s.slice(prefix.length).split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') {
      stack.pop();
      continue;
    }
    stack.push(part);
  }
  const joined = prefix + stack.join('/');
  return joined.replace(/\/+$/, '') || '/';
}

/** 상대 경로를 정규화한다. 루트 위로 올라가면 `null`, 제자리면 `''`. */
function normalizeRel(p: string): string | null {
  const stack: string[] = [];
  for (const part of p.replace(/\\/g, '/').split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') {
      if (stack.length === 0) return null;
      stack.pop();
      continue;
    }
    stack.push(part);
  }
  return stack.join('/');
}

function containment(target: string, cwd?: string): Containment {
  if (target === '' || target === '-' || target === '~') return 'outside';
  if (target.startsWith('~')) return 'outside';
  if (target.includes('$')) return 'unknown';

  const isAbs = target.startsWith('/') || /^[A-Za-z]:[\\/]/.test(target);
  if (isAbs) {
    if (!cwd) return 'unknown';
    const t = normalizeAbs(target);
    const c = normalizeAbs(cwd);
    return t === c || t.startsWith(c + '/') ? 'inside' : 'outside';
  }

  return normalizeRel(target) === null ? 'outside' : 'inside';
}

/**
 * pathspec 의 성격을 **정규화 후** 판정한다.
 *
 * 초판은 `{'.', './', '*', ':/'}` 문자열 집합이었다. 리뷰어 C 실증:
 * `./.`·`src/..`·`.//`·`././.`·worktree 루트 절대경로가 전부 뚫렸다.
 */
export type PathspecKind = 'bulk' | 'glob' | 'escape' | 'explicit' | 'unknown';

export function classifyPathspec(p: string, cwd?: string): PathspecKind {
  let s = p;

  // pathspec magic: `:/`, `:!`, `:^`, `:(top)`, `:(exclude)` …
  if (s.startsWith(':')) {
    const m = s.match(/^:(\([^)]*\)|[/!^:]*)(.*)$/);
    if (m) {
      if (m[2] === '') return 'bulk'; // `:/`, `:`, `:(top)` → 저장소 전체
      s = m[2];
    }
  }

  if (s === '') return 'bulk';
  if (s.includes('$')) return 'unknown';
  if (/[*?[\]]/.test(s)) return 'glob';

  const isAbs = s.startsWith('/') || /^[A-Za-z]:[\\/]/.test(s);
  if (isAbs) {
    if (!cwd) return 'unknown';
    const t = normalizeAbs(s);
    const c = normalizeAbs(cwd);
    if (t === c) return 'bulk'; // worktree 루트 절대경로 = 전체
    return t.startsWith(c + '/') ? 'explicit' : 'escape';
  }

  const rel = normalizeRel(s);
  if (rel === null) return 'escape';
  if (rel === '') return 'bulk'; // `.` `./` `.//` `./.` `././.` `src/..`
  return 'explicit';
}

/**
 * cwd 가 통합 담당 worktree 인가.
 *
 * **경로 접두 판정**이다. 초판은 basename 만 봐서 `<repo>-integrate/sub` 하위
 * 디렉터리에서 커밋이 막히는 오탐이 있었다 (리뷰어 C 발견, GATE-SPEC §6 G-02 (c)).
 */
export function isIntegrationWorktree(cwd: string, suffixes?: string[], roots?: string[]): boolean {
  const c = normalizeAbs(cwd);

  // ① 권위 있는 경로 — 호출자가 CONTROL.yaml `identity.map` 에서 주입한 절대 경로.
  //    **진짜 경로 접두 판정**이며 heuristic 이 아니다. 이것이 있으면 이것만 쓴다.
  if (roots && roots.length > 0) {
    return roots.some((r) => {
      const root = normalizeAbs(r);
      return c === root || c.startsWith(root + '/');
    });
  }

  // ② 폴백 heuristic — 접미사 규약. 세그먼트 이름만 보므로 `/tmp/x-integrate` 처럼
  //    저장소와 무관한 경로도 참이 된다 (리뷰어 C 라운드 2 지적). 이름만으로는
  //    구분할 방법이 없다. **`roots` 를 주입하면 이 한계가 사라진다** —
  //    S0 어댑터가 CONTROL.yaml 에서 읽어 넘기는 것이 정상 경로다.
  const list = suffixes && suffixes.length > 0 ? suffixes : ['-integrate'];
  const parts = c.split('/');
  return parts.some((seg) => list.some((sfx) => seg.length > sfx.length && seg.endsWith(sfx)));
}

/* ------------------------------------------------------------------ *
 * 3. git 하위 명령 규칙
 * ------------------------------------------------------------------ */

const GIT_GLOBAL_WITH_VALUE = new Set([
  '-C',
  '-c',
  '--exec-path',
  '--namespace',
  '--config-env',
  '--work-tree',
  '--git-dir',
]);

const GIT_GLOBAL_FLAGS = new Set([
  '-p',
  '-P',
  '--paginate',
  '--no-pager',
  '--bare',
  '--no-replace-objects',
  '--literal-pathspecs',
  '--glob-pathspecs',
  '--noglob-pathspecs',
  '--icase-pathspecs',
  '--no-optional-locks',
  '--no-lazy-fetch',
]);

/**
 * 값이 외부 명령으로 실행되는 git 설정 키.
 *
 * `git -c alias.zz='!git add .' zz` 는 **금지 목록 전체를 우회하는 범용 수단**이다
 * (리뷰어 C 실증 — 실제 스테이징 확인). alias 외에도 아래 키들이 외부 명령을 띄운다.
 */
const EXEC_CONFIG_EXACT = new Set([
  'core.pager',
  'core.editor',
  'core.sshcommand',
  'core.hookspath',
  'core.fsmonitor',
  'core.gitproxy',
  'sequence.editor',
  'diff.external',
  'credential.helper',
  'uploadpack.packobjectshook',
  'gpg.program',
  'ssh.variant',
  'init.templatedir',
  // 꼬리가 `.command` 가 아니라 `.alternaterefscommand` 라 규칙에서 빗나간다 (리뷰어 C)
  'core.alternaterefscommand',
]);
const EXEC_CONFIG_PATTERN =
  /^(?:filter\..+\.(?:clean|smudge|process)|protocol\..+\.command|merge\..+\.driver|diff\..+\.(?:command|textconv)|url\..+\.insteadof)$/;

/**
 * 설정 키가 외부 명령을 실행하는가 — **열거가 아니라 규칙으로 판정한다.**
 *
 * 2판은 `EXEC_CONFIG_EXACT` 열거였고, 그래서 `difftool.<x>.cmd`·`mergetool.<x>.cmd`·
 * `guitool.<x>.cmd`·`man.<x>.cmd`·`browser.<x>.cmd`·`pager.<cmd>`·`include.path` 가
 * 전부 빠졌다 (리뷰어 C 실행 검증). **열거 목록은 누락이 필연이다.**
 *
 * 규칙: 키의 마지막 구성요소가 "실행할 것"을 가리키면 차단한다.
 */
// `.proxy` 와 `.tool` 은 뺐다 (리뷰어 C 라운드 3 오탐 6건):
//  - `http.proxy` 는 URL 이지 명령이 아니다. 진짜 명령인 `core.gitProxy` 는 EXACT 에 있다.
//  - `.tool` 은 도구 **이름**이다 (`diff.tool=vimdiff`). 실제 명령은 `<tool>.cmd` 로 이미 잡힌다.
// "애매하면 차단"이 아니라 "애매하면 ask" 가 이 게이트의 원칙이고, 여기서는 애매하지도 않다.
const EXEC_KEY_TAIL =
  /\.(?:cmd|command|helper|driver|program|editor|pager|hook|hookspath|hookpath|sshcommand|textconv|process|clean|smudge|insteadof|askpass)$/;

function isExecConfigKey(rawKey: string): boolean {
  const k = rawKey.toLowerCase().trim();
  if (k.startsWith('alias.')) return true;
  if (EXEC_CONFIG_EXACT.has(k)) return true;
  if (EXEC_CONFIG_PATTERN.test(k)) return true;
  if (EXEC_KEY_TAIL.test(k)) return true;
  if (/^pager\./.test(k)) return true; // `pager.log` — 하위 명령별 페이저
  if (/^include(?:if)?\./.test(k)) return true; // 임의 설정 파일 끌어오기
  return false;
}

/**
 * 설정 키·값 하나를 판정한다. `-c`(1회성)와 `git config`(영속) 양쪽이 공유한다.
 * 위험이 같으므로 판정도 같아야 한다 — 영속형이 오히려 더 나쁘다.
 */
function checkConfigAssignment(rawKey: string, value: string | undefined, how: string): Verdict | null {
  const key = rawKey.trim();
  // 값이 `!` 로 시작하면 git 이 셸로 실행한다. 키 이름과 무관하게 차단한다.
  if (value !== undefined && value.trim().startsWith('!')) {
    return deny(
      `\`${how} ${key}=!…\` 의 값이 \`!\` 로 시작한다 — git 이 이를 **셸 명령으로 실행**하므로 ` +
        'G-02 금지 목록 전체가 우회된다 (GATE-SPEC §6 G-02 (d), 리뷰어 C 실증).',
      '셸 이스케이프 없이 의도한 git 명령을 그대로 실행하라.',
    );
  }
  if (key.toLowerCase().startsWith('alias.')) {
    return deny(
      `\`${how} ${key}\` 는 alias 를 정의한다. alias 는 임의의 git 명령·셸 명령으로 전개되므로 ` +
        '금지 목록 검사를 통째로 우회한다 (GATE-SPEC §6 G-02 (d)).',
      'alias 를 정의하지 말고 의도한 git 명령을 그대로 실행하라.',
    );
  }
  if (isExecConfigKey(key)) {
    return deny(
      `\`${how} ${key}\` 는 외부 명령을 실행하는 설정 키다 (GATE-SPEC §6 G-02 (d)).`,
      '설정 주입 없이 실행하라. 훅·페이저·에디터·도구 경로를 바꿔야 하면 사용자에게 요청하라.',
    );
  }
  return null;
}

/**
 * 환경변수 lane — `-c` / `git config` 와 **같은 통제를 받아야 한다**.
 *
 * git 은 설정을 세 경로로 받는다: `-c`(인자), `git config`(영속 파일), **환경변수**.
 * 앞의 둘만 막으면 세 번째가 그대로 병렬 우회로가 된다 (리뷰어 C 라운드 3 실증).
 */
/**
 * 값이 셸 명령으로 실행되는 git 환경변수 — **열거가 아니라 이름 꼬리 규칙**.
 *
 * 설정 키 쪽에서 "열거는 누락이 필연"이라 판단해 `EXEC_KEY_TAIL` 규칙으로 바꿨는데,
 * env 쪽에는 열거가 남아 있었다 (리뷰어 C 라운드 4). 같은 전환을 여기에도 적용한다.
 * `GIT_EDITOR` `GIT_SEQUENCE_EDITOR` `GIT_PAGER` `GIT_EXTERNAL_DIFF` `GIT_SSH`
 * `GIT_SSH_COMMAND` `GIT_ASKPASS` `GIT_PROXY_COMMAND` `GIT_ALTERNATE_REFS_COMMAND`
 * `GIT_MERGE_TOOL_CMD` `GIT_TEXTCONV` 가 이 하나로 덮인다.
 */
const ENV_EXEC_TAIL = /(?:^|_)(EDITOR|PAGER|ASKPASS|COMMAND|CMD|DIFF|SSH|PROXY|TEXTCONV|FILTER)$/;

/** 저장소 위치를 바꾸는 환경변수. `-C` / `--work-tree` 와 같은 containment 검사를 받는다. */
const ENV_PATH = new Set([
  'GIT_DIR',
  'GIT_WORK_TREE',
  'GIT_INDEX_FILE',
  'GIT_OBJECT_DIRECTORY',
  'GIT_ALTERNATE_OBJECT_DIRECTORIES',
  'GIT_COMMON_DIR',
  'GIT_CEILING_DIRECTORIES',
  'GIT_EXEC_PATH', // git 하위 명령 바이너리 탐색 경로 (리뷰어 C 권고, 무비용)
]);

/** `git config` 의 읽기 전용 조회 플래그. */
const CONFIG_READONLY_FLAGS = new Set([
  '--get',
  '--get-all',
  '--get-regexp',
  '--get-urlmatch',
  '--list',
  '-l',
  '--show-origin',
  '--show-scope',
  '--get-color',
  '--get-colorbool',
]);

/** **다음 토큰을 값으로 소비하는** `git config` 플래그. */
const CONFIG_VALUE_FLAGS = new Set(['-f', '--file', '--blob', '--type', '-t', '--default', '--comment']);

/**
 * `git config` 인자에서 키·값을 뽑는다.
 *
 * `positionals()` 를 그대로 쓰면 `-f other.cfg alias.zz '!…'` 에서 `other.cfg` 가
 * 키 자리로 들어와 판정이 빗나갔다 (리뷰어 C 라운드 3). 결합형 `--file=x` 는
 * 우연히 맞았는데 분리형은 틀리는 비대칭이었다.
 *
 * 리뷰어 C의 구조적 지적: **판정 함수는 합쳤는데 추출 계층이 갈라져 있었다.**
 * `-c` 는 `indexOf('=')`, `config` 는 `positionals()` 였다. 추출도 여기로 모은다.
 */
interface ConfigArgs {
  key?: string;
  value?: string;
  readOnly: boolean;
  edit: boolean;
  /** `-f` / `--file` / `--blob` 로 지정된 대상 설정 파일 */
  file?: string;
}

function parseConfigArgs(args: string[]): ConfigArgs {
  let readOnly = false;
  let edit = false;
  let file: string | undefined;
  const pos: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--') {
      pos.push(...args.slice(i + 1));
      break;
    }
    if (CONFIG_READONLY_FLAGS.has(a)) {
      readOnly = true;
      continue;
    }
    if (a === '--edit' || a === '-e') {
      edit = true;
      continue;
    }
    if (CONFIG_VALUE_FLAGS.has(a)) {
      const v = args[i + 1];
      if (a === '-f' || a === '--file' || a === '--blob') file = v;
      i += 1; // 값 토큰을 소비한다
      continue;
    }
    const eq = a.indexOf('=');
    if (a.startsWith('--') && eq > 0) {
      const k = a.slice(0, eq);
      if (CONFIG_VALUE_FLAGS.has(k)) {
        if (k === '--file' || k === '--blob') file = a.slice(eq + 1);
        continue;
      }
      if (CONFIG_READONLY_FLAGS.has(k)) readOnly = true;
      continue;
    }
    if (a.startsWith('-') && a !== '-') continue;
    pos.push(a);
  }

  return { key: pos[0], value: pos[1], readOnly, edit, file };
}

/** §12.3 승인 필요군 — 금지는 아니나 사용자 승인 없이 실행할 수 없다 (GATE-SPEC §6 G-02 (b)). */
const APPROVAL_REQUIRED = new Set(['worktree', 'branch', 'merge', 'rebase', 'cherry-pick', 'revert', 'push']);

/** 히스토리 재작성·객체 파괴 계열. */
const ESCALATE_SUBCOMMANDS = new Set([
  'filter-branch',
  'filter-repo',
  'update-ref',
  'reflog',
  'prune',
  'gc',
  'replace',
  'notes',
]);

/**
 * porcelain 금지분의 plumbing 등가물 (GATE-SPEC §6 G-02 (d)).
 * `restore`·`switch` 를 `checkout --` 등가물로 잡은 것과 같은 논리다.
 * 리뷰어 C가 `read-tree -u --reset` 로 실제 작업트리 파괴를 확인했다.
 */
const PLUMBING_DESTRUCTIVE: Record<string, { flags: string[]; equiv: string }> = {
  'read-tree': { flags: ['-u', '--reset', '-m'], equiv: 'git reset --hard' },
  'checkout-index': { flags: ['-f', '--force', '-a', '--all'], equiv: 'git checkout -- <path>' },
  // `--refresh` 는 인덱스 stat 정보를 갱신할 뿐 작업 트리를 바꾸지 않는다 — 제외 (리뷰어 C 오탐 지적)
  'update-index': { flags: ['--add', '--force-remove', '--replace'], equiv: 'git add' },
  'sparse-checkout': { flags: ['set', 'disable', 'reapply'], equiv: '작업 트리 구성 변경' },
};

/** 인자를 셸 명령 문자열로 실행하는 git 하위 명령 (GATE-SPEC §6 G-02 (d)). */
/**
 * 토큰 배열을 셸 문자열로 되돌린다.
 *
 * 단순 `join(' ')` 은 인용을 잃어버린다: `git bisect run sh -c "git add ."` 가
 * `sh -c git add .` 이 되어 재귀 시 `sh -c git` 으로 파싱되고 판정이 deny→ask 로
 * 강등됐다 (리뷰어 C 라운드 2). 공백·메타문자를 담은 토큰은 다시 인용한다.
 */
function requote(tokens: string[]): string {
  return tokens
    .map((t) => (/[\s'"$`\\|&;<>()*?[\]{}]/.test(t) || t === '' ? `'${t.split("'").join(`'\\''`)}'` : t))
    .join(' ');
}

/**
 * 셸 명령 문자열로 되돌리되, **토큰이 하나면 그대로 통과**시킨다.
 *
 * `git submodule foreach "git add ."` 는 토크나이즈 후 인자가 `['git add .']`
 * 단일 토큰이다 — 그 자체가 이미 완결된 명령행이다. 여기에 `requote()` 를 걸면
 * 공백을 보고 통째로 인용해 `'git add .'` 한 단어로 만들고, 재귀 시 명령 이름이
 * `git add .` 이 되어 아무 규칙에도 안 걸린다 (라운드 3 회귀, 리뷰어 C).
 */
function joinShell(tokens: string[]): string {
  return tokens.length === 1 ? tokens[0] : requote(tokens);
}

/** 하위 명령 토큰 뒤의 플래그를 건너뛴 나머지 — 실제 명령 문자열 부분. */
function afterSubcommand(args: string[], name: string): string[] {
  let i = args.indexOf(name) + 1;
  while (i < args.length && args[i].startsWith('-') && args[i] !== '--') i += 1;
  if (args[i] === '--') i += 1;
  return args.slice(i);
}

function extractShellStrings(sub: string, args: string[]): string[] | null {
  const pos = args.filter((a) => !a.startsWith('-'));
  const valueOf = (names: string[]): string[] => {
    const out: string[] = [];
    for (let i = 0; i < args.length; i++) {
      const a = args[i];
      for (const nm of names) {
        if (a === nm && args[i + 1] !== undefined) out.push(args[i + 1]);
        else if (a.startsWith(nm + '=')) out.push(a.slice(nm.length + 1));
      }
    }
    return out;
  };

  switch (sub) {
    // 하위 명령 뒤의 플래그(`--recursive`, `--quiet`)를 건너뛰고 명령 문자열부터 자른다.
    // 초판은 플래그를 명령의 일부로 넘겨 `foreach --recursive "git add ."` 가 ask 로 샜다 (리뷰어 C).
    case 'submodule':
      return pos[0] === 'foreach' ? [joinShell(afterSubcommand(args, 'foreach'))] : [];
    case 'bisect':
      return pos[0] === 'run' ? [joinShell(afterSubcommand(args, 'run'))] : [];
    case 'rebase':
      return valueOf(['-x', '--exec']);
    case 'difftool':
    case 'mergetool':
      return valueOf(['-x', '--extcmd']);
    case 'filter-branch':
      return valueOf([
        '--tree-filter',
        '--index-filter',
        '--parent-filter',
        '--msg-filter',
        '--commit-filter',
        '--tag-name-filter',
        '--env-filter',
      ]);
    case 'for-each-repo':
      return valueOf(['--exec', '-e']);
    default:
      return null;
  }
}

interface GitInvocation {
  sub: string;
  args: string[];
  /** `-C` / `--git-dir` / `--work-tree` 로 지정된 경로들 */
  pathOverrides: string[];
  /** `-c key=value` / `--config-env=key=ENV` 로 주입된 설정들 */
  configs: string[];
  /** 명령 앞에 붙은 `VAR=value` 접두들 */
  env: string[];
}

/**
 * 환경변수 lane 판정. `-c` 와 동일한 `checkConfigAssignment` 를 재사용한다 —
 * 판정 함수가 하나여야 세 경로(`-c`·`config`·env)가 같은 규칙을 받는다.
 */
/**
 * `GIT_CONFIG_PARAMETERS` 를 파싱한다. **git 은 두 형식을 모두 받는다.**
 *
 *   구형: `'key=value'`        (쌍 전체를 한 번 인용)
 *   신형: `'key'='value'`      (키와 값을 따로 인용, git 2.31+)
 *
 * 초판은 공백 분리 후 양끝 따옴표만 벗겨서 신형의 키가 `key'` 로 남았고,
 * 꼬리 규칙(`.external` 등)을 전부 빗나갔다. `alias.` 만 접두 검사 덕에
 * **우연히** 걸리고 있었다 (리뷰어 C 라운드 4 실증).
 */
export function parseConfigParameters(raw: string): Array<{ key: string; value?: string }> {
  const out: Array<{ key: string; value?: string }> = [];
  let i = 0;

  const readQuoted = (): string => {
    i += 1; // 여는 따옴표
    let s = '';
    while (i < raw.length) {
      if (raw[i] === "'") {
        if (raw.slice(i, i + 4) === "'\\''") {
          s += "'"; // git 의 작은따옴표 이스케이프
          i += 4;
          continue;
        }
        i += 1;
        return s;
      }
      s += raw[i];
      i += 1;
    }
    return s;
  };
  const readBare = (): string => {
    let s = '';
    while (i < raw.length && !/\s/.test(raw[i]) && raw[i] !== '=') {
      s += raw[i];
      i += 1;
    }
    return s;
  };

  while (i < raw.length) {
    while (i < raw.length && /\s/.test(raw[i])) i += 1;
    if (i >= raw.length) break;

    let key = raw[i] === "'" ? readQuoted() : readBare();
    let value: string | undefined;

    if (raw[i] === '=') {
      i += 1; // 신형 `'k'='v'`
      value = raw[i] === "'" ? readQuoted() : readBare();
    } else {
      const eq = key.indexOf('='); // 구형 `'k=v'`
      if (eq > 0) {
        value = key.slice(eq + 1);
        key = key.slice(0, eq);
      }
    }
    if (key !== '') out.push({ key, value });
  }
  return out;
}

/** 값이 셸 명령처럼 보이는가 — 경로 구분자·메타문자·공백이 있으면 그렇다. */
function looksLikeCommandValue(v: string): boolean {
  return /[/\\\s;|&$`><(){}!*?]/.test(v);
}

function checkEnvLane(env: string[], cwd: string | undefined): Verdict | null {
  if (env.length === 0) return null;
  // POSIX 환경변수는 **대소문자를 구분**한다. `git_editor=` 를 git 은 읽지 않으므로
  // 대문자화하면 과잉 매칭이 된다 (리뷰어 C 라운드 4). 원문 그대로 쓴다.
  const map = new Map<string, string>();
  for (const e of env) {
    const i = e.indexOf('=');
    if (i > 0) map.set(e.slice(0, i), e.slice(i + 1));
  }

  // ── (1) `GIT_CONFIG_KEY_<n>` / `VALUE_<n>` — `-c key=value` 와 완전 등가
  for (const [k, v] of map) {
    const m = k.match(/^GIT_CONFIG_KEY_(\d+)$/);
    if (!m) continue;
    const verdict = checkConfigAssignment(v, map.get(`GIT_CONFIG_VALUE_${m[1]}`), `GIT_CONFIG_KEY_${m[1]}=`);
    if (verdict) return verdict;
  }

  // ── (2) `GIT_CONFIG_PARAMETERS` — 두 형식 모두 파싱
  const params = map.get('GIT_CONFIG_PARAMETERS');
  if (params !== undefined) {
    for (const { key, value } of parseConfigParameters(params)) {
      const verdict = checkConfigAssignment(key, value, 'GIT_CONFIG_PARAMETERS');
      if (verdict) return verdict;
    }
  }

  for (const [name, value] of map) {
    if (!name.startsWith('GIT_')) continue; // git 과 무관한 변수는 관할 밖

    // 위에서 이미 다룬 쌍 주입 경로
    if (/^GIT_CONFIG_(COUNT|KEY_\d+|VALUE_\d+|PARAMETERS)$/.test(name)) continue;

    // ── (3) `GIT_CONFIG*` 가족 — **임의 설정 파일을 통째로 끌어온다.**
    // `include.path`·`includeIf.*`·`init.templateDir` 를 규칙으로 막아 놓고
    // 그 **환경변수 쌍둥이**를 열거에서 빠뜨렸다. 열거는 누락이 필연이므로
    // 이름 가족 전체를 규칙으로 다룬다 (리뷰어 C 라운드 4 실증).
    if (name.startsWith('GIT_CONFIG') || name === 'GIT_TEMPLATE_DIR') {
      return deny(
        `\`${name}=…\` 는 git 이 읽는 **설정 파일·템플릿 경로 전체를 갈아끼운다.** ` +
          '그 파일에 `[alias] zz = !git add .` 한 줄만 있으면 G-02 금지 목록 전체가 우회된다 ' +
          '(GATE-SPEC §6 G-02 (d), 리뷰어 C 실증). `include.path`·`init.templateDir` 의 환경변수 쌍둥이다.',
        '설정 파일을 바꾸지 말고 의도한 git 명령을 그대로 실행하라.',
      );
    }

    // ── (4) 값이 외부 명령으로 실행되는 변수 — 이름 꼬리로 판정한다
    if (ENV_EXEC_TAIL.test(name)) {
      // 값 인식: `GIT_PAGER=cat`·`GIT_EDITOR=true` 는 매우 흔한 관용구다.
      // 셸 메타문자·경로가 없으면 하드 거부 대신 사용자 판단으로 넘긴다 (§3.3).
      if (!looksLikeCommandValue(value)) {
        return ask(`\`${name}=${value}\` 는 git 이 실행하는 외부 명령을 지정한다. 단순 명령명이라 ask 로 올린다.`);
      }
      return deny(
        `\`${name}=…\` 는 git 이 외부 명령으로 실행하는 환경변수이고 값이 셸 명령 형태다 — ` +
          '`-c` 의 exec 설정 키와 등가이며 **G-02 통제 전체에 대한 병렬 우회로**다 (GATE-SPEC §6 G-02 (d)).',
        '환경변수로 명령을 주입하지 말고 의도한 git 명령을 그대로 실행하라.',
      );
    }

    // ── (5) 저장소 위치를 바꾸는 변수 — `-C` 와 같은 containment 검사
    if (ENV_PATH.has(name)) {
      const c = containment(value, cwd);
      if (c === 'outside') {
        return deny(
          `\`${name}=${value}\` 는 샤드 worktree 밖을 가리킨다 — \`git -C\` 우회와 동일하다 (GATE-SPEC §5).`,
          '자기 샤드 worktree 안에서 실행하라.',
        );
      }
      if (c === 'unknown') return ask(`\`${name}=${value}\` 가 현재 샤드 안인지 판정할 수 없다.`);
    }
  }

  return null;
}

function parseGit(args: string[], env: string[]): GitInvocation | null {
  const pathOverrides: string[] = [];
  const configs: string[] = [];
  let i = 0;
  while (i < args.length) {
    const a = args[i];
    if (GIT_GLOBAL_WITH_VALUE.has(a)) {
      const v = args[i + 1];
      if (v !== undefined) {
        if (a === '-C' || a === '--work-tree' || a === '--git-dir') pathOverrides.push(v);
        if (a === '-c' || a === '--config-env') configs.push(v);
      }
      i += 2;
      continue;
    }
    const eq = a.indexOf('=');
    if (a.startsWith('--') && eq > 0) {
      const key = a.slice(0, eq);
      if (GIT_GLOBAL_WITH_VALUE.has(key)) {
        const v = a.slice(eq + 1);
        if (key === '--work-tree' || key === '--git-dir') pathOverrides.push(v);
        if (key === '--config-env') configs.push(v);
        i += 1;
        continue;
      }
    }
    if (GIT_GLOBAL_FLAGS.has(a)) {
      i += 1;
      continue;
    }
    if (a.startsWith('-')) {
      // --version / --help 등 하위 명령 없이 끝나는 형태
      i += 1;
      continue;
    }
    break;
  }
  if (i >= args.length) return null;
  return { sub: args[i], args: args.slice(i + 1), pathOverrides, configs, env };
}

/** 인자에서 플래그가 아닌 값(pathspec 후보)만 뽑는다. `--` 이후는 전부 경로로 본다. */
function positionals(args: string[]): string[] {
  const out: string[] = [];
  let afterDD = false;
  for (const a of args) {
    if (!afterDD && a === '--') {
      afterDD = true;
      continue;
    }
    if (!afterDD && a.startsWith('-') && a !== '-') continue;
    out.push(a);
  }
  return out;
}

function deny(reason: string, next: string): Verdict {
  return { decision: 'deny', rule: RULE, reason, next };
}
function ask(reason: string): Verdict {
  return { decision: 'ask', rule: RULE, reason };
}
const ALLOW: Verdict = { decision: 'allow' };

const SEVERITY: Record<Verdict['decision'], number> = { allow: 0, ask: 1, deny: 2 };

function worse(a: Verdict, b: Verdict): Verdict {
  return SEVERITY[b.decision] > SEVERITY[a.decision] ? b : a;
}

interface SegmentEnv {
  ctx: GitGuardContext;
  recurse: (command: string) => Verdict;
}

/** pathspec 목록을 판정한다. 전부 명시 경로면 null. */
function checkPathspecs(sub: string, paths: string[], cwd: string | undefined): Verdict | null {
  for (const p of paths) {
    switch (classifyPathspec(p, cwd)) {
      case 'bulk':
        return deny(
          `\`git ${sub} ${p}\` 는 정규화하면 worktree 전체를 가리킨다 (workflow §12.1). ` +
            '의도하지 않은 파일·비밀정보가 함께 처리된다.',
          '대상 파일 경로를 하나씩 명시하라. 예: `git add src/gitguard.ts src/secrets.ts`',
        );
      case 'glob':
        return deny(
          `\`git ${sub} ${p}\` 는 와일드카드 pathspec 이라 대상이 확정되지 않는다 (G-02).`,
          '전개된 실제 파일 경로를 하나씩 명시하라.',
        );
      case 'escape':
        return deny(
          `\`git ${sub} ${p}\` 는 샤드 worktree 밖을 가리킨다 (GATE-SPEC §5).`,
          '자기 샤드 소유 경로만 대상으로 하라. 다른 샤드 파일이 필요하면 PM에게 요청하라 (workflow §2-14).',
        );
      case 'unknown':
        return ask(`\`git ${sub} ${p}\` 의 인자가 변수라 대상을 정적으로 판정할 수 없다.`);
      default:
        break;
    }
  }
  return null;
}

function checkGitSegment(inv: GitInvocation, env: SegmentEnv): Verdict {
  const { ctx } = env;
  const { sub, args } = inv;
  const paths = positionals(args);
  const hasDD = args.includes('--');
  const inIntegrate = ctx.cwd ? isIntegrationWorktree(ctx.cwd, ctx.integrateSuffixes, ctx.integrateRoots) : false;

  // ── 환경변수 lane — `-c`/`git config` 와 동일 규칙 (리뷰어 C 라운드 3)
  const envVerdict = checkEnvLane(inv.env, ctx.cwd);
  if (envVerdict) return envVerdict;

  // ── `-c <key>=<value>` 로 외부 명령을 주입하는 경로 (범용 우회)
  for (const cfg of inv.configs) {
    const eq = cfg.indexOf('=');
    const rawKey = eq >= 0 ? cfg.slice(0, eq) : cfg;
    const value = eq >= 0 ? cfg.slice(eq + 1) : undefined;
    const v = checkConfigAssignment(rawKey, value, 'git -c');
    if (v) return v;
  }

  // ── `-C` / `--work-tree` / `--git-dir` 경로 이탈
  for (const p of inv.pathOverrides) {
    const c = containment(p, ctx.cwd);
    if (c === 'outside') {
      return deny(
        `git 전역 옵션으로 샤드 worktree 밖 경로를 지정했다 (${p}). cd 우회와 동일한 효과다.`,
        '자기 샤드 worktree 안에서 실행하라. 다른 샤드의 파일이 필요하면 PM에게 소유권 변경을 요청하라 (workflow §2-14).',
      );
    }
    if (c === 'unknown') {
      return ask(`git 전역 옵션 경로(${p})가 현재 샤드 안인지 판정할 수 없다.`);
    }
  }

  // ── 하위 명령 자체가 변수 (`G=add; git $G .`)
  // 초판은 인자·명령이름이 변수면 ask 였는데 하위 명령만 무검사였다 (비대칭, 리뷰어 C 발견).
  if (sub.includes('$')) {
    return ask(`git 하위 명령이 변수(\`${sub}\`)라 무엇이 실행될지 정적으로 판정할 수 없다.`);
  }

  // ── 인자를 셸 명령으로 실행하는 하위 명령 → 그 문자열을 재귀 검사
  const shellStrings = extractShellStrings(sub, args);
  if (shellStrings !== null && shellStrings.length > 0) {
    let v: Verdict = ask(
      `\`git ${sub}\` 는 인자를 셸 명령으로 실행한다 (GATE-SPEC §6 G-02 (d)). 실행될 내용을 사용자가 확인해야 한다.`,
    );
    for (const s of shellStrings) v = worse(v, env.recurse(s));
    return v;
  }

  // ── plumbing 등가물
  const plumb = PLUMBING_DESTRUCTIVE[sub];
  if (plumb) {
    const hit = plumb.flags.find((f) => args.includes(f) || (/^-[A-Za-z]$/.test(f) && hasShortFlag(args, f.slice(1))));
    if (hit) {
      return deny(
        `\`git ${sub} ${hit}\` 는 \`${plumb.equiv}\` 와 동일한 파괴 효과를 낸다 (GATE-SPEC §6 G-02 (d), 리뷰어 C 실증).`,
        'porcelain 금지분과 같은 규칙이 적용된다. 되돌리기가 필요하면 PM에게 보고하라.',
      );
    }
    return ask(`\`git ${sub}\` 는 plumbing 명령이라 작업 트리·인덱스를 직접 조작할 수 있다.`);
  }

  switch (sub) {
    case 'stash': {
      const first = paths[0];
      if (first === 'list' || first === 'show') {
        return ask(`\`git stash ${first}\` 는 읽기 전용이지만 §12.1의 stash 금지 대상에 이름이 걸린다.`);
      }
      return deny(
        '`git stash` 는 전면 금지다 (workflow §12.1). 작업 내용이 보이지 않는 곳으로 숨겨져 유실·중복 작업의 원인이 된다.',
        '변경을 남겨둔 채 진행하거나, 필요하면 별도 브랜치에 커밋하라. 되돌리기가 필요하면 PM에게 보고하라.',
      );
    }

    case 'config': {
      // 영속 설정 변경. `-c`(1회성)와 **같은 규칙**을 적용한다 — 위험이 같고,
      // 영속형이 오히려 더 나쁘다. 2판은 이 분기가 없어 `default` 로 떨어져
      // `git config alias.zz '!git add .'` 가 무검사 통과했다 (리뷰어 C 실증).
      const cfg = parseConfigArgs(args);
      if (cfg.edit) {
        return deny(
          '`git config --edit` 는 `GIT_EDITOR` 로 지정된 임의 명령을 실행한다 (GATE-SPEC §6 G-02 (d)).',
          '설정을 봐야 하면 `git config --list` 로 조회하라. 편집은 사용자가 직접 한다.',
        );
      }
      if (cfg.readOnly) return ALLOW;
      if (cfg.key === undefined) return ALLOW; // `git config --list` 등
      const v = checkConfigAssignment(cfg.key, cfg.value, 'git config');
      if (v) return v;
      if (args.includes('--unset') || args.includes('--unset-all') || args.includes('--remove-section')) {
        return ask(`\`git config --unset ${cfg.key}\` 는 설정을 영속 제거한다.`);
      }
      return ask(
        `\`git config ${cfg.key}\`${cfg.file ? ` (대상 파일 ${cfg.file})` : ''} 는 설정을 영속 변경한다. ` +
          '게이트 동작에 영향을 줄 수 있다.',
      );
    }

    case 'reset':
      return deny(
        '`git reset` 은 전면 금지다 (workflow §12.1). 스테이징·커밋 이력을 되돌려 증거를 소멸시킨다.',
        '잘못 스테이징했다면 그대로 두고 PM에게 보고하라. 히스토리 조작은 사용자만 수행한다.',
      );

    case 'clean':
      return deny(
        '`git clean` 은 전면 금지다 (workflow §12.1). 추적되지 않는 산출물을 복구 불가능하게 삭제한다.',
        '지워야 할 파일이 있으면 경로를 명시해 개별 삭제하고 그 사실을 Proceedings에 남겨라.',
      );

    case 'checkout': {
      if (hasDD) {
        return deny(
          '`git checkout -- <path>` 는 금지다 (workflow §12.1). 작업 트리의 변경을 복구 불가능하게 폐기한다.',
          '변경을 되돌려야 하면 PM에게 보고하고 승인을 받아라.',
        );
      }
      if (hasShortFlag(args, 'f') || args.includes('--force')) {
        return deny(
          '`git checkout --force` 는 작업 트리 변경을 폐기하므로 `checkout -- <path>` 와 동치다 (G-02).',
          '강제 전환 없이 브랜치를 전환하거나, 필요하면 PM에게 보고하라.',
        );
      }
      for (const p of paths) {
        const kind = classifyPathspec(p, ctx.cwd);
        if (kind === 'bulk' || kind === 'glob') {
          return deny(
            `\`git checkout ${p}\` 는 정규화하면 작업 트리 전체를 폐기한다 (G-02).`,
            '변경을 되돌려야 하면 PM에게 보고하고 승인을 받아라.',
          );
        }
      }
      // `git checkout src/foo.ts` — 브랜치명인지 경로인지 정적으로 구분 불가
      if (paths.length === 1 && /\.[A-Za-z0-9]{1,8}$/.test(paths[0])) {
        return ask(
          `\`git checkout ${paths[0]}\` 의 인자가 브랜치명인지 파일 경로인지 판정할 수 없다. 파일이면 변경이 폐기된다.`,
        );
      }
      return ALLOW;
    }

    case 'restore': {
      const stagedOnly =
        (args.includes('--staged') || hasShortFlag(args, 'S')) &&
        !args.includes('--worktree') &&
        !hasShortFlag(args, 'W');
      if (stagedOnly) {
        return ask('`git restore --staged` 는 스테이징만 해제하지만 §12.1이 금지한 `reset` 과 효과가 겹친다.');
      }
      return deny(
        '`git restore` 는 `git checkout -- <path>` 와 동일하게 작업 트리 변경을 폐기한다 (G-02).',
        '변경을 되돌려야 하면 PM에게 보고하고 승인을 받아라.',
      );
    }

    case 'switch': {
      if (args.includes('--discard-changes') || hasShortFlag(args, 'f') || args.includes('--force')) {
        return deny(
          '`git switch --discard-changes` 는 작업 트리 변경을 폐기한다 (G-02).',
          '변경을 보존한 채 전환하거나 PM에게 보고하라.',
        );
      }
      return ALLOW;
    }

    case 'push': {
      if (
        hasShortFlag(args, 'f') ||
        args.some(
          (a) =>
            a === '--force' ||
            a === '--force-with-lease' ||
            a.startsWith('--force-with-lease=') ||
            a === '--force-if-includes',
        )
      ) {
        return deny(
          '`git push --force` / `--force-with-lease` 는 전면 금지다 (workflow §12.1). 원격 이력을 파괴한다.',
          '충돌은 merge 로 해소하라. 강제 푸시가 정말 필요하면 사용자에게 직접 요청하라.',
        );
      }
      for (const p of paths) {
        if (p.startsWith('+') && p.length > 1) {
          return deny(
            `refspec \`${p}\` 의 선행 \`+\` 는 강제 푸시와 동일하다 (G-02).`,
            '`+` 없는 refspec 을 사용하라.',
          );
        }
      }
      break; // §12.3 승인 필요군 공통 처리로 떨어진다
    }

    case 'add':
    case 'stage': {
      if (args.includes('-A') || args.includes('--all') || hasShortFlag(args, 'A')) {
        return deny(
          '`git add -A` / `--all` 는 금지다 (workflow §12.1). 의도하지 않은 파일·비밀정보가 함께 스테이징된다.',
          '스테이징할 파일 경로를 하나씩 명시하라. 예: `git add src/gitguard.ts src/secrets.ts`',
        );
      }
      const bad = checkPathspecs('add', paths, ctx.cwd);
      if (bad) return bad;
      if (paths.length === 0) {
        return deny(
          '`git add` 에 명시 경로 인자가 없다 (workflow §12.1). `-u` 등 암묵적 전체 스테이징도 같은 이유로 금지다.',
          '스테이징할 파일 경로를 하나 이상 명시하라. 예: `git add src/gitguard.ts`',
        );
      }
      // §12.3 역할 제한 — 커밋하지 않는 샤드가 스테이징할 이유가 없다.
      // 하드 거부하면 정상 진단 흐름이 끊기므로 `ask` (GATE-SPEC §6 G-02 (c)).
      if (!inIntegrate) {
        return ask(
          '`git add` 는 통합 담당 worktree 의 작업이다 (workflow §12.3). ' +
            '구현자 샤드에서 스테이징할 이유가 있는지 사용자가 확인해야 한다.',
        );
      }
      return ALLOW;
    }

    case 'rm': {
      const bad = checkPathspecs('rm', paths, ctx.cwd);
      if (bad) return bad;
      if (paths.length === 0) {
        return deny('`git rm` 에 명시 경로 인자가 없다 (G-02).', '삭제할 파일 경로를 명시하라.');
      }
      return ask('`git rm` 은 작업 트리에서 파일을 삭제한다. 소유권 검사(G-01)가 보지 못하는 삭제 경로다.');
    }

    case 'mv': {
      const bad = checkPathspecs('mv', paths, ctx.cwd);
      if (bad) return bad;
      return ask('`git mv` 는 파일을 이동한다. 소유권 검사(G-01)가 보지 못하는 경로 변경이다.');
    }

    case 'commit':
    case 'apply':
    case 'am': {
      if (sub === 'commit' && (hasShortFlag(args, 'a') || args.includes('--all'))) {
        return deny(
          '`git commit -a` 는 추적 파일 전체를 암묵 스테이징하므로 `git add -A` 와 동치다 (workflow §12.1).',
          '`git add <경로>` 로 파일을 명시해 스테이징한 뒤 `-a` 없이 커밋하라.',
        );
      }
      if (args.includes('--no-verify') || hasShortFlag(args, 'n')) {
        return deny(
          `\`git ${sub} --no-verify\` 는 훅을 건너뛴다 — 게이트 우회 시도로 취급한다 (G-02).`,
          '훅이 실패하면 원인을 고쳐라. 훅을 끄고 커밋하지 않는다.',
        );
      }
      if (!ctx.cwd) {
        // fail-closed: 통합 worktree 여부를 판정할 근거가 없다 (GATE-SPEC §4)
        return deny(
          `\`git ${sub}\` 은 통합 담당 worktree 에서만 허용되는데 (workflow §2-3, §12.3) cwd 가 주어지지 않아 판정할 수 없다.`,
          '게이트 호출자가 payload 의 cwd 를 전달하도록 수정하라. 구현자는 커밋하지 않는다.',
        );
      }
      // roots 미주입 = 판정 근거 없음. **근거가 없을 때는 권한을 주지 않는다** (§4 fail-closed).
      // 라운드 2는 접미사 heuristic 으로 폴백해 권한을 *주는* 방향이었다 — 방향이 반대였다
      // (리뷰어 C 라운드 3). 이름만으로 구분 불가하다는 논거는 옳지만 결론은 폴백 거부다.
      if (!ctx.integrateRoots || ctx.integrateRoots.length === 0) {
        return deny(
          `\`git ${sub}\` 의 통합 worktree 판정 근거(\`integrateRoots\`)가 주입되지 않았다. ` +
            '디렉터리 이름만으로는 진짜 통합 worktree 와 이름이 같은 임의 경로를 구분할 수 없다.',
          '게이트 호출자가 `CONTROL.yaml identity.map` 에서 통합 worktree 절대 경로를 읽어 ' +
            '`integrateRoots` 로 주입해야 한다. 그전까지 커밋은 사용자가 직접 수행한다.',
        );
      }
      if (!inIntegrate) {
        return deny(
          `\`git ${sub}\` 은 통합 담당 worktree 에서만 허용된다 (workflow §2-3, §12.3). 현재 cwd=${ctx.cwd}`,
          '구현자는 커밋하지 않는다. 작업을 마치면 PM에게 보고하고 통합 담당이 커밋하게 하라.',
        );
      }
      if (args.includes('--amend')) {
        return ask('`git commit --amend` 는 통합 worktree 라도 직전 커밋 이력을 재작성한다.');
      }
      return ALLOW;
    }

    default:
      break;
  }

  // ── §12.3 승인 필요군 (GATE-SPEC §6 G-02 (b))
  // 초판은 §12.1만 보고 작성해 이 명령군이 전부 무검사 통과였다 (PM 명세 결함).
  if (APPROVAL_REQUIRED.has(sub)) {
    // 순수 조회는 승인 대상이 아니다 (리뷰어 C 오탐 지적).
    // `git branch` / `-a` / `--list` / `-v` / `--show-current`, `git worktree list`
    if (sub === 'branch') {
      const mutating =
        paths.length > 0 ||
        args.some((a) =>
          /^(-[dDmMcC]|--delete|--move|--copy|--edit-description|--set-upstream-to|--unset-upstream|--force)/.test(a),
        );
      if (!mutating) return ALLOW;
    }
    if (sub === 'worktree' && (paths[0] === 'list' || paths.length === 0)) return ALLOW;
    return ask(
      `\`git ${sub}\` 는 §12.3 승인 필요군이다. 브랜치·원격·worktree 상태를 바꾸므로 사용자 승인 없이 실행하지 않는다.`,
    );
  }

  if (ESCALATE_SUBCOMMANDS.has(sub)) {
    if (sub === 'reflog' && !paths.some((p) => p === 'delete' || p === 'expire')) return ALLOW;
    if (sub === 'gc' && !args.some((a) => a.startsWith('--prune'))) return ALLOW;
    if (sub === 'notes' && !paths.some((p) => p === 'remove' || p === 'prune')) return ALLOW;
    return ask(`\`git ${sub}\` 는 금지 목록에 없으나 이력을 재작성하거나 객체를 파괴할 수 있다.`);
  }

  return ALLOW;
}

/* ------------------------------------------------------------------ *
 * 4. git 이외 — 승인 위조 / 경로 이탈 / 간접 실행
 * ------------------------------------------------------------------ */

const HARNESS_PRIVILEGED = new Set(['approve', 'resume', 'mode']);

function checkHarnessSegment(args: string[]): Verdict {
  const sub = args.find((a) => !a.startsWith('-'));
  if (sub === undefined) return ALLOW;
  if (HARNESS_PRIVILEGED.has(sub)) {
    return deny(
      `\`harness ${sub}\` 는 에이전트가 실행할 수 없다 (GATE-SPEC §6 G-04/G-06). 승인·모드 변경은 사용자 터미널에서만 성립한다.`,
      `사용자에게 승인을 요청하라. 사용자가 직접 터미널에서 \`harness ${sub} <ID>\` 를 실행한다.`,
    );
  }
  return ALLOW; // `harness status` 등 읽기 전용
}

function checkCdSegment(args: string[], ctx: GitGuardContext): Verdict {
  const target = args.find((a) => !a.startsWith('-'));
  if (target === undefined) {
    const dash = args.includes('-');
    return deny(
      dash
        ? '`cd -` 는 직전 디렉터리로 되돌아가 샤드 worktree 를 벗어날 수 있다 (GATE-SPEC §5).'
        : '인자 없는 `cd` 는 홈 디렉터리로 이동해 샤드 worktree 를 벗어난다 (GATE-SPEC §5).',
      '샤드 worktree 안의 상대 경로만 사용하라.',
    );
  }
  const c = containment(target, ctx.cwd);
  if (c === 'outside') {
    return deny(
      `\`cd ${target}\` 는 샤드 worktree 를 벗어난다 (GATE-SPEC §5, workflow §12.4). 소유권 검사(G-01)를 우회하는 경로다.`,
      '자기 샤드 worktree 안에서만 작업하라. 다른 샤드의 파일이 필요하면 PM에게 소유권 변경을 요청하라 (workflow §2-14).',
    );
  }
  if (c === 'unknown') {
    return ask(`\`cd ${target}\` 의 대상이 현재 샤드 안인지 판정할 수 없다 (변수 전개 또는 cwd 미제공).`);
  }
  return ALLOW;
}

/**
 * `-c` 뒤의 명령 문자열을 찾는다.
 * `bash -c -- "cmd"` 의 `--` 를 건너뛴다 — 초판은 옵션 종료 처리를 놓쳤다 (리뷰어 C).
 */
function shellCommandString(args: string[]): string | null {
  const ci = args.findIndex((a) => a === '-c' || (/^-[A-Za-z]+$/.test(a) && a.slice(1).includes('c')));
  if (ci < 0) return null;
  let j = ci + 1;
  while (j < args.length && args[j] === '--') j += 1;
  return args[j] ?? null;
}

/* ------------------------------------------------------------------ *
 * 5. 진입점
 * ------------------------------------------------------------------ */

/**
 * Bash 명령 문자열 하나를 검사한다.
 *
 * 복합 명령은 전부 분해해 세그먼트별로 검사하고, 가장 심각한 판정을 돌려준다
 * (`deny` > `ask` > `allow`).
 */
export function checkGitCommand(command: string, ctx: GitGuardContext = {}): Verdict {
  return checkCommandAtDepth(command, ctx, 0);
}

const MAX_DEPTH = 4;

function checkCommandAtDepth(command: string, ctx: GitGuardContext, depth: number): Verdict {
  if (typeof command !== 'string' || command.trim() === '') return ALLOW;
  if (depth > MAX_DEPTH) {
    return ask('명령 중첩이 너무 깊어 끝까지 해석하지 못했다 (`bash -c` / `eval` 중첩).');
  }

  let worst: Verdict = ALLOW;
  const record = (v: Verdict) => {
    worst = worse(worst, v);
  };
  const recurse = (s: string): Verdict => checkCommandAtDepth(s, ctx, depth + 1);

  for (const rawSegment of tokenizeShell(command)) {
    const seg = commandInfo(rawSegment);
    const { name, args } = seg;
    if (name === '') continue;

    // 명령 자체가 변수 — 정적으로 해석 불가
    if (name.startsWith('$')) {
      record(ask(`명령 이름이 변수(\`${name}\`)라 무엇이 실행될지 정적으로 판정할 수 없다.`));
      continue;
    }

    // ── 셸 재호출 (GATE-SPEC §6 G-02 (d))
    if (SHELLS.has(name)) {
      const cmd = shellCommandString(args);
      if (cmd !== null) {
        record(recurse(cmd));
        continue;
      }
      // herestring `bash <<< "git add ."` — 리다이렉션 제거 전 원본에서 찾는다
      const hs = rawSegment.indexOf('<<<');
      if (hs >= 0 && rawSegment[hs + 1] !== undefined) {
        record(recurse(rawSegment[hs + 1]));
        continue;
      }
      // `echo … | bash`, `bash script.sh` — 실행될 내용을 볼 수 없다.
      // **여기서 ask 를 내지 않는다.** 불투명한 실행 경로는 "무엇을 실행할 수 있는가"의
      // 문제이고 그것은 `G-11`(Bash 화이트리스트, S0) 관할이다. G-02 가 먼저 ask 를 내면
      // 체인에서 G-11 을 가로채 판정 근거가 G-02 로 잘못 귀속된다 (gate.ts §체인 순서).
      // G-02 는 **git 위반이 실제로 보일 때만** 발언한다.
      continue;
    }

    if (name === 'eval') {
      record(recurse(args.join(' ')));
      continue;
    }

    // `source x.sh` — 내용 불투명. G-11 관할이므로 G-02 는 침묵한다 (위 주석 참조).
    if (name === 'source' || name === '.') continue;

    // 별칭 정의는 이후 명령의 정체를 바꾼다 — 정적 추적 대상 밖
    if (name === 'alias') {
      record(ask('`alias` 정의는 이후 명령의 실체를 바꾸므로 게이트가 추적할 수 없다.'));
      continue;
    }

    // ── 비셸 인터프리터·원격 실행·빌드 도구 (GATE-SPEC §6 G-02 (d) 6행)
    //
    // `python -c` `perl -e` `ssh` `su -c` `make` `npm run` 은 전부 **불투명한 실행 경로**다.
    // 명세 (d)는 이들을 `ask` 로 올리라고 하지만, 그 판정은 `G-11`(Bash 화이트리스트)이
    // 이미 수행하고 **S0가 E2E로 검증**하고 있다. 두 게이트가 같은 명령에 ask 를 내면
    // 체인이 먼저 만난 쪽으로 귀속되어 감사 기록의 규칙 번호가 흔들린다.
    //
    // 경계: **G-11 = 무엇을 실행할 수 있는가 / G-02 = 허용된 git 명령의 의미.**
    // 따라서 G-02 는 코드 문자열이 **보일 때만** 재귀 검사해서 발언하고,
    // 보이지 않으면 침묵한다. `bash -c "git add ."` 는 보이므로 여전히 G-02 가 거부한다.
    if (
      INTERPRETERS.has(name) ||
      RUNTIMES.has(name) ||
      name === 'ssh' ||
      name === 'su' ||
      name === 'docker' ||
      name === 'kubectl' ||
      name === 'make' ||
      name === 'gradle' ||
      name === 'mvn' ||
      name === 'npm' ||
      name === 'yarn' ||
      name === 'pnpm'
    ) {
      continue;
    }

    if (name === 'git') {
      const inv = parseGit(args, seg.env);
      if (inv === null) continue; // `git --version` 등
      record(checkGitSegment(inv, { ctx, recurse }));
      continue;
    }

    if (name === 'harness') {
      record(checkHarnessSegment(args));
      continue;
    }

    if (name === 'cd' || name === 'pushd' || name === 'chdir') {
      record(checkCdSegment(args, ctx));
      continue;
    }
  }

  return worst;
}
