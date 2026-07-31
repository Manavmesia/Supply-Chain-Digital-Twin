"""Repository for TransportationRoute domain queries."""

from collections.abc import Sequence

from app.models.transportation_route import TransportationRoute
from app.repositories.base import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class TransportationRouteRepository(BaseRepository[TransportationRoute]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TransportationRoute, session)

    async def find_routes(
        self,
        origin: str,
        destination: str,
        mode: str | None = None,
    ) -> Sequence[TransportationRoute]:
        """Return all active routes between *origin* and *destination*.

        Optionally filter by *mode* (air / sea / road / rail / multimodal).
        Results are ordered by transit_days ascending so that callers can
        pick the fastest route as the first element.
        """
        conditions = [
            TransportationRoute.origin_location == origin,
            TransportationRoute.destination == destination,
            TransportationRoute.is_active.is_(True),
        ]
        if mode is not None:
            conditions.append(TransportationRoute.freight_mode == mode)

        query = (
            select(TransportationRoute)
            .where(*conditions)
            .order_by(TransportationRoute.transit_days.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def cheapest_route(
        self, origin: str, destination: str, mode: str | None = None
    ) -> TransportationRoute | None:
        """Return the single active route with the lowest base_cost for the
        given origin/destination pair.

        Used by the Transportation Agent when the order is cost-critical.
        """
        routes = await self.find_routes(origin, destination, mode)
        if not routes:
            return None
        return min(routes, key=lambda r: r.base_cost)

    async def fastest_route(
        self, origin: str, destination: str, mode: str | None = None
    ) -> TransportationRoute | None:
        """Return the single active route with the fewest transit_days for the
        given origin/destination pair.

        Used by the Transportation Agent when the order is time-critical.
        ``find_routes`` already orders by transit_days ASC, so we just
        take the first result.
        """
        routes = await self.find_routes(origin, destination, mode)
        if not routes:
            return None
        return routes[0]
