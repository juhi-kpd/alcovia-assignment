"""Run the SQL metric files against Postgres and embed the results in the dashboards.

For the GTM tracker, every query in sql/gtm is run once per month range (May–Oct 2026, any start to any end),
so the dashboard's timeline selector only switches between results the SQL produced.
For the student tracker, the generated student data (dashboards/data/student-tracker.json) is embedded as is.

Usage:  PGURI=postgresql://postgres@localhost:5433/alcovia python3 scripts/export_dashboard_data.py
"""
import json, os, re, subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PGURI = os.environ.get("PGURI", "postgresql://postgres@localhost:5433/alcovia?host=/tmp")
TODAY = date(2026, 10, 16)
MONTHS = [date(2026, m, 1) for m in range(5, 11)]

def month_end(m):
    if (m.year, m.month) == (TODAY.year, TODAY.month):
        return TODAY
    return date(m.year + (m.month == 12), m.month % 12 + 1, 1) - timedelta(days=1)

def statements(path):
    """SELECT statements in a .sql file, comments and SET lines removed."""
    text = re.sub(r"--[^\n]*", "", Path(path).read_text())
    parts = [p.strip() for p in text.split(";")]
    return [p for p in parts if p and not p.upper().startswith("SET ")]

def run(sql, from_date=None, to_date=None):
    if from_date:
        sql = re.sub(r"DATE '\d{4}-\d{2}-\d{2}' AS from_date", f"DATE '{from_date}' AS from_date", sql)
        sql = re.sub(r"DATE '\d{4}-\d{2}-\d{2}' AS to_date", f"DATE '{to_date}' AS to_date", sql)
    wrapped = f"SET search_path TO alcovia; SELECT coalesce(json_agg(q), '[]'::json) FROM ({sql}) q;"
    out = subprocess.run(["psql", PGURI, "-At", "-v", "ON_ERROR_STOP=1", "-c", wrapped], check=True, capture_output=True, text=True).stdout
    return json.loads("\n".join(l for l in out.splitlines() if l.strip() != "SET"))

gtm = {"generated": TODAY.isoformat(), "months": [m.isoformat()[:7] for m in MONTHS], "ranges": {}}
files = {name: statements(ROOT / "sql" / "gtm" / f) for name, f in [
    ("revenue", "01_revenue_vs_target.sql"), ("unpaid", "02_unpaid_invoices.sql"), ("funnel", "04_funnel_stages.sql"),
    ("funnel_kpis", "05_funnel_kpis.sql"), ("creatives", "06_creative_actions.sql"), ("pages", "07_landing_page_health.sql")]}
for a in range(len(MONTHS)):
    for b in range(a, len(MONTHS)):
        f, t = MONTHS[a].isoformat(), month_end(MONTHS[b]).isoformat()
        r = {"from": f, "to": t}
        for name, stmts in files.items():
            r[name] = run(stmts[0], f, t)
        r["drop_stages"] = run(files["funnel_kpis"][1], f, t)
        gtm["ranges"][f"{a}-{b}"] = r
gtm["renewals"] = run(statements(ROOT / "sql" / "gtm" / "03_trial_renewals_due.sql")[0])

def embed(html_path, payload):
    html = Path(html_path).read_text()
    block = '<script id="data" type="application/json">' + json.dumps(payload, separators=(",", ":")) + "</script>"
    html, n = re.subn(r'<script id="data" type="application/json">.*?</script>', lambda _: block, html, flags=re.S)
    assert n == 1, f"no data block in {html_path}"
    Path(html_path).write_text(html)

embed(ROOT / "dashboards" / "gtm-tracker.html", gtm)
embed(ROOT / "dashboards" / "student-tracker.html", json.loads((ROOT / "dashboards" / "data" / "student-tracker.json").read_text()))
(ROOT / "dashboards" / "data" / "gtm-tracker.json").write_text(json.dumps(gtm, indent=1))
print("ranges exported:", len(gtm["ranges"]))
