from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_admin_token(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    if x_admin_token != get_settings().admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid admin token is required",
        )
