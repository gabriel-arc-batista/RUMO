"""Check long-history queries without touching the user's study database."""

import json
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store, uid
from challenges import metrics

project = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    store = Store(Path(folder) / "performance.sqlite3")
    p = store.save("plans", {"name": "Teste de carga"})
    s = store.save(
        "subjects", {"plan_id": p, "name": "Matéria de teste", "color": "#5B8CFF"}
    )
    t = store.save("topics", {"subject_id": s, "name": "Assunto de teste"})
    rows = [
        (
            uid(),
            p,
            s,
            t,
            (date.today() - timedelta(days=i % 365)).isoformat(),
            "Teoria",
            2700,
            1800,
            15,
            5,
            0,
        )
        for i in range(10000)
    ]
    with store.db:
        store.db.executemany(
            "INSERT INTO sessions(id,plan_id,subject_id,topic_id,day,category,target,elapsed,correct,wrong,blank) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
    start = time.perf_counter()
    stats = store.stats(p)
    summary_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    page = store.sessions(p, limit=100)
    history_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    chart = store.grouped(p)
    chart_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    challenge = metrics(store, p, store.today())
    challenge_ms = (time.perf_counter() - start) * 1000
    assert challenge["questions"] >= 0
    assert (
        stats["count"] == 10000
        and stats["elapsed"] == 18000000
        and stats["total"] == 200000
        and stats["rate"] == 75
        and len(page) == 100
    )
    report = {
        "sessions": 10000,
        "weekly_challenges_ms": round(challenge_ms, 2),
        "summary_ms": round(summary_ms, 2),
        "history_100_rows_ms": round(history_ms, 2),
        "daily_chart_query_ms": round(chart_ms, 2),
        "resident_memory_mb": round(psutil.Process().memory_info().rss / 1024**2, 1),
        "sqlite_cache_mb": 2,
        "history_page_size": 100,
        "chart_group_limit": 60,
        "isolated_data": True,
    }
    store.close()
(project / "validation/performance-report.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report))
