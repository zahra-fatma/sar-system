import pickle, json, shap, os
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

FEATURES = ["amount","tx_count_7d","counterparty_count_30d",
            "is_pep","hour_of_day","is_round_amount",
            "is_structuring","high_velocity","high_counterparties","odd_hours"]

# Load model once at import time
with open("models/xgb_model.pkl", "rb") as f:
    MODEL = pickle.load(f)
EXPLAINER = shap.TreeExplainer(MODEL)


def run_rules(tx: dict) -> list[dict]:
    rules = []
    amt = tx.get("amount", 0)

    if 8000 < amt < 10000:
        rules.append({
            "rule": "STRUCTURING",
            "severity": "HIGH",
            "detail": f"Transaction amount ${amt:,.2f} is just below $10,000 reporting threshold"
        })
    if tx.get("is_pep", 0) == 1:
        rules.append({
            "rule": "PEP_EXPOSURE",
            "severity": "HIGH",
            "detail": "Customer or counterparty is a Politically Exposed Person"
        })
    if tx.get("tx_count_7d", 0) > 25:
        rules.append({
            "rule": "HIGH_VELOCITY",
            "severity": "MEDIUM",
            "detail": f"{tx['tx_count_7d']} transactions in last 7 days exceeds threshold of 25"
        })
    if tx.get("counterparty_count_30d", 0) > 12:
        rules.append({
            "rule": "COUNTERPARTY_SPREAD",
            "severity": "MEDIUM",
            "detail": f"Funds sent to {tx['counterparty_count_30d']} distinct counterparties in 30 days"
        })
    if amt % 1000 == 0 and amt > 0:
        rules.append({
            "rule": "ROUND_AMOUNT",
            "severity": "LOW",
            "detail": f"Transaction is a suspiciously round amount: ${amt:,.0f}"
        })
    hour = tx.get("hour_of_day", 12)
    if hour < 6 or hour > 22:
        rules.append({
            "rule": "ODD_HOURS",
            "severity": "LOW",
            "detail": f"Transaction initiated at {hour:02d}:00 — outside normal business hours"
        })
    if tx.get("country", "US") in ["AE", "NG", "RU", "IR", "KP"]:
        rules.append({
            "rule": "HIGH_RISK_JURISDICTION",
            "severity": "HIGH",
            "detail": f"Transaction involves high-risk jurisdiction: {tx['country']}"
        })
    return rules


def build_features(tx: dict) -> pd.DataFrame:
    row = {
        "amount":                 tx.get("amount", 0),
        "tx_count_7d":            tx.get("tx_count_7d", 0),
        "counterparty_count_30d": tx.get("counterparty_count_30d", 0),
        "is_pep":                 tx.get("is_pep", 0),
        "hour_of_day":            tx.get("hour_of_day", 12),
        "is_round_amount":        int(tx.get("amount", 0) % 1000 == 0),
        "is_structuring":         int(8000 < tx.get("amount", 0) < 10000),
        "high_velocity":          int(tx.get("tx_count_7d", 0) > 25),
        "high_counterparties":    int(tx.get("counterparty_count_30d", 0) > 12),
        "odd_hours":              int(tx.get("hour_of_day", 12) < 6 or
                                      tx.get("hour_of_day", 12) > 22),
    }
    return pd.DataFrame([row])[FEATURES]


def get_shap_explanation(features_df: pd.DataFrame) -> list[dict]:
    shap_vals = EXPLAINER.shap_values(features_df)[0]
    pairs = sorted(
        zip(FEATURES, shap_vals),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    return [
        {"feature": f, "shap_value": round(float(v), 4),
         "direction": "increases risk" if v > 0 else "decreases risk"}
        for f, v in pairs[:5]
    ]


def score_transaction(tx: dict) -> dict:
    rules       = run_rules(tx)
    features_df = build_features(tx)

    risk_score      = float(MODEL.predict_proba(features_df)[0][1])
    shap_explanation = get_shap_explanation(features_df)

    threshold = float(os.getenv("RISK_THRESHOLD", 0.65))
    flagged   = risk_score >= threshold or any(r["severity"] == "HIGH" for r in rules)

    return {
        "tx_id":            tx.get("tx_id"),
        "risk_score":       round(risk_score, 4),
        "flagged":          flagged,
        "triggered_rules":  rules,
        "shap_explanation": shap_explanation,
        "threshold_used":   threshold,
    }