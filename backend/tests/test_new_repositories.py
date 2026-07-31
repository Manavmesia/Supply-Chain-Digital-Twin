"""
Tests for the 8 new domain repositories (US-60).

Covers every public query method added beyond BaseRepository.
Each test runs inside a rolled-back transaction via the db_session fixture.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
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
# Helpers
# ---------------------------------------------------------------------------

def make_pricing_history(product_id: uuid.UUID = PRODUCT_LAPTOP_ID, **kwargs):
    from app.models.pricing_history import PricingHistory
    return PricingHistory(
        price_id=uuid.uuid4(),
        product_id=product_id,
        previous_price=kwargs.get("previous_price", Decimal("999.00")),
        recommended_price=kwargs.get("recommended_price", Decimal("1099.00")),
        approved_price=kwargs.get("approved_price", None),
        trigger_type=kwargs.get("trigger_type", "manual"),
        created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
    )


def make_promotion(**kwargs):
    from app.models.promotion import Promotion
    now = datetime.now(timezone.utc)
    return Promotion(
        promotion_id=uuid.uuid4(),
        name=kwargs.get("name", "Test Promo"),
        status=kwargs.get("status", "active"),
        starts_at=kwargs.get("starts_at", now - timedelta(hours=1)),
        ends_at=kwargs.get("ends_at", now + timedelta(days=7)),
        discount_percent=kwargs.get("discount_percent", Decimal("10.00")),
        created_at=now,
        updated_at=now,
    )


def make_promotion_product(promotion_id: uuid.UUID, product_id: uuid.UUID = PRODUCT_LAPTOP_ID):
    from app.models.promotion_product import PromotionProduct
    return PromotionProduct(promotion_id=promotion_id, product_id=product_id)


def make_report(**kwargs):
    from app.models.report import Report
    return Report(
        report_id=uuid.uuid4(),
        report_type=kwargs.get("report_type", "financial"),
        title=kwargs.get("title", "Test Report"),
        status=kwargs.get("status", "ready"),
        workflow_id=kwargs.get("workflow_id", None),
        generated_by_agent="ADS-18",
        payload_summary={},
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# PurchaseOrderRepository
# ---------------------------------------------------------------------------

class TestPurchaseOrderRepository:
    @pytest.mark.asyncio
    async def test_get_by_supplier_returns_matching(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        po = make_purchase_order(supplier_id=SUPPLIER_TECHCORE_ID)
        await repo.create(po)

        results = await repo.get_by_supplier(SUPPLIER_TECHCORE_ID)
        assert any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_supplier_excludes_other_suppliers(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        other_supplier = uuid.uuid4()
        po = make_purchase_order(supplier_id=SUPPLIER_TECHCORE_ID)
        await repo.create(po)

        results = await repo.get_by_supplier(other_supplier)
        assert not any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_supplier_empty_for_unknown(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)
        results = await repo.get_by_supplier(uuid.uuid4())
        assert results == [] or list(results) == []

    @pytest.mark.asyncio
    async def test_get_by_status_returns_matching(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        po = make_purchase_order(status="approved")
        await repo.create(po)

        results = await repo.get_by_status("approved")
        assert any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_status_excludes_other_statuses(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        po = make_purchase_order(status="cancelled")
        await repo.create(po)

        results = await repo.get_by_status("draft")
        assert not any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_pending_delivery_includes_overdue(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        yesterday = date.today() - timedelta(days=1)
        po = make_purchase_order(status="sent")
        po.requested_delivery = yesterday
        await repo.create(po)

        results = await repo.get_pending_delivery()
        assert any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_pending_delivery_excludes_received(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        yesterday = date.today() - timedelta(days=1)
        po = make_purchase_order(status="received")
        po.requested_delivery = yesterday
        await repo.create(po)

        results = await repo.get_pending_delivery()
        assert not any(p.po_id == po.po_id for p in results)

    @pytest.mark.asyncio
    async def test_get_pending_delivery_excludes_future_deliveries(self, db_session):
        from app.repositories.purchase_order import PurchaseOrderRepository
        repo = PurchaseOrderRepository(db_session)

        future = date.today() + timedelta(days=10)
        po = make_purchase_order(status="sent")
        po.requested_delivery = future
        await repo.create(po)

        results = await repo.get_pending_delivery()
        assert not any(p.po_id == po.po_id for p in results)


# ---------------------------------------------------------------------------
# SupportTicketRepository
# ---------------------------------------------------------------------------

class TestSupportTicketRepository:
    @pytest.mark.asyncio
    async def test_get_open_by_customer_returns_open(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="open")
        await repo.create(ticket)

        results = await repo.get_open_by_customer(CUSTOMER_ID)
        assert any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_open_by_customer_excludes_resolved(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="resolved")
        await repo.create(ticket)

        results = await repo.get_open_by_customer(CUSTOMER_ID)
        assert not any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_open_by_customer_excludes_closed(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="closed")
        await repo.create(ticket)

        results = await repo.get_open_by_customer(CUSTOMER_ID)
        assert not any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_open_by_customer_includes_escalated(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="escalated")
        await repo.create(ticket)

        results = await repo.get_open_by_customer(CUSTOMER_ID)
        assert any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_sla_breaching_returns_overdue_open_tickets(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="open")
        ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await repo.create(ticket)

        results = await repo.get_sla_breaching()
        assert any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_sla_breaching_excludes_future_deadline(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="open")
        ticket.sla_deadline = datetime.now(timezone.utc) + timedelta(hours=5)
        await repo.create(ticket)

        results = await repo.get_sla_breaching()
        assert not any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_get_sla_breaching_excludes_escalated(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="escalated")
        ticket.sla_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await repo.create(ticket)

        results = await repo.get_sla_breaching()
        assert not any(t.ticket_id == ticket.ticket_id for t in results)

    @pytest.mark.asyncio
    async def test_escalate_sets_status_and_timestamp(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)

        ticket = make_support_ticket(status="open")
        await repo.create(ticket)

        updated = await repo.escalate(ticket.ticket_id)
        assert updated is not None
        assert updated.status == "escalated"
        assert updated.escalated_at is not None

    @pytest.mark.asyncio
    async def test_escalate_nonexistent_returns_none(self, db_session):
        from app.repositories.support_ticket import SupportTicketRepository
        repo = SupportTicketRepository(db_session)
        result = await repo.escalate(uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# PricingHistoryRepository
# ---------------------------------------------------------------------------

class TestPricingHistoryRepository:
    @pytest.mark.asyncio
    async def test_get_latest_by_product_returns_newest(self, db_session):
        from app.repositories.pricing_history import PricingHistoryRepository
        repo = PricingHistoryRepository(db_session)

        older = make_pricing_history(
            created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        newer = make_pricing_history(
            recommended_price=Decimal("1299.00"),
            created_at=datetime.now(timezone.utc),
        )
        await repo.create(older)
        await repo.create(newer)

        result = await repo.get_latest_by_product(PRODUCT_LAPTOP_ID)
        assert result is not None
        assert result.price_id == newer.price_id

    @pytest.mark.asyncio
    async def test_get_latest_by_product_returns_none_for_unknown(self, db_session):
        from app.repositories.pricing_history import PricingHistoryRepository
        repo = PricingHistoryRepository(db_session)
        result = await repo.get_latest_by_product(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_pending_approval_returns_unapproved(self, db_session):
        from app.repositories.pricing_history import PricingHistoryRepository
        repo = PricingHistoryRepository(db_session)

        pending = make_pricing_history(approved_price=None)
        await repo.create(pending)

        results = await repo.get_pending_approval()
        assert any(p.price_id == pending.price_id for p in results)

    @pytest.mark.asyncio
    async def test_get_pending_approval_excludes_approved(self, db_session):
        from app.repositories.pricing_history import PricingHistoryRepository
        repo = PricingHistoryRepository(db_session)

        approved = make_pricing_history(approved_price=Decimal("1050.00"))
        await repo.create(approved)

        results = await repo.get_pending_approval()
        assert not any(p.price_id == approved.price_id for p in results)


# ---------------------------------------------------------------------------
# ContractRepository
# ---------------------------------------------------------------------------

class TestContractRepository:
    @pytest.mark.asyncio
    async def test_get_expiring_soon_returns_near_expiry(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(
            status="active",
            end_date=date.today() + timedelta(days=15),
        )
        await repo.create(contract)

        results = await repo.get_expiring_soon(days=30)
        assert any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_expiring_soon_excludes_far_future(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(
            status="active",
            end_date=date.today() + timedelta(days=90),
        )
        await repo.create(contract)

        results = await repo.get_expiring_soon(days=30)
        assert not any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_expiring_soon_excludes_already_expired(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(
            status="expired",
            end_date=date.today() - timedelta(days=5),
        )
        await repo.create(contract)

        results = await repo.get_expiring_soon(days=30)
        assert not any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_expiring_soon_includes_expiring_soon_status(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(
            status="expiring_soon",
            end_date=date.today() + timedelta(days=5),
        )
        await repo.create(contract)

        results = await repo.get_expiring_soon(days=30)
        assert any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_active_by_supplier_returns_active(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(supplier_id=SUPPLIER_TECHCORE_ID, status="active")
        await repo.create(contract)

        results = await repo.get_active_by_supplier(SUPPLIER_TECHCORE_ID)
        assert any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_active_by_supplier_excludes_terminated(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)

        contract = make_contract(supplier_id=SUPPLIER_TECHCORE_ID, status="terminated")
        await repo.create(contract)

        results = await repo.get_active_by_supplier(SUPPLIER_TECHCORE_ID)
        assert not any(c.contract_id == contract.contract_id for c in results)

    @pytest.mark.asyncio
    async def test_get_active_by_supplier_empty_for_unknown(self, db_session):
        from app.repositories.contract import ContractRepository
        repo = ContractRepository(db_session)
        results = await repo.get_active_by_supplier(uuid.uuid4())
        assert list(results) == []


# ---------------------------------------------------------------------------
# CarrierRepository
# ---------------------------------------------------------------------------

class TestCarrierRepository:
    @pytest.mark.asyncio
    async def test_get_available_returns_matching_mode(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"AIR-{uuid.uuid4().hex[:4].upper()}",
            freight_modes=["air"],
            status="active",
        )
        await repo.create(carrier)

        results = await repo.get_available("air")
        assert any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_available_excludes_inactive(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"INA-{uuid.uuid4().hex[:4].upper()}",
            freight_modes=["sea"],
            status="inactive",
        )
        await repo.create(carrier)

        results = await repo.get_available("sea")
        assert not any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_available_excludes_blacklisted(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"BLK-{uuid.uuid4().hex[:4].upper()}",
            freight_modes=["road"],
            status="blacklisted",
        )
        await repo.create(carrier)

        results = await repo.get_available("road")
        assert not any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_available_excludes_wrong_mode(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"RD-{uuid.uuid4().hex[:4].upper()}",
            freight_modes=["road"],
            status="active",
        )
        await repo.create(carrier)

        results = await repo.get_available("air")
        assert not any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_by_reliability_threshold_returns_above_min(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"REL-{uuid.uuid4().hex[:4].upper()}",
            reliability_score=Decimal("95.00"),
            status="active",
        )
        await repo.create(carrier)

        results = await repo.get_by_reliability_threshold(min_score=90)
        assert any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_by_reliability_threshold_excludes_below_min(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"LOW-{uuid.uuid4().hex[:4].upper()}",
            reliability_score=Decimal("60.00"),
            status="active",
        )
        await repo.create(carrier)

        results = await repo.get_by_reliability_threshold(min_score=70)
        assert not any(c.carrier_id == carrier.carrier_id for c in results)

    @pytest.mark.asyncio
    async def test_get_by_reliability_threshold_exact_boundary(self, db_session):
        from app.repositories.carrier import CarrierRepository
        repo = CarrierRepository(db_session)

        carrier = make_carrier(
            code=f"BND-{uuid.uuid4().hex[:4].upper()}",
            reliability_score=Decimal("70.00"),
            status="active",
        )
        await repo.create(carrier)

        # Exactly at threshold — should be included
        results = await repo.get_by_reliability_threshold(min_score=70)
        assert any(c.carrier_id == carrier.carrier_id for c in results)


# ---------------------------------------------------------------------------
# TransportationRouteRepository
# ---------------------------------------------------------------------------

class TestTransportationRouteRepository:
    @pytest.mark.asyncio
    async def test_find_routes_returns_matching(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        from app.repositories.carrier import CarrierRepository
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier(code=f"C-{uuid.uuid4().hex[:6].upper()}")
        await carrier_repo.create(carrier)

        route = make_transportation_route(
            carrier.carrier_id,
            origin_location="Newark, US",
            destination="Los Angeles, US",
            freight_mode="road",
        )
        await route_repo.create(route)

        results = await route_repo.find_routes("Newark, US", "Los Angeles, US")
        assert any(r.route_id == route.route_id for r in results)

    @pytest.mark.asyncio
    async def test_find_routes_filters_by_mode(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        from app.repositories.carrier import CarrierRepository
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier(code=f"C-{uuid.uuid4().hex[:6].upper()}", freight_modes=["road", "air"])
        await carrier_repo.create(carrier)

        road_route = make_transportation_route(carrier.carrier_id, freight_mode="road")
        air_route = make_transportation_route(carrier.carrier_id, freight_mode="air")
        await route_repo.create(road_route)
        await route_repo.create(air_route)

        results = await route_repo.find_routes(
            road_route.origin_location, road_route.destination, mode="air"
        )
        ids = {r.route_id for r in results}
        assert air_route.route_id in ids
        assert road_route.route_id not in ids

    @pytest.mark.asyncio
    async def test_find_routes_excludes_inactive(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        from app.repositories.carrier import CarrierRepository
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier(code=f"C-{uuid.uuid4().hex[:6].upper()}")
        await carrier_repo.create(carrier)

        route = make_transportation_route(carrier.carrier_id, is_active=False)
        await route_repo.create(route)

        results = await route_repo.find_routes(
            route.origin_location, route.destination
        )
        assert not any(r.route_id == route.route_id for r in results)

    @pytest.mark.asyncio
    async def test_fastest_route_returns_lowest_transit_days(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        from app.repositories.carrier import CarrierRepository
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier(code=f"C-{uuid.uuid4().hex[:6].upper()}", freight_modes=["air", "road"])
        await carrier_repo.create(carrier)

        fast = make_transportation_route(carrier.carrier_id, transit_days=1, freight_mode="air", base_cost=Decimal("2000.00"))
        slow = make_transportation_route(carrier.carrier_id, transit_days=5, freight_mode="road", base_cost=Decimal("200.00"))
        # override destination to match
        slow.origin_location = fast.origin_location
        slow.destination = fast.destination
        await route_repo.create(fast)
        await route_repo.create(slow)

        result = await route_repo.fastest_route(fast.origin_location, fast.destination)
        assert result is not None
        assert result.route_id == fast.route_id

    @pytest.mark.asyncio
    async def test_cheapest_route_returns_lowest_base_cost(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        from app.repositories.carrier import CarrierRepository
        carrier_repo = CarrierRepository(db_session)
        route_repo = TransportationRouteRepository(db_session)

        carrier = make_carrier(code=f"C-{uuid.uuid4().hex[:6].upper()}", freight_modes=["air", "road"])
        await carrier_repo.create(carrier)

        expensive = make_transportation_route(carrier.carrier_id, transit_days=1, freight_mode="air", base_cost=Decimal("2000.00"))
        cheap = make_transportation_route(carrier.carrier_id, transit_days=5, freight_mode="road", base_cost=Decimal("200.00"))
        cheap.origin_location = expensive.origin_location
        cheap.destination = expensive.destination
        await route_repo.create(expensive)
        await route_repo.create(cheap)

        result = await route_repo.cheapest_route(expensive.origin_location, expensive.destination)
        assert result is not None
        assert result.route_id == cheap.route_id

    @pytest.mark.asyncio
    async def test_fastest_route_returns_none_when_no_routes(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        repo = TransportationRouteRepository(db_session)
        result = await repo.fastest_route("Nowhere, ZZ", "Somewhere, ZZ")
        assert result is None

    @pytest.mark.asyncio
    async def test_cheapest_route_returns_none_when_no_routes(self, db_session):
        from app.repositories.transportation_route import TransportationRouteRepository
        repo = TransportationRouteRepository(db_session)
        result = await repo.cheapest_route("Nowhere, ZZ", "Somewhere, ZZ")
        assert result is None


# ---------------------------------------------------------------------------
# PromotionRepository
# ---------------------------------------------------------------------------

class TestPromotionRepository:
    @pytest.mark.asyncio
    async def test_get_active_promotions_returns_active(self, db_session):
        from app.repositories.promotion import PromotionRepository
        repo = PromotionRepository(db_session)

        promo = make_promotion(status="active")
        await repo.create(promo)

        results = await repo.get_active_promotions()
        assert any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_active_promotions_excludes_scheduled(self, db_session):
        from app.repositories.promotion import PromotionRepository
        repo = PromotionRepository(db_session)

        promo = make_promotion(status="scheduled")
        await repo.create(promo)

        results = await repo.get_active_promotions()
        assert not any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_active_promotions_excludes_completed(self, db_session):
        from app.repositories.promotion import PromotionRepository
        repo = PromotionRepository(db_session)

        promo = make_promotion(status="completed")
        await repo.create(promo)

        results = await repo.get_active_promotions()
        assert not any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_product_returns_promotion_containing_product(self, db_session):
        from app.repositories.promotion import PromotionRepository
        from app.repositories.base import BaseRepository
        from app.models.promotion_product import PromotionProduct
        repo = PromotionRepository(db_session)
        pp_repo = BaseRepository(PromotionProduct, db_session)

        promo = make_promotion(status="active")
        await repo.create(promo)
        pp = make_promotion_product(promo.promotion_id, PRODUCT_LAPTOP_ID)
        await pp_repo.create(pp)

        results = await repo.get_by_product(PRODUCT_LAPTOP_ID)
        assert any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_product_excludes_cancelled_promotions(self, db_session):
        from app.repositories.promotion import PromotionRepository
        from app.repositories.base import BaseRepository
        from app.models.promotion_product import PromotionProduct
        repo = PromotionRepository(db_session)
        pp_repo = BaseRepository(PromotionProduct, db_session)

        promo = make_promotion(status="cancelled")
        await repo.create(promo)
        pp = make_promotion_product(promo.promotion_id, PRODUCT_LAPTOP_ID)
        await pp_repo.create(pp)

        results = await repo.get_by_product(PRODUCT_LAPTOP_ID)
        assert not any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_product_excludes_expired_promotions(self, db_session):
        from app.repositories.promotion import PromotionRepository
        from app.repositories.base import BaseRepository
        from app.models.promotion_product import PromotionProduct
        repo = PromotionRepository(db_session)
        pp_repo = BaseRepository(PromotionProduct, db_session)

        now = datetime.now(timezone.utc)
        promo = make_promotion(
            status="active",
            ends_at=now - timedelta(hours=1),
        )
        await repo.create(promo)
        pp = make_promotion_product(promo.promotion_id, PRODUCT_LAPTOP_ID)
        await pp_repo.create(pp)

        results = await repo.get_by_product(PRODUCT_LAPTOP_ID)
        assert not any(p.promotion_id == promo.promotion_id for p in results)

    @pytest.mark.asyncio
    async def test_get_by_product_empty_for_unknown_product(self, db_session):
        from app.repositories.promotion import PromotionRepository
        repo = PromotionRepository(db_session)
        results = await repo.get_by_product(uuid.uuid4())
        assert list(results) == []


# ---------------------------------------------------------------------------
# ReportRepository
# ---------------------------------------------------------------------------

class TestReportRepository:
    @pytest.mark.asyncio
    async def test_get_by_type_returns_matching(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        report = make_report(report_type="financial", status="ready")
        await repo.create(report)

        results = await repo.get_by_type("financial")
        assert any(r.report_id == report.report_id for r in results)

    @pytest.mark.asyncio
    async def test_get_by_type_excludes_other_types(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        report = make_report(report_type="risk", status="ready")
        await repo.create(report)

        results = await repo.get_by_type("financial")
        assert not any(r.report_id == report.report_id for r in results)

    @pytest.mark.asyncio
    async def test_get_by_type_excludes_archived(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        report = make_report(report_type="financial", status="archived")
        await repo.create(report)

        results = await repo.get_by_type("financial")
        assert not any(r.report_id == report.report_id for r in results)

    @pytest.mark.asyncio
    async def test_get_by_workflow_returns_matching(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        wf_id = uuid.uuid4()
        r1 = make_report(workflow_id=wf_id)
        r2 = make_report(workflow_id=wf_id)
        other = make_report(workflow_id=uuid.uuid4())
        await repo.create(r1)
        await repo.create(r2)
        await repo.create(other)

        results = await repo.get_by_workflow(wf_id)
        ids = {r.report_id for r in results}
        assert r1.report_id in ids
        assert r2.report_id in ids
        assert other.report_id not in ids

    @pytest.mark.asyncio
    async def test_get_by_workflow_empty_for_unknown(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)
        results = await repo.get_by_workflow(uuid.uuid4())
        assert list(results) == []

    @pytest.mark.asyncio
    async def test_archive_sets_status(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        report = make_report(status="ready")
        await repo.create(report)

        updated = await repo.archive(report.report_id)
        assert updated is not None
        assert updated.status == "archived"

    @pytest.mark.asyncio
    async def test_archive_removes_from_get_by_type(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)

        report = make_report(report_type="audit", status="ready")
        await repo.create(report)
        await repo.archive(report.report_id)

        results = await repo.get_by_type("audit")
        assert not any(r.report_id == report.report_id for r in results)

    @pytest.mark.asyncio
    async def test_archive_nonexistent_returns_none(self, db_session):
        from app.repositories.report import ReportRepository
        repo = ReportRepository(db_session)
        result = await repo.archive(uuid.uuid4())
        assert result is None
