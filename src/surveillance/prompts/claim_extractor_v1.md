You are decomposing a compliance investigation's finding text into discrete,
checkable factual claims.

For every distinct factual assertion in the finding text (not opinions or
recommendations — assertions about what happened, what a rule requires, or
what a value was), produce one claim:
- id: a short stable identifier ("c1", "c2", ...).
- text: the exact claim, one sentence.
- cited_tool_call_ids: the tool_call_id(s) from the list below whose result
  you believe supports this claim. Only cite ids from the provided list —
  never invent one.

Do not merge unrelated facts into one claim, and do not split a single fact
into several claims. Every sentence of the finding text that asserts a fact
should map to at least one claim.
