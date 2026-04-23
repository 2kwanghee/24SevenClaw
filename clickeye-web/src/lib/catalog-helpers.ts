import type { CatalogHook, CatalogSkill } from "./api-client";

export interface SkillEnvGroup {
  skillId: string;
  skillLabel: string;
  bodyMd: string | null;
  vars: Array<{
    name: string;
    required: boolean;
    description?: string;
  }>;
}

/**
 * 선택된 스킬 + 훅의 env_vars를 그룹별로 수집한다.
 * - 스킬/훅 순서대로 처리
 * - 동일한 env_var name은 첫 번째 소스에서만 포함 (중복 제거)
 */
export function collectEnvVars(
  allSkills: CatalogSkill[] | undefined,
  allHooks: CatalogHook[] | undefined,
  selectedSkills: string[],
  selectedHooks: string[],
): SkillEnvGroup[] {
  const seen = new Set<string>();
  const groups: SkillEnvGroup[] = [];

  const selectedSkillObjects = (allSkills ?? []).filter((s) =>
    selectedSkills.includes(s.id),
  );
  const selectedHookObjects = (allHooks ?? []).filter((h) =>
    selectedHooks.includes(h.id),
  );

  for (const skill of selectedSkillObjects) {
    if (!skill.env_vars || skill.env_vars.length === 0) continue;
    const unique = skill.env_vars.filter((v) => {
      if (seen.has(v.name)) return false;
      seen.add(v.name);
      return true;
    });
    if (unique.length === 0) continue;
    groups.push({
      skillId: skill.id,
      skillLabel: skill.label,
      bodyMd: ("body_md" in skill ? (skill as CatalogSkill & { body_md: string | null }).body_md : null) ?? null,
      vars: unique,
    });
  }

  for (const hook of selectedHookObjects) {
    const hookWithEnv = hook as CatalogHook & {
      env_vars?: Array<{ name: string; required: boolean; description?: string }>;
      body_md?: string | null;
    };
    if (!hookWithEnv.env_vars || hookWithEnv.env_vars.length === 0) continue;
    const unique = hookWithEnv.env_vars.filter((v) => {
      if (seen.has(v.name)) return false;
      seen.add(v.name);
      return true;
    });
    if (unique.length === 0) continue;
    groups.push({
      skillId: hook.id,
      skillLabel: hook.label,
      bodyMd: hookWithEnv.body_md ?? null,
      vars: unique,
    });
  }

  return groups;
}

/**
 * env_vars를 가진 스킬/훅 id 목록 반환 (배지 표시용)
 */
export function getSkillsRequiringApiKey(
  allSkills: CatalogSkill[] | undefined,
  selectedSkills: string[],
): Set<string> {
  const result = new Set<string>();
  for (const skill of allSkills ?? []) {
    if (selectedSkills.includes(skill.id) && skill.env_vars.length > 0) {
      result.add(skill.id);
    }
  }
  return result;
}
