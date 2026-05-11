import chalk from "chalk";
import {
  fetchCatalog,
  type CatalogCategory,
  type CatalogItem,
} from "../api/catalog.js";
import { AuthRequiredError, ApiError } from "../api/client.js";

const VALID_CATEGORIES: CatalogCategory[] = [
  "agents",
  "skills",
  "hooks",
  "platforms",
  "pipelines",
];

function getLabel(item: CatalogItem): string {
  return item.label;
}

function getDescription(item: CatalogItem): string {
  return "description" in item && item.description ? item.description : "";
}

function getSlug(item: CatalogItem): string {
  return "slug" in item ? item.slug : item.id;
}

export async function listCommand(category: string): Promise<void> {
  if (!VALID_CATEGORIES.includes(category as CatalogCategory)) {
    console.error(
      chalk.red(
        `❌ 알 수 없는 카테고리: ${category}\n` +
          `   사용 가능: ${VALID_CATEGORIES.join(" | ")}`,
      ),
    );
    process.exit(1);
  }

  try {
    const items = await fetchCatalog(category as CatalogCategory);

    if (items.length === 0) {
      console.log(chalk.yellow(`\n${category} 카탈로그가 비어 있습니다.\n`));
      return;
    }

    console.log(chalk.bold(`\n📦 ${category} (${items.length}개)\n`));

    for (const item of items) {
      const slug = getSlug(item);
      const label = getLabel(item);
      const desc = getDescription(item);

      console.log(
        `  ${chalk.cyan(slug.padEnd(22))} ${chalk.white(label)}`,
      );
      if (desc) {
        console.log(`  ${" ".repeat(22)} ${chalk.dim(desc)}`);
      }
    }
    console.log();
  } catch (err) {
    if (err instanceof AuthRequiredError) {
      console.error(chalk.red(`\n❌ ${err.message}\n`));
    } else if (err instanceof ApiError) {
      console.error(chalk.red(`\n❌ API 오류 (${err.status}): ${err.message}\n`));
    } else {
      console.error(chalk.red(`\n❌ 카탈로그 조회 실패: ${String(err)}\n`));
    }
    process.exit(1);
  }
}
