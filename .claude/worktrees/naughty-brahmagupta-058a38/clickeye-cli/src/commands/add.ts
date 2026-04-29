import fs from "node:fs/promises";
import path from "node:path";
import chalk from "chalk";
import ora from "ora";
import inquirer from "inquirer";
import Handlebars from "handlebars";
import catalogAgents from "../catalog/agents.json" with { type: "json" };
import catalogSkills from "../catalog/skills.json" with { type: "json" };
import catalogStacks from "../catalog/stacks.json" with { type: "json" };
import type { CatalogAgent, AgentId, WorkflowId, StackPreset } from "../types.js";
import type { CatalogSkill } from "../generators/skill.js";
import { TEMPLATES_DIR } from "../paths.js";

type AddCategory = "agent" | "skill" | "hook";

interface AddFlags {
  yes?: boolean;
  dryRun?: boolean;
  stack?: string;
}

interface FileToWrite {
  relativePath: string;
  content: string;
}

/** settings.json을 읽어서 파싱 */
async function readSettings(
  targetDir: string
): Promise<Record<string, unknown> | null> {
  const settingsPath = path.join(targetDir, ".claude/settings.json");
  try {
    const raw = await fs.readFile(settingsPath, "utf-8");
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/** settings.json에 Hook 추가 */
async function updateSettingsHooks(
  targetDir: string,
  hookName: string,
  entry: { type: string; command: string }
): Promise<void> {
  const settings = await readSettings(targetDir);
  if (!settings) return;

  const hooks = (settings.hooks ?? {}) as Record<
    string,
    { type: string; command: string }[]
  >;

  if (!hooks[hookName]) {
    hooks[hookName] = [];
  }

  // 중복 방지
  const exists = hooks[hookName].some((h) => h.command === entry.command);
  if (!exists) {
    hooks[hookName].push(entry);
  }

  settings.hooks = hooks;

  const settingsPath = path.join(targetDir, ".claude/settings.json");
  await fs.writeFile(settingsPath, JSON.stringify(settings, null, 2) + "\n");
}

/** 기술 스택 감지 — 기존 설정에서 읽거나 기본값 사용 */
async function detectStack(targetDir: string): Promise<StackPreset> {
  // CLAUDE.md에서 스택 정보 추출 시도
  try {
    const claudeMd = await fs.readFile(
      path.join(targetDir, "CLAUDE.md"),
      "utf-8"
    );
    for (const stack of catalogStacks) {
      if (claudeMd.includes(stack.name)) return stack.id as StackPreset;
    }
  } catch {
    // CLAUDE.md가 없으면 무시
  }
  return "fastapi-nextjs";
}

/** add agent 처리 */
async function addAgent(
  agentId: string,
  targetDir: string,
  flags: AddFlags
): Promise<void> {
  const agent = (catalogAgents as CatalogAgent[]).find(
    (a) => a.id === agentId
  );
  if (!agent) {
    console.error(
      chalk.red(`\n❌ 알 수 없는 에이전트: "${agentId}"`)
    );
    console.log(chalk.dim("\n사용 가능한 에이전트:"));
    for (const a of catalogAgents as CatalogAgent[]) {
      console.log(chalk.dim(`  ${a.id} — ${a.name}: ${a.description}`));
    }
    process.exit(1);
  }

  const outputPath = path.join(targetDir, `.claude/agents/${agent.outputFile}`);

  // 충돌 감지
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: `${agent.outputFile}이(가) 이미 존재합니다. 덮어쓰시겠습니까?`,
          default: false,
        },
      ]);
      if (!overwrite) {
        console.log(chalk.yellow("⏭️  건너뜀"));
        return;
      }
    }
  }

  const stackPreset = flags.stack
    ? (flags.stack as StackPreset)
    : await detectStack(targetDir);
  const stack = catalogStacks.find((s) => s.id === stackPreset);

  const templateSource = await fs.readFile(
    path.join(TEMPLATES_DIR, agent.template),
    "utf-8"
  );
  const template = Handlebars.compile(templateSource);
  const content = template({
    projectName: path.basename(targetDir),
    projectType: "fullstack",
    stack,
    agent,
  });

  const file: FileToWrite = {
    relativePath: `.claude/agents/${agent.outputFile}`,
    content,
  };

  if (flags.dryRun) {
    console.log(chalk.yellow("\n📋 --dry-run: 생성할 파일:"));
    console.log(chalk.dim(`  ${file.relativePath}`));
    return;
  }

  const spinner = ora("에이전트 파일 생성 중...").start();
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk.green(`에이전트 추가 완료: ${agent.name}`));
  console.log(chalk.dim(`  ${file.relativePath}`));
}

/** add skill 처리 */
async function addSkill(
  skillId: string,
  targetDir: string,
  flags: AddFlags
): Promise<void> {
  const skill = (catalogSkills as CatalogSkill[]).find(
    (s) => s.id === skillId
  );
  if (!skill) {
    console.error(
      chalk.red(`\n❌ 알 수 없는 스킬: "${skillId}"`)
    );
    console.log(chalk.dim("\n사용 가능한 스킬:"));
    for (const s of catalogSkills as CatalogSkill[]) {
      console.log(chalk.dim(`  ${s.id} — ${s.name}: ${s.description}`));
    }
    process.exit(1);
  }

  const outputPath = path.join(
    targetDir,
    `.claude/skills/${skill.outputFile}`
  );

  // 충돌 감지
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: `${skill.outputFile}이(가) 이미 존재합니다. 덮어쓰시겠습니까?`,
          default: false,
        },
      ]);
      if (!overwrite) {
        console.log(chalk.yellow("⏭️  건너뜀"));
        return;
      }
    }
  }

  const stackPreset = flags.stack
    ? (flags.stack as StackPreset)
    : await detectStack(targetDir);
  const stack = catalogStacks.find((s) => s.id === stackPreset);

  const templateSource = await fs.readFile(
    path.join(TEMPLATES_DIR, skill.template),
    "utf-8"
  );
  const template = Handlebars.compile(templateSource);
  const content = template({
    projectName: path.basename(targetDir),
    projectType: "fullstack",
    stack,
  });

  const file: FileToWrite = {
    relativePath: `.claude/skills/${skill.outputFile}`,
    content,
  };

  if (flags.dryRun) {
    console.log(chalk.yellow("\n📋 --dry-run: 생성할 파일:"));
    console.log(chalk.dim(`  ${file.relativePath}`));
    return;
  }

  const spinner = ora("스킬 파일 생성 중...").start();
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk.green(`스킬 추가 완료: ${skill.name}`));
  console.log(chalk.dim(`  ${file.relativePath}`));

  // Hook 자동 등록
  for (const hookName of skill.hooks) {
    await updateSettingsHooks(targetDir, hookName, {
      type: "command",
      command:
        hookName === "UserPromptSubmit"
          ? "bash scripts/harness-gate.sh"
          : `echo "🔍 AI 리뷰: ${skill.name} 검증 중..."`,
    });
    console.log(
      chalk.dim(`  ↳ settings.json에 ${hookName} Hook 등록됨`)
    );
  }
}

/** add hook 처리 */
async function addHook(
  hookId: string,
  targetDir: string,
  flags: AddFlags
): Promise<void> {
  // 현재는 harness-gate만 지원
  if (hookId !== "harness-gate") {
    console.error(
      chalk.red(`\n❌ 알 수 없는 Hook: "${hookId}"`)
    );
    console.log(chalk.dim("\n사용 가능한 Hook:"));
    console.log(
      chalk.dim("  harness-gate — lint + typecheck + test 게이트")
    );
    process.exit(1);
  }

  const outputPath = path.join(targetDir, "scripts/harness-gate.sh");

  // 충돌 감지
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: "harness-gate.sh가 이미 존재합니다. 덮어쓰시겠습니까?",
          default: false,
        },
      ]);
      if (!overwrite) {
        console.log(chalk.yellow("⏭️  건너뜀"));
        return;
      }
    }
  }

  const stackPreset = flags.stack
    ? (flags.stack as StackPreset)
    : await detectStack(targetDir);
  const stack = catalogStacks.find((s) => s.id === stackPreset);

  const templateSource = await fs.readFile(
    path.join(TEMPLATES_DIR, "hooks/harness-gate.sh.hbs"),
    "utf-8"
  );
  const template = Handlebars.compile(templateSource);
  const content = template({ stack });

  if (flags.dryRun) {
    console.log(chalk.yellow("\n📋 --dry-run: 생성할 파일:"));
    console.log(chalk.dim("  scripts/harness-gate.sh"));
    return;
  }

  const spinner = ora("Hook 스크립트 생성 중...").start();
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk.green("Hook 추가 완료: harness-gate"));
  console.log(chalk.dim("  scripts/harness-gate.sh"));

  // settings.json에 Hook 등록
  await updateSettingsHooks(targetDir, "UserPromptSubmit", {
    type: "command",
    command: "bash scripts/harness-gate.sh",
  });
  console.log(
    chalk.dim("  ↳ settings.json에 UserPromptSubmit Hook 등록됨")
  );
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/** add 명령어 메인 핸들러 */
export async function addCommand(
  category: string,
  id: string,
  flags: AddFlags
): Promise<void> {
  const targetDir = process.cwd();

  // 카테고리 유효성 검사
  const validCategories: AddCategory[] = ["agent", "skill", "hook"];
  if (!validCategories.includes(category as AddCategory)) {
    console.error(
      chalk.red(`\n❌ 알 수 없는 카테고리: "${category}"`)
    );
    console.log(chalk.dim("\n사용법:"));
    console.log(chalk.dim("  24sc add agent <id>   — 에이전트 추가"));
    console.log(chalk.dim("  24sc add skill <id>   — 스킬 추가"));
    console.log(chalk.dim("  24sc add hook <id>    — Hook 추가"));
    process.exit(1);
  }

  if (!id) {
    console.error(
      chalk.red(`\n❌ ID를 지정해주세요`)
    );
    console.log(
      chalk.dim(`\n사용법: 24sc add ${category} <id>`)
    );
    process.exit(1);
  }

  console.log(
    chalk.bold(`\n🔧 ${category} 추가: ${id}\n`)
  );

  switch (category as AddCategory) {
    case "agent":
      await addAgent(id, targetDir, flags);
      break;
    case "skill":
      await addSkill(id, targetDir, flags);
      break;
    case "hook":
      await addHook(id, targetDir, flags);
      break;
  }
}
