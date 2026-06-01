
from dotenv import load_dotenv
load_dotenv()

import pandas as pd, numpy as np, sqlite3, pickle, json, os, shap
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
print("DB_PATH =", os.getenv("DB_PATH"))


FEATURES = ["amount","tx_count_7d","counterparty_count_30d",
            "is_pep","hour_of_day","is_round_amount",
            "is_structuring","high_velocity","high_counterparties","odd_hours"]

def train():
    conn = sqlite3.connect(os.getenv("DB_PATH"))
    df = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()

    df["is_round_amount"] = (df["amount"] % 1000 == 0).astype(int)
    df["is_structuring"]  = ((df["amount"] < 10000) & (df["amount"] > 8000)).astype(int)
    df["high_velocity"]   = (df["tx_count_7d"] > 25).astype(int)
    df["high_counterparties"] = (df["counterparty_count_30d"] > 12).astype(int)
    df["odd_hours"]       = ((df["hour_of_day"] < 6) | (df["hour_of_day"] > 22)).astype(int)

    X, y = df[FEATURES], df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                          scale_pos_weight=len(y[y==0])/len(y[y==1]),
                          eval_metric="logloss", random_state=42)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:,1]
    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_prob):.3f}")

    os.makedirs("models", exist_ok=True)
    with open("models/xgb_model.pkl", "wb") as f:
        pickle.dump(model, f)

    explainer = shap.TreeExplainer(model)
    print("Model + SHAP explainer saved.")
    with open("models/features.json", "w") as f:
        json.dump(FEATURES, f)

if __name__ == "__main__":
    train()