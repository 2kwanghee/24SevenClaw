// src/cli.ts
import { Command } from "commander";

// src/commands/init.ts
import path7 from "path";
import chalk from "chalk";
import ora from "ora";

// src/wizard/project.ts
import inquirer from "inquirer";

// src/catalog/stacks.json
var stacks_default = [
  {
    id: "fastapi-nextjs",
    name: "FastAPI + Next.js",
    backend: "FastAPI + SQLAlchemy",
    frontend: "Next.js 15 + Tailwind",
    test: {
      backend: "uv run pytest --tb=short -q",
      frontend: "npm run test"
    },
    lint: {
      backend: "uv run ruff check .",
      frontend: "npm run lint"
    },
    typecheck: {
      backend: "uv run mypy app/",
      frontend: "npx tsc --noEmit"
    }
  },
  {
    id: "django-react",
    name: "Django + React",
    backend: "Django + DRF",
    frontend: "React + Vite",
    test: {
      backend: "uv run pytest --tb=short -q",
      frontend: "npm run test"
    },
    lint: {
      backend: "uv run ruff check .",
      frontend: "npm run lint"
    },
    typecheck: {
      backend: "uv run mypy .",
      frontend: "npx tsc --noEmit"
    }
  },
  {
    id: "express-vue",
    name: "Express + Vue",
    backend: "Express + Prisma",
    frontend: "Vue 3 + Vite",
    test: {
      backend: "npm run test:backend",
      frontend: "npm run test"
    },
    lint: {
      backend: "npx eslint src/",
      frontend: "npm run lint"
    },
    typecheck: {
      backend: "npx tsc --noEmit",
      frontend: "npx tsc --noEmit"
    }
  },
  {
    id: "nestjs-nextjs",
    name: "NestJS + Next.js",
    backend: "NestJS + TypeORM",
    frontend: "Next.js 15",
    test: {
      backend: "npm run test:backend",
      frontend: "npm run test"
    },
    lint: {
      backend: "npx eslint src/",
      frontend: "npm run lint"
    },
    typecheck: {
      backend: "npx tsc --noEmit",
      frontend: "npx tsc --noEmit"
    }
  },
  {
    id: "flask-react",
    name: "Flask + React",
    backend: "Flask + SQLAlchemy",
    frontend: "React + Vite",
    test: {
      backend: "uv run pytest --tb=short -q",
      frontend: "npm run test"
    },
    lint: {
      backend: "uv run ruff check .",
      frontend: "npm run lint"
    },
    typecheck: {
      backend: "uv run mypy .",
      frontend: "npx tsc --noEmit"
    }
  },
  {
    id: "custom",
    name: "\uCEE4\uC2A4\uD140 (\uC9C1\uC811 \uC785\uB825)",
    backend: "",
    frontend: "",
    test: {
      backend: "",
      frontend: ""
    },
    lint: {
      backend: "",
      frontend: ""
    },
    typecheck: {
      backend: "",
      frontend: ""
    }
  }
];

// src/wizard/project.ts
var PROJECT_TYPES = [
  { name: "\uC6F9\uC571 (\uD504\uB860\uD2B8\uC5D4\uB4DC \uC911\uC2EC)", value: "webapp" },
  { name: "REST API (\uBC31\uC5D4\uB4DC \uC911\uC2EC)", value: "rest-api" },
  { name: "\uD480\uC2A4\uD0DD (\uBC31\uC5D4\uB4DC + \uD504\uB860\uD2B8\uC5D4\uB4DC)", value: "fullstack" },
  { name: "\uCEE4\uC2A4\uD140 (\uC9C1\uC811 \uC124\uC815)", value: "custom" }
];
var STACK_CHOICES = stacks_default.map(
  (s) => ({
    name: `${s.name}${s.id === "custom" ? "" : ` \u2014 ${s.backend} / ${s.frontend}`}`,
    value: s.id
  })
);
async function promptProjectInfo() {
  const answers = await inquirer.prompt([
    {
      type: "input",
      name: "name",
      message: "\uD504\uB85C\uC81D\uD2B8 \uC774\uB984:",
      default: "my-project",
      validate: (input) => {
        if (!/^[a-z0-9][a-z0-9._-]*$/.test(input)) {
          return "\uC18C\uBB38\uC790, \uC22B\uC790, \uD558\uC774\uD508, \uC810, \uC5B8\uB354\uC2A4\uCF54\uC5B4\uB9CC \uC0AC\uC6A9 \uAC00\uB2A5\uD569\uB2C8\uB2E4 (\uC18C\uBB38\uC790/\uC22B\uC790\uB85C \uC2DC\uC791)";
        }
        return true;
      }
    },
    {
      type: "list",
      name: "type",
      message: "\uD504\uB85C\uC81D\uD2B8 \uC720\uD615:",
      choices: PROJECT_TYPES
    },
    {
      type: "list",
      name: "stack",
      message: "\uAE30\uC220 \uC2A4\uD0DD:",
      choices: STACK_CHOICES
    }
  ]);
  return answers;
}
function defaultProjectInfo() {
  return {
    name: "my-project",
    type: "fullstack",
    stack: "fastapi-nextjs"
  };
}

// src/wizard/agents.ts
import inquirer2 from "inquirer";

// src/catalog/agents.json
var agents_default = [
  {
    id: "backend",
    name: "\uC2DC\uB2C8\uC5B4 \uBC31\uC5D4\uB4DC \uC5D4\uC9C0\uB2C8\uC5B4",
    description: "API \uC124\uACC4, DB, \uC11C\uBC84 \uB85C\uC9C1 \uC804\uB2F4",
    outputFile: "api-agent.md",
    template: "agents/api-agent.md.hbs",
    required: false
  },
  {
    id: "frontend",
    name: "\uD504\uB860\uD2B8\uC5D4\uB4DC \uC804\uBB38\uAC00",
    description: "\uCEF4\uD3EC\uB10C\uD2B8, \uC0C1\uD0DC\uAD00\uB9AC, \uB77C\uC6B0\uD305 \uC804\uB2F4",
    outputFile: "web-agent.md",
    template: "agents/web-agent.md.hbs",
    required: false
  },
  {
    id: "uiux",
    name: "UI/UX \uB514\uC790\uC774\uB108",
    description: "\uC811\uADFC\uC131, \uBC18\uC751\uD615, \uB514\uC790\uC778 \uC2DC\uC2A4\uD15C \uC804\uB2F4",
    outputFile: "uiux-agent.md",
    template: "agents/uiux-agent.md.hbs",
    required: false
  },
  {
    id: "devops",
    name: "DevOps \uC5D4\uC9C0\uB2C8\uC5B4",
    description: "Docker, CI/CD, \uBC30\uD3EC \uC804\uB2F4",
    outputFile: "infra-agent.md",
    template: "agents/infra-agent.md.hbs",
    required: false
  },
  {
    id: "fullstack",
    name: "\uD480\uC2A4\uD0DD \uC2DC\uB2C8\uC5B4",
    description: "\uBC31\uC5D4\uB4DC+\uD504\uB860\uD2B8 \uD1B5\uD569 \uAC1C\uBC1C",
    outputFile: "fullstack-agent.md",
    template: "agents/fullstack-agent.md.hbs",
    required: false
  },
  {
    id: "harness",
    name: "\uD558\uB124\uC2A4 \uC5D4\uC9C0\uB2C8\uC5B4 (\uD544\uC218)",
    description: "4\uB2E8\uACC4 \uD488\uC9C8 \uD1B5\uC81C \u2014 Router\u2192Context\u2192Loop\u2192Worker",
    outputFile: "harness-guide.md",
    template: "agents/harness-guide.md.hbs",
    required: true
  }
];

// src/wizard/agents.ts
async function promptAgentSelection() {
  const optionalAgents = agents_default.filter((a) => !a.required);
  const answers = await inquirer2.prompt([
    {
      type: "checkbox",
      name: "agents",
      message: "\uACE0\uC6A9\uD560 \uC5D0\uC774\uC804\uD2B8\uB97C \uC120\uD0DD\uD558\uC138\uC694 (\uD558\uB124\uC2A4 \uC5D4\uC9C0\uB2C8\uC5B4\uB294 \uD544\uC218 \uD3EC\uD568):",
      choices: optionalAgents.map((a) => ({
        name: `${a.name} \u2014 ${a.description}`,
        value: a.id,
        checked: a.id === "backend" || a.id === "frontend"
      }))
    }
  ]);
  const agents = [...answers.agents, "harness"];
  return { agents };
}
function defaultAgentSelection() {
  return {
    agents: ["backend", "frontend", "harness"]
  };
}

// src/wizard/workflow.ts
import inquirer3 from "inquirer";

// src/catalog/skills.json
var skills_default = [
  {
    id: "tdd",
    name: "TDD \uC2A4\uB9C8\uD2B8 \uCF54\uB529",
    description: "\uD14C\uC2A4\uD2B8 \uBA3C\uC800 \uC791\uC131 \u2192 \uCF54\uB4DC \uAD6C\uD604 \u2192 \uB9AC\uD329\uD130\uB9C1 \uC6CC\uD06C\uD50C\uB85C",
    template: "skills/tdd.md.hbs",
    outputFile: "tdd-smart-coding.md",
    dependencies: [],
    hooks: []
  },
  {
    id: "ai-critique",
    name: "AI \uCF54\uB4DC \uB9AC\uBDF0",
    description: "\uCF54\uB4DC \uC791\uC131 \uD6C4 AI \uC790\uB3D9 \uB9AC\uBDF0 + \uAC1C\uC120 \uC81C\uC548",
    template: "skills/ai-critique.md.hbs",
    outputFile: "ai-critique.md",
    dependencies: [],
    hooks: ["PostToolUse"]
  },
  {
    id: "linear",
    name: "Linear \uC5F0\uB3D9",
    description: "Linear \uC774\uC288 \uAE30\uBC18 \uC791\uC5C5 \uCD94\uC801 + \uC0C1\uD0DC \uB3D9\uAE30\uD654",
    template: "skills/linear.md.hbs",
    outputFile: "linear-sync.md",
    dependencies: ["linear"],
    hooks: []
  },
  {
    id: "ralph-loop",
    name: "Ralph \uC790\uC728 \uB8E8\uD504",
    description: "fix_plan.md \uAE30\uBC18 \uC790\uC728 \uAC1C\uBC1C \uB8E8\uD504 (\uAD6C\uD604\u2192\uAC80\uC99D\u2192\uCEE4\uBC0B)",
    template: "skills/ralph-loop.md.hbs",
    outputFile: "ralph-loop.md",
    dependencies: [],
    hooks: []
  },
  {
    id: "harness-gate",
    name: "\uD558\uB124\uC2A4 Gate",
    description: "lint + typecheck + test \uD1B5\uACFC \uD6C4\uC5D0\uB9CC \uCEE4\uBC0B \uD5C8\uC6A9",
    template: "skills/harness-gate.md.hbs",
    outputFile: "harness-gate.md",
    dependencies: [],
    hooks: ["UserPromptSubmit"]
  }
];

// src/wizard/workflow.ts
async function promptWorkflowSelection() {
  const answers = await inquirer3.prompt([
    {
      type: "checkbox",
      name: "workflows",
      message: "\uC801\uC6A9\uD560 \uC6CC\uD06C\uD50C\uB85C\uC6B0\uB97C \uC120\uD0DD\uD558\uC138\uC694 (\uD558\uB124\uC2A4 Gate \uAD8C\uC7A5):",
      choices: skills_default.map((s) => ({
        name: `${s.name} \u2014 ${s.description}`,
        value: s.id,
        checked: s.id === "harness-gate" || s.id === "tdd"
      }))
    }
  ]);
  return { workflows: answers.workflows };
}
function defaultWorkflowSelection() {
  return {
    workflows: ["tdd", "harness-gate"]
  };
}

// src/generators/agent.ts
import fs2 from "fs/promises";
import path2 from "path";
import Handlebars from "handlebars";

// src/paths.ts
import { fileURLToPath } from "url";
import path from "path";
import fs from "fs";
var __dirname2 = path.dirname(fileURLToPath(import.meta.url));
function resolveDir(name) {
  const bundled = path.join(__dirname2, name);
  if (fs.existsSync(bundled)) return bundled;
  const source = path.join(__dirname2, "..", name);
  if (fs.existsSync(source)) return source;
  throw new Error(`${name} \uB514\uB809\uD1A0\uB9AC\uB97C \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4`);
}
var TEMPLATES_DIR = resolveDir("templates");
var CATALOG_DIR = resolveDir("catalog");

// src/generators/agent.ts
async function loadTemplate(templatePath) {
  const fullPath = path2.join(TEMPLATES_DIR, templatePath);
  return fs2.readFile(fullPath, "utf-8");
}
async function generateAgentFiles(options) {
  const stack = stacks_default.find((s) => s.id === options.project.stack);
  const selectedAgents = agents_default.filter(
    (a) => options.agents.agents.includes(a.id) || a.required
  );
  const files = [];
  for (const agent of selectedAgents) {
    const templateSource = await loadTemplate(agent.template);
    const template = Handlebars.compile(templateSource);
    const content = template({
      projectName: options.project.name,
      projectType: options.project.type,
      stack,
      agent
    });
    files.push({
      relativePath: `.claude/agents/${agent.outputFile}`,
      content
    });
  }
  return files;
}
function getAgentReferences(options) {
  const selectedAgents = agents_default.filter(
    (a) => options.agents.agents.includes(a.id) || a.required
  );
  return selectedAgents.map((a) => ({
    file: `.claude/agents/${a.outputFile}`,
    name: a.name
  }));
}

// src/generators/skill.ts
import fs3 from "fs/promises";
import path3 from "path";
import Handlebars2 from "handlebars";
async function generateSkillFiles(options) {
  const workflows = options.workflows?.workflows ?? [];
  if (workflows.length === 0) return [];
  const stack = stacks_default.find((s) => s.id === options.project.stack);
  const selectedSkills = skills_default.filter(
    (s) => workflows.includes(s.id)
  );
  const files = [];
  for (const skill of selectedSkills) {
    const templateSource = await fs3.readFile(
      path3.join(TEMPLATES_DIR, skill.template),
      "utf-8"
    );
    const template = Handlebars2.compile(templateSource);
    const content = template({
      projectName: options.project.name,
      projectType: options.project.type,
      stack
    });
    files.push({
      relativePath: `.claude/skills/${skill.outputFile}`,
      content
    });
  }
  return files;
}
function getSelectedSkills(options) {
  const workflows = options.workflows?.workflows ?? [];
  return skills_default.filter(
    (s) => workflows.includes(s.id)
  );
}

// src/generators/settings.ts
function generateSettings(options) {
  const hooks = {
    UserPromptSubmit: [],
    PreToolUse: [],
    PostToolUse: [],
    Stop: []
  };
  const workflows = options.workflows?.workflows ?? [];
  if (workflows.includes("harness-gate")) {
    hooks.UserPromptSubmit.push({
      type: "command",
      command: "bash scripts/harness-gate.sh"
    });
  }
  const selectedSkills = getSelectedSkills(options);
  for (const skill of selectedSkills) {
    for (const hookName of skill.hooks) {
      if (hookName === "PostToolUse") {
        hooks.PostToolUse.push({
          type: "command",
          command: `echo "\u{1F50D} AI \uB9AC\uBDF0: ${skill.name} \uAC80\uC99D \uC911..."`
        });
      }
    }
  }
  const settings = {
    permissions: {
      allow: [
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash(npm run lint:*)",
        "Bash(npm run test:*)",
        "Bash(npx tsc --noEmit)"
      ],
      deny: [
        "Bash(rm -rf *)",
        "Bash(git push *)",
        "Bash(git checkout main)"
      ]
    },
    hooks
  };
  return {
    relativePath: ".claude/settings.json",
    content: JSON.stringify(settings, null, 2) + "\n"
  };
}

// src/generators/claude-md.ts
import fs4 from "fs/promises";
import path4 from "path";
import Handlebars3 from "handlebars";
async function generateClaudeMd(options) {
  const templateSource = await fs4.readFile(
    path4.join(TEMPLATES_DIR, "claude.md.hbs"),
    "utf-8"
  );
  const template = Handlebars3.compile(templateSource);
  const stack = stacks_default.find((s) => s.id === options.project.stack);
  const agentRefs = getAgentReferences(options);
  const content = template({
    projectName: options.project.name,
    projectType: options.project.type,
    stack,
    agentRefs,
    generatedAt: (/* @__PURE__ */ new Date()).toISOString().split("T")[0]
  });
  return {
    relativePath: "CLAUDE.md",
    content
  };
}

// src/generators/hook.ts
import fs5 from "fs/promises";
import path5 from "path";
import Handlebars4 from "handlebars";
async function generateHookFiles(options) {
  const workflows = options.workflows?.workflows ?? [];
  if (!workflows.includes("harness-gate")) return [];
  const stack = stacks_default.find((s) => s.id === options.project.stack);
  const templateSource = await fs5.readFile(
    path5.join(TEMPLATES_DIR, "hooks/harness-gate.sh.hbs"),
    "utf-8"
  );
  const template = Handlebars4.compile(templateSource);
  const content = template({ stack });
  return [
    {
      relativePath: "scripts/harness-gate.sh",
      content
    }
  ];
}

// src/generators/scripts.ts
function generateScriptFiles(options) {
  const workflows = options.workflows?.workflows ?? [];
  if (workflows.length === 0) return [];
  const stack = stacks_default.find((s) => s.id === options.project.stack);
  const files = [];
  if (workflows.includes("ralph-loop")) {
    files.push({
      relativePath: ".ralph/fix_plan.md",
      content: `# Ralph Loop \u2014 \uC791\uC5C5 \uD050 (Fix Plan)

> Claude\uAC00 \uC774 \uD30C\uC77C\uC744 \uC77D\uACE0 \uBBF8\uC644\uB8CC(\`- [ ]\`) \uD56D\uBAA9\uC744 \uCC98\uB9AC\uD55C\uB2E4.
> \uC644\uB8CC \uC2DC \`- [x]\`\uB85C \uD45C\uC2DC\uD558\uACE0 \uCEE4\uBC0B\uD55C\uB2E4.
> \`- [!]\`\uB294 \uAC74\uB108\uB6F4 \uD56D\uBAA9 (\uC0AC\uC720 \uAE30\uB85D \uD544\uC218).

---

## P0: \uAE34\uAE09

## P1: \uB192\uC74C

## P2: \uAE30\uB2A5 \uC694\uAD6C\uC0AC\uD56D

- [ ] **\uCCAB \uBC88\uC9F8 \uD0DC\uC2A4\uD06C\uB97C \uC5EC\uAE30\uC5D0 \uC791\uC131\uD558\uC138\uC694**
  > \uC0C1\uC138 \uC124\uBA85

---

## \uC9C4\uD589 \uB85C\uADF8

| \uC2DC\uAC01 | \uD56D\uBAA9 | \uC0C1\uD0DC | \uBE44\uACE0 |
|------|------|------|------|
`
    });
  }
  if ((workflows.includes("tdd") || workflows.includes("harness-gate")) && stack && stack.id !== "custom") {
    const lines = ["#!/usr/bin/env bash", "# \uC804\uCCB4 \uD14C\uC2A4\uD2B8 \uC2E4\uD589 \uC2A4\uD06C\uB9BD\uD2B8", "set -euo pipefail", ""];
    if (stack.test.backend) {
      lines.push("echo '\u{1F9EA} \uBC31\uC5D4\uB4DC \uD14C\uC2A4\uD2B8...'", stack.test.backend, "");
    }
    if (stack.test.frontend) {
      lines.push("echo '\u{1F9EA} \uD504\uB860\uD2B8\uC5D4\uB4DC \uD14C\uC2A4\uD2B8...'", stack.test.frontend, "");
    }
    lines.push('echo "\u2705 \uBAA8\uB4E0 \uD14C\uC2A4\uD2B8 \uD1B5\uACFC"');
    files.push({
      relativePath: "scripts/run-tests.sh",
      content: lines.join("\n") + "\n"
    });
  }
  return files;
}

// src/generators/writer.ts
import fs6 from "fs/promises";
import path6 from "path";
async function writeFiles(targetDir, files) {
  const written = [];
  for (const file of files) {
    const fullPath = path6.join(targetDir, file.relativePath);
    const dir = path6.dirname(fullPath);
    await fs6.mkdir(dir, { recursive: true });
    await fs6.writeFile(fullPath, file.content, "utf-8");
    written.push(file.relativePath);
  }
  return written;
}

// src/commands/init.ts
async function initCommand(flags) {
  console.log(
    chalk.bold("\n\u{1F916} 24SevenClaw \u2014 AI \uC5D0\uC774\uC804\uD2B8 \uC6CC\uD06C\uD50C\uB85C\uC6B0 \uC124\uC815\n")
  );
  const project = flags.yes ? defaultProjectInfo() : await promptProjectInfo();
  const agents = flags.yes ? defaultAgentSelection() : await promptAgentSelection();
  const workflows = flags.yes ? defaultWorkflowSelection() : await promptWorkflowSelection();
  const options = { project, agents, workflows };
  const targetDir = path7.resolve(process.cwd(), project.name);
  console.log(
    chalk.dim(`
\u{1F4C1} \uB300\uC0C1 \uB514\uB809\uD1A0\uB9AC: ${targetDir}
`)
  );
  const spinner = ora("\uD30C\uC77C \uC0DD\uC131 \uC911...").start();
  try {
    const agentFiles = await generateAgentFiles(options);
    const skillFiles = await generateSkillFiles(options);
    const hookFiles = await generateHookFiles(options);
    const scriptFiles = generateScriptFiles(options);
    const settingsFile = generateSettings(options);
    const claudeMdFile = await generateClaudeMd(options);
    const allFiles = [
      ...agentFiles,
      ...skillFiles,
      ...hookFiles,
      ...scriptFiles,
      settingsFile,
      claudeMdFile
    ];
    if (flags.dryRun) {
      spinner.stop();
      console.log(chalk.yellow("\n\u{1F4CB} --dry-run: \uC0DD\uC131\uD560 \uD30C\uC77C \uBAA9\uB85D:\n"));
      for (const f of allFiles) {
        console.log(chalk.dim(`  ${f.relativePath}`));
      }
      return;
    }
    const written = await writeFiles(targetDir, allFiles);
    spinner.succeed(
      chalk.green(`${written.length}\uAC1C \uD30C\uC77C \uC0DD\uC131 \uC644\uB8CC!`)
    );
    console.log(chalk.bold("\n\u2705 \uC124\uC815 \uC644\uB8CC!\n"));
    console.log(chalk.dim("\uC0DD\uC131\uB41C \uD30C\uC77C:"));
    for (const f of written) {
      console.log(chalk.dim(`  ${f}`));
    }
    console.log(chalk.bold("\n\u{1F680} \uB2E4\uC74C \uB2E8\uACC4:"));
    console.log(chalk.cyan(`  cd ${project.name}`));
    console.log(chalk.cyan("  claude"));
    console.log(
      chalk.dim("\n  Claude Code\uAC00 \uD558\uB124\uC2A4 \uC5D4\uC9C0\uB2C8\uC5B4\uB9C1\uC744 \uC790\uB3D9\uC73C\uB85C \uC801\uC6A9\uD569\uB2C8\uB2E4.\n")
    );
  } catch (error) {
    spinner.fail("\uD30C\uC77C \uC0DD\uC131 \uC2E4\uD328");
    if (error instanceof Error) {
      console.error(chalk.red(`
\u274C ${error.message}`));
    }
    process.exit(1);
  }
}

// src/commands/add.ts
import fs7 from "fs/promises";
import path8 from "path";
import chalk2 from "chalk";
import ora2 from "ora";
import inquirer4 from "inquirer";
import Handlebars5 from "handlebars";
async function readSettings(targetDir) {
  const settingsPath = path8.join(targetDir, ".claude/settings.json");
  try {
    const raw = await fs7.readFile(settingsPath, "utf-8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
async function updateSettingsHooks(targetDir, hookName, entry) {
  const settings = await readSettings(targetDir);
  if (!settings) return;
  const hooks = settings.hooks ?? {};
  if (!hooks[hookName]) {
    hooks[hookName] = [];
  }
  const exists = hooks[hookName].some((h) => h.command === entry.command);
  if (!exists) {
    hooks[hookName].push(entry);
  }
  settings.hooks = hooks;
  const settingsPath = path8.join(targetDir, ".claude/settings.json");
  await fs7.writeFile(settingsPath, JSON.stringify(settings, null, 2) + "\n");
}
async function detectStack(targetDir) {
  try {
    const claudeMd = await fs7.readFile(
      path8.join(targetDir, "CLAUDE.md"),
      "utf-8"
    );
    for (const stack of stacks_default) {
      if (claudeMd.includes(stack.name)) return stack.id;
    }
  } catch {
  }
  return "fastapi-nextjs";
}
async function addAgent(agentId, targetDir, flags) {
  const agent = agents_default.find(
    (a) => a.id === agentId
  );
  if (!agent) {
    console.error(
      chalk2.red(`
\u274C \uC54C \uC218 \uC5C6\uB294 \uC5D0\uC774\uC804\uD2B8: "${agentId}"`)
    );
    console.log(chalk2.dim("\n\uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uC5D0\uC774\uC804\uD2B8:"));
    for (const a of agents_default) {
      console.log(chalk2.dim(`  ${a.id} \u2014 ${a.name}: ${a.description}`));
    }
    process.exit(1);
  }
  const outputPath = path8.join(targetDir, `.claude/agents/${agent.outputFile}`);
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer4.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: `${agent.outputFile}\uC774(\uAC00) \uC774\uBBF8 \uC874\uC7AC\uD569\uB2C8\uB2E4. \uB36E\uC5B4\uC4F0\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?`,
          default: false
        }
      ]);
      if (!overwrite) {
        console.log(chalk2.yellow("\u23ED\uFE0F  \uAC74\uB108\uB700"));
        return;
      }
    }
  }
  const stackPreset = flags.stack ? flags.stack : await detectStack(targetDir);
  const stack = stacks_default.find((s) => s.id === stackPreset);
  const templateSource = await fs7.readFile(
    path8.join(TEMPLATES_DIR, agent.template),
    "utf-8"
  );
  const template = Handlebars5.compile(templateSource);
  const content = template({
    projectName: path8.basename(targetDir),
    projectType: "fullstack",
    stack,
    agent
  });
  const file = {
    relativePath: `.claude/agents/${agent.outputFile}`,
    content
  };
  if (flags.dryRun) {
    console.log(chalk2.yellow("\n\u{1F4CB} --dry-run: \uC0DD\uC131\uD560 \uD30C\uC77C:"));
    console.log(chalk2.dim(`  ${file.relativePath}`));
    return;
  }
  const spinner = ora2("\uC5D0\uC774\uC804\uD2B8 \uD30C\uC77C \uC0DD\uC131 \uC911...").start();
  await fs7.mkdir(path8.dirname(outputPath), { recursive: true });
  await fs7.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk2.green(`\uC5D0\uC774\uC804\uD2B8 \uCD94\uAC00 \uC644\uB8CC: ${agent.name}`));
  console.log(chalk2.dim(`  ${file.relativePath}`));
}
async function addSkill(skillId, targetDir, flags) {
  const skill = skills_default.find(
    (s) => s.id === skillId
  );
  if (!skill) {
    console.error(
      chalk2.red(`
\u274C \uC54C \uC218 \uC5C6\uB294 \uC2A4\uD0AC: "${skillId}"`)
    );
    console.log(chalk2.dim("\n\uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uC2A4\uD0AC:"));
    for (const s of skills_default) {
      console.log(chalk2.dim(`  ${s.id} \u2014 ${s.name}: ${s.description}`));
    }
    process.exit(1);
  }
  const outputPath = path8.join(
    targetDir,
    `.claude/skills/${skill.outputFile}`
  );
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer4.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: `${skill.outputFile}\uC774(\uAC00) \uC774\uBBF8 \uC874\uC7AC\uD569\uB2C8\uB2E4. \uB36E\uC5B4\uC4F0\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?`,
          default: false
        }
      ]);
      if (!overwrite) {
        console.log(chalk2.yellow("\u23ED\uFE0F  \uAC74\uB108\uB700"));
        return;
      }
    }
  }
  const stackPreset = flags.stack ? flags.stack : await detectStack(targetDir);
  const stack = stacks_default.find((s) => s.id === stackPreset);
  const templateSource = await fs7.readFile(
    path8.join(TEMPLATES_DIR, skill.template),
    "utf-8"
  );
  const template = Handlebars5.compile(templateSource);
  const content = template({
    projectName: path8.basename(targetDir),
    projectType: "fullstack",
    stack
  });
  const file = {
    relativePath: `.claude/skills/${skill.outputFile}`,
    content
  };
  if (flags.dryRun) {
    console.log(chalk2.yellow("\n\u{1F4CB} --dry-run: \uC0DD\uC131\uD560 \uD30C\uC77C:"));
    console.log(chalk2.dim(`  ${file.relativePath}`));
    return;
  }
  const spinner = ora2("\uC2A4\uD0AC \uD30C\uC77C \uC0DD\uC131 \uC911...").start();
  await fs7.mkdir(path8.dirname(outputPath), { recursive: true });
  await fs7.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk2.green(`\uC2A4\uD0AC \uCD94\uAC00 \uC644\uB8CC: ${skill.name}`));
  console.log(chalk2.dim(`  ${file.relativePath}`));
  for (const hookName of skill.hooks) {
    await updateSettingsHooks(targetDir, hookName, {
      type: "command",
      command: hookName === "UserPromptSubmit" ? "bash scripts/harness-gate.sh" : `echo "\u{1F50D} AI \uB9AC\uBDF0: ${skill.name} \uAC80\uC99D \uC911..."`
    });
    console.log(
      chalk2.dim(`  \u21B3 settings.json\uC5D0 ${hookName} Hook \uB4F1\uB85D\uB428`)
    );
  }
}
async function addHook(hookId, targetDir, flags) {
  if (hookId !== "harness-gate") {
    console.error(
      chalk2.red(`
\u274C \uC54C \uC218 \uC5C6\uB294 Hook: "${hookId}"`)
    );
    console.log(chalk2.dim("\n\uC0AC\uC6A9 \uAC00\uB2A5\uD55C Hook:"));
    console.log(
      chalk2.dim("  harness-gate \u2014 lint + typecheck + test \uAC8C\uC774\uD2B8")
    );
    process.exit(1);
  }
  const outputPath = path8.join(targetDir, "scripts/harness-gate.sh");
  if (await fileExists(outputPath)) {
    if (!flags.yes) {
      const { overwrite } = await inquirer4.prompt([
        {
          type: "confirm",
          name: "overwrite",
          message: "harness-gate.sh\uAC00 \uC774\uBBF8 \uC874\uC7AC\uD569\uB2C8\uB2E4. \uB36E\uC5B4\uC4F0\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?",
          default: false
        }
      ]);
      if (!overwrite) {
        console.log(chalk2.yellow("\u23ED\uFE0F  \uAC74\uB108\uB700"));
        return;
      }
    }
  }
  const stackPreset = flags.stack ? flags.stack : await detectStack(targetDir);
  const stack = stacks_default.find((s) => s.id === stackPreset);
  const templateSource = await fs7.readFile(
    path8.join(TEMPLATES_DIR, "hooks/harness-gate.sh.hbs"),
    "utf-8"
  );
  const template = Handlebars5.compile(templateSource);
  const content = template({ stack });
  if (flags.dryRun) {
    console.log(chalk2.yellow("\n\u{1F4CB} --dry-run: \uC0DD\uC131\uD560 \uD30C\uC77C:"));
    console.log(chalk2.dim("  scripts/harness-gate.sh"));
    return;
  }
  const spinner = ora2("Hook \uC2A4\uD06C\uB9BD\uD2B8 \uC0DD\uC131 \uC911...").start();
  await fs7.mkdir(path8.dirname(outputPath), { recursive: true });
  await fs7.writeFile(outputPath, content, "utf-8");
  spinner.succeed(chalk2.green("Hook \uCD94\uAC00 \uC644\uB8CC: harness-gate"));
  console.log(chalk2.dim("  scripts/harness-gate.sh"));
  await updateSettingsHooks(targetDir, "UserPromptSubmit", {
    type: "command",
    command: "bash scripts/harness-gate.sh"
  });
  console.log(
    chalk2.dim("  \u21B3 settings.json\uC5D0 UserPromptSubmit Hook \uB4F1\uB85D\uB428")
  );
}
async function fileExists(filePath) {
  try {
    await fs7.access(filePath);
    return true;
  } catch {
    return false;
  }
}
async function addCommand(category, id, flags) {
  const targetDir = process.cwd();
  const validCategories = ["agent", "skill", "hook"];
  if (!validCategories.includes(category)) {
    console.error(
      chalk2.red(`
\u274C \uC54C \uC218 \uC5C6\uB294 \uCE74\uD14C\uACE0\uB9AC: "${category}"`)
    );
    console.log(chalk2.dim("\n\uC0AC\uC6A9\uBC95:"));
    console.log(chalk2.dim("  24sc add agent <id>   \u2014 \uC5D0\uC774\uC804\uD2B8 \uCD94\uAC00"));
    console.log(chalk2.dim("  24sc add skill <id>   \u2014 \uC2A4\uD0AC \uCD94\uAC00"));
    console.log(chalk2.dim("  24sc add hook <id>    \u2014 Hook \uCD94\uAC00"));
    process.exit(1);
  }
  if (!id) {
    console.error(
      chalk2.red(`
\u274C ID\uB97C \uC9C0\uC815\uD574\uC8FC\uC138\uC694`)
    );
    console.log(
      chalk2.dim(`
\uC0AC\uC6A9\uBC95: 24sc add ${category} <id>`)
    );
    process.exit(1);
  }
  console.log(
    chalk2.bold(`
\u{1F527} ${category} \uCD94\uAC00: ${id}
`)
  );
  switch (category) {
    case "agent":
      await addAgent(id, targetDir, flags);
      break;
    case "skill":
      await addSkill(id, targetDir, flags);
      break;
    case "hook":
      await addHook(id, targetDir, flags);
      break;
  }
}

// src/commands/doctor.ts
import fs8 from "fs/promises";
import path9 from "path";
import chalk3 from "chalk";
async function fileExists2(filePath) {
  try {
    await fs8.access(filePath);
    return true;
  } catch {
    return false;
  }
}
async function isExecutable(filePath) {
  try {
    await fs8.access(filePath, fs8.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}
async function checkClaudeDir(targetDir) {
  const exists = await fileExists2(path9.join(targetDir, ".claude"));
  return {
    label: ".claude/ \uB514\uB809\uD1A0\uB9AC \uC874\uC7AC",
    passed: exists,
    detail: exists ? void 0 : "24sc init\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694"
  };
}
async function checkSettingsJson(targetDir) {
  const settingsPath = path9.join(targetDir, ".claude/settings.json");
  if (!await fileExists2(settingsPath)) {
    return {
      label: "settings.json \uC874\uC7AC",
      passed: false,
      detail: "24sc init\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694"
    };
  }
  try {
    const raw = await fs8.readFile(settingsPath, "utf-8");
    const settings = JSON.parse(raw);
    const hasPermissions = settings.permissions != null;
    const hasHooks = settings.hooks != null;
    if (!hasPermissions || !hasHooks) {
      const missing = [];
      if (!hasPermissions) missing.push("permissions");
      if (!hasHooks) missing.push("hooks");
      return {
        label: "settings.json \uC720\uD6A8\uC131",
        passed: false,
        detail: `\uD544\uC218 \uD544\uB4DC \uB204\uB77D: ${missing.join(", ")}`
      };
    }
    return { label: "settings.json \uC720\uD6A8\uC131", passed: true };
  } catch (error) {
    return {
      label: "settings.json \uC720\uD6A8\uC131",
      passed: false,
      detail: error instanceof SyntaxError ? "JSON \uD30C\uC2F1 \uC2E4\uD328 \u2014 \uC62C\uBC14\uB978 JSON \uD615\uC2DD\uC778\uC9C0 \uD655\uC778\uD558\uC138\uC694" : "\uD30C\uC77C \uC77D\uAE30 \uC2E4\uD328"
    };
  }
}
async function checkHookScripts(targetDir) {
  const results = [];
  const scriptsDir = path9.join(targetDir, "scripts");
  if (!await fileExists2(scriptsDir)) {
    return [];
  }
  const entries = await fs8.readdir(scriptsDir);
  const shellScripts = entries.filter((e) => e.endsWith(".sh"));
  for (const script of shellScripts) {
    const scriptPath = path9.join(scriptsDir, script);
    const executable = await isExecutable(scriptPath);
    results.push({
      label: `scripts/${script} \uC2E4\uD589 \uAD8C\uD55C`,
      passed: executable,
      detail: executable ? void 0 : `chmod +x scripts/${script} \uC73C\uB85C \uAD8C\uD55C\uC744 \uBD80\uC5EC\uD558\uC138\uC694`
    });
  }
  return results;
}
async function checkAgentReferences(targetDir) {
  const results = [];
  const claudeMdPath = path9.join(targetDir, "CLAUDE.md");
  if (!await fileExists2(claudeMdPath)) {
    return [
      {
        label: "CLAUDE.md \uC874\uC7AC",
        passed: false,
        detail: "24sc init\uC73C\uB85C \uC0DD\uC131\uD558\uC138\uC694"
      }
    ];
  }
  const claudeMd = await fs8.readFile(claudeMdPath, "utf-8");
  const agentRefs = claudeMd.match(/\.claude\/agents\/[\w-]+\.md/g) ?? [];
  for (const ref of agentRefs) {
    const refPath = path9.join(targetDir, ref);
    const exists = await fileExists2(refPath);
    results.push({
      label: `${ref} \uCC38\uC870 \uBB34\uACB0\uC131`,
      passed: exists,
      detail: exists ? void 0 : `\uD30C\uC77C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. 24sc add agent <id>\uB85C \uCD94\uAC00\uD558\uC138\uC694`
    });
  }
  if (agentRefs.length === 0) {
    results.push({
      label: "\uC5D0\uC774\uC804\uD2B8 \uD30C\uC77C \uCC38\uC870",
      passed: true,
      detail: "CLAUDE.md\uC5D0 \uC5D0\uC774\uC804\uD2B8 \uCC38\uC870 \uC5C6\uC74C (\uC815\uC0C1)"
    });
  }
  return results;
}
async function checkEnvVars(targetDir) {
  const results = [];
  const envPath = path9.join(targetDir, ".env");
  if (!await fileExists2(envPath)) {
    const examplePath = path9.join(targetDir, ".env.example");
    if (await fileExists2(examplePath)) {
      results.push({
        label: ".env \uD30C\uC77C \uC874\uC7AC",
        passed: false,
        detail: ".env.example\uC744 \uBCF5\uC0AC\uD558\uC5EC .env\uB97C \uC0DD\uC131\uD558\uC138\uC694"
      });
    }
    return results;
  }
  return results;
}
async function checkClaudeMd(targetDir) {
  const exists = await fileExists2(path9.join(targetDir, "CLAUDE.md"));
  return {
    label: "CLAUDE.md \uC874\uC7AC",
    passed: exists,
    detail: exists ? void 0 : "24sc init\uC73C\uB85C \uC0DD\uC131\uD558\uC138\uC694"
  };
}
async function doctorCommand() {
  const targetDir = process.cwd();
  console.log(chalk3.bold("\n\u{1F50D} 24SevenClaw \uC124\uC815 \uC9C4\uB2E8\n"));
  console.log(chalk3.dim(`\uAC80\uC0AC \uACBD\uB85C: ${targetDir}
`));
  const allResults = [];
  allResults.push(await checkClaudeDir(targetDir));
  allResults.push(await checkClaudeMd(targetDir));
  allResults.push(await checkSettingsJson(targetDir));
  allResults.push(...await checkHookScripts(targetDir));
  allResults.push(...await checkAgentReferences(targetDir));
  allResults.push(...await checkEnvVars(targetDir));
  let passCount = 0;
  let failCount = 0;
  for (const result of allResults) {
    const icon = result.passed ? chalk3.green("\u2705") : chalk3.red("\u274C");
    console.log(`${icon} ${result.label}`);
    if (result.detail) {
      console.log(chalk3.dim(`   \u2192 ${result.detail}`));
    }
    if (result.passed) passCount++;
    else failCount++;
  }
  console.log(chalk3.bold("\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500"));
  if (failCount === 0) {
    console.log(
      chalk3.green(`
\u{1F389} \uBAA8\uB4E0 \uAC80\uC0AC \uD1B5\uACFC! (${passCount}/${passCount})`)
    );
  } else {
    console.log(
      chalk3.yellow(
        `
\u26A0\uFE0F  ${failCount}\uAC1C \uD56D\uBAA9 \uC2E4\uD328 (${passCount}/${passCount + failCount} \uD1B5\uACFC)`
      )
    );
    console.log(
      chalk3.dim(
        "\n\uC704 \u274C \uD56D\uBAA9\uC758 \uC548\uB0B4\uB97C \uB530\uB77C \uBB38\uC81C\uB97C \uD574\uACB0\uD558\uC138\uC694."
      )
    );
  }
  console.log();
}

// src/cli.ts
var program = new Command();
program.name("24sc").description(
  "24SevenClaw CLI \u2014 \uD558\uB124\uC2A4 \uC5D4\uC9C0\uB2C8\uC5B4\uB9C1\uC774 \uD0D1\uC7AC\uB41C AI \uAC1C\uBC1C \uC6CC\uD06C\uD50C\uB85C\uC6B0\uB97C \uD55C \uC904 \uBA85\uB839\uC73C\uB85C \uAD6C\uCD95"
).version("0.1.0");
program.command("init").description("\uC0C8 \uD504\uB85C\uC81D\uD2B8\uC5D0 AI \uC5D0\uC774\uC804\uD2B8 \uC6CC\uD06C\uD50C\uB85C\uC6B0\uB97C \uC124\uC815\uD569\uB2C8\uB2E4").option("--yes", "\uBAA8\uB4E0 \uC9C8\uBB38\uC744 \uAE30\uBCF8\uAC12\uC73C\uB85C \uC2A4\uD0B5").option("--dry-run", "\uC0DD\uC131\uD560 \uD30C\uC77C \uBAA9\uB85D\uB9CC \uCD9C\uB825 (\uC2E4\uC81C \uC0DD\uC131 \uC548 \uD568)").action(initCommand);
program.command("add").description("\uAE30\uC874 \uD504\uB85C\uC81D\uD2B8\uC5D0 \uC5D0\uC774\uC804\uD2B8, \uC2A4\uD0AC, Hook\uC744 \uCD94\uAC00\uD569\uB2C8\uB2E4").argument("<category>", "\uCD94\uAC00\uD560 \uC720\uD615 (agent | skill | hook)").argument("<id>", "\uCD94\uAC00\uD560 \uD56D\uBAA9 ID (\uC608: backend, tdd, harness-gate)").option("--yes", "\uD655\uC778 \uC9C8\uBB38 \uC5C6\uC774 \uB36E\uC5B4\uC4F0\uAE30").option("--dry-run", "\uC0DD\uC131\uD560 \uD30C\uC77C \uBAA9\uB85D\uB9CC \uCD9C\uB825 (\uC2E4\uC81C \uC0DD\uC131 \uC548 \uD568)").option("--stack <preset>", "\uAE30\uC220 \uC2A4\uD0DD \uD504\uB9AC\uC14B \uC9C0\uC815").action(addCommand);
program.command("doctor").description("\uD604\uC7AC \uD504\uB85C\uC81D\uD2B8\uC758 24SevenClaw \uC124\uC815 \uC0C1\uD0DC\uB97C \uC9C4\uB2E8\uD569\uB2C8\uB2E4").action(doctorCommand);
program.parse();
//# sourceMappingURL=cli.js.map