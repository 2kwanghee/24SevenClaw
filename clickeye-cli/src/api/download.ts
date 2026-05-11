import { unlink, mkdir, readdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { tmpdir } from "node:os";
import { randomUUID } from "node:crypto";
import { apiClient } from "./client.js";

const execFileAsync = promisify(execFile);
const ZIP_TIMEOUT_MS = 120_000;

/**
 * Downloads a project ZIP from the API and extracts it to destDir/<safeName>/.
 * With force=false (default) the destination must not exist or be empty.
 * With force=true existing files are overwritten (used by `ce redownload`).
 * Returns the resolved destination path.
 */
export async function downloadAndExtract(
  projectId: string,
  envVars: Record<string, string>,
  projectName: string,
  destDir: string = process.cwd(),
  force = false,
): Promise<string> {
  try {
    await execFileAsync("unzip", ["--version"]);
  } catch {
    throw new Error(
      "`unzip`이 설치되어 있지 않습니다. `sudo apt install unzip`을 실행해 주세요.",
    );
  }

  const safeName = projectName.replace(/[^a-zA-Z0-9가-힣._-]/g, "_");
  if (!safeName || /^\.+$/.test(safeName)) {
    throw new Error("유효하지 않은 프로젝트 이름입니다.");
  }
  const projectDir = resolve(destDir, safeName);

  // Guard before the expensive API call
  if (!force) {
    const dirFiles = await readdir(projectDir).catch(() => [] as string[]);
    if (dirFiles.length > 0) {
      throw new Error(
        `대상 디렉토리가 비어 있지 않습니다: ${projectDir}\n` +
        "  `ce redownload <projectId>`를 사용하면 덮어쓸 수 있습니다.",
      );
    }
  }

  const response = await apiClient.postRaw(
    `/api/v1/projects/${projectId}/redownload`,
    { env_vars: envVars },
    ZIP_TIMEOUT_MS,
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`ZIP 다운로드 실패 (${response.status}): ${text}`);
  }

  const tmpZip = join(tmpdir(), `ce-project-${randomUUID()}.zip`);
  const buffer = await response.arrayBuffer();
  await writeFile(tmpZip, Buffer.from(buffer));

  await mkdir(projectDir, { recursive: true });

  try {
    const flags = force
      ? ["-o", "-q", tmpZip, "-d", projectDir]
      : ["-q", tmpZip, "-d", projectDir];
    await execFileAsync("unzip", flags);
  } finally {
    await unlink(tmpZip).catch(() => undefined);
  }

  return projectDir;
}

/** @deprecated use downloadAndExtract(..., true) */
export async function downloadAndExtractForce(
  projectId: string,
  envVars: Record<string, string>,
  projectName: string,
  destDir: string = process.cwd(),
): Promise<string> {
  return downloadAndExtract(projectId, envVars, projectName, destDir, true);
}
