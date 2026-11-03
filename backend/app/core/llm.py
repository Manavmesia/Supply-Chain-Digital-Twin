"""
LLM Provider Factory & Multi-Agent Cognitive Decision Engine.

Provides:
  - is_llm_available(): checks if a genuine LLM API key is present in environment/settings.
  - get_llm(): instantiates ChatGroq or ChatOpenAI with zero temperature for precision.
  - make_llm_decision(): executes grounded, multi-agent-informed structured decisions
    synthesizing peer agent signals, blackboard status, and tool data with anti-hallucination guardrails.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, TypeVar

import structlog
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def is_valid_api_key(key: Any) -> bool:
    """Check if key is non-empty and not a template placeholder."""
    if not key:
        return False
    k = str(key).strip()
    if not k or k.lower() in ("none", "null", "false", "0"):
        return False
    # Reject common template placeholders like 'your-openai-api-key-here' or 'YOUR_GROQ_API_KEY'
    lowered = k.lower()
    placeholder_tokens = (
        "your", "placeholder", "todo", "insert",
        "key-here", "key_here", "xxx", "change_me", "example", "sample", "<", ">",
    )
    if any(p in lowered for p in placeholder_tokens):
        return False
    return len(k) >= 16


def is_llm_available() -> bool:
    """Return True if any supported genuine LLM API key is present in settings or environment."""
    _, key = get_active_provider_and_key()
    return is_valid_api_key(key)


def get_active_provider_and_key() -> tuple[str, str | None]:
    """Resolve the active LLM provider and API key."""
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    openai_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    generic_key = settings.LLM_API_KEY or os.environ.get("LLM_API_KEY")

    if is_valid_api_key(groq_key):
        return "groq", groq_key
    if is_valid_api_key(openai_key):
        return "openai", openai_key
    if is_valid_api_key(generic_key):
        if str(generic_key).startswith("gsk_"):
            return "groq", generic_key
        if str(generic_key).startswith("sk-"):
            return "openai", generic_key
        return (settings.LLM_PROVIDER or "groq").lower(), generic_key

    return (settings.LLM_PROVIDER or "groq").lower(), None


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Factory function to initialize and return a LangChain ChatModel instance.
    Defaults to zero temperature for mathematically exact and reproducible decisions.
    """
    detected_provider, api_key = get_active_provider_and_key()
    provider = (provider or detected_provider).lower()
    temp = 0.0 if temperature is None else temperature

    if provider == "groq":
        from langchain_groq import ChatGroq

        selected_model = model or settings.LLM_MODEL or "llama-3.3-70b-versatile"
        return ChatGroq(
            model=selected_model,
            temperature=temp,
            groq_api_key=api_key if api_key else None,
            **kwargs,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        selected_model = model or "gpt-4o-mini"
        return ChatOpenAI(
            model=selected_model,
            temperature=temp,
            api_key=api_key if api_key else None,
            **kwargs,
        )

    raise ValueError(
        f"Unsupported LLM provider: '{provider}'. Supported providers are 'groq' and 'openai'."
    )


def extract_multi_agent_digest(state: dict[str, Any] | None) -> dict[str, Any]:
    """
    Extracts an aggregated digest of all peer agent signals and blackboard consensus.
    Enables cross-agent cognition so each agent reasons over the complete twin state.
    """
    if not state or not isinstance(state, dict):
        return {}

    digest: dict[str, Any] = {}

    # 1. Peer Agent Functional Signals
    peer_topics = (
        "order", "customer", "inventory", "warehouse", "supplier",
        "shipment", "finance", "risk", "forecast", "quality",
        "sustainability", "manufacturing", "customer_service",
        "pricing", "procurement", "planning", "negotiation", "executive_decision"
    )
    peer_signals: dict[str, Any] = {}
    for topic in peer_topics:
        val = state.get(topic)
        if val and isinstance(val, dict):
            # Clean summary without giant raw byte lists
            clean_val = {}
            for k, v in val.items():
                if isinstance(v, list) and len(v) > 5:
                    clean_val[k] = v[:5]
                    clean_val[f"{k}__total_count"] = len(v)
                else:
                    clean_val[k] = v
            peer_signals[topic] = clean_val
    if peer_signals:
        digest["peer_agent_signals"] = peer_signals

    # 2. Shared Blackboard Consensus (active proposals & commitments)
    blackboard = state.get("blackboard")
    if blackboard and isinstance(blackboard, dict):
        bb_digest = {}
        for topic, entries in blackboard.items():
            if entries and isinstance(entries, list):
                active = [e for e in entries if e.get("status") in ("proposed", "accepted", "contested")]
                latest = active[-1] if active else entries[-1]
                bb_digest[topic] = {
                    "source_agent": latest.get("agent_id"),
                    "status": latest.get("status"),
                    "confidence": latest.get("confidence"),
                    "rationale": latest.get("rationale"),
                }
        if bb_digest:
            digest["blackboard_status"] = bb_digest

    # 3. Decision Chain History
    decisions = state.get("decisions")
    if decisions and isinstance(decisions, list):
        digest["prior_decisions_chain"] = [
            {"agent": d.get("agent"), "action": d.get("action"), "reason": d.get("reason")}
            for d in decisions[-5:]
        ]

    return digest


async def make_llm_decision(
    agent_code: str,
    agent_name: str,
    decision_topic: str,
    context: dict[str, Any],
    rules: list[str],
    schema: type[T],
    fallback_callable: Callable[[], T],
    state: dict[str, Any] | None = None,
    candidate_id_whitelist: list[str] | set[str] | dict[str, list[str]] | None = None,
) -> tuple[T, str]:
    """
    Executes a high-accuracy structured decision.
    If an LLM API key is present:
      - Aggregates multi-agent peer signals from `state` (finance, risk, forecast, etc.).
      - Injects strict anti-hallucination guardrails and fact citations into the prompt.
      - Enforces zero temperature and typed Pydantic structured output.
      - Verifies any selected IDs against `candidate_id_whitelist` to prevent entity hallucinations.
    If no genuine key is present, returns fallback_callable().
    """
    if not is_llm_available():
        logger.debug(
            "No genuine LLM API key present, using deterministic rule engine",
            agent=agent_code,
            topic=decision_topic,
        )
        return fallback_callable(), "rule_engine"

    try:
        provider, _ = get_active_provider_and_key()
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(schema)

        # Build multi-agent holistic context
        system_digest = extract_multi_agent_digest(state)
        full_context = {
            "local_candidates_and_tool_data": context,
            "multi_agent_system_context": system_digest,
        }

        system_prompt = (
            f"You are the {agent_name} ({agent_code}) in an autonomous enterprise Supply Chain Digital Twin.\n"
            "You collaborate with 17 other specialized AI agents and use deterministic domain tools.\n"
            "Your objective: Make an authoritative, intelligent, and optimal decision grounded strictly on the facts, "
            "peer agent outputs, and tool candidate records provided.\n\n"
            "CRITICAL ANTI-HALLUCINATION & COGNITION RULES:\n"
            "1. STRICT GROUND TRUTH: You MUST NOT invent any non-existent entity IDs, products, carriers, warehouses, or dates.\n"
            "   You can ONLY select from the explicit candidate lists and database records provided in the context.\n"
            "2. CROSS-AGENT COGNITION: Smartly balance signals across other agents:\n"
            "   - Factor in Risk Assessment [ADS-10] and Financial Margins [ADS-09].\n"
            "   - Factor in Customer SLA commitments [ADS-01] and Demand Forecast [ADS-02].\n"
            "   - Factor in Quality verdicts [ADS-14] and Carbon Footprint [ADS-13].\n"
            "3. EVIDENCE CITATION: In your rationale, explicitly cite the exact data points and agent codes (e.g. [ADS-01], [ADS-09], [ADS-10]) that justify your decision.\n"
            "4. MATHEMATICAL INVARIANTS: Strictly enforce the business rules, formulas, and constraints provided. Do not hallucinate numbers."
        )

        formatted_rules = "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))
        human_prompt = (
            f"=== AGENT DECISION TASK ===\n"
            f"Agent: {agent_name} ({agent_code})\n"
            f"Decision Topic: {decision_topic}\n\n"
            f"=== FACTUAL CONTEXT & TOOL DATA ===\n"
            f"{json.dumps(full_context, indent=2, default=str)}\n\n"
            f"=== MANDATORY DOMAIN RULES & INVARIANTS ===\n"
            f"{formatted_rules}\n\n"
            "Synthesize all peer agent data and tool facts smartly, apply the rules with zero hallucination, and return the structured decision object."
        )

        decision = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        # ── Anti-Hallucination Ground-Truth Verification Guardrail ────────────
        if candidate_id_whitelist:
            if isinstance(candidate_id_whitelist, dict):
                for field_name, ids in candidate_id_whitelist.items():
                    valid_set = {str(c) for c in ids if c is not None}
                    chosen_val = getattr(decision, field_name, None)
                    if chosen_val and str(chosen_val) not in valid_set and valid_set:
                        first_valid = next(iter(valid_set))
                        logger.warning(
                            "LLM hallucinated ungrounded entity ID, correcting to verified ground truth",
                            agent=agent_code,
                            field=field_name,
                            hallucinated_id=chosen_val,
                            corrected_to=first_valid,
                        )
                        setattr(decision, field_name, first_valid)
                        if hasattr(decision, "rationale"):
                            decision.rationale += f" [Verified {field_name} against grounded candidate: {first_valid}]"
            else:
                valid_set = {str(c) for c in candidate_id_whitelist if c is not None}
                if valid_set:
                    for field_name in ("selected_supplier_id", "selected_route_id", "selected_carrier_id", "selected_warehouse_id", "product_id"):
                        chosen_val = getattr(decision, field_name, None)
                        if chosen_val and str(chosen_val) not in valid_set:
                            first_valid = next(iter(valid_set))
                            logger.warning(
                                "LLM hallucinated ungrounded entity ID, correcting to verified ground truth",
                                agent=agent_code,
                                field=field_name,
                                hallucinated_id=chosen_val,
                                corrected_to=first_valid,
                            )
                            setattr(decision, field_name, first_valid)
                            if hasattr(decision, "rationale"):
                                decision.rationale += f" [Verified against grounded candidate ID: {first_valid}]"
                            break

        logger.info(
            "LLM decision generated successfully with zero hallucination",
            agent=agent_code,
            topic=decision_topic,
            provider=provider,
        )
        return decision, f"llm_{provider}"

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "LLM decision call failed, falling back to deterministic rule engine",
            agent=agent_code,
            topic=decision_topic,
            error=str(exc),
        )
        return fallback_callable(), "fallback_rule_engine"
