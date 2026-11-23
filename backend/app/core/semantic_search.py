"""
Local Semantic Document Retrieval & Contract RAG Service.

Provides 100% free, in-process semantic document search over supplier contracts,
carrier SLAs, and incident playbooks without external embedding API dependencies.
Uses normalized term-frequency / inverse-document-frequency (TF-IDF) cosine similarity.
"""

from __future__ import annotations

import math
import re
from typing import Any

# Standard stopwords for supply chain legal contracts
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "having", "do", "does", "did", "doing", "shall", "must", "may",
}

_BASELINE_KNOWLEDGE_DOCUMENTS = [
    {
        "doc_id": "doc-sla-siemens-001",
        "doc_type": "contract",
        "title": "Siemens Global Master Sourcing Agreement (MSA-2026)",
        "source": "Legal & Procurement Affairs",
        "content": (
            "Clause 4.2 — Delivery Time & SLA Penalty Terms: Guaranteed replenishment lead time is 4 business days. "
            "For each 24-hour delivery delay beyond the agreed delivery window, a liquidated damages penalty of 2.0% "
            "of total purchase order value shall be automatically deducted, up to a maximum cap of 15.0%. "
            "Quality compliance threshold requires an acceptance rate of >= 98.5% defect-free units. "
            "Defective batches require immediate remanufacturing or expedited credit memo within 48 hours."
        ),
        "metadata": {"party": "Siemens Global Automations", "tier": "Enterprise", "priority_level": "critical"},
    },
    {
        "doc_id": "doc-sla-tesla-002",
        "doc_type": "contract",
        "title": "Tesla Energy Strategic Partner Supply Terms (ST-402)",
        "source": "Strategic Sourcing Office",
        "content": (
            "Section 7.1 — Volume Pricing & Bulk Tiers: Standard pricing applies to base orders under 20 units. "
            "Tier 1 volume discount of 6.5% automatically applies for order quantities between 20 and 50 units. "
            "Tier 2 volume discount of 10.0% applies for orders exceeding 50 units. "
            "Section 8.4 — Expedited Air Corridor Clause: In the event of critical safety stock deficits at Gigafactory "
            "assembly lines, supplier must activate dedicated priority air freight routing with transit time <= 24 hours."
        ),
        "metadata": {"party": "Tesla Energy & Storage", "tier": "Enterprise", "priority_level": "critical"},
    },
    {
        "doc_id": "doc-sla-schneider-003",
        "doc_type": "contract",
        "title": "Schneider Electric Grid Equipment Sourcing Standard",
        "source": "Global Supply Chain Governance",
        "content": (
            "Article 12 — Dual-Sourcing & Sustainability Mandate: Procurement must maintain at least two qualified "
            "Tier-1 manufacturing suppliers for electronic switchgear and industrial sensors. "
            "Low-carbon freight routing (rail or road over air) is mandated whenever margin is below 20% or route "
            "distance is under 1,000 km. Sustainability compliance score hurdle is 60.0 points."
        ),
        "metadata": {"party": "Schneider Electric Grid", "tier": "Enterprise", "priority_level": "standard"},
    },
    {
        "doc_id": "doc-sop-carrier-004",
        "doc_type": "sop",
        "title": "Standard Operating Procedure: Regional Logistics & Freight Rerouting (SOP-LOG-04)",
        "source": "Transportation Operations Hub",
        "content": (
            "Procedure 3.1 — Carrier Delay Protocol: When road transit corridors exceed 4 hours of unanticipated dwell "
            "time due to severe weather, customs inspection, or infrastructure bottlenecks, Transportation Agent (ADS-06) "
            "must autonomously trigger route recalculation. If road corridor is closed, intermodal rail transfer at nearest "
            "inland dry port must be scheduled. Customer Service Agent (ADS-07) must be notified to revise ETA."
        ),
        "metadata": {"domain": "transportation", "scope": "global", "urgency": "medium"},
    },
    {
        "doc_id": "doc-sop-inventory-005",
        "doc_type": "sop",
        "title": "Standard Operating Procedure: Safety Buffer Violation & Auto-Replenishment (SOP-INV-02)",
        "source": "Central Inventory Control",
        "content": (
            "Procedure 2.4 — Safety Stock Breach Escalation: When available minus reserved inventory drops below "
            "safety stock buffer, ADS-03 must immediately notify ADS-05 Supplier to generate inbound purchase order. "
            "Reorder quantity must be determined via Economic Order Quantity (EOQ) formula with minimum batch size of 100 units. "
            "If supplier lead time exceeds 5 days, secondary regional warehouse transfer must be evaluated simultaneously."
        ),
        "metadata": {"domain": "inventory", "scope": "warehouses", "urgency": "high"},
    },
]


def _tokenize(text: str) -> list[str]:
    """Lowercase and extract alphanumeric word tokens, removing stopwords."""
    words = re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text.lower())
    return [w for w in words if w not in _STOPWORDS]


class SemanticKnowledgeRetriever:
    """Zero-cost local semantic search and contract retrieval engine."""

    def __init__(self, documents: list[dict[str, Any]] | None = None) -> None:
        self.documents = list(documents or _BASELINE_KNOWLEDGE_DOCUMENTS)
        self._doc_tokens: list[list[str]] = [_tokenize(doc["content"] + " " + doc["title"]) for doc in self.documents]
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._build_index()

    def _build_index(self) -> None:
        n_docs = len(self.documents)
        df: dict[str, int] = {}
        for tokens in self._doc_tokens:
            unique_tokens = set(tokens)
            for t in unique_tokens:
                df[t] = df.get(t, 0) + 1

        for token, count in df.items():
            self._vocab[token] = len(self._vocab)
            # Standard smoothed IDF: log((N + 1) / (df + 1)) + 1.0
            self._idf[token] = math.log((n_docs + 1.0) / (count + 1.0)) + 1.0

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        vec: dict[str, float] = {}
        length_sq = 0.0
        for t, count in tf.items():
            if t in self._idf:
                weight = float(count) * self._idf[t]
                vec[t] = weight
                length_sq += weight * weight

        # Normalize to unit sphere for fast cosine similarity
        norm = math.sqrt(length_sq) or 1.0
        return {t: w / norm for t, w in vec.items()}

    def search(self, query: str, top_k: int = 2, min_score: float = 0.05) -> list[dict[str, Any]]:
        """
        Search indexed knowledge documents using cosine similarity.
        Returns top-k documents sorted by relevance score.
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return self.documents[:top_k]

        q_vec = self._vectorize(query_tokens)
        results: list[tuple[float, dict[str, Any]]] = []

        for idx, doc in enumerate(self.documents):
            d_tokens = self._doc_tokens[idx]
            d_vec = self._vectorize(d_tokens)

            # Dot product of normalized unit vectors = cosine similarity
            score = sum(q_vec[t] * d_vec.get(t, 0.0) for t in q_vec if t in d_vec)
            if score >= min_score:
                results.append((score, {**doc, "relevance_score": round(score, 4)}))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]


# Global singleton instance for high-speed in-process retrieval
default_knowledge_retriever = SemanticKnowledgeRetriever()


def query_contract_clauses(query: str, top_k: int = 2) -> list[dict[str, Any]]:
    """Helper function to query contract and SLA clauses across agents."""
    return default_knowledge_retriever.search(query, top_k=top_k)
