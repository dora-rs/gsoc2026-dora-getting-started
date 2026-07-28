import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const workProductRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const languages = [
  {
    directory: join(workProductRoot, "en", "src", "weeks"),
    versionHeading: "## Version Information",
    downloadsHeading: "## Downloads",
  },
  {
    directory: join(workProductRoot, "zh", "src", "weeks"),
    versionHeading: "## 版本信息",
    downloadsHeading: "## 下载",
  },
];

const errors = [];
let chapterCount = 0;

for (const language of languages) {
  const chapterFiles = readdirSync(language.directory)
    .filter((name) => name.endsWith(".md"))
    .sort();

  for (const fileName of chapterFiles) {
    chapterCount += 1;
    const filePath = join(language.directory, fileName);
    const displayPath = relative(workProductRoot, filePath).replaceAll("\\", "/");
    const lines = readFileSync(filePath, "utf8").split(/\r?\n/);
    const h1Index = lines.findIndex((line) => /^# /.test(line));
    const h2Headings = lines
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => /^## /.test(line));

    if (h1Index === -1) {
      errors.push(`${displayPath}: missing chapter title`);
      continue;
    }

    const contentBeforeTitle = lines
      .slice(0, h1Index)
      .some((line) => line.trim().length > 0);
    if (contentBeforeTitle) {
      errors.push(`${displayPath}: chapter title must be the first content`);
    }

    const versionSection = h2Headings[0];
    if (!versionSection || versionSection.line !== language.versionHeading) {
      errors.push(
        `${displayPath}: first section must be "${language.versionHeading}"`,
      );
      continue;
    }

    const contentBeforeVersion = lines
      .slice(h1Index + 1, versionSection.index)
      .some((line) => line.trim().length > 0);
    if (contentBeforeVersion) {
      errors.push(
        `${displayPath}: version information must immediately follow the title`,
      );
    }

    const downloadsIndex = h2Headings.findIndex(
      ({ line }) => line === language.downloadsHeading,
    );
    if (downloadsIndex > -1 && downloadsIndex !== 1) {
      errors.push(
        `${displayPath}: "${language.downloadsHeading}" must immediately follow the version section`,
      );
    }

    const archiveLinkLines = lines
      .map((line, index) => ({ line, index }))
      .filter(({ line }) =>
        /\]\(\.\.\/assets\/[^)\s]+\.zip(?:#[^)\s]*)?\)/i.test(line),
      );

    if (archiveLinkLines.length === 0) {
      continue;
    }

    if (downloadsIndex === -1) {
      errors.push(
        `${displayPath}: downloadable archives require a "${language.downloadsHeading}" section`,
      );
      continue;
    }

    const downloadSection = h2Headings[downloadsIndex];
    const nextSection = h2Headings[downloadsIndex + 1];
    const downloadEnd = nextSection ? nextSection.index : lines.length;
    for (const archiveLink of archiveLinkLines) {
      if (
        archiveLink.index <= downloadSection.index ||
        archiveLink.index >= downloadEnd
      ) {
        errors.push(
          `${displayPath}:${archiveLink.index + 1}: archive links must be in "${language.downloadsHeading}"`,
        );
      }
    }
  }
}

if (errors.length > 0) {
  console.error("Chapter structure validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log(`Validated chapter structure: ${chapterCount} files.`);
