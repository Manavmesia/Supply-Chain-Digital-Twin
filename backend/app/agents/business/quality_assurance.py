"""
ADS-14 — Quality Assurance Agent

Responsibilities (from AIS-14 & BACKLOG EP-28 US-122-126):
  - Triggered by InspectionRequested event (from Manufacturing Agent)
  - Read manufacturing state for production run details (mo_id, planned_qty, product_id)
  - Simulate quality inspection: calculate defect rate using a deterministic hash of
    product_id (for test reproducibility) with realistic 0–6% range
  - Apply acceptance criteria: defect_rate <= 3% → PASS, > 3% → FAIL
  - Write QualityInspection DB record
  - Publish InspectionCompleted always
  - Publish QualityPassed or QualityFailed based on outcome
  - QualityFailed → route to Planner for re-manufacture decision
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base_agent import BaseAgent
from app.graph.state import SupplyChainState
from app.models.quality_inspection import QualityInspection

logger = structlog.get_logger(__name__)

_DEFECT_RATE_PASS_THRESHOLD = 3.0    # defect_rate % <= this → PASS
_DEFAULT_SAMPLE_SIZE = 10             # minimum sample size
_SAMPLE_SIZE_RATIO = 0.05             # sample 5% of production qty


def _deterministic_defect_rate(product_id_str: str, mo_id_str: str) -> float:
    """
    Return a deterministic defect rate (0.0–6.0%) based on product and order IDs.
    Uses SHA-256 hash so tests get reproducible results without mocking random.
    In production this would be replaced by actual sensor/measurement data.
    """
    seed = f"{product_id_str}:{mo_id_str}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    # Take first 4 hex chars as an integer (0–65535), scale to 0.0–6.0%
    raw = int(digest[:4], 16)
    return round((raw / 65535.0) * 6.0, 2)


class QualityAssuranceAgent(BaseAgent):
    agent_code = "ADS-14"
    agent_name = "Quality Assurance Agent"

    async def _execute(self, state: SupplyChainState) -> dict[str, Any]:
        session: AsyncSession = self.session
        manufacturing_state: dict = state.get("manufacturing") or {}
        order: dict = state.get("order") or {}

        event_history = list(state.get("event_history") or [])
        decisions = list(state.get("decisions") or [])
        now = datetime.now(timezone.utc)

        # ── 1. Determine what to inspect ──────────────────────────────────────
        # If manufacturing completed, inspect each MO; otherwise inspect from order items
        manufacturing_orders = manufacturing_state.get("orders") or []

        if not manufacturing_orders:
            # No manufacturing run — inspect from order items directly
            items = order.get("items") or []
            if items:
                item = items[0]
                manufacturing_orders = [{
                    "mo_id": str(uuid.uuid4()),
                    "product_id": str(item["product_id"]),
                    "planned_qty": int(item.get("quantity", 10)),
                    "warehouse_id": str(uuid.uuid4()),
                }]

        if not manufacturing_orders:
            decisions = self._record_decision(
                decisions, "qa_skipped",
                "No manufacturing orders or items to inspect",
            )
            return {
                "quality": {"status": "skipped", "reason": "no_items"},
                "decisions": decisions,
                "event_history": event_history,
            }

        inspection_results: list[dict[str, Any]] = []
        overall_status = "passed"

        for mo in manufacturing_orders:
            mo_id_str = str(mo.get("mo_id", uuid.uuid4()))
            product_id_str = str(mo.get("product_id", uuid.uuid4()))
            planned_qty = int(mo.get("planned_qty", 100))

            # ── 2. Calculate sample size and defect rate ──────────────────────
            sample_size = max(_DEFAULT_SAMPLE_SIZE, int(planned_qty * _SAMPLE_SIZE_RATIO))
            defect_rate = _deterministic_defect_rate(product_id_str, mo_id_str)
            defect_count = int((defect_rate / 100.0) * sample_size)
            passed = defect_rate <= _DEFECT_RATE_PASS_THRESHOLD
            inspection_status = "passed" if passed else "failed"

            if not passed:
                overall_status = "failed"

            # ── 3. Write QualityInspection DB record ──────────────────────────
            inspection_id = uuid.uuid4()
            if session:
                try:
                    inspection = QualityInspection(
                        inspection_id=inspection_id,
                        product_id=uuid.UUID(product_id_str),
                        manufacturing_order_id=uuid.UUID(mo_id_str),
                        sample_size=sample_size,
                        defect_count=defect_count,
                        defect_rate=Decimal(str(defect_rate)),
                        status=inspection_status,
                        inspector_agent=self.agent_code,
                        inspected_at=now,
                        created_at=now,
                    )
                    session.add(inspection)
                    await session.flush()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not persist inspection record", error=str(exc))

            # ── 4. Build inspection result payload ────────────────────────────
            inspection_payload = {
                "inspection_id": str(inspection_id),
                "mo_id": mo_id_str,
                "product_id": product_id_str,
                "sample_size": sample_size,
                "defect_count": defect_count,
                "defect_rate_pct": defect_rate,
                "status": inspection_status,
                "passed": passed,
            }

            # Always publish InspectionCompleted
            await self._publish(state, "InspectionCompleted", inspection_payload)
            event_history = self._append_event(event_history, "InspectionCompleted", inspection_payload)

            if passed:
                await self._publish(state, "QualityPassed", inspection_payload)
                event_history = self._append_event(event_history, "QualityPassed", inspection_payload)
                logger.info(
                    "Quality inspection passed",
                    product_id=product_id_str,
                    defect_rate=defect_rate,
                )
            else:
                await self._publish(state, "QualityFailed", inspection_payload)
                event_history = self._append_event(event_history, "QualityFailed", inspection_payload)
                logger.warning(
                    "Quality inspection FAILED",
                    product_id=product_id_str,
                    defect_rate=defect_rate,
                    defect_count=defect_count,
                )

            decisions = self._record_decision(
                decisions,
                f"quality_{inspection_status}",
                f"Inspection {inspection_id}: defect rate {defect_rate:.2f}% → {inspection_status}",
                inspection_payload,
            )

            inspection_results.append(inspection_payload)

        return {
            "quality": {
                "status": overall_status,
                "inspections": inspection_results,
                "all_passed": overall_status == "passed",
                "failed_count": sum(1 for r in inspection_results if not r["passed"]),
            },
            "decisions": decisions,
            "event_history": event_history,
        }
