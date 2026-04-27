import fs from "node:fs/promises";
import path from "node:path";
import chalk from "chalk";

interface CheckResult {
  label: string;
  passed: boolean;
  detail?: string;
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function isExecutable(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

/** .claude/ 디렉토리 존재 여부 검사 */
async function checkClaudeDir(targetDir: string): Promise<CheckResult> {
  const exists = await fileExists(path.join(targetDir, ".claude"));
  return {
    label: ".claude/ 디렉토리 존재",
    passed: exists,
    detail: exists ? undefined : "24sc init을 먼저 실행하세요",
  };
}

/** settings.json 유효성 검사 */
async function checkSettingsJson(targetDir: string): Promise<CheckResult> {
  const settingsPath = path.join(targetDir, ".claude/settings.json");

  if (!(await fileExists(settingsPath))) {
    return {
      label: "settings.json 존재",
      passed: false,
      detail: "24sc init을 먼저 실행하세요",
    };
  }

  try {
    const raw = await fs.readFile(settingsPath, "utf-8");
    const settings = JSON.parse(raw);

    // 필수 필드 확인
    const hasPermissions = settings.permissions != null;
    const hasHooks = settings.hooks != null;

    if (!hasPermissions || !hasHooks) {
      const missing: string[] = [];
      if (!hasPermissions) missing.push("permissions");
      if (!hasHooks) missing.push("hooks");
      return {
        label: "settings.json 유효성",
        passed: false,
        detail: `필수 필드 누락: ${missing.join(", ")}`,
      };
    }

    return { label: "settings.json 유효성", passed: true };
  } catch (error) {
    return {
      label: "settings.json 유효성",
      passed: false,
      detail:
        error instanceof SyntaxError
          ? "JSON 파싱 실패 — 올바른 JSON 형식인지 확인하세요"
          : "파일 읽기 실패",
    };
  }
}

/** Hook 스크립트 실행 권한 확인 */
async function checkHookScripts(targetDir: string): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  const scriptsDir = path.join(targetDir, "scripts");

  if (!(await fileExists(scriptsDir))) {
    return [];
  }

  const entries = await fs.readdir(scriptsDir);
  const shellScripts = entries.filter((e) => e.endsWith(".sh"));

  for (const script of shellScripts) {
    const scriptPath = path.join(scriptsDir, script);
    const executable = await isExecutable(scriptPath);
    results.push({
      label: `scripts/${script} 실행 권한`,
      passed: executable,
      detail: executable
        ? undefined
        : `chmod +x scripts/${script} 으로 권한을 부여하세요`,
    });
  }

  return results;
}

/** 에이전트 파일 참조 무결성 검사 */
async function checkAgentReferences(
  targetDir: string
): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  const claudeMdPath = path.join(targetDir, "CLAUDE.md");

  if (!(await fileExists(claudeMdPath))) {
    return [
      {
        label: "CLAUDE.md 존재",
        passed: false,
        detail: "24sc init으로 생성하세요",
      },
    ];
  }

  const claudeMd = await fs.readFile(claudeMdPath, "utf-8");

  // .claude/agents/*.md 참조 추출
  const agentRefs = claudeMd.match(/\.claude\/agents\/[\w-]+\.md/g) ?? [];

  for (const ref of agentRefs) {
    const refPath = path.join(targetDir, ref);
    const exists = await fileExists(refPath);
    results.push({
      label: `${ref} 참조 무결성`,
      passed: exists,
      detail: exists
        ? undefined
        : `파일이 없습니다. 24sc add agent <id>로 추가하세요`,
    });
  }

  if (agentRefs.length === 0) {
    results.push({
      label: "에이전트 파일 참조",
      passed: true,
      detail: "CLAUDE.md에 에이전트 참조 없음 (정상)",
    });
  }

  return results;
}

/** .env 필수 변수 확인 */
async function checkEnvVars(targetDir: string): Promise<CheckResult[]> {
  const results: CheckResult[] = [];
  const envPath = path.join(targetDir, ".env");

  if (!(await fileExists(envPath))) {
    // .env가 없으면 .env.example 확인
    const examplePath = path.join(targetDir, ".env.example");
    if (await fileExists(examplePath)) {
      results.push({
        label: ".env 파일 존재",
        passed: false,
        detail: ".env.example을 복사하여 .env를 생성하세요",
      });
    }
    return results;
  }

  return results;
}

/** CLAUDE.md 존재 확인 */
async function checkClaudeMd(targetDir: string): Promise<CheckResult> {
  const exists = await fileExists(path.join(targetDir, "CLAUDE.md"));
  return {
    label: "CLAUDE.md 존재",
    passed: exists,
    detail: exists ? undefined : "24sc init으로 생성하세요",
  };
}

/** doctor 명령어 메인 핸들러 */
export async function doctorCommand(): Promise<void> {
  const targetDir = process.cwd();

  console.log(chalk.bold("\n🔍 ClickEye 설정 진단\n"));
  console.log(chalk.dim(`검사 경로: ${targetDir}\n`));

  const allResults: CheckResult[] = [];

  // 순서대로 검사 실행
  allResults.push(await checkClaudeDir(targetDir));
  allResults.push(await checkClaudeMd(targetDir));
  allResults.push(await checkSettingsJson(targetDir));
  allResults.push(...(await checkHookScripts(targetDir)));
  allResults.push(...(await checkAgentReferences(targetDir)));
  allResults.push(...(await checkEnvVars(targetDir)));

  // 결과 출력
  let passCount = 0;
  let failCount = 0;

  for (const result of allResults) {
    const icon = result.passed ? chalk.green("✅") : chalk.red("❌");
    console.log(`${icon} ${result.label}`);
    if (result.detail) {
      console.log(chalk.dim(`   → ${result.detail}`));
    }
    if (result.passed) passCount++;
    else failCount++;
  }

  // 요약
  console.log(chalk.bold("\n────────────────────────────────"));
  if (failCount === 0) {
    console.log(
      chalk.green(`\n🎉 모든 검사 통과! (${passCount}/${passCount})`)
    );
  } else {
    console.log(
      chalk.yellow(
        `\n⚠️  ${failCount}개 항목 실패 (${passCount}/${passCount + failCount} 통과)`
      )
    );
    console.log(
      chalk.dim(
        "\n위 ❌ 항목의 안내를 따라 문제를 해결하세요."
      )
    );
  }
  console.log();
}
