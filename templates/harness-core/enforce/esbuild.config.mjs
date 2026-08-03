// esbuild 번들 구성 — GATE-SPEC §8 (원본 infraeye-harness/esbuild.config.mjs 이식, CE-329)
//
// 훅은 툴 호출마다 프로세스가 뜬다. 목표 p95 < 50ms.
// 따라서 런타임 의존성 해석(node_modules 탐색)이 일어나지 않도록
// 모든 의존성을 단일 CJS 파일에 인라인한다. dist/ 는 커밋 대상이다.
//
// ── 이식 시 바꾼 것은 targets 하나뿐이다 ─────────────────────────────────
// 산출물은 워크스페이스에 실제 배포되는 훅 1파일이므로 `dist/` 가 아니라
// 조달 스크립트가 복사하는 `../hooks/gitguard-gate.cjs` 로 낸다. node 내장 모듈만
// 쓰는 자족 번들이라 워크스페이스에 node_modules 가 없어도 동작한다.
// `failClosedBanner` 는 **무수정**이다 — 아래 주석의 `exit 1` 함정이 집행면의
// 존재 이유 그 자체다.

import { build } from 'esbuild';

/**
 * 🚨 번들 최상단 주입 코드 — GATE-SPEC §3.2 `exit 1` 함정
 *
 * `src/gate.ts` 안의 `process.exitCode = 2`는 **모듈 import보다 나중에** 실행된다
 * (CJS 변환 시 require가 앞으로 끌려간다). 즉 로딩 단계에서 예외가 나면 Node가
 * 기본 종료 코드 `1`로 죽고, Claude Code는 그걸 non-blocking error로 보아
 * **툴을 실행한다.** 가드레일이 조용히 열리는 정확히 그 시나리오다.
 *
 * 그래서 어떤 모듈 코드보다 먼저 실행되는 배너에 최후의 방어선을 박는다.
 * 본체 핸들러가 등록된 뒤에는(`__HARNESS_HANDLERS__`) 감사 기록을 남길 수 있는
 * 본체 쪽에 양보한다.
 */
const failClosedBanner = `process.exitCode = 2;
(function () {
  var bail = function (e) {
    if (globalThis.__HARNESS_HANDLERS__) return;
    try {
      process.stderr.write(
        '[하네스 게이트] 거부 — G-00 게이트 로딩 중 예외 (fail-closed)\\n' +
        '  오류: ' + ((e && e.stack) || e) + '\\n' +
        '  조치: 예외는 허용이 아니라 거부로 떨어진다 (GATE-SPEC §4). 게이트 결함이므로 PM에게 보고하라.\\n'
      );
    } catch (_) {}
    process.exit(2);
  };
  process.on('uncaughtException', bail);
  process.on('unhandledRejection', bail);
})();
`;

const common = {
  bundle: true,
  platform: 'node',
  target: 'node20',
  format: 'cjs',
  minify: true,
  legalComments: 'none',
  logLevel: 'info',
  // 런타임 require 없음: node 내장 모듈만 external
  external: [],
};

const targets = [
  {
    entryPoints: ['src/enforce.ts'],
    outfile: '../hooks/gitguard-gate.cjs',
    banner: { js: failClosedBanner },
  },
];

for (const t of targets) {
  await build({ ...common, ...t });
}
