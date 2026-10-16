"""Check every n8n export: valid JSON, connections point at real nodes, and each Postgres node's SQL
prepares cleanly against db/schema.sql (PREPARE parses it and checks tables, columns and types).
Usage: PGURI=postgresql://postgres@localhost:5433/alcovia python3 scripts/check_n8n_sql.py
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PGURI = os.environ.get("PGURI", "postgresql://postgres@localhost:5433/alcovia?host=/tmp")
bad = 0
for f in sorted((ROOT / "n8n").glob("*.json")):
    wf = json.loads(f.read_text())
    names = {n["name"] for n in wf["nodes"]}
    assert len(names) == len(wf["nodes"]), f"{f.name}: duplicate node names"
    for src, c in wf["connections"].items():
        assert src in names, f"{f.name}: connection from unknown node {src}"
        for out in c["main"]:
            for t in out:
                assert t["node"] in names, f"{f.name}: connection to unknown node {t['node']}"
    for n in wf["nodes"]:
        if n["type"] != "n8n-nodes-base.postgres":
            continue
        q = n["parameters"]["query"]
        sql = f"BEGIN; PREPARE chk AS {q}; ROLLBACK;"
        r = subprocess.run(["psql", PGURI, "-v", "ON_ERROR_STOP=1", "-q", "-c", sql], capture_output=True, text=True)
        status = "ok" if r.returncode == 0 else "FAIL " + r.stderr.strip().splitlines()[0]
        bad += r.returncode != 0
        print(f"{f.name:34} {n['name']:28} {status}")
sys.exit(1 if bad else 0)
