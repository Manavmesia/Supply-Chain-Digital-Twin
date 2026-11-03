"""
Tests for LLM multi-agent cognition, anti-hallucination guardrails, and deterministic fallback.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import BaseModel

from app.core.llm import (
    extract_multi_agent_digest,
    is_valid_api_key,
    make_llm_decision,
)


class DummyDecisionSchema(BaseModel):
    selected_supplier_id: str
    priority: str
    rationale: str


class DummyTransportSchema(BaseModel):
    selected_route_id: str
    selected_carrier_id: str
    mode: str
    rationale: str


def test_is_valid_api_key():
    # Invalid / empty / placeholder keys
    assert not is_valid_api_key(None)
    assert not is_valid_api_key("")
    assert not is_valid_api_key("   ")
    assert not is_valid_api_key("your-openai-api-key-here")
    assert not is_valid_api_key("YOUR_GROQ_API_KEY")
    assert not is_valid_api_key("<insert-key-here>")
    assert not is_valid_api_key("todo_add_key")
    assert not is_valid_api_key("short")

    # Valid genuine keys
    assert is_valid_api_key("gsk_1234567890abcdef1234567890abcdef")
    assert is_valid_api_key("sk-proj-1234567890abcdef1234567890abcdef")


def test_extract_multi_agent_digest():
    state = {
        "order": {"order_id": "ord-1", "customer_tier": "enterprise"},
        "finance": {"profit_margin": 0.28, "approved": True},
        "risk": {"composite_score": 0.15, "risk_level": "LOW"},
        "forecast": {"predicted_demand": 500},
        "blackboard": {
            "sourcing": [
                {
                    "agent_id": "ADS-04",
                    "status": "accepted",
                    "confidence": 0.95,
                    "rationale": "Primary tier-1 supplier chosen",
                }
            ]
        },
        "decisions": [
            {"agent": "ADS-01", "action": "order_created", "reason": "SLA priority"}
        ],
    }

    digest = extract_multi_agent_digest(state)
    assert "peer_agent_signals" in digest
    assert digest["peer_agent_signals"]["finance"]["profit_margin"] == 0.28
    assert digest["peer_agent_signals"]["risk"]["risk_level"] == "LOW"
    assert "blackboard_status" in digest
    assert digest["blackboard_status"]["sourcing"]["status"] == "accepted"
    assert "prior_decisions_chain" in digest
    assert len(digest["prior_decisions_chain"]) == 1


@pytest.mark.asyncio
async def test_make_llm_decision_offline_fallback():
    with patch("app.core.llm.is_llm_available", return_value=False):
        def _fallback():
            return DummyDecisionSchema(
                selected_supplier_id="sup_default",
                priority="standard",
                rationale="Fallback deterministic rule",
            )

        dec, src = await make_llm_decision(
            agent_code="ADS-04",
            agent_name="Supplier Agent",
            decision_topic="Supplier Evaluation",
            context={"order_units": 100},
            rules=["Rule 1"],
            schema=DummyDecisionSchema,
            fallback_callable=_fallback,
        )

        assert src == "rule_engine"
        assert dec.selected_supplier_id == "sup_default"
        assert dec.priority == "standard"


@pytest.mark.asyncio
async def test_make_llm_decision_synthesizes_context_and_executes():
    mock_decision = DummyDecisionSchema(
        selected_supplier_id="sup_101",
        priority="high",
        rationale="Selected based on [ADS-10] low risk and [ADS-09] 28% margin",
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=mock_decision)
    mock_llm.with_structured_output.return_value = mock_structured

    with (
        patch("app.core.llm.is_llm_available", return_value=True),
        patch("app.core.llm.get_active_provider_and_key", return_value=("groq", "gsk_valid")),
        patch("app.core.llm.get_llm", return_value=mock_llm),
    ):
        state = {
            "risk": {"composite_score": 0.12, "risk_level": "LOW"},
            "finance": {"profit_margin": 0.28},
        }

        dec, src = await make_llm_decision(
            agent_code="ADS-04",
            agent_name="Supplier Agent",
            decision_topic="Supplier Selection",
            context={"candidate_suppliers": ["sup_101", "sup_102"]},
            rules=["Choose reliable supplier"],
            schema=DummyDecisionSchema,
            fallback_callable=lambda: None,
            state=state,
            candidate_id_whitelist=["sup_101", "sup_102"],
        )

        assert src == "llm_groq"
        assert dec.selected_supplier_id == "sup_101"
        assert "[ADS-10]" in dec.rationale

        # Verify cross-agent prompt construction
        mock_structured.ainvoke.assert_awaited_once()
        call_args = mock_structured.ainvoke.call_args[0][0]
        sys_msg = call_args[0].content
        human_msg = call_args[1].content

        assert "CRITICAL ANTI-HALLUCINATION & COGNITION RULES" in sys_msg
        assert "multi_agent_system_context" in human_msg
        assert "composite_score" in human_msg


@pytest.mark.asyncio
async def test_anti_hallucination_guardrail_flat_list():
    # LLM returns a hallucinated ID that does not exist in the candidate list
    hallucinated_decision = DummyDecisionSchema(
        selected_supplier_id="invented_phantom_supplier_999",
        priority="critical",
        rationale="Selected phantom supplier with zero defects",
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=hallucinated_decision)
    mock_llm.with_structured_output.return_value = mock_structured

    with (
        patch("app.core.llm.is_llm_available", return_value=True),
        patch("app.core.llm.get_active_provider_and_key", return_value=("openai", "sk-proj-valid")),
        patch("app.core.llm.get_llm", return_value=mock_llm),
    ):
        dec, src = await make_llm_decision(
            agent_code="ADS-04",
            agent_name="Supplier Agent",
            decision_topic="Supplier Sourcing",
            context={"candidates": ["sup_real_1", "sup_real_2"]},
            rules=["Must pick valid candidate"],
            schema=DummyDecisionSchema,
            fallback_callable=lambda: None,
            candidate_id_whitelist=["sup_real_1", "sup_real_2"],
        )

        assert src == "llm_openai"
        # The guardrail must intercept and replace the hallucinated entity
        assert dec.selected_supplier_id in ("sup_real_1", "sup_real_2")
        assert "Verified against grounded candidate ID" in dec.rationale


@pytest.mark.asyncio
async def test_anti_hallucination_guardrail_dict_multientity():
    # LLM hallucinates both route and carrier
    hallucinated_decision = DummyTransportSchema(
        selected_route_id="route_fake_abc",
        selected_carrier_id="carrier_fake_xyz",
        mode="air",
        rationale="Super fast flight",
    )

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(return_value=hallucinated_decision)
    mock_llm.with_structured_output.return_value = mock_structured

    with (
        patch("app.core.llm.is_llm_available", return_value=True),
        patch("app.core.llm.get_active_provider_and_key", return_value=("groq", "gsk_valid")),
        patch("app.core.llm.get_llm", return_value=mock_llm),
    ):
        dec, src = await make_llm_decision(
            agent_code="ADS-06",
            agent_name="Transportation Agent",
            decision_topic="Route Carrier Sourcing",
            context={},
            rules=["Match route and carrier"],
            schema=DummyTransportSchema,
            fallback_callable=lambda: None,
            candidate_id_whitelist={
                "selected_route_id": ["route_grounded_1"],
                "selected_carrier_id": ["carrier_grounded_1"],
            },
        )

        assert src == "llm_groq"
        assert dec.selected_route_id == "route_grounded_1"
        assert dec.selected_carrier_id == "carrier_grounded_1"
        assert "Verified selected_route_id against grounded candidate" in dec.rationale
        assert "Verified selected_carrier_id against grounded candidate" in dec.rationale
