"""
Email open-tracking server.
- GET /pixel/<uid>.gif  → returns 1×1 transparent GIF, logs the open
- GET /stats            → JSON summary of opens
- GET /report           → HTML dashboard
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "opens.db")

# ── 1×1 transparent GIF (43 bytes) ───────────────────────────────────────────
PIXEL = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00"
    b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"\x44\x01\x00\x3b"
)


# ── DB setup ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS sends (
                uid        TEXT PRIMARY KEY,
                email      TEXT,
                name       TEXT,
                company    TEXT,
                sheet      TEXT,
                row_num    INTEGER,
                sent_at    TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS opens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                uid        TEXT,
                opened_at  TEXT,
                ip         TEXT,
                user_agent TEXT
            )
        """)


init_db()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/pixel/<uid>.gif")
def pixel(uid):
    """Serve the tracking pixel and log the open."""
    # Ignore bot/prefetch requests
    ua = request.headers.get("User-Agent", "")
    if any(bot in ua.lower() for bot in ["bot", "spider", "preview", "prefetch", "google image"]):
        return Response(PIXEL, mimetype="image/gif")

    with get_db() as db:
        db.execute(
            "INSERT INTO opens (uid, opened_at, ip, user_agent) VALUES (?, ?, ?, ?)",
            (uid, datetime.utcnow().isoformat(), request.remote_addr, ua),
        )

    # Headers to prevent caching (force a fresh request each open)
    resp = Response(PIXEL, mimetype="image/gif")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"]        = "no-cache"
    resp.headers["Expires"]       = "0"
    return resp


@app.route("/register", methods=["POST"])
def register():
    """Called by send_batch.py after each send to register uid→lead mapping."""
    data = request.get_json(force=True)
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO sends (uid, email, name, company, sheet, row_num, sent_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["uid"], data["email"], data["name"],
                data.get("company", ""), data.get("sheet", ""),
                data.get("row_num", 0),
                datetime.utcnow().isoformat(),
            ),
        )
    return jsonify({"ok": True})


@app.route("/stats")
def stats():
    """JSON open stats."""
    with get_db() as db:
        total_sent   = db.execute("SELECT COUNT(*) FROM sends").fetchone()[0]
        total_opens  = db.execute("SELECT COUNT(DISTINCT uid) FROM opens").fetchone()[0]
        recent_opens = db.execute("""
            SELECT s.name, s.email, s.company, MAX(o.opened_at) as last_open, COUNT(o.id) as times
            FROM opens o JOIN sends s ON o.uid = s.uid
            GROUP BY o.uid ORDER BY last_open DESC LIMIT 50
        """).fetchall()
    return jsonify({
        "total_sent":   total_sent,
        "total_opened": total_opens,
        "open_rate":    f"{round(total_opens/total_sent*100, 1)}%" if total_sent else "0%",
        "recent_opens": [dict(r) for r in recent_opens],
    })


@app.route("/report")
def report():
    """Simple HTML dashboard."""
    with get_db() as db:
        total_sent  = db.execute("SELECT COUNT(*) FROM sends").fetchone()[0]
        total_opens = db.execute("SELECT COUNT(DISTINCT uid) FROM opens").fetchone()[0]
        rows = db.execute("""
            SELECT s.name, s.email, s.company, s.sheet,
                   MAX(o.opened_at) as last_open, COUNT(o.id) as times
            FROM opens o JOIN sends s ON o.uid = s.uid
            GROUP BY o.uid ORDER BY last_open DESC
        """).fetchall()

    rate = f"{round(total_opens/total_sent*100,1)}%" if total_sent else "0%"
    table_rows = "".join(
        f"<tr><td>{r['name']}</td><td>{r['email']}</td><td>{r['company']}</td>"
        f"<td>{r['sheet']}</td><td>{r['times']}</td><td>{r['last_open'][:16]}</td></tr>"
        for r in rows
    )
    html = f"""<!DOCTYPE html><html><head><title>Email Open Tracker</title>
<style>
  body{{font-family:sans-serif;padding:30px;background:#f5f5f5}}
  .cards{{display:flex;gap:20px;margin-bottom:30px}}
  .card{{background:#fff;border-radius:8px;padding:20px 30px;min-width:160px;box-shadow:0 1px 4px rgba(0,0,0,.1)}}
  .card h2{{margin:0;font-size:36px;color:#2563eb}}.card p{{margin:4px 0 0;color:#666;font-size:13px}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.1)}}
  th{{background:#2563eb;color:#fff;padding:10px 14px;text-align:left;font-size:13px}}
  td{{padding:9px 14px;border-bottom:1px solid #f0f0f0;font-size:13px}}
  tr:last-child td{{border:none}}
</style></head><body>
<h1 style="margin-bottom:20px">Email Open Tracker</h1>
<div class="cards">
  <div class="card"><h2>{total_sent}</h2><p>Emails sent</p></div>
  <div class="card"><h2>{total_opens}</h2><p>Unique opens</p></div>
  <div class="card"><h2>{rate}</h2><p>Open rate</p></div>
</div>
<table>
  <tr><th>Name</th><th>Email</th><th>Company</th><th>Sheet</th><th>Opens</th><th>Last opened</th></tr>
  {table_rows if table_rows else '<tr><td colspan="6" style="text-align:center;color:#999">No opens recorded yet</td></tr>'}
</table></body></html>"""
    return html


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
