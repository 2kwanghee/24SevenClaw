import inquirer from "inquirer";
import chalk from "chalk";
import { apiClient } from "../api/client.js";
import {
  loadCredentials,
  saveCredentials,
  clearCredentials,
  decodeJwtExpiry,
} from "./credentials.js";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export async function loginCommand(): Promise<void> {
  console.log(chalk.bold("\n🔐 ClickEye 로그인\n"));

  const existing = await loadCredentials();
  if (existing) {
    const { proceed } = await inquirer.prompt<{ proceed: boolean }>([
      {
        type: "confirm",
        name: "proceed",
        message: `이미 ${chalk.cyan(existing.email)}(으)로 로그인되어 있습니다. 다시 로그인하시겠습니까?`,
        default: false,
      },
    ]);
    if (!proceed) return;
  }

  const { email, password } = await inquirer.prompt<{
    email: string;
    password: string;
  }>([
    {
      type: "input",
      name: "email",
      message: "이메일:",
      validate: (v: string) =>
        /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) || "유효한 이메일을 입력해 주세요",
    },
    {
      type: "password",
      name: "password",
      message: "비밀번호:",
      mask: "*",
    },
  ]);

  try {
    const res = await apiClient.post<TokenResponse>(
      "/api/v1/auth/login",
      { email, password },
      false, // 로그인은 인증 불필요
    );

    await saveCredentials({
      access_token: res.access_token,
      refresh_token: res.refresh_token,
      email,
      expires_at: decodeJwtExpiry(res.access_token),
    });

    console.log(chalk.green(`\n✅ ${email}으로 로그인되었습니다.\n`));
  } catch (err) {
    const msg = err instanceof Error ? err.message : "로그인에 실패했습니다";
    console.error(chalk.red(`\n❌ ${msg}\n`));
    process.exit(1);
  }
}

export async function logoutCommand(): Promise<void> {
  const creds = await loadCredentials();
  if (!creds) {
    console.log(chalk.yellow("현재 로그인 상태가 아닙니다."));
    return;
  }
  await clearCredentials();
  console.log(chalk.green(`\n✅ ${creds.email} 로그아웃되었습니다.\n`));
}
