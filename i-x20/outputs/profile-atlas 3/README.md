# Profile Atlas

Profile Atlas is a beginner-friendly Streamlit application that stores public competitive-programming and developer profile links, refreshes available statistics, keeps historical snapshots, and creates professional Excel reports.

The normal workflow is:

1. Upload an Excel workbook once.
2. Click **Fetch All**.
3. Wait while each public profile is processed independently.
4. Generate and download the Excel report.
5. Next week, click **Fetch This Week**—no upload is needed again.

## Supported platforms

| Platform | Collection strategy | Important limits |
|---|---|---|
| Codeforces | Official public API | Public profiles only |
| GitHub | Official REST API | Contributions are not exposed by the REST profile API and remain `N/A` |
| LeetCode | Public GraphQL response used by public profiles | Endpoint/fields may change; no password is used |
| CodeChef | Public profile page | Only clearly exposed values are parsed |
| HackerRank | Public profile endpoints | Only public fields are used |
| GeeksforGeeks | Public profile page | Only clearly exposed values are parsed |
| LinkedIn | URL preservation only | No scraping of gated pages; metrics remain `N/A` without a permitted API |

The app never invents statistics. Missing, private, unsupported, or unavailable values are displayed as `N/A`.

## Install

Python 3.11 or newer is recommended.

### Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Your browser opens automatically. After the first installation, `start.command` (macOS) or `start.bat` (Windows) starts the app when the virtual environment already exists.

## Input workbook

Only `.xlsx` files are accepted. `Register No` and `Name` columns are required. All platform columns are optional and can appear in any order:

| Register No | Name | CodeChef | LeetCode | HackerRank | Codeforces | GFG | LinkedIn | GitHub |
|---|---|---|---|---|---|---|---|---|
| REG-001 | Student 1 | https://www.codechef.com/users/example | https://leetcode.com/u/example/ |  | https://codeforces.com/profile/example |  |  | https://github.com/example |

Use `sample_input.xlsx` as a starting point. Empty cells are allowed. Invalid links are skipped and recorded in the Errors sheet. Duplicate student/platform/username entries are stored once, while the same public account assigned to multiple students is fetched once per refresh and saved for each student.

## Excel output

Reports are saved in `reports/` with dated, non-overwriting names such as `profile_report_2026-09-03.xlsx`. Each workbook contains:

1. Summary
2. Weekly Progress
3. CodeChef
4. LeetCode
5. HackerRank
6. Codeforces
7. GFG
8. LinkedIn
9. GitHub
10. Activity Log
11. Errors

Headers are frozen, filters are enabled, URLs are clickable, column widths are bounded, and useful number columns have conditional formatting.

## Configuration

Copy `.env.example` to `.env`. The GitHub token is optional:

```dotenv
GITHUB_TOKEN=
DATABASE_PATH=data/profiles.db
REPORTS_DIR=reports
FETCH_INTERVAL_DAYS=7
REQUEST_TIMEOUT_SECONDS=15
MAX_WORKERS=6
```

A fine-grained GitHub personal access token with read-only access to public resources raises the API rate limit. Never commit `.env`. The application does not store the token in SQLite or Excel.

## Weekly scheduler

`scheduler.py` performs one unattended pass: it selects active profiles older than `FETCH_INTERVAL_DAYS`, refreshes them, stores new snapshots and activity, and creates a report.

```bash
python scheduler.py
```

Run that command weekly with Windows Task Scheduler, cron, launchd, or another scheduler. Streamlit does not need to stay open.

## Data storage and safety

SQLite data is stored in `data/profiles.db`. The database keeps profile links, status, immutable snapshots, deduplicated activities, errors, and report history. It never stores passwords, browser cookies, user session tokens, or private profile data.

Requests have timeouts, bounded exponential retries, platform-specific pacing, and controlled concurrency. A failed profile is logged and the rest of the batch continues.

## Tests

Tests use temporary databases and mocked adapters; they do not make real platform requests.

```bash
pytest -q
```

To confirm the Streamlit module loads:

```bash
python -m py_compile app.py scheduler.py tracker/*.py tracker/scrapers/*.py
```

## Troubleshooting

- **Workbook rejected:** confirm the extension is `.xlsx` and a column is exactly named `Name` (case does not matter).
- **Profile failed:** open Reports, generate a workbook, and read the Errors sheet. Common causes are a renamed account, public endpoint changes, rate limits, or a private profile.
- **GitHub rate limited:** add `GITHUB_TOKEN` to `.env`, then restart Streamlit.
- **Metric is N/A:** the site may not expose that value publicly. This is intentional and preferable to guessing.
- **Database locked:** close duplicate scheduler/app processes and try again. SQLite WAL mode and a busy timeout already reduce normal contention.
- **Public site changed:** the CodeChef, HackerRank, GFG, and LeetCode adapters are isolated in `tracker/scrapers/` so they can be updated without changing the database or report code.
