"""
Generate two baseline evaluation datasets from golden_labels.csv:
  1. keyword_baseline.csv  — BM25 / lexical overlap re-ranking
  2. vector_baseline.csv   — Semantic similarity (cosine) re-ranking

Both files keep the SAME rows and columns; only job_rank changes per resume.
Labels (is_relevant, relevance_reason) are preserved exactly as-is.
"""

import math
import csv
import re
from collections import Counter

# ---------------------------------------------------------------------------
# 1.  Load golden_labels.csv (stdlib only — no pandas needed for generation)
# ---------------------------------------------------------------------------
import os
import pathlib

# Support both old (data/) and new (golden_dataset/) locations
_script_dir = pathlib.Path(__file__).parent
_candidates = [
    _script_dir / "golden_labels.csv",                           # data/
    _script_dir.parent / "golden_dataset" / "golden_labels.csv", # golden_dataset/
]
INPUT_FILE = next((str(p) for p in _candidates if p.exists()), "golden_labels.csv")
print(f"Reading input from: {INPUT_FILE}")

# Write outputs to a baselines/ subfolder to avoid PermissionError
# when the previous CSVs are open in another application
_out_dir = _script_dir / "baselines"
_out_dir.mkdir(exist_ok=True)
KW_OUTPUT  = str(_out_dir / "keyword_baseline.csv")
VEC_OUTPUT = str(_out_dir / "vector_baseline.csv")

with open(INPUT_FILE, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames          # preserve original column order
    rows = list(reader)

# Group rows by resume_id  (each group has exactly 5 jobs)
from itertools import groupby
rows_sorted = sorted(rows, key=lambda r: r["resume_id"])
resume_groups = {k: list(g) for k, g in groupby(rows_sorted, key=lambda r: r["resume_id"])}

# ---------------------------------------------------------------------------
# 2.  BM25 / Keyword Baseline
# ---------------------------------------------------------------------------
# Simple BM25-style scoring:
#   - Tokenise query and document (job_title + job_description_preview)
#   - Compute term frequency (TF) with saturation: tf / (tf + k1)
#   - Compute inverse document frequency (IDF) across the 5 docs per resume
#   - Score = Σ  idf(t) * tf_saturation(t, doc)

def tokenize(text: str) -> list[str]:
    """Lowercase, strip non-alphanumeric, split into tokens."""
    return re.findall(r"[a-z0-9+#]+", text.lower())

def bm25_score(query_tokens: list[str], doc_tokens: list[str],
               df_map: dict[str, int], n_docs: int,
               k1: float = 1.5, b: float = 0.0) -> float:
    """
    Simplified BM25 (no doc-length normalization since we compare within
    the same result set and descriptions are truncated to similar lengths).
    """
    tf = Counter(doc_tokens)
    score = 0.0
    for t in query_tokens:
        if t not in tf:
            continue
        t_freq = tf[t]
        # IDF with smoothing
        df = df_map.get(t, 0)
        idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
        # TF saturation
        tf_component = (t_freq * (k1 + 1)) / (t_freq + k1 * (1 - b + b))
        score += idf * tf_component
    return score

keyword_rows = []
for resume_id, group in resume_groups.items():
    query_tokens = tokenize(group[0]["search_query"])

    # Build document token lists and DF map
    doc_token_lists = []
    for row in group:
        doc_text = (row["job_title"] or "") + " " + (row["job_description_preview"] or "")
        doc_token_lists.append(tokenize(doc_text))

    # Document frequency per term (across the 5 docs in this resume group)
    df_map: dict[str, int] = {}
    for dtl in doc_token_lists:
        for t in set(dtl):
            df_map[t] = df_map.get(t, 0) + 1

    # Score each job
    scored = []
    for row, dtl in zip(group, doc_token_lists):
        s = bm25_score(query_tokens, dtl, df_map, n_docs=len(group))
        scored.append((s, row))

    # Sort descending by score (higher = better match)
    scored.sort(key=lambda x: x[0], reverse=True)

    # Assign new ranks 1-5
    for rank, (_, row) in enumerate(scored, start=1):
        new_row = dict(row)
        new_row["job_rank"] = str(rank)
        keyword_rows.append(new_row)

# Write keyword_baseline.csv
with open(KW_OUTPUT, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(keyword_rows)

print(f"✅  Wrote {KW_OUTPUT}  ({len(keyword_rows)} rows)")

# ---------------------------------------------------------------------------
# 3.  Vector-Only Baseline  (sentence-transformers, 768-d, cosine similarity)
# ---------------------------------------------------------------------------
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("Installing sentence-transformers …")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "sentence-transformers", "-q"])
    from sentence_transformers import SentenceTransformer, util

print("Loading embedding model (all-mpnet-base-v2, 768-d) …")
model = SentenceTransformer("all-mpnet-base-v2")   # 768-dim

vector_rows = []
for resume_id, group in resume_groups.items():
    query_text = group[0]["search_query"]

    # Build doc texts
    doc_texts = []
    for row in group:
        doc_texts.append(
            (row["job_title"] or "") + ". " + (row["job_description_preview"] or "")
        )

    # Encode query + docs in one batch
    embeddings = model.encode([query_text] + doc_texts, convert_to_tensor=True)
    query_emb  = embeddings[0]
    doc_embs   = embeddings[1:]

    # Cosine similarities
    cos_scores = util.cos_sim(query_emb, doc_embs)[0].tolist()

    # Pair scores with rows
    scored = list(zip(cos_scores, group))
    scored.sort(key=lambda x: x[0], reverse=True)

    for rank, (_, row) in enumerate(scored, start=1):
        new_row = dict(row)
        new_row["job_rank"] = str(rank)
        vector_rows.append(new_row)

# Write vector_baseline.csv
with open(VEC_OUTPUT, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(vector_rows)

print(f"✅  Wrote {VEC_OUTPUT}  ({len(vector_rows)} rows)")
print("\nDone. Both baseline files are ready for evaluation.")
