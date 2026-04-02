import { Command } from "commander";
import { initCommand } from "./commands/init.js";

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

program.parse();
