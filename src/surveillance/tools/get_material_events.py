"""Deterministic lookup against the seeded corporate-events calendar.

New in this repo (docs/PLAN.md §3.3.11): the source rule table penalises
"suspicious timing near earnings" but no tool could ever establish an earnings
date, so the model would have had to invent one. This tool is the evidence
source that reasoning was missing.
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from surveillance.store.policy_store import PolicyStore


class GetMaterialEventsArgs(BaseModel):
    issuer_cik: str = Field(description="Issuer's CIK identifier")
    on_date: str = Field(description="Date to check, in 'YYYY-MM-DD' format")


def build_get_material_events_tool(policy_store: PolicyStore) -> StructuredTool:
    def get_material_events(issuer_cik: str, on_date: str) -> str:
        """Check whether a date falls inside a seeded corporate-event blackout
        window (e.g. an earnings announcement) for an issuer.

        Args:
            issuer_cik: Issuer's CIK identifier.
            on_date: Date to check ('YYYY-MM-DD').

        Returns:
            JSON stating whether `on_date` falls inside a blackout window, and
            the event details if so.
        """
        event = policy_store.get_material_event_for_date(issuer_cik, on_date)
        if event is None:
            return json.dumps({"issuer_cik": issuer_cik, "on_date": on_date, "in_blackout": False})
        return json.dumps(
            {
                "issuer_cik": issuer_cik,
                "on_date": on_date,
                "in_blackout": True,
                "event_type": event.event_type,
                "event_date": event.event_date,
                "blackout_start": event.blackout_start,
                "blackout_end": event.blackout_end,
            },
            indent=2,
        )

    return StructuredTool.from_function(
        func=get_material_events,
        name="get_material_events",
        args_schema=GetMaterialEventsArgs,
    )
