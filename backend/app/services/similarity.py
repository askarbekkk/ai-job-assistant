"""Text similarity between a resume and job postings (Section 10, step 3).

Backends:
  * "sbert" — Sentence-BERT embeddings (sentence-transformers). The default model
              is multilingual so Korean postings work too. Job embeddings are
              cached in the `jobs.embedding` column.
  * "tfidf" — pure-Python TF-IDF cosine. Used when sentence-transformers is not
              installed; scores are lower on average, so tune weights per backend.
"""

import logging
import math
import re
from collections import Counter
from functools import lru_cache

from ..config import settings

log = logging.getLogger(__name__)

_TOKEN = re.compile(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]|[0-9]+|[가-힣]+")
_STOPWORDS = set(
    "a an and are as at be by for from has have in is it of on or our the to we will with you your "
    "this that who can work team experience skills".split()
)


@lru_cache
def _sbert_model():
    from sentence_transformers import SentenceTransformer

    log.info("Loading sentence embedding model %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


@lru_cache
def backend() -> str:
    mode = settings.embedding_backend.lower()
    if mode == "tfidf":
        return "tfidf"
    try:
        _sbert_model()
        return "sbert"
    except ImportError:
        if mode == "sbert":
            raise
        log.info("sentence-transformers not installed; using TF-IDF similarity")
        return "tfidf"


# ---------------------------------------------------------------- SBERT


def encode(texts: list[str]) -> list[list[float]]:
    vectors = _sbert_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embedding_record(text: str) -> dict:
    return {"model": settings.embedding_model, "vector": encode([text])[0]}


def is_current(record: dict | None) -> bool:
    return bool(record) and record.get("model") == settings.embedding_model


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# ---------------------------------------------------------------- TF-IDF


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOPWORDS]


def tfidf_similarities(query: str, docs: list[str]) -> list[float]:
    doc_tokens = [Counter(_tokens(d)) for d in docs]
    query_tokens = Counter(_tokens(query))
    n = len(docs) + 1
    df: Counter = Counter()
    for counts in [*doc_tokens, query_tokens]:
        df.update(counts.keys())
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}

    def vec(counts: Counter) -> dict[str, float]:
        v = {t: (1 + math.log(c)) * idf[t] for t, c in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    q = vec(query_tokens)
    return [sum(q.get(t, 0.0) * x for t, x in vec(c).items()) for c in doc_tokens]


# ---------------------------------------------------------------- facade


def similarities(resume_text: str, resume_embedding: dict | None, jobs: list) -> list[float]:
    """Cosine similarity in [0, 1] between the resume and each job, in order.

    In SBERT mode, jobs without a current embedding get one computed and stored
    on the object (the caller commits).
    """
    if not jobs:
        return []
    if backend() == "tfidf":
        return tfidf_similarities(resume_text, [job_text(j) for j in jobs])

    missing = [j for j in jobs if not is_current(j.embedding)]
    if missing:
        for job, vector in zip(missing, encode([job_text(j) for j in missing])):
            job.embedding = {"model": settings.embedding_model, "vector": vector}
    query = resume_embedding["vector"] if is_current(resume_embedding) else encode([resume_text])[0]
    return [max(0.0, min(1.0, _dot(query, j.embedding["vector"]))) for j in jobs]


def job_text(job) -> str:
    return f"{job.title}\n{job.description}"
