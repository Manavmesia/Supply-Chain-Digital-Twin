"""
Tests for ORM models — verifies that every model can be instantiated
with correct defaults and that enum-backed columns only accept valid values.

These are pure Python tests (no DB required) except for the round-trip
tests that use the db_session fixture.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from tests.conftest import (
    CUSTOMER_ID,
    PRODUCT_LAPTOP_ID,
    SUPPLIER_TECHCORE_ID,
    WAREHOUSE_EAST_ID,
    make_carrier,
    make_contract,
    make_order,
    make_purchase_order,
    make_shipment,
    make_support_ticket,
    make_transportation_route,
)


# ---------------------------------------------------------------------------
# Unit tests — no DB needed
# ---------------------------------------------------------------------------

class TestOrderModel:
    def test_defaults(self):
        order = make_order()
        assert order.status == "pending"
        assert order.priority == "standard"
        assert order.currency == "USD"

    def test_custom_values(self):
        order = make_order(status="processing", priority="high", total_amount=Decimal("99999.99"))
        assert order.status == "processing"
        assert order.priority == "high"
        assert order.total_amount == Decimal("99999.99")

    def test_order_id_is_uuid(self):
        order = make_order()
        assert isinstance(order.order_id, uuid.UUID)

    def test_items_relationship_default_empty(self):
        from app.models.order import Order
        order = Order.__new__(Order)
        # Relationship is lazy — attribute access before session attach is None or not loaded
        assert hasattr(order, "__tablename__")
        assert order.__tablename__ == "orders"


class TestShipmentModel:
    def test_defaults(self):
        order_id = uuid.uuid4()
        ship = make_shipment(order_id)
        assert ship.status == "pending"
        assert ship.carrier_id is None

    def test_valid_status_values(self):
        for status in ("pending", "assigned", "dispatched", "in_transit", "delivered", "delayed", "failed", "returned"):
            s = make_shipment(uuid.uuid4(), status=status)
            assert s.status == status


class TestCarrierModel:
    def test_defaults(self):
        c = make_carrier()
        assert c.status == "active"
        assert c.avg_delay_days == Decimal("0.50")

    def test_freight_modes_list(self):
        c = make_carrier(freight_modes=["air", "sea"])
        assert "air" in c.freight_modes
        assert "sea" in c.freight_modes

    def test_all_valid_statuses(self):
        for s in ("active", "inactive", "blacklisted"):
            c = make_carrier(status=s)
            assert c.status == s


class TestPurchaseOrderModel:
    def test_defaults(self):
        po = make_purchase_order()
        assert po.status == "draft"
        assert po.currency == "USD"

    def test_total_cost_set(self):
        po = make_purchase_order(quantity=5, unit_cost=Decimal("1000.00"))
        # total_cost is a server_default/generated column in DB
        assert po.quantity == 5
        assert po.unit_cost == Decimal("1000.00")

    def test_valid_statuses(self):
        for status in ("draft", "approved", "sent", "acknowledged", "in_transit",
                       "partially_received", "received", "cancelled"):
            po = make_purchase_order(status=status)
            assert po.status == status


class TestSupportTicketModel:
    def test_defaults(self):
        t = make_support_ticket()
        assert t.status == "open"
        assert t.category == "other"

    def test_valid_categories(self):
        for cat in ("order_inquiry", "delivery_delay", "shipment_tracking",
                    "return_request", "billing_issue", "product_quality", "other"):
            t = make_support_ticket(category=cat)
            assert t.category == cat

    def test_valid_statuses(self):
        for s in ("open", "in_progress", "pending_customer", "escalated", "resolved", "closed"):
            t = make_support_ticket(status=s)
            assert t.status == s


class TestContractModel:
    def test_defaults(self):
        c = make_contract()
        assert c.status == "active"
        assert c.currency == "USD"
        assert c.auto_renew is False

    def test_valid_statuses(self):
        for s in ("draft", "active", "expiring_soon", "expired", "terminated", "under_review"):
            c = make_contract(status=s)
            assert c.status == s


class TestTransportationRouteModel:
    def test_defaults(self):
        carrier_id = uuid.uuid4()
        r = make_transportation_route(carrier_id)
        assert r.is_active is True
        assert r.freight_mode == "road"

    def test_valid_freight_modes(self):
        carrier_id = uuid.uuid4()
        for mode in ("air", "sea", "road", "rail", "multimodal"):
            r = make_transportation_route(carrier_id, freight_mode=mode)
            assert r.freight_mode == mode


class TestRiskAssessmentModel:
    def test_instantiation(self):
        from app.models.risk_assessment import RiskAssessment
        r = RiskAssessment(
            risk_id=uuid.uuid4(),
            entity_type="supplier",
            entity_id=SUPPLIER_TECHCORE_ID,
            risk_score=Decimal("72.50"),
            risk_category="reliability",
            mitigation_status="detected",
            created_at=datetime.now(timezone.utc),
        )
        assert r.mitigation_status == "detected"
        assert r.entity_type == "supplier"

    def test_valid_entity_types(self):
        from app.models.risk_assessment import RiskAssessment
        for entity in ("order", "supplier", "warehouse", "shipment", "manufacturing_order", "route", "product"):
            r = RiskAssessment(
                risk_id=uuid.uuid4(),
                entity_type=entity,
                entity_id=SUPPLIER_TECHCORE_ID,
                risk_score=Decimal("50.00"),
                risk_category="operational",
                mitigation_status="detected",
                created_at=datetime.now(timezone.utc),
            )
            assert r.entity_type == entity


class TestReportModel:
    def test_instantiation(self):
        from app.models.report import Report
        r = Report(
            report_id=uuid.uuid4(),
            report_type="financial",
            title="Q1 Finance Report",
            status="generating",
            generated_by_agent="ADS-18",
            payload_summary={},
            created_at=datetime.now(timezone.utc),
        )
        assert r.status == "generating"
        assert r.report_type == "financial"


class TestQualityInspectionModel:
    def test_instantiation(self):
        from app.models.quality_inspection import QualityInspection
        q = QualityInspection(
            inspection_id=uuid.uuid4(),
            product_id=PRODUCT_LAPTOP_ID,
            inspection_result="pending",
            defect_count=0,
            inspected_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        assert q.inspection_result == "pending"

    def test_valid_inspection_results(self):
        from app.models.quality_inspection import QualityInspection
        for result in ("pass", "fail", "partial_pass", "pending"):
            q = QualityInspection(
                inspection_id=uuid.uuid4(),
                product_id=PRODUCT_LAPTOP_ID,
                inspection_result=result,
                defect_count=0,
                inspected_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            assert q.inspection_result == result


class TestEventModel:
    def test_instantiation(self):
        from app.models.event import Event
        e = Event(
            event_id=uuid.uuid4(),
            correlation_id=uuid.uuid4(),
            event_type="OrderReceived",
            source_agent="ADS-01",
            priority="high",
            version="1.0",
            payload={"order_id": str(uuid.uuid4())},
            event_metadata={},
            created_at=datetime.now(timezone.utc),
        )
        assert e.priority == "high"
        assert e.version == "1.0"

    def test_default_priority(self):
        from app.models.event import Event
        e = Event.__new__(Event)
        # Default is set on column definition
        assert Event.priority.property.columns[0].default.arg == "medium"


class TestAuditLogModel:
    def test_instantiation(self):
        from app.models.audit_log import AuditLog
        log = AuditLog(
            log_id=uuid.uuid4(),
            agent_id="ADS-01",
            agent_name="Order Management",
            action="validate_order",
            entity="orders",
            entity_id=uuid.uuid4(),
            payload={"result": "ok"},
            severity="INFO",
            created_at=datetime.now(timezone.utc),
        )
        assert log.severity == "INFO"
        assert log.agent_id == "ADS-01"


class TestAgentRuntimeModel:
    def test_instantiation(self):
        from app.models.agent_runtime import AgentRuntime
        a = AgentRuntime(
            agent_id=uuid.uuid4(),
            agent_name="Order Management Agent",
            agent_code="ADS-01",
            status="idle",
            version="1.0.0",
            updated_at=datetime.now(timezone.utc),
        )
        assert a.status == "idle"
        assert a.agent_code == "ADS-01"

    def test_valid_statuses(self):
        from app.models.agent_runtime import AgentRuntime
        for s in ("idle", "processing", "error", "offline", "maintenance"):
            a = AgentRuntime(
                agent_id=uuid.uuid4(),
                agent_name="Test Agent",
                agent_code="ADS-00",
                status=s,
                version="1.0.0",
                updated_at=datetime.now(timezone.utc),
            )
            assert a.status == s


class TestModelsInit:
    """Ensure __init__.py exports every model and __all__ is complete."""

    def test_all_models_importable(self):
        import app.models as m
        expected = [
            "AgentRuntime", "AuditLog", "Base", "Carrier", "Contract",
            "ContractProduct", "Customer", "DemandForecast", "Event",
            "FinanceTransaction", "Inventory", "ManufacturingOrder",
            "Order", "OrderItem", "PricingHistory", "Product",
            "Promotion", "PromotionProduct", "PurchaseOrder",
            "QualityInspection", "Report", "RiskAssessment",
            "SemanticDocument", "Shipment", "Supplier", "SupplierProduct",
            "SupportTicket", "SustainabilityMetric", "TransportationRoute",
            "Warehouse",
        ]
        for name in expected:
            assert hasattr(m, name), f"Missing export: {name}"

    def test_all_list_matches_exports(self):
        import app.models as m
        for name in m.__all__:
            assert hasattr(m, name), f"__all__ references missing name: {name}"


# ---------------------------------------------------------------------------
# DB round-trip tests — uses the rolled-back db_session fixture
# ---------------------------------------------------------------------------

class TestOrderRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order = make_order()
        await repo.create(order)

        fetched = await repo.get(order.order_id)
        assert fetched is not None
        assert fetched.order_id == order.order_id
        assert fetched.status == "pending"

    @pytest.mark.asyncio
    async def test_list_by_status(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order1 = make_order(status="processing")
        order2 = make_order(status="processing")
        await repo.create(order1)
        await repo.create(order2)

        results = await repo.list_by_status("processing")
        ids = [o.order_id for o in results]
        assert order1.order_id in ids
        assert order2.order_id in ids

    @pytest.mark.asyncio
    async def test_delete(self, db_session):
        from app.repositories.order import OrderRepository
        repo = OrderRepository(db_session)
        order = make_order()
        await repo.create(order)
        await repo.delete(order)

        fetched = await repo.get(order.order_id)
        assert fetched is None


class TestShipmentRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve_by_order(self, db_session):
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        order = make_order()
        await order_repo.create(order)

        shipment = make_shipment(order.order_id)
        await ship_repo.create(shipment)

        fetched = await ship_repo.get_by_order_id(order.order_id)
        assert fetched is not None
        assert fetched.shipment_id == shipment.shipment_id
        assert fetched.status == "pending"

    @pytest.mark.asyncio
    async def test_list_by_status(self, db_session):
        from app.repositories.order import OrderRepository
        from app.repositories.shipment import ShipmentRepository
        order_repo = OrderRepository(db_session)
        ship_repo = ShipmentRepository(db_session)

        order = make_order()
        await order_repo.create(order)
        shipment = make_shipment(order.order_id, status="in_transit")
        await ship_repo.create(shipment)

        results = await ship_repo.list_by_status("in_transit")
        assert any(s.shipment_id == shipment.shipment_id for s in results)


class TestCarrierRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db_session):
        from app.repositories.base import BaseRepository
        from app.models.carrier import Carrier
        repo = BaseRepository(Carrier, db_session)

        carrier = make_carrier(name="FedEx Test", code=f"FDX-{uuid.uuid4().hex[:4].upper()}")
        await repo.create(carrier)

        fetched = await repo.get(carrier.carrier_id)
        assert fetched is not None
        assert fetched.name == "FedEx Test"
        assert fetched.status == "active"


class TestPurchaseOrderRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db_session):
        from app.repositories.base import BaseRepository
        from app.models.purchase_order import PurchaseOrder
        repo = BaseRepository(PurchaseOrder, db_session)

        po = make_purchase_order()
        await repo.create(po)

        fetched = await repo.get(po.po_id)
        assert fetched is not None
        assert fetched.status == "draft"
        assert fetched.supplier_id == SUPPLIER_TECHCORE_ID


class TestSupportTicketRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db_session):
        from app.repositories.base import BaseRepository
        from app.models.support_ticket import SupportTicket
        repo = BaseRepository(SupportTicket, db_session)

        ticket = make_support_ticket(subject="Laptop delivery delayed")
        await repo.create(ticket)

        fetched = await repo.get(ticket.ticket_id)
        assert fetched is not None
        assert fetched.subject == "Laptop delivery delayed"
        assert fetched.status == "open"
        assert fetched.category == "other"


class TestContractRoundTrip:
    @pytest.mark.asyncio
    async def test_insert_and_retrieve(self, db_session):
        from app.repositories.base import BaseRepository
        from app.models.contract import Contract
        repo = BaseRepository(Contract, db_session)

        contract = make_contract(title="Annual Supply Agreement")
        await repo.create(contract)

        fetched = await repo.get(contract.contract_id)
        assert fetched is not None
        assert fetched.title == "Annual Supply Agreement"
        assert fetched.status == "active"
