import { Command } from "commander";
import { initCommand } from "./commands/init.js";
import { addCommand } from "./commands/add.js";
import { doctorCommand } from "./commands/doctor.js";
import { loginCommand, logoutCommand } from "./auth/login.js";

const program = new Command();

program
  .name("24sc")
  .description(
    "ClickEye CLI — AI 솔루션 빌더 (clickeye.ai 위저드의 터미널 버전)"
  )
  .version("0.1.0");

program
  .command("init")
  .description("새 프로젝트에 AI 에이전트 워크플로우를 설정합니다")
  .option("--yes", "모든 질문을 기본값으로 스킵")
  .option("--dry-run", "생성할 파일 목록만 출력 (실제 생성 안 함)")
  .action(initCommand);

program
  .command("add")
  .description("기존 프로젝트에 에이전트, 스킬, Hook을 추가합니다")
  .argument("<category>", "추가할 유형 (agent | skill | hook)")
  .argument("<id>", "추가할 항목 ID (예: backend, tdd, harness-gate)")
  .option("--yes", "확인 질문 없이 덮어쓰기")
  .option("--dry-run", "생성할 파일 목록만 출력 (실제 생성 안 함)")
  .option("--stack <preset>", "기술 스택 프리셋 지정")
  .action(addCommand);

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

program.parse();
