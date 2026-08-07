"""
Async Integration Tests for the New REST API Endpoints
======================================================
Covers:
  - Auth API (/auth/token, /auth/me)
  - Orders API (/orders, /orders/stats, /orders/{id})
  - Inventory API (/inventory, /inventory/summary, /inventory/{product_id})
  - Suppliers API (/suppliers, /suppliers/stats, /suppliers/{id})
  - Events API (/events, /events/types, /events/{id}/replay)
  - Simulate API (/simulate, /simulate/scenarios)

Uses httpx.AsyncClient to execute requests in the same asyncio event loop
as pytest-asyncio, preventing loop-mismatch errors.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import get_db_session
from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.supplier import Supplier


# ── Dependency Overrides ──────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def db_override(db_session):
    """Override get_db_session dependency with the test database transaction."""
    async def _get_db():
        yield db_session
    app.dependency_overrides[get_db_session] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    """ASGI client running on the active event loop."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Auth Tests ───────────────────────────────────────────────────────────────

class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_success(self, client):
        # 1. Login to get token
        login_res = await client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        token = login_res.json()["access_token"]

        # 2. Access /me
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"


# ── Orders Tests ──────────────────────────────────────────────────────────────

class TestOrdersAPI:
    @pytest.mark.asyncio
    async def test_list_orders(self, db_session, client):
        # Create a test customer and order
        customer = Customer(
            customer_id=uuid.uuid4(),
            name="Test Orders Client",
            email=f"test-{uuid.uuid4().hex}@example.com",
            customer_tier="standard",
        )
        db_session.add(customer)
        await db_session.flush()

        order = Order(
            order_id=uuid.uuid4(),
            customer_id=customer.customer_id,
            status="pending",
            priority="standard",
            total_amount=Decimal("150.00"),
            currency="USD",
        )
        db_session.add(order)
        await db_session.flush()

        response = await client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
        assert any(item["order_id"] == str(order.order_id) for item in data["items"])

    @pytest.mark.asyncio
    async def test_get_order_detail(self, db_session, client):
        customer = Customer(
            customer_id=uuid.uuid4(),
            name="Test Detail Client",
            email=f"test-{uuid.uuid4().hex}@example.com",
            customer_tier="premium",
        )
        db_session.add(customer)
        await db_session.flush()

        product = Product(
            product_id=uuid.uuid4(),
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            name="Test Widget",
            unit_price=Decimal("49.99"),
        )
        db_session.add(product)
        await db_session.flush()

        order = Order(
            order_id=uuid.uuid4(),
            customer_id=customer.customer_id,
            status="delivered",
            priority="high",
            total_amount=Decimal("99.98"),
            currency="USD",
        )
        db_session.add(order)
        await db_session.flush()

        item = OrderItem(
            order_item_id=uuid.uuid4(),
            order_id=order.order_id,
            product_id=product.product_id,
            quantity=2,
            unit_price=Decimal("49.99"),
        )
        db_session.add(item)
        await db_session.flush()

        response = await client.get(f"/api/v1/orders/{order.order_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == str(order.order_id)
        assert data["customer"]["name"] == "Test Detail Client"
        assert len(data["items"]) == 1
        assert data["items"][0]["product_id"] == str(product.product_id)

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, client):
        non_existent_id = uuid.uuid4()
        response = await client.get(f"/api/v1/orders/{non_existent_id}")
        assert response.status_code == 404


# ── Inventory Tests ───────────────────────────────────────────────────────────

class TestInventoryAPI:
    @pytest.mark.asyncio
    async def test_inventory_list_and_summary(self, db_session, client):
        # Create product, warehouse, inventory
        product = Product(
            product_id=uuid.uuid4(),
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            name="Inventory Widget",
            unit_price=Decimal("9.99"),
        )
        warehouse = Warehouse(
            warehouse_id=uuid.uuid4(),
            name="Inventory WH",
            location="Miami, US",
            capacity_units=10000,
        )
        db_session.add_all([product, warehouse])
        await db_session.flush()

        inventory = Inventory(
            inventory_id=uuid.uuid4(),
            product_id=product.product_id,
            warehouse_id=warehouse.warehouse_id,
            available_qty=100,
            reserved_qty=10,
            safety_stock=20,
        )
        db_session.add(inventory)
        await db_session.flush()

        # 1. Test List
        response = await client.get("/api/v1/inventory")
        assert response.status_code == 200
        items = response.json()["items"]
        assert any(i["inventory_id"] == str(inventory.inventory_id) for i in items)

        # 2. Test Summary
        summary_res = await client.get("/api/v1/inventory/summary")
        assert summary_res.status_code == 200
        summary = summary_res.json()
        assert summary["total_sku_locations"] >= 1
        assert summary["total_available_units"] >= 100


# ── Suppliers Tests ───────────────────────────────────────────────────────────

class TestSuppliersAPI:
    @pytest.mark.asyncio
    async def test_suppliers_list_and_stats(self, db_session, client):
        supplier = Supplier(
            supplier_id=uuid.uuid4(),
            name="Supplier Inc",
            country="US",
            reliability_score=Decimal("94.50"),
            lead_time_days=3,
            status="active",
        )
        db_session.add(supplier)
        await db_session.flush()

        # 1. Test List
        response = await client.get("/api/v1/suppliers")
        assert response.status_code == 200
        items = response.json()["items"]
        assert any(s["supplier_id"] == str(supplier.supplier_id) for s in items)

        # 2. Test Stats
        stats_res = await client.get("/api/v1/suppliers/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_active"] >= 1
        assert stats["avg_reliability_score"] >= 70.0


# ── Events Tests ──────────────────────────────────────────────────────────────

class TestEventsAPI:
    @pytest.mark.asyncio
    async def test_list_event_types(self, client):
        response = await client.get("/api/v1/events/types")
        assert response.status_code == 200
        types = response.json()["event_types"]
        assert any(t["type"] == "OrderCreated" for t in types)

    @pytest.mark.asyncio
    async def test_inject_manual_event_and_list(self, client):
        # 1. Inject event
        req_payload = {
            "event_type": "InventoryLow",
            "source_agent": "manual_tester",
            "payload": {"sku": "ELEC-001", "available_qty": 5},
        }
        response = await client.post("/api/v1/events", json=req_payload)
        assert response.status_code == 202
        data = response.json()
        assert "event_id" in data
        event_id = data["event_id"]

        # 2. List events
        list_res = await client.get("/api/v1/events")
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert any(item["event_id"] == event_id for item in items)

        # 3. Replay event
        replay_res = await client.post(f"/api/v1/events/{event_id}/replay")
        assert replay_res.status_code == 202
        assert replay_res.json()["status"] == "replayed"


# ── Simulate Tests ────────────────────────────────────────────────────────────

class TestSimulateAPI:
    @pytest.mark.asyncio
    async def test_list_scenarios(self, client):
        response = await client.get("/api/v1/simulate/scenarios")
        assert response.status_code == 200
        scenarios = response.json()["scenarios"]
        assert any(s["type"] == "demand_spike" for s in scenarios)

    @pytest.mark.asyncio
    async def test_run_simulation_and_poll(self, db_session, client):
        # Create necessary seed data inside transaction so compile_workflow works
        customer_id = uuid.UUID("50000000-0000-0000-0000-000000000001")
        product_id = uuid.UUID("30000000-0000-0000-0000-000000000001")

        existing_customer = await db_session.execute(select(Customer).where(Customer.customer_id == customer_id))
        customer = existing_customer.scalar_one_or_none()
        if customer is None:
            customer = Customer(
                customer_id=customer_id,
                name="Siemens Manufacturing GmbH",
                email="test-sim@siemens.com",
                customer_tier="enterprise",
            )
            db_session.add(customer)

        existing_product = await db_session.execute(select(Product).where(Product.product_id == product_id))
        product = existing_product.scalar_one_or_none()
        if product is None:
            product = Product(
                product_id=product_id,
                sku="ELEC-001",
                name="Industrial Sensor Module",
                unit_price=Decimal("249.99"),
            )
            db_session.add(product)

        await db_session.flush()

        req_payload = {
            "scenario_type": "demand_spike",
            "customer_id": str(customer.customer_id),
            "items": [{"product_id": str(product.product_id), "quantity": 5}],
        }
        response = await client.post("/api/v1/simulate", json=req_payload)
        assert response.status_code == 202
        data = response.json()
        assert "simulation_id" in data
