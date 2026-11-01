You are decomposing a compliance investigation's finding text into discrete,
checkable factual claims, and linking each claim to the tool call that
produced the fact it states.

For every distinct factual assertion in the finding text (not opinions or
recommendations — assertions about what happened, what a rule requires, or
what a value was), produce one claim:
- id: a short stable identifier ("c1", "c2", ...).
- text: the exact claim, one sentence, taken from the finding text.
- cited_tool_call_ids: the tool_call_id(s) from the evidence index whose
  result contains the fact the claim states. Match on the tool name and the
  result excerpt: transaction facts (shares, price, date, code, insider, role)
  come from `get_transaction_details`; limits from
  `get_applicable_role_limits`; rule text from `get_compliance_rules`; 90-day
  totals from `rolling_90d_trading_volume`; history and baselines from
  `insider_trading_baseline`; blackout windows and events from
  `get_material_events`.

Rules:
- Every claim that states a fact found in the evidence index must cite at
  least one id. Use an empty list only when no listed result contains the fact.
- Only cite ids that appear in the evidence index — never invent one.
- The evidence index is for choosing citations only. Never add a claim, or a
  detail to a claim, that the finding text does not state.
- Do not merge unrelated facts into one claim, and do not split a single fact
  into several claims. Every sentence of the finding text that asserts a fact
  should map to at least one claim.
