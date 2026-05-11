import { createWriteStream, mkdirSync } from "node:fs";
import { unlink, mkdir } from "node:fs/promises";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { tmpdir } from "node:os";
import { loadCredentials } from "../auth/credentials.js";

const execFileAsync = promisify(execFile);
const REQUEST_TIMEOUT_MS = 120_000; // ZIP generation can be slow

function getApiBase(): string {
  return process.env["CLICKEYE_API_URL"] ?? "http://localhost:8000";
}

/**
 * Downloads a project ZIP from the API and extracts it to destDir.
 * Returns the resolved destination path.
 */
export async function downloadAndExtract(
  projectId: string,
  envVars: Record<string, string>,
  projectName: string,
  destDir: string = process.cwd(),
): Promise<string> {
  const creds = await loadCredentials();
  if (!creds) throw new Error("인증이 필요합니다. `ce login`을 먼저 실행해 주세요.");

  const url = `${getApiBase()}/api/v1/projects/${projectId}/redownload`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${creds.access_token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ env_vars: envVars }),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`ZIP 다운로드 실패 (${response.status}): ${text}`);
  }

  // Write ZIP to temp file
  const tmpZip = join(tmpdir(), `ce-project-${Date.now()}.zip`);
  const buffer = await response.arrayBuffer();
  await writeBuffer(tmpZip, buffer);

  // Extract to destDir/<projectName>/
  const safeName = projectName.replace(/[^a-zA-Z0-9가-힣._-]/g, "_");
  const projectDir = resolve(destDir, safeName);
  await mkdir(projectDir, { recursive: true });

  try {
    await execFileAsync("unzip", ["-o", tmpZip, "-d", projectDir]);
  } finally {
    await unlink(tmpZip).catch(() => undefined);
  }

  return projectDir;
}

function writeBuffer(filePath: string, buffer: ArrayBuffer): Promise<void> {
  return new Promise((resolve, reject) => {
    const stream = createWriteStream(filePath);
    stream.on("error", reject);
    stream.on("finish", resolve);
    stream.write(Buffer.from(buffer));
    stream.end();
  });
}
