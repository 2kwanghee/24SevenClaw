import inquirer from "inquirer";
import type { ProjectInfo, ProjectType, StackPreset } from "../types.js";
import stacks from "../catalog/stacks.json" with { type: "json" };

const PROJECT_TYPES: { name: string; value: ProjectType }[] = [
  { name: "웹앱 (프론트엔드 중심)", value: "webapp" },
  { name: "REST API (백엔드 중심)", value: "rest-api" },
  { name: "풀스택 (백엔드 + 프론트엔드)", value: "fullstack" },
  { name: "커스텀 (직접 설정)", value: "custom" },
];

const STACK_CHOICES: { name: string; value: StackPreset }[] = stacks.map(
  (s) => ({
    name: `${s.name}${s.id === "custom" ? "" : ` — ${s.backend} / ${s.frontend}`}`,
    value: s.id as StackPreset,
  })
);

export async function promptProjectInfo(): Promise<ProjectInfo> {
  const answers = await inquirer.prompt([
    {
      type: "input",
      name: "name",
      message: "프로젝트 이름:",
      default: "my-project",
      validate: (input: string) => {
        if (!/^[a-z0-9][a-z0-9._-]*$/.test(input)) {
          return "소문자, 숫자, 하이픈, 점, 언더스코어만 사용 가능합니다 (소문자/숫자로 시작)";
        }
        return true;
      },
    },
    {
      type: "list",
      name: "type",
      message: "프로젝트 유형:",
      choices: PROJECT_TYPES,
    },
    {
      type: "list",
      name: "stack",
      message: "기술 스택:",
      choices: STACK_CHOICES,
    },
  ]);

  return answers as ProjectInfo;
}

/** --yes 플래그 시 기본값으로 생성 */
export function defaultProjectInfo(): ProjectInfo {
  return {
    name: "my-project",
    type: "fullstack",
    stack: "fastapi-nextjs",
  };
}
