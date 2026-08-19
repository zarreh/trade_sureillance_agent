# False positives

!!! info "In one paragraph, for a non-engineer"
    The number that matters most to whether anyone would actually use this is
    how often it cries wolf on a clean trade — that's tracked explicitly here,
    not folded into a single accuracy number that could hide it.

Per [Evaluation](evaluation.md), the Layer 1 canonical run (n=10, oracle-scored)
currently shows a **0% false-positive rate on `clear` labels** — no clean
trade in the canonical set was flagged or escalated. At n=10 this demonstrates
the mechanism works, not a production false-positive rate; that number can
only be published from Layer 2's stratified, hand-labelled set (150–300
cases) against pinned model versions, which does not exist yet (see
[Evaluation](evaluation.md) § Layer 2).

**The alert-fatigue chart (precision/recall vs. alert volume) is not
published for the same reason.** It needs a labelled set large and varied
enough to sweep a confidence threshold meaningfully — with 10 canonical
cases, that curve would have three or four points and imply a precision this
app exists to argue should never be published without an *n* beside it. This
page will carry the real curve once Layer 2 is populated.
