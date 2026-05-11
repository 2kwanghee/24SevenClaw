import { readFile, writeFile, mkdir, unlink, chmod } from "node:fs/promises";
import { join } from "node:path";
import { homedir } from "node:os";
import type { WizardState } from "./state.js";

function sessionDir(): string {
  return join(homedir(), ".config", "clickeye");
}

function sessionFile(sessionId: string): string {
  return join(sessionDir(), `session-${sessionId}.json`);
}

export async function saveSession(state: WizardState): Promise<void> {
  if (!state.sessionId) return;
  const dir = sessionDir();
  const file = sessionFile(state.sessionId);
  await mkdir(dir, { recursive: true, mode: 0o700 });
  await writeFile(file, JSON.stringify(state, null, 2), {
    encoding: "utf-8",
    mode: 0o600,
  });
  await chmod(file, 0o600);
}

export async function loadSession(sessionId: string): Promise<WizardState | null> {
  let raw: string;
  try {
    raw = await readFile(sessionFile(sessionId), "utf-8");
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw new Error(
      `세션 파일을 읽을 수 없습니다: ${String(err)}\n` +
        `세션 파일이 손상되었을 수 있습니다. 삭제 후 새로 시작하세요:\n` +
        `  rm ${sessionFile(sessionId)}`,
    );
  }
  try {
    return JSON.parse(raw) as WizardState;
  } catch {
    throw new Error(
      `세션 파일이 손상되었습니다 (JSON 파싱 실패).\n` +
        `삭제 후 새로 시작하세요:\n  rm ${sessionFile(sessionId)}`,
    );
  }
}

export async function deleteSession(sessionId: string): Promise<void> {
  try {
    await unlink(sessionFile(sessionId));
  } catch {
    // 파일이 없어도 무시
  }
}
