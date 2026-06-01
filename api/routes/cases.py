from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3, json, os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()


def get_conn():
    return sqlite3.connect(os.getenv("DB_PATH"))


@router.get("/cases")
def list_cases(status: Optional[str] = None):
    conn  = get_conn()
    query = "SELECT * FROM cases"
    params = ()
    if status:
        query  += " WHERE status = ?"
        params  = (status,)
    query += " ORDER BY created_at DESC"

    cur  = conn.execute(query, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()

    cases = []
    for row in rows:
        c = dict(zip(cols, row))
        c["triggered_rules"] = json.loads(c["triggered_rules"] or "[]")
        c["shap_values"]     = json.loads(c["shap_values"]     or "[]")
        cases.append(c)
    return {"cases": cases, "total": len(cases)}


@router.get("/cases/{case_id}")
def get_case(case_id: int):
    conn = get_conn()
    cur  = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    cols = [d[0] for d in cur.description]
    row  = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    c = dict(zip(cols, row))
    c["triggered_rules"] = json.loads(c["triggered_rules"] or "[]")
    c["shap_values"]     = json.loads(c["shap_values"]     or "[]")
    return c


class ReviewPayload(BaseModel):
    action:        str
    analyst_notes: Optional[str] = ""
    narrative:     Optional[str] = None


@router.patch("/cases/{case_id}/review")
def review_case(case_id: int, payload: ReviewPayload):
    if payload.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    conn = get_conn()
    row  = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")
    if row[0] == "approved":
        conn.close()
        raise HTTPException(status_code=400, detail="Approved cases are locked")

    new_status = "approved" if payload.action == "approve" else "rejected"
    conn.execute("""
        UPDATE cases
        SET status = ?, analyst_notes = ?, narrative = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, payload.analyst_notes, payload.narrative, case_id))
    conn.commit()
    conn.close()
    return {"case_id": case_id, "status": new_status}