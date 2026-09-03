import json
import pdfplumber

SOURCE = "/Users/anafathabassumsadiq/Downloads/links - next 60.xlsx"
OUTPUT = "/Users/anafathabassumsadiq/Documents/Codex/2026-09-03/i-x20/work/next60.json"

rows = []
with pdfplumber.open(SOURCE) as pdf:
    for page_number, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        if not tables:
            continue
        for source_row in tables[0]:
            if page_number == 1 and source_row[0] == "SNO":
                continue
            sno, register_no, name, dept, leetcode, codechef = [value or "" for value in source_row]
            linkedin = ""
            if leetcode.strip().lower().startswith("https://www.linkedin.com/"):
                linkedin, leetcode = leetcode, ""
            rows.append([
                register_no, name, codechef, leetcode, "", "", "", linkedin, "", sno, dept
            ])

with open(OUTPUT, "w", encoding="utf-8") as stream:
    json.dump(rows, stream, ensure_ascii=False, indent=2)

print(f"Extracted {len(rows)} rows")
