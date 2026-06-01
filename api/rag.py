
import os, json
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader

load_dotenv()

DOCS_PATH = "data/docs"

def retrieve_context(query: str, k: int = 3) -> list[dict]:
    docs = []
    if os.path.exists(DOCS_PATH):
        for fname in os.listdir(DOCS_PATH):
            fpath = os.path.join(DOCS_PATH, fname)
            try:
                if fname.endswith(".txt"):
                    loader = TextLoader(fpath)
                    pages = loader.load()
                    for page in pages:
                        docs.append({
                            "content": page.page_content,
                            "source": fname,
                            "page": 0,
                        })
            except Exception as e:
                print(f"Skipped {fname}: {e}")

    if not docs:
        docs = _fallback_docs()

    query_words = set(query.lower().split())
    scored_docs = []

    for doc in docs:
        content_words = set(doc["content"].lower().split())
        overlap = len(query_words & content_words)
        if overlap > 0:
            scored_docs.append({
                "content": doc["content"],
                "source": doc["source"],
                "page": doc["page"],
                "score": overlap,
            })

    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:k] if scored_docs else _fallback_docs()[:k]


def _fallback_docs() -> list[dict]:
    text = """
    SUSPICIOUS ACTIVITY REPORT GUIDANCE

    A SAR narrative must clearly describe: who is involved, what happened,
    when it occurred, where it took place, why it is suspicious, and how
    the suspicious activity was conducted (the 5 Ws + How).

    STRUCTURING: Structuring occurs when a person conducts transactions
    below the $10,000 CTR threshold to evade reporting requirements.
    This is a federal crime under 31 USC 5324.

    MONEY LAUNDERING TYPOLOGIES:
    Placement: Introducing illicit funds into the financial system.
    Layering: Disguising the trail through wire transfers and shell companies.
    Integration: Re-entering funds into the legitimate economy.

    SAR NARRATIVE REQUIREMENTS:
    1. Identify all subjects with full name, DOB, address, and account numbers.
    2. Describe the suspicious transactions with exact dates, amounts, and methods.
    3. Explain why the activity is suspicious, citing specific indicators.
    4. Reference any prior SARs filed on the same subject if applicable.
    5. Describe any steps taken to verify the activity before filing.

    HIGH RISK INDICATORS:
    - Transactions just below reporting thresholds (structuring)
    - Rapid movement of funds through multiple accounts
    - Transactions involving high-risk jurisdictions
    - Politically Exposed Persons (PEPs) with no clear business rationale
    - Round-dollar transactions with no clear business purpose
    - Transactions outside normal business hours
    - High counterparty diversity over short time periods
    """
    return [{"content": text, "source": "fallback_guidance", "page": 0}]
