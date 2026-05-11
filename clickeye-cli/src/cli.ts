import { Command } from "commander";
import { initCommand } from "./commands/init.js";
import { doctorCommand } from "./commands/doctor.js";
import { loginCommand, logoutCommand } from "./auth/login.js";
import { listCommand } from "./commands/list.js";
import { redownloadCommand } from "./commands/redownload.js";

const program = new Command();

program
  .name("ce")
  .description(
    "ClickEye CLI — AI 솔루션 빌더 (clickeye.ai 위저드의 터미널 버전)"
  )
  .version("1.0.0");

program
  .command("init")
  .description("12단계 위저드로 AI 솔루션을 설계하고 ZIP을 다운로드합니다")
  .option("--resume <sessionId>", "이전 세션 ID로 재개합니다")
  .action(initCommand);

program
  .command("list")
  .description("카탈로그 항목을 조회합니다")
  .argument("<category>", "조회할 유형 (agents | skills | hooks | platforms | pipelines)")
  .action(listCommand);

program
  .command("doctor")
  .description("현재 프로젝트의 ClickEye 설정 상태를 진단합니다")
  .action(doctorCommand);

program
  .command("login")
  .description("ClickEye 계정으로 로그인합니다")
  .action(loginCommand);

program
  .command("logout")
  .description("현재 계정에서 로그아웃합니다")
  .action(logoutCommand);

program
  .command("redownload")
  .description("기존 프로젝트의 ZIP을 재다운로드하고 압축 해제합니다")
  .argument("<projectId>", "재다운로드할 프로젝트 UUID")
  .option("--env-file <path>", ".env 파일에서 환경 변수를 읽어옵니다")
  .option("--output <dir>", "압축 해제 대상 디렉토리 (기본값: 현재 디렉토리)")
  .option("--name <name>", "압축 해제 디렉토리명 (기본값: 프로젝트 ID)")
  .action((projectId: string, flags: { envFile?: string; output?: string; name?: string }) =>
    redownloadCommand(projectId, flags),
  );

program.parse();
