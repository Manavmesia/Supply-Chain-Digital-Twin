"""
Pydantic schemas for the workflow API endpoints.
"""  

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OrderItemRequest(BaseModel):
    """A single order line item."""
    product_id: UUID
    quantity: int = Field(gt=0, description="Must be a positive integer")


class OrderWorkflowRequest(BaseModel):
    """
    POST /api/v1/workflows/orders

    Kicks off the full supply chain workflow for a customer order.

    Note: `priority` is intentionally absent — it is auto-assigned by the
    Order Management Agent (ADS-01) based on customer tier and order value.
    End users must not be able to influence routing or approval thresholds
    by manipulating priority directly.
    """
    customer_id: UUID
    items: list[OrderItemRequest] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def no_duplicate_products(cls, items: list[OrderItemRequest]) -> list[OrderItemRequest]:
        seen: set[UUID] = set()
        for item in items:
            if item.product_id in seen:
                raise ValueError(f"Duplicate product_id {item.product_id} in order")
            seen.add(item.product_id)
        return items


class WorkflowStatusResponse(BaseModel):
    """GET /api/v1/workflows/{workflow_id}"""
    workflow_id: str
    correlation_id: str | None
    workflow_status: str
    current_node: str | None
    active_agents: list[str]
    order: dict | None
    shipment: dict | None
    executive_decision: dict | None
    requires_human_approval: bool
    event_count: int
    error_count: int
    blackboard: dict | None = None
    human_overrides: dict | None = None


class WorkflowAcceptedResponse(BaseModel):
    """202 response after workflow is accepted."""
    workflow_id: str
    correlation_id: str
    message: str = "Workflow accepted and running"
