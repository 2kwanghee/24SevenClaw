import { Command } from "commander";
import { initCommand } from "./commands/init.js";
import { addCommand } from "./commands/add.js";
import { doctorCommand } from "./commands/doctor.js";

const program = new Command();

program
  .name("24sc")
  .description(
    "24SevenClaw CLI — 하네스 엔지니어링이 탑재된 AI 개발 워크플로우를 한 줄 명령으로 구축"
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
  .description("현재 프로젝트의 24SevenClaw 설정 상태를 진단합니다")
  .action(doctorCommand);

program.parse();
