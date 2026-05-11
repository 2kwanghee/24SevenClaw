import chalk from "chalk";
import ora from "ora";
import { downloadAndExtract } from "../api/download.js";
import { loadCredentials } from "../auth/credentials.js";

interface RedownloadFlags {
  envFile?: string;
  output?: string;
  name?: string;
}

export async function redownloadCommand(
  projectId: string,
  flags: RedownloadFlags,
): Promise<void> {
  const creds = await loadCredentials();
  if (!creds) {
    console.error(
      chalk.red("\n❌ 인증이 필요합니다. `ce login`을 먼저 실행해 주세요.\n"),
    );
    process.exit(1);
  }

  const envVars: Record<string, string> = {};

  if (flags.envFile) {
    const { readFile } = await import("node:fs/promises");
    try {
      const content = await readFile(flags.envFile, "utf-8");
      for (const line of content.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith("#")) continue;
        const eqIdx = trimmed.indexOf("=");
        if (eqIdx === -1) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        const value = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
        if (key) envVars[key] = value;
      }
    } catch {
      console.error(chalk.red(`\n❌ 환경 파일을 읽을 수 없습니다: ${flags.envFile}\n`));
      process.exit(1);
    }
  }

  const projectName = flags.name ?? projectId;
  const destDir = flags.output ?? process.cwd();

  const spinner = ora("프로젝트 ZIP을 다운로드하고 있습니다...").start();
  try {
    const projectDir = await downloadAndExtract(
      projectId,
      envVars,
      projectName,
      destDir,
      true,
    );
    spinner.succeed(`압축 해제 완료: ${projectDir}`);
    console.log(chalk.bold.green("\n✅ 재다운로드 완료!\n"));
  } catch (err) {
    spinner.fail("다운로드 실패");
    console.error(chalk.red(`\n❌ ${String(err)}\n`));
    process.exit(1);
  }
}
