"""
Tests for the Spatial Digital Twin Network Topology API.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_get_network_topology_endpoint():
    """Verify that /api/v1/analytics/network returns valid nodes, lanes, and active shipments."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/analytics/network")
        assert res.status_code == 200
        data = res.json()

        assert "summary" in data
        assert "nodes" in data
        assert "lanes" in data
        assert "active_shipments" in data

        # Check nodes
        nodes = data["nodes"]
        assert len(nodes) >= 10
        node_types = {n["type"] for n in nodes}
        assert "supplier" in node_types
        assert "warehouse" in node_types
        assert "plant" in node_types
        assert "market" in node_types

        # Check lanes
        lanes = data["lanes"]
        assert len(lanes) >= 8
        lane_modes = {l["mode"] for l in lanes}
        assert "air" in lane_modes
        assert "road" in lane_modes
        assert "sea" in lane_modes

        # Check active shipments
        shipments = data["active_shipments"]
        assert len(shipments) >= 1
        for s in shipments:
            assert "from_node" in s
            assert "to_node" in s
            assert "progress_pct" in s
            assert 0 <= s["progress_pct"] <= 100
