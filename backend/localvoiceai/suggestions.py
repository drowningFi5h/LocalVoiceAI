"""Bounded local lexical matching; suggestions are not evidence of an answer."""

import re
from difflib import SequenceMatcher

STOP = set(
    "a an the about tell me what is are was in on of to my your document documents file uploaded please can you summarize explain hi hello thanks it this that does how".split()
)


def words(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP]


def suggest_sources(query, sources, chunks):
    tokens = words(query)[:30]
    if not tokens:
        return []
    content = {}
    for chunk in chunks:
        content.setdefault(chunk["source_id"], set()).update(words(chunk["text"]))
    results = []
    for source in sources:
        title = words(re.sub(r"\.(pdf|md|txt)$", "", source["title"], flags=re.I))
        if not title:
            continue
        title_score = max((SequenceMatcher(None, q, t).ratio() for q in tokens for t in title), default=0)
        hits = sum(q in content.get(source["id"], set()) for q in tokens)
        topic_score = hits / len(tokens)
        if title_score >= 0.72 or (hits >= 1 and topic_score >= 0.5):
            results.append(
                {
                    "id": source["id"],
                    "title": source["title"],
                    "match": "Similar name" if title_score >= 0.72 else "Related topic",
                    "score": max(title_score if title_score >= 0.72 else 0, topic_score * 0.8),
                }
            )
    return sorted(results, key=lambda item: (-item["score"], item["title"]))[:3]
