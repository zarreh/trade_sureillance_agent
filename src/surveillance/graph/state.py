from typing import TypedDict


class SkeletonState(TypedDict):
    """Phase 0 walking-skeleton state — replaced by SurveillanceState in Phase 3."""

    message: str
    echoed: str
    done: bool
