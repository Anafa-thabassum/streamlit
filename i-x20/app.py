from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from tracker.config import PROJECT_ROOT, settings
from tracker.dashboard import dashboard_metrics
from tracker.database import Database
from tracker.excel_reader import read_profiles_excel
from tracker.logging_config import configure_logging
from tracker.profile_service import ProfileService
from tracker.reporting import ExcelReportWriter, latest_snapshot_rows, weekly_progress_rows
from tracker.url_parser import InvalidProfileUrl, parse_profile_url

st.set_page_config(page_title="Profile Atlas", page_icon="◈", layout="wide")

st.markdown("""
<style>
:root {
  --app-bg:#f3f6fa; --surface:#ffffff; --surface-soft:#eaf8f7;
  --ink:#14213d; --muted:#59677b; --border:#d7e0e9;
  --teal:#087f8c; --teal-hover:#056773; --sidebar:#101d2d;
  --button-text:#ffffff; --secondary-button:#ffffff; --card-shadow:0 10px 30px rgba(20,33,61,.08);
}
@media (prefers-color-scheme: dark) {
  :root {
    --app-bg:#08111f; --surface:#111c2c; --surface-soft:#122b31;
    --ink:#f1f5f9; --muted:#bdc8d6; --border:#33445a;
    --teal:#19a7b5; --teal-hover:#25becd; --sidebar:#07101d;
    --button-text:#ffffff; --secondary-button:#17263a; --card-shadow:0 12px 32px rgba(0,0,0,.2);
  }
}
.stApp, [data-testid="stAppViewContainer"] { background:var(--app-bg); color:var(--ink); }
[data-testid="stHeader"] { background:var(--app-bg); }
[data-testid="stToolbar"] { color:var(--ink); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#101d2d 0%,#142a3d 100%); border-right:1px solid rgba(255,255,255,.07); }
[data-testid="stSidebar"] * { color: #f8fafc; }
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius:9px; padding:.28rem .45rem; margin:.06rem 0;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:rgba(255,255,255,.08); }
h1, h2, h3, p, label, [data-testid="stMarkdownContainer"] { color:var(--ink); }
.eyebrow { color:var(--teal); font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
.hero { position:relative; overflow:hidden; padding:1.7rem 1.9rem; border:1px solid var(--border); border-radius:22px; background:linear-gradient(125deg,var(--surface) 0%,var(--surface-soft) 100%); margin-bottom:1.25rem; box-shadow:var(--card-shadow); }
.hero:after { content:""; position:absolute; width:180px; height:180px; right:-65px; top:-90px; border-radius:50%; background:rgba(8,127,140,.09); }
.hero h1 { margin:.1rem 0 .3rem; font-size:2.15rem; }
.hero p { color:var(--muted); margin:0; max-width:760px; }
.step-card { min-height:108px; padding:1.1rem 1.15rem; border:1px solid var(--border); border-radius:16px; background:var(--surface); box-shadow:0 5px 18px rgba(20,33,61,.05); }
.step-number { display:inline-grid; place-items:center; width:28px; height:28px; margin-right:.45rem; border-radius:9px; color:#fff; background:var(--teal); font-weight:800; }
.step-title { color:var(--ink); font-weight:800; }
.step-card p { margin:.8rem 0 0; color:var(--muted); font-size:.94rem; }
[data-testid="stMetric"], [data-testid="stForm"] { background:var(--surface); border:1px solid var(--border); }
[data-testid="stMetric"] { padding:14px; border-radius:14px; }
[data-testid="stForm"] { border-radius:18px; padding:1.35rem 1.35rem .55rem; box-shadow:0 10px 30px rgba(0,0,0,.12); }
[data-testid="stTextInput"] input { border-radius:10px; }
.flow-note { background:var(--surface-soft); color:var(--ink); border-radius:12px; padding:.75rem 1rem; margin:.25rem 0 1rem; font-size:.92rem; }
.status-ok { color:#067647; font-weight:700; }
.status-warn { color:#b54708; font-weight:700; }
.stButton>button, .stDownloadButton>button {
  background:var(--secondary-button); color:var(--ink) !important;
  border:1px solid var(--border) !important; border-radius:10px; font-weight:700;
  box-shadow:0 3px 10px rgba(20,33,61,.06); min-height:2.7rem;
}
.stButton>button:hover, .stDownloadButton>button:hover {
  border-color:var(--teal) !important; color:var(--teal) !important;
}
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] {
  background:var(--teal) !important; border-color:var(--teal) !important;
  color:var(--button-text) !important;
}
.stButton>button[kind="primary"]:hover, .stDownloadButton>button[kind="primary"]:hover {
  background:var(--teal-hover) !important; color:#ffffff !important;
}
.stButton>button:disabled, .stDownloadButton>button:disabled {
  opacity:.6; color:var(--muted) !important;
}
[data-testid="stFileUploaderDropzone"] { background:var(--surface); border:1.5px dashed var(--border); border-radius:14px; padding:1rem; box-shadow:0 4px 16px rgba(20,33,61,.04); }
[data-testid="stFileUploaderDropzone"] button {
  background:var(--teal) !important; border:1px solid var(--teal) !important;
  color:#ffffff !important; opacity:1 !important; font-weight:700 !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
  background:var(--teal-hover) !important; border-color:var(--teal-hover) !important;
  color:#ffffff !important;
}
[data-testid="stFileUploaderDropzone"] button *,
[data-testid="stFileUploaderDropzone"] button svg {
  color:#ffffff !important; fill:#ffffff !important;
}
[data-testid="stFileUploaderDropzone"] small { color:var(--muted) !important; }
[data-testid="stTooltipIcon"] svg { color:var(--muted) !important; fill:var(--muted) !important; }
</style>
""", unsafe_allow_html=True)

settings.ensure_directories()


@st.cache_resource
def resources():
    database = Database(settings.database_path)
    logger = configure_logging(PROJECT_ROOT / "logs")
    return database, ProfileService(database, settings, logger)


database, service = resources()
# Re-run idempotent migrations on every script refresh. Streamlit caches the
# Database object, so this also upgrades a database created by an older app version.
database.initialize()


def hero(title: str, description: str, eyebrow: str = "Profile Atlas") -> None:
    st.markdown(
        f'<div class="hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )


def fmt(value, digits=0):
    if value is None:
        return "N/A"
    return f"{value:,.{digits}f}" if isinstance(value, float) else f"{value:,}" if isinstance(value, int) else str(value)


def latest_results_table(profile_ids: list[int] | None = None) -> pd.DataFrame:
    """Return a compact, user-facing view of the latest fetched statistics."""
    rows = latest_snapshot_rows(database)
    if profile_ids is not None:
        wanted = set(profile_ids)
        rows = [row for row in rows if row["profile_id"] in wanted]
    display = []
    for row in rows:
        rank = row.get("global_rank") if row.get("global_rank") is not None else row.get("rank")
        display.append({
            "Register No": row.get("student_register_no"), "Name": row.get("student_name"),
            "Platform": row.get("platform"), "Username": row.get("username"),
            "Rating": row.get("rating"), "Global Rank": rank,
            "Country Rank": row.get("country_rank"), "Problems Solved": row.get("problems_solved"),
            "Status": row.get("fetch_status"), "Last Updated": row.get("last_fetched"),
        })
    return pd.DataFrame(display)


def run_fetch(profiles: list[dict]) -> None:
    if not profiles:
        st.info("No profiles match this refresh option.")
        return None
    bar = st.progress(0, text=f"Preparing {len(profiles)} profiles…")
    status = st.empty()

    def update(done, total, profile, success):
        bar.progress(done / total, text=f"Processing {done} / {total}")
        state = "Fetched" if success else "Recorded failure for"
        status.caption(f"{state} {profile['student_name']} · {profile['platform']}")

    summary = service.fetch_profiles(profiles, progress=update)
    if summary.failed:
        st.warning(f"Refresh finished: {summary.succeeded} succeeded, {summary.failed} failed. Failures were saved and did not stop the batch.")
    else:
        st.success(f"Refresh complete — {summary.succeeded} profile(s) updated.")
    return summary


page = st.sidebar.radio(
    "Navigate",
    ["Home", "Dashboard", "Profiles", "Fetch Data", "Weekly Progress", "Activity", "Reports", "Settings"],
)
st.sidebar.caption("Public data only · No passwords or session cookies")

if page == "Home":
    hero("Upload. Fetch. Download.", "Give Profile Atlas one Excel sheet containing Register No, Name, and the available profile links. It will fetch public data and return a complete Excel report.", "One simple workflow")
    step1, step2, step3 = st.columns(3)
    step1.markdown('<div class="step-card"><span class="step-number">1</span><span class="step-title">Upload</span><p>Choose your completed Excel sheet.</p></div>', unsafe_allow_html=True)
    step2.markdown('<div class="step-card"><span class="step-number">2</span><span class="step-title">Fetch</span><p>Click once to collect public statistics.</p></div>', unsafe_allow_html=True)
    step3.markdown('<div class="step-card"><span class="step-number">3</span><span class="step-title">Export</span><p>Download the populated Excel report.</p></div>', unsafe_allow_html=True)
    template_path = PROJECT_ROOT / "sample_input.xlsx"
    if template_path.exists():
        st.download_button(
            "Download Excel Template",
            data=template_path.read_bytes(),
            file_name="profile_atlas_input_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    upload = st.file_uploader(
        "Upload the completed Excel sheet",
        type=["xlsx"],
        help="Required columns: Register No and Name. Platform-link columns are optional.",
    )
    if upload:
        try:
            imported = read_profiles_excel(upload.getvalue())
        except Exception as exc:
            st.error(f"This sheet cannot be processed: {exc}")
        else:
            summary_left, summary_middle, summary_right = st.columns(3)
            summary_left.metric("Students", imported.student_count)
            summary_middle.metric("Valid profiles", len(imported.profiles))
            summary_right.metric("Invalid links", len(imported.issues))
            if imported.profiles:
                preview = pd.DataFrame(imported.profiles).rename(columns={
                    "student_register_no": "Register No",
                    "student_name": "Name",
                    "platform": "Platform",
                    "username": "Username",
                    "profile_url": "Profile URL",
                })
                st.dataframe(preview, width="stretch", hide_index=True)
            if imported.issues:
                st.warning("Invalid links will be skipped and included in the Errors sheet.")
                st.dataframe(pd.DataFrame([issue.__dict__ for issue in imported.issues]), width="stretch", hide_index=True)
            if st.button("Fetch Profiles & Create Excel Report", type="primary", width="stretch", disabled=not imported.profiles):
                profile_ids = []
                for profile in imported.profiles:
                    profile_id, _ = database.upsert_profile(**profile)
                    profile_ids.append(profile_id)
                if imported.issues:
                    database.save_import_errors(imported.issues)
                run_fetch(database.list_profiles(ids=profile_ids, active_only=True))
                results = latest_results_table(profile_ids)
                if not results.empty:
                    st.subheader("Fetched results")
                    st.dataframe(results, width="stretch", hide_index=True)
                report_path = ExcelReportWriter(database, settings.reports_dir).generate()
                st.session_state["latest_report"] = str(report_path)
                st.success("Your fetched Excel report is ready.")
                st.download_button(
                    "Download Fetched Data",
                    data=report_path.read_bytes(),
                    file_name=report_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    width="stretch",
                )

elif page == "Dashboard":
    hero("A clear weekly view of every coding profile", "Upload once, refresh safely, and follow progress over time without replacing earlier results.")
    metrics = dashboard_metrics(database)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Students", fmt(metrics["total_students"]))
    c2.metric("Active profiles", fmt(metrics["total_profiles"]))
    c3.metric("Fetched", fmt(metrics["successful"]))
    c4.metric("Failed", fmt(metrics["failed"]))
    c5.metric("Problems tracked", fmt(metrics["total_problems"]))
    st.caption(f"Last fetched: {metrics['last_fetch'] or 'Never'}")
    latest_results = latest_results_table()
    if not latest_results.empty:
        st.subheader("Latest profile results")
        st.caption("CodeChef Global Rank and Country Rank appear here after a successful fetch.")
        st.dataframe(latest_results, width="stretch", hide_index=True)
    st.subheader("This week")
    a, b, c, d, e = st.columns(5)
    a.metric("Problems added", fmt(metrics["problems_this_week"]))
    b.metric("Avg. LeetCode solved", fmt(metrics["average_leetcode_problems"], 1))
    c.metric("Avg. LeetCode rating", fmt(metrics["average_ratings"]["LeetCode"], 1))
    d.metric("Avg. CodeChef rating", fmt(metrics["average_ratings"]["CodeChef"], 1))
    e.metric("Avg. Codeforces rating", fmt(metrics["average_ratings"]["Codeforces"], 1))
    st.subheader("GitHub")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Repositories", fmt(metrics["github_repositories"]))
    g2.metric("Followers", fmt(metrics["github_followers"]))
    g3.metric("Contributions", fmt(metrics["github_contributions"]))
    g4.metric("Commits this week", fmt(metrics["github_weekly_commits"]))
    snapshots = database.query("""
      SELECT p.student_name AS Student, p.platform AS Platform, s.fetched_at AS Date,
             s.problems_solved AS "Problems solved", s.rating AS Rating, s.contributions AS Contributions
      FROM profile_snapshots s JOIN profiles p ON p.id=s.profile_id ORDER BY s.fetched_at
    """)
    if snapshots:
        frame = pd.DataFrame(snapshots)
        f1, f2, f3 = st.columns(3)
        students = ["All", *sorted(frame["Student"].unique())]
        selected_student = f1.selectbox("Student", students)
        selected_platform = f2.selectbox("Platform", ["All", *sorted(frame["Platform"].unique())])
        window = f3.selectbox("Date range", ["All time", "Last 7 days", "Last 30 days", "Last 90 days"])
        if selected_student != "All":
            frame = frame[frame["Student"] == selected_student]
        if selected_platform != "All":
            frame = frame[frame["Platform"] == selected_platform]
        if window != "All time":
            days = int(window.split()[1])
            parsed_dates = pd.to_datetime(frame["Date"], utc=True, errors="coerce")
            frame = frame[parsed_dates >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)]
        metric = st.selectbox("Trend", ["Problems solved", "Rating", "Contributions"])
        chart = frame.dropna(subset=[metric]).pivot_table(index="Date", columns="Platform", values=metric, aggfunc="last")
        if not chart.empty:
            st.line_chart(chart)
        else:
            st.info("No historical values are available for this trend yet.")
    else:
        st.info("Upload and fetch profiles to begin building the dashboard.")

elif page == "Profiles":
    hero("Saved profiles", "Search, correct, deactivate, or reactivate the profile links stored in this tracker.")
    search_col, platform_col = st.columns([2, 1])
    search = search_col.text_input("Search", placeholder="Student, username, or URL")
    platform = platform_col.selectbox("Platform", ["All", "CodeChef", "LeetCode", "HackerRank", "Codeforces", "GFG", "LinkedIn", "GitHub"])
    profiles = database.list_profiles(platform=platform, search=search)
    if profiles:
        st.dataframe(pd.DataFrame(profiles)[["student_register_no", "student_name", "platform", "username", "profile_url", "active", "last_fetched", "fetch_status", "last_error"]], width="stretch", hide_index=True)
        labels = {f"{p.get('student_register_no') or 'No register no.'} · {p['student_name']} · {p['platform']} · @{p['username']}": p for p in profiles}
        selected_label = st.selectbox("Manage one profile", list(labels))
        selected = labels[selected_label]
        new_url = st.text_input("Profile URL", value=selected["profile_url"])
        b1, b2 = st.columns(2)
        if b1.button("Save URL", width="stretch"):
            try:
                parsed = parse_profile_url(selected["platform"], new_url)
                database.update_profile_url(selected["id"], parsed.username, parsed.url)
            except (InvalidProfileUrl, Exception) as exc:
                st.error(str(exc))
            else:
                st.success("Profile updated.")
                st.rerun()
        action = "Deactivate" if selected["active"] else "Reactivate"
        if b2.button(action, width="stretch"):
            database.set_profile_active(selected["id"], not bool(selected["active"]))
            st.success(f"Profile {action.lower()}d.")
            st.rerun()
    else:
        st.info("No saved profiles match these filters.")

elif page == "Fetch Data":
    hero("Refresh profile data", "Choose a safe, repeatable refresh. Every result is saved as a new historical snapshot.")
    all_profiles = database.list_profiles(active_only=True)
    last = max((p["last_fetched"] for p in all_profiles if p["last_fetched"]), default=None)
    next_date = None
    if last:
        try:
            next_date = (datetime.fromisoformat(last) + timedelta(days=settings.fetch_interval_days)).date().isoformat()
        except ValueError:
            pass
    st.caption(f"Last fetched: {last or 'Never'}  ·  Next recommended fetch: {next_date or 'After the first fetch'}")
    f1, f2 = st.columns(2)
    if f1.button("Fetch All", type="primary", width="stretch"):
        run_fetch(all_profiles)
    if f2.button("Fetch This Week", width="stretch"):
        run_fetch(database.list_profiles(active_only=True, due_days=settings.fetch_interval_days))
    options = {f"{p.get('student_register_no') or 'No register no.'} · {p['student_name']} · {p['platform']} · @{p['username']}": p for p in all_profiles}
    selected = st.multiselect("Or select specific profiles", list(options))
    if st.button("Fetch Selected Profiles", disabled=not selected, width="stretch"):
        run_fetch([options[label] for label in selected])

elif page == "Weekly Progress":
    hero("Weekly progress", "The latest snapshot is compared with the previous one for each saved profile.")
    rows = weekly_progress_rows(database)
    if rows:
        frame = pd.DataFrame(rows)
        c1, c2 = st.columns(2)
        student = c1.selectbox("Student", ["All", *sorted(frame["Name"].unique())])
        platform = c2.selectbox("Platform", ["All", *sorted(frame["Platform"].unique())])
        if student != "All": frame = frame[frame["Name"] == student]
        if platform != "All": frame = frame[frame["Platform"] == platform]
        st.dataframe(frame, width="stretch", hide_index=True)
    else:
        st.info("At least one successful fetch is needed; changes appear after the second snapshot.")

elif page == "Activity":
    hero("Activity history", "Recent public submissions, contests, and GitHub events are kept without duplicates.")
    rows = database.query("""
      SELECT p.student_name AS Name, p.platform AS Platform, p.username AS Username,
             a.activity_date AS Date, a.activity_type AS Type, a.title AS Item,
             a.difficulty AS Difficulty, a.status AS Status, a.rating_change AS "Rating Change", a.url AS URL
      FROM activities a JOIN profiles p ON p.id=a.profile_id
      ORDER BY COALESCE(a.activity_date, a.first_seen_at) DESC
    """)
    if rows:
        frame = pd.DataFrame(rows)
        c1, c2 = st.columns(2)
        student = c1.selectbox("Student", ["All", *sorted(frame["Name"].unique())])
        platform = c2.selectbox("Platform", ["All", *sorted(frame["Platform"].unique())])
        if student != "All": frame = frame[frame["Name"] == student]
        if platform != "All": frame = frame[frame["Platform"] == platform]
        st.dataframe(frame, width="stretch", hide_index=True, column_config={"URL": st.column_config.LinkColumn()})
    else:
        st.info("No public activity has been collected yet.")

elif page == "Reports":
    hero("Excel reports", "Generate a dated workbook with summary, platform detail, weekly progress, activity, and errors.")
    if st.button("Generate Excel Report", type="primary", width="stretch"):
        path = ExcelReportWriter(database, settings.reports_dir).generate()
        st.session_state["latest_report"] = str(path)
        st.success(f"Created {path.name}")
    latest_path = Path(st.session_state.get("latest_report", "")) if st.session_state.get("latest_report") else database.latest_report()
    if latest_path and latest_path.exists():
        st.download_button("Download Latest Report", data=latest_path.read_bytes(), file_name=latest_path.name,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
        st.caption(f"Latest: {latest_path.name}")
    history = database.query("SELECT created_at AS Created, path AS Report FROM reports ORDER BY created_at DESC")
    if history:
        st.dataframe(pd.DataFrame(history), width="stretch", hide_index=True)

elif page == "Settings":
    hero("Settings", "Current safe defaults for refreshes, storage, and API access.")
    st.write(f"**Refresh interval:** {settings.fetch_interval_days} days")
    st.write(f"**Maximum parallel requests:** {settings.max_workers}")
    st.write(f"**Request timeout:** {settings.request_timeout_seconds:g} seconds")
    st.write(f"**GitHub token:** {'Configured' if settings.github_token else 'Not configured (public rate limit applies)'}")
    st.info("Edit .env to change settings, then restart the app. Tokens are never stored in SQLite or exported to Excel.")
    st.warning("LinkedIn metrics are intentionally recorded as N/A unless a permitted API integration is available. The app does not scrape gated pages or bypass access controls.")
