"""Natural keys for dedup (NFR-04). Pure functions only — no I/O, no state.

KNOWN LIMIT: exact-match after normalization. Near-duplicate phrasings
("send the itinerary" vs "send the Jakarta itinerary") produce different
keys and survive dedup. Accepted for MVP; fuzzy matching is TODO.
"""

import hashlib
import re

_WS = re.compile(r"\s+")

def _normalize(text: str) -> str:
    text = text.casefold().strip()
    text = _WS.sub(" ", text)          # collapse runs of whitespace to one space
    return text.rstrip(".!?,;: ")      # trailing punctuation only — internal stays

def _digest(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]

def commitment_key(owner: str, action: str) -> str:
    return _digest("commitment", _normalize(owner), _normalize(action))

def decision_key(owner: str, statement: str) -> str:
    return _digest("decision", _normalize(owner), _normalize(statement))

def key_fact_key(statement: str) -> str:
    return _digest("key_fact", _normalize(statement))
