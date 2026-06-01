from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import sqlite3, json, os, io
import pandas as pd
from api.detection import score_transaction
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()


class Transaction(BaseModel):
    tx_id:                  str
    account_id:             str
    customer_name:          str
    amount:                 float
    counterparty:           str
    tx_type:                str
    hour_of_day:            int
    tx_count_7d:            int
    counterparty_count_30d: int
    is_pep:                 int = 0
    country:                str = "US"
    timestamp:              str


@router.post("/ingest")
def ingest_transaction(tx: Transaction):
    result = score_transaction(tx.model_dump())

    if not result["flagged"]:
        return {"status": "ok", "flagged": False, "risk_score": result["risk_score"]}

    conn = sqlite3.connect(os.getenv("DB_PATH"))

    existing = conn.execute(
        "SELECT id FROM cases WHERE tx_id = ?", (tx.tx_id,)
    ).fetchone()

    if existing:
        conn.close()
        return {"status": "duplicate", "case_id": existing[0], "flagged": True}

    cur = conn.execute("""
        INSERT INTO cases
            (tx_id, risk_score, status, triggered_rules, shap_values)
        VALUES (?, ?, 'open', ?, ?)
    """, (
        tx.tx_id,
        result["risk_score"],
        json.dumps(result["triggered_rules"]),
        json.dumps(result["shap_explanation"]),
    ))
    conn.commit()
    case_id = cur.lastrowid
    conn.close()

    return {
        "status":           "flagged",
        "case_id":          case_id,
        "risk_score":       result["risk_score"],
        "rules_hit":        [r["rule"] for r in result["triggered_rules"]],
        "top_shap_feature": result["shap_explanation"][0]["feature"],
    }


@router.post("/ingest/bulk")
async def ingest_bulk(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    required_cols = ["tx_id","account_id","customer_name","amount","counterparty",
                     "tx_type","hour_of_day","tx_count_7d","counterparty_count_30d","timestamp"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {missing}")

    # Fill optional columns with defaults
    if "is_pep"   not in df.columns: df["is_pep"]   = 0
    if "country"  not in df.columns: df["country"]  = "US"

    results = {"total": len(df), "flagged": 0, "clean": 0, "duplicate": 0, "errors": 0, "cases": []}

    conn = sqlite3.connect(os.getenv("DB_PATH"))

    for _, row in df.iterrows():
        try:
            tx = row.to_dict()
            tx["hour_of_day"]            = int(tx["hour_of_day"])
            tx["tx_count_7d"]            = int(tx["tx_count_7d"])
            tx["counterparty_count_30d"] = int(tx["counterparty_count_30d"])
            tx["is_pep"]                 = int(tx.get("is_pep", 0))
            tx["amount"]                 = float(tx["amount"])

            # Save to transactions table if not exists
            existing_tx = conn.execute(
                "SELECT tx_id FROM transactions WHERE tx_id = ?", (tx["tx_id"],)
            ).fetchone()
            if not existing_tx:
                conn.execute("""
                    INSERT OR IGNORE INTO transactions
                        (tx_id, account_id, customer_name, amount, counterparty,
                         tx_type, hour_of_day, tx_count_7d, counterparty_count_30d,
                         is_pep, country, timestamp)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    tx["tx_id"], tx["account_id"], tx["customer_name"], tx["amount"],
                    tx["counterparty"], tx["tx_type"], tx["hour_of_day"], tx["tx_count_7d"],
                    tx["counterparty_count_30d"], tx["is_pep"], tx.get("country","US"), tx["timestamp"]
                ))

            result = score_transaction(tx)

            if not result["flagged"]:
                results["clean"] += 1
                continue

            existing_case = conn.execute(
                "SELECT id FROM cases WHERE tx_id = ?", (tx["tx_id"],)
            ).fetchone()

            if existing_case:
                results["duplicate"] += 1
                continue

            cur = conn.execute("""
                INSERT INTO cases
                    (tx_id, risk_score, status, triggered_rules, shap_values)
                VALUES (?, ?, 'open', ?, ?)
            """, (
                tx["tx_id"],
                result["risk_score"],
                json.dumps(result["triggered_rules"]),
                json.dumps(result["shap_explanation"]),
            ))
            conn.commit()
            results["flagged"] += 1
            results["cases"].append({
                "case_id":    cur.lastrowid,
                "tx_id":      tx["tx_id"],
                "risk_score": result["risk_score"],
                "rules_hit":  [r["rule"] for r in result["triggered_rules"]],
            })

        except Exception as e:
            results["errors"] += 1

    conn.commit()
    conn.close()
    return results