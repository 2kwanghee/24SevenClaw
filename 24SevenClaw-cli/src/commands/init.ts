import path from "node:path";
import chalk from "chalk";
import ora from "ora";
import { promptProjectInfo, defaultProjectInfo } from "../wizard/project.js";
import { promptAgentSelection, defaultAgentSelection } from "../wizard/agents.js";
import { generateAgentFiles } from "../generators/agent.js";
import { generateSettings } from "../generators/settings.js";
import { generateClaudeMd } from "../generators/claude-md.js";
import { writeFiles } from "../generators/writer.js";
import type { InitOptions } from "../types.js";

interface InitFlags {
  yes?: boolean;
  dryRun?: boolean;
}

export async function initCommand(flags: InitFlags): Promise<void> {
  console.log(
    chalk.bold("\n🤖 24SevenClaw — AI 에이전트 워크플로우 설정\n")
  );

  // Step 1 & 2: 위저드 또는 기본값
  const project = flags.yes
    ? defaultProjectInfo()
    : await promptProjectInfo();

  const agents = flags.yes
    ? defaultAgentSelection()
    : await promptAgentSelection();

  const options: InitOptions = { project, agents };
  const targetDir = path.resolve(process.cwd(), project.name);

  console.log(
    chalk.dim(`\n📁 대상 디렉토리: ${targetDir}\n`)
  );

  // 파일 생성
  const spinner = ora("파일 생성 중...").start();

  try {
    const agentFiles = await generateAgentFiles(options);
    const settingsFile = generateSettings(options);
    const claudeMdFile = await generateClaudeMd(options);

    const allFiles = [...agentFiles, settingsFile, claudeMdFile];

    if (flags.dryRun) {
      spinner.stop();
      console.log(chalk.yellow("\n📋 --dry-run: 생성할 파일 목록:\n"));
      for (const f of allFiles) {
        console.log(chalk.dim(`  ${f.relativePath}`));
      }
      return;
    }

    const written = await writeFiles(targetDir, allFiles);

    spinner.succeed(
      chalk.green(`${written.length}개 파일 생성 완료!`)
    );

    // 결과 요약
    console.log(chalk.bold("\n✅ 설정 완료!\n"));
    console.log(chalk.dim("생성된 파일:"));
    for (const f of written) {
      console.log(chalk.dim(`  ${f}`));
    }

    console.log(chalk.bold("\n🚀 다음 단계:"));
    console.log(chalk.cyan(`  cd ${project.name}`));
    console.log(chalk.cyan("  claude"));
    console.log(
      chalk.dim("\n  Claude Code가 하네스 엔지니어링을 자동으로 적용합니다.\n")
    );
  } catch (error) {
    spinner.fail("파일 생성 실패");
    if (error instanceof Error) {
      console.error(chalk.red(`\n❌ ${error.message}`));
    }
    process.exit(1);
  }
}
