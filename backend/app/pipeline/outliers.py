from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import AdvanceWindow, QualityFlag, QualityStatus
from app.models import CollectionJob, FareObservation, RawQuote

OUTLIER_METHOD_VERSION = "mad-v1"
MINIMUM_GROUP_SIZE = 5
MODIFIED_Z_THRESHOLD = Decimal("3.5")
MAD_SCALE = Decimal("0.6745")


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def flag_statistical_outliers(session: Session, run_id: uuid.UUID) -> int:
    """Flag robust route-window outliers without excluding genuine price surges."""
    rows = list(
        session.execute(
            select(FareObservation, CollectionJob)
            .join(RawQuote, FareObservation.raw_quote_id == RawQuote.id)
            .join(CollectionJob, RawQuote.collection_job_id == CollectionJob.id)
            .where(
                CollectionJob.collection_run_id == run_id,
                FareObservation.included_in_index.is_(True),
                FareObservation.total_fare.is_not(None),
            )
        )
    )
    groups: dict[tuple[uuid.UUID, AdvanceWindow], list[FareObservation]] = defaultdict(list)
    for observation, job in rows:
        groups[(job.route_id, observation.advance_window)].append(observation)

    flagged = 0
    for observations in groups.values():
        if len(observations) < MINIMUM_GROUP_SIZE:
            continue
        values = [observation.total_fare for observation in observations]
        complete_values = [value for value in values if value is not None]
        center = _median(complete_values)
        mad = _median([abs(value - center) for value in complete_values])
        for observation in observations:
            assert observation.total_fare is not None
            deviation = abs(observation.total_fare - center)
            is_outlier = (
                deviation > 0 if mad == 0 else MAD_SCALE * deviation / mad > MODIFIED_Z_THRESHOLD
            )
            if not is_outlier or QualityFlag.POSSIBLE_OUTLIER.value in observation.quality_flags:
                continue
            observation.quality_flags = [
                *observation.quality_flags,
                QualityFlag.POSSIBLE_OUTLIER.value,
            ]
            observation.quality_status = QualityStatus.ELIGIBLE_FLAGGED
            observation.quality_score = max(0, (observation.quality_score or 100) - 5)
            flagged += 1
    session.flush()
    return flagged
