/**
 * G-02 gitguard 테스트 — CYCLE-20260726-00 / S1 / TASK-GATE-002
 *
 * 러너: node:test (`node --test test/gitguard.test.ts`).
 * Node 22.18+ 는 타입 스트리핑이 기본 활성이라 별도 트랜스파일 없이 실행된다.
 * S0 가 다른 러너를 확정하면 import 확장자만 조정하면 된다 (통합 시 확인 요청 사항).
 */

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import {
  checkGitCommand,
  classifyPathspec,
  isIntegrationWorktree,
  parseConfigParameters,
  tokenizeShell,
  type Verdict,
} from '../src/gitguard.ts';
import { scanSecrets } from '../src/secrets.ts';

const HERE = dirname(fileURLToPath(import.meta.url));

/** 샤드 구현자의 전형적 cwd. 통합 worktree 가 아니다. */
const SHARD_CWD = '/mnt/c/workspace/infraeye3-s1';
const INTEGRATE_CWD = '/mnt/c/workspace/infraeye3-integrate';

/**
 * 통합 worktree 의 **절대 경로 주입**.
 *
 * `commit`/`apply` 는 `integrateRoots` 가 없으면 fail-closed 로 거부한다 —
 * 판정 근거가 없을 때 권한을 주는 쪽이 아니라 막는 쪽이 §4다 (리뷰어 C 라운드 3).
 * 따라서 커밋 허용을 기대하는 테스트는 **반드시 roots 를 주입해야 한다.**
 */
const INTEGRATE_ROOTS = [INTEGRATE_CWD];
type ExtraCtx = { integrateRoots?: string[]; integrateSuffixes?: string[] };

const run = (cmd: string, cwd: string = SHARD_CWD, extra: ExtraCtx = {}): Verdict =>
  checkGitCommand(cmd, { cwd, ...extra });

function assertDeny(cmd: string, cwd: string = SHARD_CWD, extra: ExtraCtx = {}) {
  const v = run(cmd, cwd, extra);
  assert.equal(v.decision, 'deny', `deny 를 기대했으나 ${v.decision}: ${cmd}`);
  if (v.decision !== 'deny') return;
  // AC-6: 사유 + 규칙번호 + 다음 조치
  assert.equal(v.rule, 'G-02', `규칙번호가 G-02 가 아니다: ${cmd}`);
  assert.ok(v.reason.length > 10, `사유가 비어 있다: ${cmd}`);
  assert.ok(v.next.length > 10, `다음 조치가 비어 있다: ${cmd}`);
}

function assertAllow(cmd: string, cwd: string = SHARD_CWD, extra: ExtraCtx = {}) {
  const v = run(cmd, cwd, extra);
  assert.equal(v.decision, 'allow', `allow 를 기대했으나 ${v.decision}: ${cmd}`);
}

function assertAsk(cmd: string, cwd: string = SHARD_CWD, extra: ExtraCtx = {}) {
  const v = run(cmd, cwd, extra);
  assert.equal(v.decision, 'ask', `ask 를 기대했으나 ${v.decision}: ${cmd}`);
}

/* ------------------------------------------------------------------ *
 * 토크나이저
 * ------------------------------------------------------------------ */

test('tokenizeShell: 공백 변형을 하나의 토큰 목록으로 정규화한다', () => {
  assert.deepEqual(tokenizeShell('git   add   .'), [['git', 'add', '.']]);
  assert.deepEqual(tokenizeShell('git\tadd\t.'), [['git', 'add', '.']]);
});

test('tokenizeShell: 인용부호를 해제한다', () => {
  assert.deepEqual(tokenizeShell('git add "."'), [['git', 'add', '.']]);
  assert.deepEqual(tokenizeShell("git add '.'"), [['git', 'add', '.']]);
  assert.deepEqual(tokenizeShell('git add "-A"'), [['git', 'add', '-A']]);
});

test('tokenizeShell: 복합 명령을 세그먼트로 분해한다', () => {
  assert.deepEqual(tokenizeShell('a && b ; c | d || e'), [['a'], ['b'], ['c'], ['d'], ['e']]);
  assert.deepEqual(tokenizeShell('echo $(git stash)'), [['echo'], ['git', 'stash']]);
  assert.deepEqual(tokenizeShell('echo `git reset`'), [['echo'], ['git', 'reset']]);
  assert.deepEqual(tokenizeShell('(cd src && git add .)'), [['cd', 'src'], ['git', 'add', '.']]);
});

test('tokenizeShell: 주석과 리다이렉션을 분리한다', () => {
  assert.deepEqual(tokenizeShell('git status # 확인'), [['git', 'status']]);
  assert.deepEqual(tokenizeShell('git add . > /dev/null'), [['git', 'add', '.', '>', '/dev/null']]);
});

/* ------------------------------------------------------------------ *
 * 거부 — 게이트별 3건 이상 (AC-2)
 * ------------------------------------------------------------------ */

test('G-02 거부: git add 전체 스테이징 변형', () => {
  for (const cmd of [
    'git add .',
    'git   add   .',
    'git add "."',
    "git add '.'",
    'git add ./',
    'git add -A',
    'git add --all',
    'git add *',
    'git add :/',
    'git add -- .',
    'git add',
    'git add -u',
    'git add src/*.ts',
    'git stage .',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: stash / reset / clean', () => {
  for (const cmd of [
    'git stash',
    'git stash push -m wip',
    'git stash pop',
    'git reset',
    'git reset --hard HEAD~1',
    'git reset --soft HEAD~1',
    'git clean -fd',
    'git clean -fdx',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: checkout -- <path> 및 등가 형태', () => {
  for (const cmd of [
    'git checkout -- .',
    'git checkout -- src/gate.ts',
    'git checkout .',
    'git checkout --force main',
    'git checkout -f main',
    'git restore src/gate.ts',
    'git switch --discard-changes main',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: 강제 푸시', () => {
  for (const cmd of [
    'git push --force',
    'git push -f origin main',
    'git push --force-with-lease origin main',
    'git push --force-with-lease=main:main origin',
    'git push --force-if-includes origin main',
    'git push origin +main',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: 복합 명령 체인에 숨긴 금지 명령', () => {
  for (const cmd of [
    'npm test && git add .',
    'echo hi ; git add -A',
    'git status | grep foo ; git add .',
    'false || git add --all',
    'git status && npm run build && git add . && echo done',
    '(cd src && git add .)',
    'echo $(git stash)',
    'echo `git reset --hard`',
    'git status\ngit clean -fd',
    'git add . > /dev/null 2>&1',
    'git add . # 이건 그냥 편의상',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: 래퍼·절대경로·환경변수로 감싼 형태', () => {
  for (const cmd of [
    'sudo git add .',
    'env GIT_DIR=.git git add -A',
    '/usr/bin/git add .',
    'FOO=bar git clean -fdx',
    'git -C . add .',
    'git --no-pager add -A',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: harness 승인 위조 시도', () => {
  for (const cmd of [
    'harness approve CYCLE-20260726-00',
    'harness resume',
    'harness mode RUNNING',
    'node dist/harness.cjs approve CYCLE-20260726-00',
    'npx harness approve CYCLE-20260726-00',
    './bin/harness approve CYCLE-20260726-00',
    'npm test && harness approve CYCLE-20260726-00',
  ]) {
    assertDeny(cmd);
  }
});

test('G-02 거부: 샤드 worktree 경로 이탈', () => {
  for (const cmd of [
    'cd ../infraeye3-s0 && echo x',
    'cd ../../ && ls',
    'cd /mnt/c/workspace/infraeye3-s0 && npm test',
    'cd',
    'cd ~',
    'cd -',
    'pushd ../infraeye3-s2',
    'git -C ../infraeye3-s0 status',
    'git --work-tree=/mnt/c/workspace/infraeye3-s0 status',
  ]) {
    assertDeny(cmd);
  }
});

/* ------------------------------------------------------------------ *
 * git commit — 통합 worktree 한정
 * ------------------------------------------------------------------ */

test('G-02: git commit 은 통합 worktree 에서만 허용된다', () => {
  assertDeny('git commit -m "feat: x"', SHARD_CWD, { integrateRoots: INTEGRATE_ROOTS });
  assertDeny('git commit', SHARD_CWD, { integrateRoots: INTEGRATE_ROOTS });
  assertAllow('git commit -m "feat: x"', INTEGRATE_CWD, { integrateRoots: INTEGRATE_ROOTS });
});

/**
 * 판정 근거가 없을 때의 방향 — **권한을 주지 않는다** (§4 fail-closed).
 *
 * 라운드 2는 `integrateRoots` 가 없으면 접미사 heuristic 으로 폴백해 커밋을
 * *허용*했다. 이름만으로는 진짜 통합 worktree 와 이름이 같은 임의 경로를
 * 구분할 수 없으므로, 폴백의 결론은 허용이 아니라 거부여야 한다 (리뷰어 C 라운드 3).
 * 이 경로를 검증하는 테스트가 없어서 방향 오류가 3라운드 동안 남아 있었다.
 */
test('G-02: integrateRoots 미주입이면 commit·apply 를 fail-closed 로 거부한다', () => {
  for (const cmd of ['git commit -m x', 'git apply patch.diff', 'git am patch.mbox']) {
    // 통합 worktree 이름을 그대로 써도 근거가 없으면 거부다
    assertDeny(cmd, INTEGRATE_CWD);
    assertDeny(cmd, INTEGRATE_CWD + '/sub');
    assertDeny(cmd, SHARD_CWD);
  }
  // 거부 사유가 "근거 없음"임을 명시해야 조치가 가능하다
  const v = run('git commit -m x', INTEGRATE_CWD);
  assert.equal(v.decision, 'deny');
  if (v.decision !== 'deny') return;
  assert.match(v.reason, /integrateRoots/);
  assert.match(v.next, /CONTROL\.yaml/);
  // roots 를 주면 같은 명령이 통과한다 — 거부가 근거 부재 때문임을 보인다
  assertAllow('git commit -m x', INTEGRATE_CWD, { integrateRoots: INTEGRATE_ROOTS });
});

test('G-02: cwd 미제공 시 commit 은 fail-closed 로 거부한다', () => {
  const v = checkGitCommand('git commit -m "x"');
  assert.equal(v.decision, 'deny');
});

test('G-02: commit -a 는 통합 worktree 에서도 거부한다 (add -A 등가)', () => {
  assertDeny('git commit -am "wip"', INTEGRATE_CWD, { integrateRoots: INTEGRATE_ROOTS });
  assertDeny('git commit -a -m "wip"', INTEGRATE_CWD, { integrateRoots: INTEGRATE_ROOTS });
});

test('G-02: commit --amend 는 통합 worktree 에서 ask', () => {
  assertAsk('git commit --amend --no-edit', INTEGRATE_CWD, { integrateRoots: INTEGRATE_ROOTS });
});

/* ------------------------------------------------------------------ *
 * ask — 판정 불가·인접 위험
 * ------------------------------------------------------------------ */

test('G-02 ask: 정적으로 판정할 수 없는 인자', () => {
  assertAsk('git add "$FILE"');
  assertAsk('cd "$TARGET"');
  assertAsk('git checkout src/gate.ts');
});

test('G-02 ask: 금지 목록 밖의 이력 재작성·파괴 계열', () => {
  assertAsk('git rebase -i HEAD~3');
  assertAsk('git filter-branch --tree-filter true HEAD');
  assertAsk('git branch -D feature/old');
  assertAsk('git push --delete origin feature/old');
  assertAsk('git stash list');
  assertAsk('git restore --staged src/gate.ts');
});

/* ------------------------------------------------------------------ *
 * 허용 — 정상 작업이 막히면 안 된다 (AC-2)
 * ------------------------------------------------------------------ */

test('G-02 허용: 읽기 전용·브랜치 조작', () => {
  for (const cmd of [
    'git status',
    'git diff --stat',
    'git log --oneline -20',
    'git show HEAD',
    'git checkout -b feature/gate',
    'git checkout main',
    'git switch main',
    'cd src && ls',
    'cd ./test/fixtures',
    'harness status',
    'npm test',
    'npm ci',
    'node --test test/gitguard.test.ts',
    'echo "git add ." > note.txt',
    'git --version',
    '',
  ]) {
    assertAllow(cmd);
  }
});

test('G-02: §12.3 역할 제한 — 명시 경로 add 도 통합 worktree 밖에서는 ask', () => {
  // 초판은 allow 였다. 커밋하지 않는 샤드가 스테이징할 이유가 없다 (GATE-SPEC §6 G-02 (c)).
  // 하드 거부하지 않는 이유는 정상 진단 흐름을 끊지 않기 위함이다.
  assertAsk('git add src/gitguard.ts');
  assertAsk('git add src/gitguard.ts src/secrets.ts');
  assertAsk('npm test && git add src/secrets.ts');
  // 통합 worktree 에서는 통과
  assertAllow('git add src/gitguard.ts', INTEGRATE_CWD);
});

test('G-02 허용: G-04 관할 명령은 gitguard 가 판정하지 않는다', () => {
  // protect.ts (S0) 가 막는다. gitguard 가 중복 판정하면 책임 경계가 흐려진다.
  assertAllow('echo x > docs/Harness/CONTROL.yaml');
  assertAllow("sed -i 's/PAUSED/RUNNING/' docs/Harness/CONTROL.yaml");
});

/* ------------------------------------------------------------------ *
 * 리뷰어 C 실증 우회 7계열 — AC-4 의 실제 근거
 *
 * 초판은 `git add .` 을 막으면서 등가 표현 10종을 통과시켰다.
 * 아래 7개 테스트가 계열별 명시 케이스이며, 픽스처 대조는 그 위의 회귀 그물이다.
 * ------------------------------------------------------------------ */

test('F1 계열: git 내장 셸 이스케이프 — `-c alias.*` 는 금지 목록 전체 우회다', () => {
  // 리뷰어 C 실증: 실제 스테이징 확인됨
  assertDeny("git -c alias.zz='!git add .' zz");
  assertDeny('git -c alias.co=checkout co -- .');
  // alias 외에도 값이 외부 명령으로 실행되는 설정 키들
  assertDeny('git -c core.pager="git add ." log');
  assertDeny('git -c core.editor=vim commit -m x');
  assertDeny('git -c core.hooksPath=/dev/null commit -m x');
  assertDeny("git -c credential.helper='!sh -c \"git add .\"' fetch");
  assertDeny("git -c filter.x.clean='git add .' status");
  // 셸 문자열을 받는 하위 명령은 그 문자열을 재귀 검사한다
  assertDeny('git submodule foreach git add .');
  assertDeny('git bisect run git add .');
  assertDeny('git rebase -x "git add ." main');
  assertDeny('git difftool -x "git add ." HEAD');
  assertDeny('git filter-branch --tree-filter "git add ." HEAD');
  // 무해한 셸 문자열이면 deny 가 아니라 ask (실행 내용은 사용자가 확인)
  assertAsk('git submodule foreach npm test');
  // 무해한 설정 키는 통과
  assertAllow('git -c user.name=x log');
});

test('F1 계열: 영속형 alias — `git config` 도 `-c` 와 같은 규칙이다', () => {
  // 라운드 1은 인라인만 막고 영속형을 남겼다. 위험은 같고 영속형이 더 나쁘다.
  assertDeny("git config alias.zz '!git add .'");
  assertDeny("git config --global alias.zz '!git add .'");
  assertDeny('git config --local alias.co checkout');
  assertDeny('git config --unset alias.zz');
  assertDeny('git config core.hooksPath /dev/null');
  assertDeny("git config difftool.x.cmd 'git add .'");
  // 조회는 통과, 그 밖의 영속 변경은 ask
  assertAllow('git config --list');
  assertAllow('git config --get user.email');
  assertAllow('git config -l');
  assertAsk('git config user.name kim');
});

test('F1 계열: exec 설정 키는 열거가 아니라 규칙으로 판정한다', () => {
  // 열거 목록은 누락이 필연이다 — 아래는 전부 라운드 1 열거에서 빠져 있었다
  assertDeny("git -c difftool.x.cmd='git add .' difftool --tool=x -y");
  assertDeny("git -c mergetool.x.cmd='git add .' mergetool");
  assertDeny("git -c credential.https://x.io.helper='!git add .' fetch");
  assertDeny('git -c include.path=/tmp/evil.cfg log');
  assertDeny("git -c guitool.x.cmd='git add .' gui");
  assertDeny("git -c man.x.cmd='git add .' help");
  assertDeny("git -c browser.x.cmd='git add .' help -w x");
  assertDeny("git -c pager.log='git add .' log");
  assertDeny("git -c core.askpass='git add .' fetch");
  // 값이 `!` 로 시작하면 키와 무관하게 셸로 실행된다
  assertDeny("git -c anything.at.all='!git add .' log");
  // 무해한 설정은 통과 — 규칙이 과하게 넓으면 안 된다
  assertAllow('git -c user.name=kim log');
  assertAllow('git -c color.ui=false status');
  assertAllow('git -c push.default=simple log');
});

test('F2 계열: 절대경로도 상대경로와 같은 강도로 정규화한다', () => {
  // 라운드 2까지 `normalizeAbs` 는 후행 슬래시만 제거했다 — 같은 파일 안에서
  // 정규화 강도가 두 갈래였고 아래 5건이 전부 뚫렸다 (리뷰어 C 라운드 2).
  assertDeny(`git add ${SHARD_CWD}/.`);
  assertDeny(`git add ${SHARD_CWD}/./`);
  assertDeny(`git add ${SHARD_CWD}/src/..`);
  assertDeny(`git add ${SHARD_CWD}/../infraeye3-s0/x.ts`);
  assertDeny(`cd ${SHARD_CWD}/../infraeye3-s0`);
  assertDeny(`git -C ${SHARD_CWD}/../infraeye3-s0 status`);
  assertDeny(`git --work-tree=${SHARD_CWD}/../infraeye3-s0 status`);
  // 샤드 안으로 되돌아오는 `..` 는 정상이다
  assertAllow(`cd ${SHARD_CWD}/src/../test`);
  assert.equal(classifyPathspec(`${SHARD_CWD}/.`, SHARD_CWD), 'bulk');
  assert.equal(classifyPathspec(`${SHARD_CWD}/src/..`, SHARD_CWD), 'bulk');
  assert.equal(classifyPathspec(`${SHARD_CWD}/../infraeye3-s0/x.ts`, SHARD_CWD), 'escape');
  assert.equal(classifyPathspec(`${SHARD_CWD}/src/../src/a.ts`, SHARD_CWD), 'explicit');
});

test('인용 손실: 셸 문자열 재귀 시 인용을 보존한다', () => {
  // `join(' ')` 이면 `sh -c git add .` 로 뭉개져 deny→ask 로 강등됐다
  assertDeny('git bisect run sh -c "git add ."');
  assertDeny('git submodule foreach sh -c "git add ."');
  assertAsk('git bisect run npm test');
});

test('오탐: 순수 조회·비파괴 명령은 막지 않는다', () => {
  assertAsk('git update-index --refresh'); // 인덱스 stat 갱신일 뿐 deny 아님
  for (const cmd of ['git branch', 'git branch -a', 'git branch --list', 'git branch -v', 'git worktree list']) {
    assertAllow(cmd);
  }
  // 변경 계열은 여전히 ask
  assertAsk('git branch -D old');
  assertAsk('git branch feature/x');
  assertAsk('git worktree add ../x');
});

/**
 * F8 — 환경변수 lane.
 *
 * git 은 설정을 **세 경로**로 받는다: `-c`(인자) · `git config`(파일) · **환경변수**.
 * 앞의 둘만 통제하면 세 번째가 그대로 병렬 우회로가 된다. `commandInfo` 가
 * `VAR=x` 접두를 내용도 보지 않고 버리고 있었던 것이 원인이다 (리뷰어 C 라운드 3 실증).
 */
test('F8 계열: 환경변수 lane 이 `-c` 와 같은 통제를 받는다', () => {
  // `-c alias.zz=…` 와 완전 등가
  assertDeny("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=alias.zz GIT_CONFIG_VALUE_0='!git add .' git zz");
  assertDeny("GIT_CONFIG_PARAMETERS='alias.zz=!git add .' git zz");
  // 값이 셸로 실행되는 환경변수 = exec 설정 키
  for (const cmd of [
    "GIT_EXTERNAL_DIFF='git add .' git diff",
    "GIT_EDITOR='git add .' git config -e",
    "GIT_SEQUENCE_EDITOR='git add .' git rebase -i HEAD~2",
    "GIT_PAGER='git add .' git log",
    "GIT_SSH_COMMAND='ssh -i /tmp/k' git fetch",
    "GIT_ASKPASS='git add .' git fetch",
  ]) {
    assertDeny(cmd);
  }
  // 저장소 위치 변경 = `-C` 우회와 동일한 containment 검사
  assertDeny('GIT_DIR=/mnt/c/workspace/infraeye3-s0/.git git status');
  assertDeny('GIT_WORK_TREE=../infraeye3-s0 git status');
  // 샤드 안이거나 git 과 무관한 변수는 통과 — 과차단하지 않는다
  assertAllow('GIT_DIR=.git git status');
  assertAllow('FOO=bar git status');
  assertAllow('NODE_ENV=test npm test');
});

/**
 * env lane 을 **열거에서 규칙으로**.
 *
 * 설정 키 쪽에서 "열거는 누락이 필연"이라 판단해 규칙으로 바꿨는데 env 쪽에는
 * 열거가 남아 있었고, 그래서 `GIT_CONFIG*` 가족 4건이 통째로 빠졌다 (리뷰어 C 라운드 4).
 * 같은 실수를 두 곳에서 한 것이므로 여기서도 이름 가족·꼬리 규칙으로 전환한다.
 */
test('F8 계열: `GIT_CONFIG*` 가족은 설정 파일을 갈아끼우므로 전면 거부', () => {
  // C 재검토 지정 6줄 중 4줄
  assertDeny('GIT_CONFIG_GLOBAL=/tmp/evil.cfg git zz');
  assertDeny('GIT_CONFIG_SYSTEM=/tmp/evil.cfg git zz');
  assertDeny('GIT_CONFIG=/tmp/evil.cfg git zz');
  assertDeny('GIT_TEMPLATE_DIR=/tmp/evil git init');
  // 같은 가족의 미래 이름도 규칙이 덮는다 — 열거였다면 또 빠졌을 것들
  assertDeny('GIT_CONFIG_NOSYSTEM=1 git zz');
  assertDeny('GIT_CONFIG_LOCAL=/tmp/evil.cfg git zz');
  // 저장소 위치 계열
  assertDeny('GIT_EXEC_PATH=/tmp/evil git status');
});

test('F8 계열: `GIT_CONFIG_PARAMETERS` 두 형식을 모두 파싱한다', () => {
  // C 재검토 지정 6줄 중 2줄 — 신형(`'k'='v'`)이 미파싱이었다
  assertDeny(`GIT_CONFIG_PARAMETERS="'diff.external'='touch /tmp/x'" git diff`);
  assertDeny(`GIT_CONFIG_PARAMETERS="'core.pager'='git add .'" git log`);
  // 구형도 계속 잡힌다
  assertDeny(`GIT_CONFIG_PARAMETERS="'diff.external=touch /tmp/x'" git diff`);
  assertDeny(`GIT_CONFIG_PARAMETERS='alias.zz=!git add .' git zz`);

  // 파서 단위 — 두 형식이 같은 결과를 내야 한다
  assert.deepEqual(parseConfigParameters(`'diff.external=touch /tmp/x'`), [
    { key: 'diff.external', value: 'touch /tmp/x' },
  ]);
  assert.deepEqual(parseConfigParameters(`'diff.external'='touch /tmp/x'`), [
    { key: 'diff.external', value: 'touch /tmp/x' },
  ]);
  assert.deepEqual(parseConfigParameters(`'core.pager'='git add .' 'user.name'='kim'`), [
    { key: 'core.pager', value: 'git add .' },
    { key: 'user.name', value: 'kim' },
  ]);
});

test('F8 계열: env 값 인식과 대소문자 구분 (과차단 방지)', () => {
  // `GIT_PAGER=cat` 은 흔한 관용구다. 셸 메타문자·경로가 없으면 ask (§3.3)
  assertAsk('GIT_PAGER=cat git log');
  assertAsk('GIT_EDITOR=true git commit');
  assertAsk('GIT_EDITOR=vim git commit');
  // 값이 셸 명령 형태면 deny
  assertDeny("GIT_PAGER='less -R' git log");
  assertDeny("GIT_EDITOR='git add .' git config -e");
  // POSIX env 는 대소문자 구분 — git 이 읽지 않는 이름을 막지 않는다
  assertAllow('git_editor=x git status');
  assertAllow('GIT_DIR=.git git status');
  assertAllow('NODE_ENV=test npm test');
});

test('F1 계열: 셸 문자열 앞 플래그를 건너뛴다', () => {
  assertDeny('git submodule foreach --recursive "git add ."');
  assertDeny('git submodule foreach --quiet --recursive "git add ."');
  assertAsk('git submodule foreach --recursive npm test');
});

test('F1 계열: config 값소비 플래그와 `--edit`', () => {
  // `positionals()` 는 `-f` 가 다음 토큰을 먹는 걸 몰라 `other.cfg` 를 키로 봤다.
  // 결합형(`--file=x`)만 우연히 맞고 분리형은 틀리는 비대칭이었다 (리뷰어 C).
  assertDeny("git config -f other.cfg alias.zz '!git add .'");
  assertDeny("git config --file other.cfg alias.zz '!git add .'");
  assertDeny("git config --blob HEAD:x alias.zz '!git add .'");
  assertDeny("git config --file=other.cfg alias.zz '!git add .'");
  // `--edit` 는 GIT_EDITOR 로 임의 명령을 띄운다
  assertDeny('git config --edit');
  assertDeny('git config -e');
  // 값소비 플래그를 제대로 건너뛰면 키는 `core.bare` 다
  assertAsk('git config --type bool core.bare true');
});

test('권고 4·5: exec 키 규칙이 과차단하지 않고, 빠진 키를 잡는다', () => {
  // `.proxy` 는 URL, `.tool` 은 도구 이름 — 명령이 아니다
  assertAllow('git -c http.proxy=http://p:8080 fetch');
  assertAllow('git -c https.proxy=http://p:8080 fetch');
  assertAllow('git -c diff.tool=vimdiff difftool');
  assertAllow('git -c merge.tool=vimdiff mergetool');
  // 진짜 명령은 여전히 잡힌다
  assertDeny("git -c difftool.vimdiff.cmd='git add .' difftool");
  assertDeny("git -c core.gitProxy='git add .' fetch");
  // 꼬리가 `.command` 가 아니라 규칙에서 빗나갔던 키
  assertDeny("git -c core.alternateRefsCommand='git add .' log");
});

test('F2 계열: 경로 정규화 — 문자열 집합이 아니라 정규화로 판정한다', () => {
  // 초판 자기모순: `./` 는 거부인데 `.//` 는 통과였다
  for (const p of ['./', './.', './/', '././.', 'src/..', 'src/../.', '..', '../', ':/', ':', ':(top)']) {
    assertDeny(`git add ${p}`);
  }
  // worktree 루트 절대경로 = 전체
  assertDeny(`git add ${SHARD_CWD}`);
  assertDeny(`git add ${SHARD_CWD}/`);
  // 단위 판정
  assert.equal(classifyPathspec('./.', SHARD_CWD), 'bulk');
  assert.equal(classifyPathspec('src/..', SHARD_CWD), 'bulk');
  assert.equal(classifyPathspec(SHARD_CWD, SHARD_CWD), 'bulk');
  assert.equal(classifyPathspec('src/a.ts', SHARD_CWD), 'explicit');
  assert.equal(classifyPathspec('../other/a.ts', SHARD_CWD), 'escape');
  assert.equal(classifyPathspec('src/*.ts', SHARD_CWD), 'glob');
});

test('F3 계열: plumbing 등가물은 porcelain 금지분과 같이 취급한다', () => {
  // 리뷰어 C 실증: 실제 작업트리 파괴 확인됨
  assertDeny('git read-tree -u --reset HEAD'); // = reset --hard
  assertDeny('git read-tree --reset -u HEAD');
  assertDeny('git checkout-index -f -a'); // = checkout -- <path>
  assertDeny('git checkout-index --force --all');
  assertDeny('git update-index --add src/x.ts'); // = add
  assertDeny('git update-index --force-remove src/x.ts');
  assertDeny('git sparse-checkout set src');
  // 파괴 플래그가 없어도 plumbing 자체가 인덱스를 직접 만진다
  assertAsk('git read-tree HEAD');
});

test('F4 계열: 셸 재호출 — `-c` 가 없어도 최소 ask', () => {
  assertDeny('bash -c "git add ."');
  assertDeny('bash -c -- "git add ."'); // 초판은 `--` 옵션 종료를 놓쳤다
  assertDeny("sh -c 'git add .'");
  assertDeny('bash -lc "git add ."');
  assertDeny('bash <<< "git add ."'); // herestring
  assertDeny('script -qec "git add ." /dev/null');
  assertDeny('eval "git add ."');
});

/**
 * G-02 와 G-11 의 경계.
 *
 * 명세 §6 G-02 (d) 6행은 인터프리터 우회를 `ask` 로 올리라고 한다. 그러나 그 판정은
 * `G-11`(Bash 화이트리스트, S0 소유)이 이미 수행하고 E2E로 검증하고 있다.
 * `gate.ts` 체인은 **ask 만 내는 G-11 을 맨 끝에 두므로**(deny 게이트 우선),
 * G-02 가 같은 명령에 먼저 ask 를 내면 감사 기록의 규칙 번호가 G-11 → G-02 로
 * 잘못 귀속된다. 실제로 재작업 중 S0의 G-11 E2E 2건을 깨뜨렸다.
 *
 * 경계: **G-11 = 무엇을 실행할 수 있는가 / G-02 = 허용된 git 명령의 의미.**
 * G-02 는 코드 문자열이 보일 때만 발언하고, 불투명하면 침묵한다.
 */
test('G-02/G-11 경계: 불투명한 실행 경로에는 G-02 가 발언하지 않는다', () => {
  for (const cmd of [
    'echo "git add ." | bash',
    'bash run.sh',
    'source setup.sh',
    '. ./setup.sh',
    'python3 -c "import subprocess"',
    'perl -e "system(1)"',
    'node -e "require(1)"',
    'ssh host "git add ."',
    'su - user -c "git add ."',
    'make build',
    'npm run build',
  ]) {
    assertAllow(cmd);
  }
  // 반면 문자열이 보이면 G-02 가 판정한다 — 위임하지 않는다
  assertDeny('bash -c "git add ."');
  assertDeny('bash <<< "git add ."');
});

test('F5 계열: 변수 전개 — 하위명령·명령이름·인자를 대칭으로 다룬다', () => {
  // 초판은 인자·명령이름만 ask 였고 하위 명령이 변수면 무검사 통과였다
  assertAsk('G=add; git $G .');
  assertAsk('git $SUB .');
  assertAsk('git ${SUB} .');
  assertAsk('GIT=git; $GIT add .');
  assertAsk('git add "$FILE"');
  assertAsk('cd "$TARGET"');
});

test('F6 계열: §12.3 승인 필요군은 전부 ask (초판 무검사 통과)', () => {
  for (const cmd of [
    'git worktree add ../infraeye3-s9',
    'git worktree remove ../infraeye3-s2',
    'git branch feature/x',
    'git branch -D feature/old',
    'git merge main',
    'git cherry-pick abc1234',
    'git revert abc1234',
    'git push origin main',
    'git rebase -i HEAD~3',
  ]) {
    assertAsk(cmd);
  }
  // (a) 절대 거부가 (b) 승인 필요보다 우선한다
  assertDeny('git push --force origin main');
});

test('F7 계열: 바이너리 직접 실행 — 확장자·런타임 래핑과 무관하게 같은 판정', () => {
  for (const cmd of [
    'harness approve CYCLE-20260726-00',
    './bin/harness approve CYCLE-20260726-00',
    './bin/harness.js approve CYCLE-20260726-00',
    './bin/harness.ts approve CYCLE-20260726-00',
    'dist/harness.cjs approve CYCLE-20260726-00',
    'node dist/harness.cjs approve CYCLE-20260726-00',
    'npx harness approve CYCLE-20260726-00',
    'harness resume',
    'harness mode RUNNING',
  ]) {
    assertDeny(cmd);
  }
  assertAllow('harness status');
});

test('오탐 회귀: 통합 worktree 하위 디렉터리에서 커밋이 막히지 않는다', () => {
  // 초판은 basename 만 봐서 `<repo>-integrate/sub` 에서 오탐이 났다 (리뷰어 C)
  assert.equal(isIntegrationWorktree('/w/repo-integrate'), true);
  assert.equal(isIntegrationWorktree('/w/repo-integrate/sub/deep'), true);
  assert.equal(isIntegrationWorktree('/w/repo-s1'), false);
  assertAllow('git commit -m x', INTEGRATE_CWD + '/sub/deep', { integrateRoots: INTEGRATE_ROOTS });
  // 명명 규약은 주입 가능해야 한다 (하드코딩 금지)
  assert.equal(isIntegrationWorktree('/w/repo-merge', ['-merge']), true);
  assert.equal(isIntegrationWorktree('/w/repo-integrate', ['-merge']), false);
});

/**
 * 접미사 heuristic 은 이름만 보므로 `/tmp/x-integrate` 같은 무관한 경로도 참이 된다
 * (리뷰어 C 라운드 2 — 하위 디렉터리 오탐을 고치면서 반대로 열린 부분).
 * 이름만으로는 구분할 방법이 없다. **절대 경로를 주입하면 진짜 경로 접두 판정이 된다.**
 */
test('통합 worktree: roots 주입 시 진짜 경로 접두 판정이 된다', () => {
  const roots = ['/w/repo-integrate'];
  assert.equal(isIntegrationWorktree('/w/repo-integrate', undefined, roots), true);
  assert.equal(isIntegrationWorktree('/w/repo-integrate/sub/deep', undefined, roots), true);
  // 무관한 경로 — heuristic 이면 통과하지만 roots 로는 차단된다
  assert.equal(isIntegrationWorktree('/tmp/x-integrate', undefined, roots), false);
  // 접두 유사어도 차단 (`repo-integrate-evil`)
  assert.equal(isIntegrationWorktree('/w/repo-integrate-evil', undefined, roots), false);
  // 커밋 판정에 실제로 반영된다
  assert.equal(checkGitCommand('git commit -m x', { cwd: '/tmp/x-integrate', integrateRoots: roots }).decision, 'deny');
  assert.equal(
    checkGitCommand('git commit -m x', { cwd: '/w/repo-integrate/sub', integrateRoots: roots }).decision,
    'allow',
  );
});

/* ------------------------------------------------------------------ *
 * 픽스처 전량 대조 (회귀 그물) + AC-4 계열 커버리지
 * ------------------------------------------------------------------ */

interface FixtureCase {
  expected: 'deny' | 'ask' | 'allow';
  gate: string;
  family: string;
  payload: string;
  lineNo: number;
}

export function loadBypassFixture(): FixtureCase[] {
  const raw = readFileSync(join(HERE, 'fixtures', 'bypass-attempts.txt'), 'utf8');
  const cases: FixtureCase[] = [];
  raw.split(/\r?\n/).forEach((line, i) => {
    if (line.trim() === '' || line.startsWith('#')) return;
    const parts = line.split('\t');
    assert.ok(parts.length >= 4, `픽스처 ${i + 1}행 형식 오류(4열 필요): ${line}`);
    cases.push({
      expected: parts[0].trim() as FixtureCase['expected'],
      gate: parts[1].trim(),
      family: parts[2].trim(),
      // 명령 안의 탭은 그대로 살리고, 리터럴 \n 만 개행으로 되돌린다
      payload: parts.slice(3).join('\t').replace(/\\n/g, '\n'),
      lineNo: i + 1,
    });
  });
  return cases;
}

function judge(c: FixtureCase): string {
  if (c.gate === 'G-03') return scanSecrets(c.payload, 'docs/x.md').decision;
  return checkGitCommand(c.payload, { cwd: SHARD_CWD }).decision;
}

test('픽스처: 모든 케이스가 기대 판정과 일치한다 (회귀 그물)', () => {
  const cases = loadBypassFixture();
  const failures = cases
    .filter((c) => judge(c) !== c.expected)
    .map((c) => `${c.lineNo}행 [${c.gate}/${c.family}] 기대=${c.expected} 실제=${judge(c)} :: ${JSON.stringify(c.payload)}`);
  assert.deepEqual(failures, [], `픽스처 불일치 ${failures.length}건\n${failures.join('\n')}`);
});

/**
 * AC-4 의 실제 근거.
 *
 * **"픽스처의 우회가 전부 차단된다"는 단언은 동어반복이다** — 픽스처에는 이미
 * 막히는 것만 들어가기 때문이다(리뷰어 C 지적). 초판 AC-4 가 정확히 그 형태였고,
 * 그래서 픽스처에 한 건도 없는 계열이 10종이나 있었는데도 녹색이었다.
 *
 * 그래서 단언을 **커버리지**로 바꾼다: 리뷰어 C가 실증한 7계열 각각이 최소
 * 케이스 수를 갖고 있어야 한다. 계열이 비면 이 테스트가 먼저 깨진다.
 */
const REQUIRED_FAMILIES: Array<[string, number, string]> = [
  ['F1', 8, 'git 내장 셸 이스케이프 (-c alias.* · foreach · bisect run · -x)'],
  ['F2', 10, '경로 정규화 (./. · src/.. · .// · worktree 루트)'],
  ['F3', 7, 'plumbing 등가물 (read-tree · checkout-index · update-index)'],
  ['F4', 12, '셸 재호출 (bash -c -- · 파이프 · herestring · source · 인터프리터)'],
  ['F5', 5, '변수 전개 (하위명령·명령이름·인자)'],
  ['F6', 8, '§12.3 승인 필요군'],
  ['F7', 9, '바이너리 직접 실행'],
  ['F8', 10, '환경변수 lane (GIT_CONFIG_* · GIT_EDITOR · GIT_DIR)'],
  ['S1', 6, 'G-03 BOOT_05 형태'],
  ['S2', 5, 'G-03 기호 없는 값'],
  ['S3', 6, 'G-03 따옴표 키·XML'],
  ['S4', 10, 'G-03 오탐 회귀'],
];

test('AC-4: 리뷰어 C·D 실증 계열이 전부 픽스처에 최소 커버리지로 존재한다', () => {
  const cases = loadBypassFixture();
  const thin = REQUIRED_FAMILIES.filter(([id, min]) => cases.filter((c) => c.family === id).length < min).map(
    ([id, min, desc]) => `${id} (${desc}): ${cases.filter((c) => c.family === id).length}건 < 최소 ${min}건`,
  );
  assert.deepEqual(thin, [], `계열 커버리지 미달:\n${thin.join('\n')}`);
});

test('AC-4: 각 계열의 우회 케이스가 단 한 건도 allow 로 새지 않는다', () => {
  const leaked = loadBypassFixture()
    .filter((c) => c.family !== '-' && c.family !== 'S4' && c.expected !== 'allow')
    .filter((c) => judge(c) === 'allow')
    .map((c) => `${c.lineNo}행 [${c.family}]: ${c.payload}`);
  assert.deepEqual(leaked, [], `우회 시도가 통과했다:\n${leaked.join('\n')}`);
});
