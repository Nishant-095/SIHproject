from __future__ import annotations

import uuid

from sqlalchemy import Boolean, CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import CreatedAtMixin


class Route(CreatedAtMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (
        CheckConstraint("origin_iata <> destination_iata", name="ck_routes_distinct_airports"),
        UniqueConstraint("origin_iata", "destination_iata", name="uq_routes_direction"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    origin_iata: Mapped[str] = mapped_column(String(3))
    destination_iata: Mapped[str] = mapped_column(String(3))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    selection_basis: Mapped[str] = mapped_column(Text)
