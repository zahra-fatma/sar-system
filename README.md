#  AI-Powered SAR Generation System

> An intelligent, end-to-end **Suspicious Activity Report (SAR)** generation system that combines machine learning, explainable AI, and large language models to automate AML compliance workflows.

---

## 📸 Overview

Financial institutions file thousands of SARs every year — a process that is manual, time-consuming, and error-prone. This system automates the entire pipeline: from ingesting raw transactions, to detecting suspicious patterns, to generating regulator-ready narratives — all with a human analyst in the loop.

---

## ⚙️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI | REST backend, async request handling |
| ML Model | XGBoost | Transaction risk scoring (0–1) |
| Explainability | SHAP | Per-prediction feature importance |
| Detection | Rule Engine | 7 hard-coded AML rules (BSA/FATF) |
| RAG | LangChain + ChromaDB | Regulatory document retrieval |
| LLM | Mistral AI | SAR narrative generation |
| Database | SQLite | Case storage + full audit trail |
| Frontend | Jinja2 + HTML/CSS/JS | Analyst review dashboard |

---

## 🚀 Features

### 🔍 Detection Engine
- **XGBoost classifier** trained on synthetic AML transaction data
- **7-rule AML engine** covering structuring, PEP exposure, high velocity, counterparty spread, round amounts, odd hours, and high-risk jurisdictions
- **SHAP explainability** — every prediction comes with a ranked list of features that drove the risk score, making decisions auditable and defensible

### 🧠 AI Narrative Generation
- **RAG pipeline** retrieves the most relevant regulatory guidance (FinCEN SAR guidelines, BSA, FATF recommendations) before generating
- **Mistral AI** generates structured, regulator-ready SAR narratives grounded only in the evidence — no hallucinated facts
- Every narrative is saved with a full **audit log**: model used, RAG sources retrieved, prompt length, and timestamp

### 📋 Case Management
- Flagged transactions automatically create cases in the queue
- Analyst dashboard with **approve / reject** workflow and notes
- Case status tracking: `open → under_review → approved / rejected`
- **CSV bulk ingestion** — upload hundreds of transactions at once

### 🔒 Compliance-First Design
- All narratives cite specific regulatory frameworks (31 USC 5324, 31 CFR §1020.320, FATF)
- SHAP values logged per case for audit trail
- Approved cases locked — cannot be modified after decision

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Transaction Input                         │
│              (Single API / Bulk CSV Upload)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────▼───────────┐
          │   AML Rule Engine     │  ← 7 rules (structuring,
          │   + XGBoost Model     │    PEP, velocity, etc.)
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   SHAP Explainer      │  ← Top features ranked
          │   Risk Score 0–1      │    per prediction
          └───────────┬───────────┘
                      │ (if flagged)
          ┌───────────▼───────────┐
          │   Case Saved to DB    │  ← SQLite + audit trail
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   RAG Retrieval       │  ← Keyword search over
          │   (LangChain)         │    AML regulatory docs
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   Mistral AI          │  ← Grounded SAR narrative
          │   Narrative Generator │    (5 structured sections)
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   Analyst Dashboard   │  ← Review, approve/reject
          │   (Jinja2 UI)         │    Add notes, lock case
          └───────────┬───────────┘
                      │
          ┌───────────▼───────────┐
          │   SAR Filed           │  ← Ready for FinCEN
          └───────────────────────┘
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Analyst dashboard |
| `GET` | `/health` | Health check |
| `POST` | `/api/ingest` | Ingest a single transaction |
| `POST` | `/api/ingest/bulk` | Bulk ingest via CSV upload |
| `GET` | `/api/cases` | List all cases (filter by status) |
| `GET` | `/api/cases/{id}` | Get full case details |
| `POST` | `/api/cases/{id}/generate` | Generate SAR narrative via LLM |
| `PATCH` | `/api/cases/{id}/review` | Approve or reject a case |

### Example: Ingest a suspicious transaction

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tx_id": "TX99001",
    "account_id": "ACC-7712",
    "customer_name": "Marcus Webb",
    "amount": 9400.00,
    "counterparty": "Gulf Trade Partners LLC",
    "tx_type": "wire",
    "hour_of_day": 3,
    "tx_count_7d": 28,
    "counterparty_count_30d": 14,
    "is_pep": 1,
    "country": "AE",
    "timestamp": "2025-05-20T03:22:00"
  }'
```

**Response:**
```json
{
  "status": "flagged",
  "case_id": 1,
  "risk_score": 0.9992,
  "rules_hit": ["STRUCTURING", "PEP_EXPOSURE", "HIGH_VELOCITY", "ODD_HOURS", "HIGH_RISK_JURISDICTION"],
  "top_shap_feature": "is_pep"
}
```

---

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.10+
- Git
- A free [Mistral AI API key](https://console.mistral.ai)

### 1. Clone the repository
```bash
git clone https://github.com/zahra-fatma/sar-system
cd sar-system
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```

Edit `.env` and add your Mistral API key:
```
MISTRAL_API_KEY=your_key_here
DB_PATH=data/sar.db
CHROMA_PATH=./data/chroma
RISK_THRESHOLD=0.65
```

### 5. Generate synthetic data and train model
```bash
python data/generate_data.py   # generates 1000 synthetic transactions
python models/train.py         # trains XGBoost, prints ROC-AUC
```

### 6. Start the server
```bash
uvicorn main:app --reload
```

### 7. Open the dashboard
```
http://localhost:8000
```

---

## 📂 Project Structure

```
sar-system/
├── main.py                    # FastAPI app + UI routes
├── .env                       # Environment variables (not committed)
├── requirements.txt
├── data/
│   ├── generate_data.py       # Synthetic transaction generator
│   └── docs/                  # AML regulatory documents for RAG
├── models/
│   ├── train.py               # XGBoost training + SHAP setup
│   └── xgb_model.pkl          # Trained model (not committed)
├── api/
│   ├── detection.py           # Rule engine + XGBoost scorer
│   ├── narrative.py           # RAG + Mistral AI narrative generator
│   ├── rag.py                 # Document retrieval pipeline
│   └── routes/
│       ├── ingest.py          # Transaction ingestion endpoints
│       ├── cases.py           # Case management endpoints
│       └── narrative.py       # Narrative generation endpoint
└── ui/
    └── templates/
        ├── index.html         # Case queue dashboard
        └── case.html          # Case detail + review page
```

---

## 🔮 Future Roadmap

- [ ] **Isolation Forest** — unsupervised anomaly detection layer
- [ ] **Graph Neural Network** — detect transaction network patterns
- [ ] **Kafka streaming** — real-time transaction ingestion
- [ ] **FinCEN API integration** — auto-file approved SARs
- [ ] **Docker + Kubernetes** — production deployment
- [ ] **Role-based access control** — multi-analyst support

---


> Built as a portfolio project demonstrating applied ML, LLM integration, and AML compliance automation.
