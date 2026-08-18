"""Resolves the synthetic firm-policy limits applicable to an insider's role.

Renamed from the source notebook's `get_insider_authorization` (docs/PLAN.md
§3.4): relationship and title *select an applicable limit*. They do not
establish that a trade was authorised or pre-cleared.
"""

from __future__ import annotations

import json

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from surveillance.store.policy_store import PolicyStore


class GetApplicableRoleLimitsArgs(BaseModel):
    relationship: str = Field(
        description="Insider relationship from the filing, e.g. 'Officer', "
        "'Director', or a comma-separated combination"
    )
    title: str | None = Field(
        default=None, description="Insider job title, if known, e.g. 'Chief Financial Officer'"
    )


def build_get_applicable_role_limits_tool(policy_store: PolicyStore) -> StructuredTool:
    def get_applicable_role_limits(relationship: str, title: str | None = None) -> str:
        """Retrieve the synthetic firm-policy trading limits applicable to an
        insider's relationship and title.

        This selects an *applicable* limit from a seeded policy table — it
        does not establish that any specific trade was authorised or
        pre-cleared.

        Args:
            relationship: Insider relationship, e.g. 'Officer' or 'Director'.
            title: Insider job title, if known.

        Returns:
            JSON with the applicable single-trade and rolling 90-day limits.
        """
        limit = policy_store.get_role_limit(relationship, title)
        return json.dumps(
            {
                "relationship": limit.relationship,
                "authorization_level": limit.authorization_level,
                "single_trade_limit": limit.single_trade_limit,
                "rolling_90d_limit": limit.rolling_90d_limit,
                "blackout_restrictions": limit.blackout_restrictions,
                "currency": "USD",
            },
            indent=2,
        )

    return StructuredTool.from_function(
        func=get_applicable_role_limits,
        name="get_applicable_role_limits",
        args_schema=GetApplicableRoleLimitsArgs,
    )
