"""add_supplementary_tables

Revision ID: a1b2c3d4e5f6
Revises: 922ae13073d0
Create Date: 2026-07-30

US-59: Proper Alembic migration for all supplementary tables defined in
01_schema.sql v1.1 (AUD-39 to AUD-46 fixes).

Replaces the initial migration's raw psql subprocess with native
Alembic DDL so that:
  - alembic upgrade head   → creates all tables cleanly
  - alembic downgrade -1   → reverses cleanly in the correct drop order
  - CI can run migrations without a psql binary on the PATH
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "922ae13073d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enum(*values: str, name: str) -> postgresql.ENUM:
    """Return a PostgreSQL ENUM that is created/dropped by the migration."""
    return postgresql.ENUM(*values, name=name, create_type=True)


def _existing_enum(*values: str, name: str) -> postgresql.ENUM:
    """Reference an ENUM that already exists in the DB (create_type=False)."""
    return postgresql.ENUM(*values, name=name, create_type=False)


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    """Create all supplementary tables, indexes, and the shipments.carrier_id FK."""

    # ── 1. ENUMs ────────────────────────────────────────────────────────────

    purchase_order_status = _enum(
        "draft", "approved", "sent", "acknowledged", "in_transit",
        "partially_received", "received", "cancelled",
        name="purchase_order_status",
    )
    purchase_order_status.create(op.get_bind(), checkfirst=True)

    ticket_status = _enum(
        "open", "in_progress", "pending_customer", "escalated", "resolved", "closed",
        name="ticket_status",
    )
    ticket_status.create(op.get_bind(), checkfirst=True)

    ticket_category = _enum(
        "order_inquiry", "delivery_delay", "shipment_tracking",
        "return_request", "billing_issue", "product_quality", "other",
        name="ticket_category",
    )
    ticket_category.create(op.get_bind(), checkfirst=True)

    pricing_trigger = _enum(
        "demand_spike", "low_inventory", "promotion", "cost_change",
        "competitor_price", "manual", "risk_adjustment", "scheduled",
        name="pricing_trigger",
    )
    pricing_trigger.create(op.get_bind(), checkfirst=True)

    contract_status = _enum(
        "draft", "active", "expiring_soon", "expired", "terminated", "under_review",
        name="contract_status",
    )
    contract_status.create(op.get_bind(), checkfirst=True)

    carrier_status = _enum(
        "active", "inactive", "blacklisted",
        name="carrier_status",
    )
    carrier_status.create(op.get_bind(), checkfirst=True)

    freight_mode_type = _enum(
        "air", "sea", "road", "rail", "multimodal",
        name="freight_mode_type",
    )
    freight_mode_type.create(op.get_bind(), checkfirst=True)

    promotion_status = _enum(
        "scheduled", "active", "completed", "cancelled",
        name="promotion_status",
    )
    promotion_status.create(op.get_bind(), checkfirst=True)

    report_type = _enum(
        "executive_summary", "operational_kpi", "financial", "risk",
        "sustainability", "quality", "audit", "workflow", "custom",
        name="report_type",
    )
    report_type.create(op.get_bind(), checkfirst=True)

    report_status = _enum(
        "generating", "ready", "failed", "archived",
        name="report_status",
    )
    report_status.create(op.get_bind(), checkfirst=True)

    # ── 2. CARRIERS ──────────────────────────────────────────────────────────

    op.create_table(
        "carriers",
        sa.Column("carrier_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column(
            "freight_modes",
            postgresql.ARRAY(_existing_enum(
                "air", "sea", "road", "rail", "multimodal",
                name="freight_mode_type",
            )),
            nullable=False,
        ),
        sa.Column("tracking_url", sa.Text, nullable=True),
        sa.Column("api_endpoint", sa.Text, nullable=True),
        sa.Column(
            "reliability_score",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="80.0",
        ),
        sa.Column(
            "avg_delay_days",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "status",
            _existing_enum("active", "inactive", "blacklisted", name="carrier_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("blacklist_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("code", name="carriers_code_unique"),
    )

    # ── 3. TRANSPORTATION ROUTES ─────────────────────────────────────────────

    op.create_table(
        "transportation_routes",
        sa.Column("route_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "carrier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("carriers.carrier_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "origin_warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("origin_location", sa.Text, nullable=False),
        sa.Column("destination", sa.Text, nullable=False),
        sa.Column(
            "freight_mode",
            _existing_enum("air", "sea", "road", "rail", "multimodal", name="freight_mode_type"),
            nullable=False,
        ),
        sa.Column("transit_days", sa.Integer, nullable=False),
        sa.Column("base_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("cost_per_kg", sa.Numeric(8, 4), nullable=False, server_default="0.0"),
        sa.Column("cost_per_m3", sa.Numeric(8, 4), nullable=False, server_default="0.0"),
        sa.Column("co2_per_tonne_km", sa.Numeric(8, 4), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("route_hash", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 4. ADD carrier_id FK to shipments (AUD-45) ───────────────────────────

    op.add_column(
        "shipments",
        sa.Column(
            "carrier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("carriers.carrier_id", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── 5. PURCHASE ORDERS ───────────────────────────────────────────────────

    op.create_table(
        "purchase_orders",
        sa.Column("po_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses.warehouse_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.Text, nullable=False, server_default="USD"),
        sa.Column(
            "status",
            _existing_enum(
                "draft", "approved", "sent", "acknowledged", "in_transit",
                "partially_received", "received", "cancelled",
                name="purchase_order_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("requested_delivery", sa.Date, nullable=True),
        sa.Column("confirmed_delivery", sa.Date, nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triggered_by_agent", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 6. SUPPORT TICKETS ───────────────────────────────────────────────────

    op.create_table(
        "support_tickets",
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.customer_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("orders.order_id", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "shipment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("shipments.shipment_id", onupdate="CASCADE", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category",
            _existing_enum(
                "order_inquiry", "delivery_delay", "shipment_tracking",
                "return_request", "billing_issue", "product_quality", "other",
                name="ticket_category",
            ),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "status",
            _existing_enum(
                "open", "in_progress", "pending_customer", "escalated", "resolved", "closed",
                name="ticket_status",
            ),
            nullable=False,
            server_default="open",
        ),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("assigned_agent", sa.Text, nullable=True),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 7. PRICING HISTORY ───────────────────────────────────────────────────

    op.create_table(
        "pricing_history",
        sa.Column("price_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("previous_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("recommended_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("approved_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "trigger_type",
            _existing_enum(
                "demand_spike", "low_inventory", "promotion", "cost_change",
                "competitor_price", "manual", "risk_adjustment", "scheduled",
                name="pricing_trigger",
            ),
            nullable=False,
            server_default="manual",
        ),
        sa.Column("trigger_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("margin_impact", sa.Numeric(6, 2), nullable=True),
        sa.Column("demand_signal", sa.Numeric(12, 2), nullable=True),
        sa.Column("approved_by_agent", sa.Text, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 8. CONTRACTS ─────────────────────────────────────────────────────────

    op.create_table(
        "contracts",
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.supplier_id", onupdate="CASCADE", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contract_reference", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column(
            "status",
            _existing_enum(
                "draft", "active", "expiring_soon", "expired", "terminated", "under_review",
                name="contract_status",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("contract_type", sa.Text, nullable=True),
        sa.Column("total_value", sa.Numeric(16, 2), nullable=True),
        sa.Column("currency", sa.Text, nullable=False, server_default="USD"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("auto_renew", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notice_period_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("payment_terms_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("terms", sa.Text, nullable=True),
        sa.Column("document_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("contract_reference", name="contracts_reference_unique"),
    )

    op.create_table(
        "contract_products",
        sa.Column(
            "contract_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contracts.contract_id", onupdate="CASCADE", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("contracted_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("min_volume", sa.Integer, nullable=True),
        sa.Column("max_volume", sa.Integer, nullable=True),
    )

    # ── 9. PROMOTIONS ────────────────────────────────────────────────────────

    op.create_table(
        "promotions",
        sa.Column("promotion_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            _existing_enum("scheduled", "active", "completed", "cancelled", name="promotion_status"),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_segment", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "promotion_products",
        sa.Column(
            "promotion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("promotions.promotion_id", onupdate="CASCADE", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.product_id", onupdate="CASCADE", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )

    # ── 10. REPORTS ──────────────────────────────────────────────────────────

    op.create_table(
        "reports",
        sa.Column("report_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_type",
            _existing_enum(
                "executive_summary", "operational_kpi", "financial", "risk",
                "sustainability", "quality", "audit", "workflow", "custom",
                name="report_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column(
            "status",
            _existing_enum("generating", "ready", "failed", "archived", name="report_status"),
            nullable=False,
            server_default="generating",
        ),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by_agent", sa.Text, nullable=False, server_default="ADS-18"),
        sa.Column("storage_url", sa.Text, nullable=True),
        sa.Column("payload_summary", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── 11. INDEXES (US-62) ──────────────────────────────────────────────────

    op.create_index("idx_po_supplier_status", "purchase_orders", ["supplier_id", "status"])
    op.create_index("idx_po_product_id",      "purchase_orders", ["product_id"])
    op.create_index("idx_po_created_at",      "purchase_orders", [sa.text("created_at DESC")])
    op.create_index(
        "idx_po_workflow_id", "purchase_orders", ["workflow_id"],
        postgresql_where=sa.text("workflow_id IS NOT NULL"),
    )

    op.create_index("idx_tickets_customer_status", "support_tickets", ["customer_id", "status"])
    op.create_index(
        "idx_tickets_sla_deadline", "support_tickets", ["sla_deadline"],
        postgresql_where=sa.text("status NOT IN ('resolved', 'closed')"),
    )

    op.create_index(
        "idx_pricing_product_created", "pricing_history",
        ["product_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_pricing_pending", "pricing_history", ["product_id"],
        postgresql_where=sa.text("approved_price IS NULL"),
    )

    op.create_index("idx_contracts_supplier", "contracts", ["supplier_id", "status"])
    op.create_index(
        "idx_contracts_end_date", "contracts", ["end_date", "status"],
        postgresql_where=sa.text("status IN ('active', 'expiring_soon')"),
    )

    op.create_index(
        "idx_carriers_status", "carriers",
        ["status", sa.text("reliability_score DESC")],
    )

    op.create_index("idx_routes_carrier", "transportation_routes", ["carrier_id", "is_active"])
    op.create_index(
        "idx_routes_origin_dest", "transportation_routes",
        ["origin_location", "destination", "freight_mode"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    op.create_index(
        "idx_promotions_active", "promotions", ["starts_at", "ends_at"],
        postgresql_where=sa.text("status IN ('scheduled', 'active')"),
    )

    op.create_index(
        "idx_reports_type_status", "reports",
        ["report_type", "status", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_reports_workflow_id", "reports", ["workflow_id"],
        postgresql_where=sa.text("workflow_id IS NOT NULL"),
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Drop all supplementary tables and ENUMs in safe reverse order."""

    # Indexes
    for idx in [
        "idx_reports_workflow_id", "idx_reports_type_status",
        "idx_promotions_active",
        "idx_routes_origin_dest", "idx_routes_carrier",
        "idx_carriers_status",
        "idx_contracts_end_date", "idx_contracts_supplier",
        "idx_pricing_pending", "idx_pricing_product_created",
        "idx_tickets_sla_deadline", "idx_tickets_customer_status",
        "idx_po_workflow_id", "idx_po_created_at", "idx_po_product_id", "idx_po_supplier_status",
    ]:
        op.drop_index(idx, if_exists=True)

    # Tables (leaves → roots)
    op.drop_table("reports")
    op.drop_table("promotion_products")
    op.drop_table("promotions")
    op.drop_table("contract_products")
    op.drop_table("contracts")
    op.drop_table("pricing_history")
    op.drop_table("support_tickets")
    op.drop_table("purchase_orders")

    # Remove carrier_id from shipments
    op.drop_column("shipments", "carrier_id")

    op.drop_table("transportation_routes")
    op.drop_table("carriers")

    # ENUMs
    for name in [
        "report_status", "report_type", "promotion_status",
        "freight_mode_type", "carrier_status", "contract_status",
        "pricing_trigger", "ticket_category", "ticket_status",
        "purchase_order_status",
    ]:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
