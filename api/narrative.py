import os, json, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from mistralai import Mistral
from api.rag import retrieve_context

load_dotenv()
client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))


def build_prompt(case: dict, tx: dict, context_chunks: list[dict]) -> str:
    rules = case.get("triggered_rules", [])
    shap  = case.get("shap_values", [])

    rules_text = "\n".join(
        f"  - [{r['severity']}] {r['rule']}: {r['detail']}" for r in rules
    ) or "  None triggered"

    shap_text = "\n".join(
        f"  - {s['feature']}: SHAP={s['shap_value']} ({s['direction']})" for s in shap
    ) or "  Not available"

    context_text = "\n\n".join(
        f"[Source: {c['source']}, p.{c['page']}]\n{c['content']}" for c in context_chunks
    )

    return f"""You are a compliance analyst writing a Suspicious Activity Report (SAR) narrative.
Generate a professional, regulator-ready SAR narrative based ONLY on the evidence below.
Do not invent facts. Every claim must be traceable to the provided data.

=== TRANSACTION DETAILS ===
Transaction ID  : {tx.get('tx_id')}
Customer Name   : {tx.get('customer_name')}
Account ID      : {tx.get('account_id')}
Amount          : ${tx.get('amount', 0):,.2f}
Type            : {tx.get('tx_type')}
Counterparty    : {tx.get('counterparty')}
Country         : {tx.get('country')}
Timestamp       : {tx.get('timestamp')}
Risk Score      : {case.get('risk_score')} / 1.0

=== TRIGGERED AML RULES ===
{rules_text}

=== ML MODEL EXPLANATION (SHAP) ===
Top features driving the suspicious classification:
{shap_text}

=== RELEVANT REGULATORY GUIDANCE ===
{context_text}

=== INSTRUCTIONS ===
Write the SAR narrative in these exact sections:

**SUBJECT INFORMATION**
Full name, account number, and any known identifying information.

**SUSPICIOUS ACTIVITY SUMMARY**
A 2-3 sentence plain-English summary of what happened and why it is suspicious.

**DETAILED TRANSACTION DESCRIPTION**
Specific transaction facts: date, amount, type, counterparty, jurisdiction.
Reference each triggered AML rule and explain its significance.

**RISK INDICATORS**
Bullet list of each red flag observed, grounded in the SHAP and rule evidence above.

**BASIS FOR FILING**
Explain why this activity warrants a SAR filing, citing relevant regulatory guidance.

Write clearly and factually. Do not speculate beyond the evidence provided."""


def generate_narrative(case_id: int) -> dict:
    conn = sqlite3.connect(os.getenv("DB_PATH"))

    cur  = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    cols = [d[0] for d in cur.description]
    row  = cur.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Case {case_id} not found")
    case = dict(zip(cols, row))
    case["triggered_rules"] = json.loads(case["triggered_rules"] or "[]")
    case["shap_values"]     = json.loads(case["shap_values"]     or "[]")

    tx_cur  = conn.execute("SELECT * FROM transactions WHERE tx_id = ?", (case["tx_id"],))
    tx_cols = [d[0] for d in tx_cur.description]
    tx_row  = tx_cur.fetchone()
    tx = dict(zip(tx_cols, tx_row)) if tx_row else {}

    search_query   = f"SAR narrative {' '.join(r['rule'] for r in case['triggered_rules'])}"
    context_chunks = retrieve_context(search_query, k=3)

    prompt = build_prompt(case, tx, context_chunks)

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    narrative = response.choices[0].message.content

    audit = {
        "generated_at":      datetime.utcnow().isoformat(),
        "model":             "mistral-small-latest",
        "rag_query":         search_query,
        "retrieved_sources": [{"source": c["source"], "page": c["page"], "score": c["score"]}
                               for c in context_chunks],
        "rules_used":        case["triggered_rules"],
        "shap_used":         case["shap_values"],
        "prompt_length":     len(prompt),
    }

    conn.execute("""
        UPDATE cases
        SET narrative = ?, audit_log = ?, status = 'under_review'
        WHERE id = ?
    """, (narrative, json.dumps(audit), case_id))
    conn.commit()
    conn.close()

    return {
        "case_id":   case_id,
        "narrative": narrative,
        "audit":     audit,
    }