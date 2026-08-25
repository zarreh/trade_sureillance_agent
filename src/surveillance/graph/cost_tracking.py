"""Per-node LLM cost accounting via a LangChain callback (docs/PLAN.md §5.5).

Implemented in `zarreh_agentkit.cost` (extracted substrate); re-exported here so
`surveillance.graph.cost_tracking` imports keep working. The price table there
covers this app's models (`gpt-4o-mini`, `gpt-4o`).
"""

from zarreh_agentkit.cost import CostTrackingHandler, estimate_cost_usd

__all__ = ["CostTrackingHandler", "estimate_cost_usd"]
