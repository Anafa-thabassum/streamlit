import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputPath = "/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/outputs/links-next-60-profile-atlas.xlsx";
const previewPath = "/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/work/next60-profile-atlas-preview.png";
const rows = JSON.parse(await fs.readFile("/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/work/next60.json", "utf8"));
const headers = ["Register No", "Name", "CodeChef", "LeetCode", "HackerRank", "Codeforces", "GFG", "LinkedIn", "GitHub", "SNO", "Dept"];

const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Profiles");
sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers, ...rows];
const used = sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length);
used.format.font = { name: "Aptos", size: 10, color: "#172033" };
used.format.verticalAlignment = "center";
const header = sheet.getRangeByIndexes(0, 0, 1, headers.length);
header.format = {
  fill: "#14213D",
  font: { name: "Aptos Display", size: 11, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "left",
  verticalAlignment: "center",
  wrapText: true,
  borders: { bottom: { style: "medium", color: "#00A6A6" } },
};
header.format.rowHeight = 30;
const data = sheet.getRangeByIndexes(1, 0, rows.length, headers.length);
data.format.borders = { insideHorizontal: { style: "thin", color: "#E3E8EF" } };
data.format.rowHeight = 24;
sheet.getRange(`A2:A${rows.length + 1}`).format.numberFormat = "@";
sheet.getRange(`J2:J${rows.length + 1}`).format.numberFormat = "0";
for (const address of [`C2:C${rows.length + 1}`, `D2:D${rows.length + 1}`, `E2:E${rows.length + 1}`, `F2:F${rows.length + 1}`, `G2:G${rows.length + 1}`, `H2:H${rows.length + 1}`, `I2:I${rows.length + 1}`]) {
  sheet.getRange(address).format.font = { name: "Aptos", size: 10, color: "#0563C1" };
}
const widths = [17, 25, 48, 48, 32, 32, 32, 44, 36, 8, 10];
widths.forEach((width, index) => {
  sheet.getRangeByIndexes(0, index, rows.length + 1, 1).format.columnWidth = width;
});
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(2);
sheet.showGridLines = false;
sheet.tables.add(`A1:K${rows.length + 1}`, true, "ProfileAtlasInput").style = "TableStyleMedium2";
sheet.getRange(`A2:A${rows.length + 1}`).format.numberFormat = "@";
header.format = {
  fill: "#14213D",
  font: { name: "Aptos Display", size: 11, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "left",
  verticalAlignment: "center",
  wrapText: true,
  borders: { bottom: { style: "medium", color: "#00A6A6" } },
};

const check = await workbook.inspect({ kind: "table", range: `Profiles!A1:K${rows.length + 1}`, include: "values,formulas", tableMaxRows: 65, tableMaxCols: 11, maxChars: 24000 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const preview = await workbook.render({ sheetName: "Profiles", range: "A1:K20", scale: 1.2, format: "png" });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
