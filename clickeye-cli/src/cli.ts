import { Command } from "commander";
import { doctorCommand } from "./commands/doctor.js";
import { loginCommand, logoutCommand } from "./auth/login.js";
import { listCommand } from "./commands/list.js";

const program = new Command();

program
  .name("ce")
  .description("ClickEye CLI — 카탈로그 조회 및 프로젝트 설정 진단 도구")
  .version("1.0.0");

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

program.parse();
