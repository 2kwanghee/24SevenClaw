import type { InitOptions, CatalogSkill, GeneratedFile, EnvVarDefinition } from "../types";
import catalogSkills from "../catalog/skills.json";

interface EnvVarMeta extends EnvVarDefinition {
  skillName: string;
}

/** 선택된 스킬에서 필요한 환경 변수 정의를 수집 */
function getEnvVarDefinitions(options: InitOptions): EnvVarMeta[] {
  const workflows = options.workflows?.workflows ?? [];
  const selectedSkills = (catalogSkills as CatalogSkill[]).filter((s) =>
    (workflows as string[]).includes(s.id)
  );

  const seen = new Set<string>();
  const vars: EnvVarMeta[] = [];

  for (const skill of selectedSkills) {
    for (const v of skill.envVars ?? []) {
      if (!seen.has(v.name)) {
        vars.push({ ...v, skillName: skill.name });
        seen.add(v.name);
      }
    }
  }

  return vars;
}

/** 명백히 위험한 값 감지 (셸 인젝션 등) */
function isDangerousValue(value: string): boolean {
  const patterns = [";", "&&", "||", "`", "$(", "${"];
  return patterns.some((p) => value.includes(p));
}

/** 환경 변수 값 검증 — 비어있거나 위험하면 빈 문자열 반환 */
function validateEnvValue(value: string, meta: EnvVarMeta): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (isDangerousValue(trimmed)) return "";
  return trimmed;
}

/** .env / .env.example 파일 생성 */
export function generateEnvFiles(options: InitOptions): GeneratedFile[] {
  const definitions = getEnvVarDefinitions(options);
  const envVars = options.envVars ?? {};

  // 모든 변수명 수집: 카탈로그 정의 + 사용자 추가
  const allVarNames: string[] = [];
  const varMeta = new Map<string, EnvVarMeta>();

  for (const defn of definitions) {
    allVarNames.push(defn.name);
    varMeta.set(defn.name, defn);
  }

  for (const name of Object.keys(envVars)) {
    if (!varMeta.has(name)) {
      allVarNames.push(name);
      varMeta.set(name, {
        name,
        description: "",
        pattern: "",
        required: false,
        skillName: "",
      });
    }
  }

  if (allVarNames.length === 0) return [];

  const envLines: string[] = [
    "# 환경 변수 — 이 파일을 .gitignore에 추가하세요",
    "# 자동 생성됨 (24SevenClaw)",
    "",
  ];

  const exampleLines: string[] = [
    "# 환경 변수 템플릿 — 복사하여 .env로 사용",
    "# cp .env.example .env",
    "",
  ];

  for (const name of allVarNames) {
    const meta = varMeta.get(name)!;
    const rawValue = envVars[name] ?? "";
    const value = validateEnvValue(rawValue, meta);

    // 주석 추가
    const parts: string[] = [];
    if (meta.skillName) parts.push(meta.skillName);
    if (meta.description) parts.push(meta.description);

    if (parts.length > 0) {
      const comment = parts.join(" — ");
      envLines.push(`# ${comment}`);
      exampleLines.push(`# ${comment}`);
    }

    envLines.push(`${name}=${value}`, "");
    exampleLines.push(`${name}=`, "");
  }

  return [
    { relativePath: ".env", content: envLines.join("\n") },
    { relativePath: ".env.example", content: exampleLines.join("\n") },
  ];
}

/** 선택된 스킬이 요구하는 환경 변수 정의 목록 반환 (UI에서 폼 생성용) */
export function getRequiredEnvVars(options: InitOptions): EnvVarMeta[] {
  return getEnvVarDefinitions(options);
}
