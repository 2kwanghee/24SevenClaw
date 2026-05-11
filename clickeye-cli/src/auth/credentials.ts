import { readFile, writeFile, unlink, mkdir, chmod } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";

export interface Credentials {
  access_token: string;
  refresh_token: string;
  email: string;
  expires_at: number; // epoch ms
}

// 호출 시점마다 계산 — 테스트에서 HOME 환경변수 오버라이드가 반영된다
function credDir(): string {
  return join(homedir(), ".config", "clickeye");
}
function credFile(): string {
  return join(credDir(), "credentials.json");
}

export async function loadCredentials(): Promise<Credentials | null> {
  try {
    const raw = await readFile(credFile(), "utf8");
    return JSON.parse(raw) as Credentials;
  } catch {
    return null;
  }
}

export async function saveCredentials(creds: Credentials): Promise<void> {
  // 디렉토리는 0700으로 생성 — 타 사용자가 목록 조회 불가
  await mkdir(credDir(), { recursive: true, mode: 0o700 });
  await writeFile(credFile(), JSON.stringify(creds, null, 2), {
    encoding: "utf8",
    mode: 0o600,
  });
  // 기존 파일 re-open 시 mode 옵션이 무시되므로 명시적으로 0600 재적용
  await chmod(credFile(), 0o600);
}

export async function clearCredentials(): Promise<void> {
  try {
    await unlink(credFile());
  } catch {
    // 파일이 없으면 무시
  }
}

export function isExpired(creds: Credentials): boolean {
  // 30초 여유를 두고 만료 판단
  return Date.now() >= creds.expires_at - 30_000;
}

export function decodeJwtExpiry(token: string): number {
  try {
    const payload = token.split(".")[1];
    if (!payload) return Date.now() + 3600_000;
    const decoded = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8"),
    ) as { exp?: number };
    return (decoded.exp ?? 0) * 1000;
  } catch {
    return Date.now() + 3600_000; // 1시간 fallback
  }
}
