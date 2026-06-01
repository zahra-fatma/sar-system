import json, sqlite3, os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from api.routes.ingest    import router as ingest_router
from api.routes.cases     import router as cases_router
from api.routes.narrative import router as narrative_router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SAR Generation System", version="0.1.0")
templates = Jinja2Templates(directory="ui/templates")

app.include_router(ingest_router,    prefix="/api", tags=["Ingestion"])
app.include_router(cases_router,     prefix="/api", tags=["Cases"])
app.include_router(narrative_router, prefix="/api", tags=["Narrative"])


def get_db():
    return sqlite3.connect(os.getenv("DB_PATH", "data/sar.db"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = get_db()
    cur  = conn.execute("SELECT * FROM cases ORDER BY created_at DESC")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()

    cases = []
    stats = {"open": 0, "under_review": 0, "approved": 0, "rejected": 0}
    for row in rows:
        c = dict(zip(cols, row))
        c["triggered_rules"] = json.loads(c["triggered_rules"] or "[]")
        c["shap_values"]     = json.loads(c["shap_values"]     or "[]")
        cases.append(c)
        status = c["status"]
        if status in stats:
            stats[status] += 1

    return templates.TemplateResponse("index.html", {
        "request": request,
        "cases":   cases,
        "stats":   stats,
    })


@app.get("/case/{case_id}", response_class=HTMLResponse)
def case_detail(request: Request, case_id: int):
    conn = get_db()

    cur  = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    cols = [d[0] for d in cur.description]
    row  = cur.fetchone()
    if not row:
        return HTMLResponse("<h1>Case not found</h1>", status_code=404)
    case = dict(zip(cols, row))
    case["triggered_rules"] = json.loads(case["triggered_rules"] or "[]")
    case["shap_values"]     = json.loads(case["shap_values"]     or "[]")
    case["audit_log"]       = json.loads(case["audit_log"]       or "null")

    tx_cur  = conn.execute("SELECT * FROM transactions WHERE tx_id = ?", (case["tx_id"],))
    tx_cols = [d[0] for d in tx_cur.description]
    tx_row  = tx_cur.fetchone()
    tx = dict(zip(tx_cols, tx_row)) if tx_row else {}
    conn.close()

    return templates.TemplateResponse("case.html", {
        "request": request,
        "case":    case,
        "tx":      tx,
    })