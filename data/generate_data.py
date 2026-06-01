import pandas as pd
import numpy as np
from faker import Faker
import sqlite3, os
from dotenv import load_dotenv

load_dotenv()
fake = Faker()
np.random.seed(42)
N = 1000

def generate():
    records = []
    for i in range(N):
        amount = np.random.choice(
            [np.random.uniform(100, 9500),      # structuring range
             np.random.uniform(10000, 100000),  # normal large
             round(np.random.uniform(1000, 50000), -3)],  # round amounts
            p=[0.3, 0.5, 0.2]
        )
        records.append({
            "tx_id": f"TX{i:05d}",
            "account_id": fake.bothify("ACC-####"),
            "customer_name": fake.name(),
            "amount": round(amount, 2),
            "counterparty": fake.company(),
            "tx_type": np.random.choice(["wire", "cash", "ach", "check"], p=[0.3,0.2,0.4,0.1]),
            "hour_of_day": np.random.randint(0, 24),
            "tx_count_7d": np.random.randint(1, 40),
            "counterparty_count_30d": np.random.randint(1, 20),
            "is_pep": np.random.choice([0, 1], p=[0.95, 0.05]),
            "country": np.random.choice(["US","UK","AE","NG","RU","DE"], p=[0.5,0.2,0.1,0.05,0.05,0.1]),
            "timestamp": fake.date_time_between(start_date="-90d").isoformat(),
        })

    df = pd.DataFrame(records)

    # Rule-based suspicious labels for training
    df["is_round_amount"] = (df["amount"] % 1000 == 0).astype(int)
    df["is_structuring"] = ((df["amount"] < 10000) & (df["amount"] > 8000)).astype(int)
    df["high_velocity"] = (df["tx_count_7d"] > 25).astype(int)
    df["high_counterparties"] = (df["counterparty_count_30d"] > 12).astype(int)
    df["odd_hours"] = ((df["hour_of_day"] < 6) | (df["hour_of_day"] > 22)).astype(int)

    suspicion_score = (
        df["is_structuring"] * 2 +
        df["is_pep"] * 3 +
        df["high_velocity"] * 2 +
        df["high_counterparties"] +
        df["is_round_amount"] +
        df["odd_hours"] +
        (df["country"].isin(["AE","NG","RU"])).astype(int) * 2
    )
    df["label"] = (suspicion_score >= 4).astype(int)
    print(f"Generated {len(df)} transactions — {df['label'].sum()} suspicious ({df['label'].mean()*100:.1f}%)")

    db_path = os.getenv("DB_PATH", "./data/sar.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    df.to_sql("transactions", conn, if_exists="replace", index=False)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_id TEXT, risk_score REAL, status TEXT DEFAULT 'open',
            triggered_rules TEXT, shap_values TEXT,
            narrative TEXT, audit_log TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT, analyst_notes TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Saved to {db_path}")
    return df

if __name__ == "__main__":
    generate()