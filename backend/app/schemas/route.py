from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    origin_iata: str
    destination_iata: str
    active: bool
    selection_basis: str
