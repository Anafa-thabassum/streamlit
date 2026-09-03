import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "/Users/anafathabassumsadiq/Downloads/links - next 60.xlsx";
const outputPath = "/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/outputs/links-next-60-profile-atlas.xlsx";
const previewDir = "/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/work/next60-previews";
const mode = process.argv[2] || "inspect";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));

if (mode === "inspect") {
  const summary = await workbook.inspect({
    kind: "workbook,sheet,table,region,computedStyle",
    maxChars: 14000,
    tableMaxRows: 10,
    tableMaxCols: 14,
    tableMaxCellChars: 100,
  });
  console.log(summary.ndjson);
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheet of workbook.worksheets.items) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1.2, format: "png" });
    await fs.writeFile(`${previewDir}/${sheet.name.replace(/[^a-z0-9_-]/gi, "_")}-before.png`, new Uint8Array(await preview.arrayBuffer()));
  }
  process.exit(0);
}

for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange(true);
  if (!used) continue;
  const header = used.getRow(0);
  header.format = {
    fill: "#14213D",
    font: { bold: true, color: "#FFFFFF", size: 11 },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    wrapText: true,
    borders: { bottom: { style: "medium", color: "#00A6A6" } },
  };
  header.format.rowHeight = 30;
  used.format.font = { name: "Aptos", size: 10 };
  header.format.font = { name: "Aptos Display", size: 11, bold: true, color: "#FFFFFF" };
  used.format.verticalAlignment = "center";
  used.format.autofitColumns();
  used.format.autofitRows();
  const colCount = used.columnCount;
  for (let col = 0; col < colCount; col++) {
    const column = used.getColumn(col);
    if (column.format.columnWidth > 34) column.format.columnWidth = 34;
    if (column.format.columnWidth < 12) column.format.columnWidth = 12;
  }
  if (used.rowCount > 1) {
    const data = used.getRangeByIndexes(1, 0, used.rowCount - 1, used.columnCount);
    data.format.borders = { insideHorizontal: { style: "thin", color: "#E5EAF0" } };
  }
  sheet.freezePanes.freezeRows(1);
  sheet.showGridLines = false;
}

await fs.mkdir(previewDir, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1.2, format: "png" });
  await fs.writeFile(`${previewDir}/${sheet.name.replace(/[^a-z0-9_-]/gi, "_")}-after.png`, new Uint8Array(await preview.arrayBuffer()));
}

const check = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 9000, tableMaxRows: 10, tableMaxCols: 14 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
await fs.mkdir(new URL("../outputs/", import.meta.url), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
