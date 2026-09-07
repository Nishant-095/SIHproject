from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.enums import SourceReviewStatus, SourceType
from app.models.base import CreatedAtMixin, utc_now
from app.models.types import enum_type


class Source(CreatedAtMixin, Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[SourceType] = mapped_column(enum_type(SourceType, "source_type"))
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    collection_method: Mapped[str] = mapped_column(String(40))
    review_status: Mapped[SourceReviewStatus] = mapped_column(
        enum_type(SourceReviewStatus, "source_review_status"),
        default=SourceReviewStatus.PENDING_REVIEW,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1)
    parser_version: Mapped[str] = mapped_column(String(40), default="unversioned")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
