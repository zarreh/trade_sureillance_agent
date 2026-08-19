# Why the grounding check has to happen before publication, not after (draft — staged for `/writing`)

This is drafted content for the per-app post described in
`PORTFOLIO_PLAN_V3.md` §14 (`/writing`). It lives here, excluded from this
repo's own published docs site, because the shared portfolio site does not
exist yet in this workspace.

---

Most "grounded" AI demos I've seen check the wrong artifact. They generate an
answer, then run a second model over the *conversation* to see if the claims
in it look supported, and if that check passes, they hand the user... a
brand new answer, written by a third call. Nothing connects the thing that
passed the check to the thing the user actually reads.

Building the grounding loop for this insider-trading investigation agent
made that failure mode concrete enough that I ended up writing an
architecture decision record about it (D-A2-1). Here's the shape of the
mistake, and why the fix is almost embarrassingly simple once you see it.

## The mistake

An earlier version of this pipeline looked like:

```
investigate → judge_grounding → finalizer (LLM writes the user-facing text)
```

`judge_grounding` scored the *investigation transcript* — did the model's
reasoning, across the whole back-and-forth, look supported by the tool
calls it made? If yes, a `finalizer` step took over and wrote the finding a
user actually sees.

The problem: that finalizer is a fresh LLM call, writing fresh text, *after*
the check that was supposed to prove the text was trustworthy. Nothing
stops the finalizer from paraphrasing its way into a claim that was never in
the judged transcript at all. The grounding check and the published output
are two different artifacts, connected by nothing but hope.

## The fix

Judge the thing you're about to publish, not a proxy for it:

```
draft_finding (LLM) → extract_claims (decomposes THAT draft's own text)
                    → judge_grounding (scores each claim against real tool results)
                    → publish (no model call — assembles the judged draft verbatim)
```

`publish` is a plain function. It builds the terminal object from the judged
draft's own `model_dump()` plus the grounding report — there's no prompt for
it to run, so there's no way for it to alter the text. A test asserts
`published.finding_text == draft_finding.finding_text` on every pull
request. If that assertion could ever fail, the architecture would be
broken, not just the test.

## What this bought, concretely

When the check fails, the entire draft gets thrown out — not patched, not
partially kept — and the investigation goes back to gather more evidence
with the *specific* unsupported claims as feedback, capped at two extra
passes. Two canonical test scenarios exercise this directly: one where the
draft becomes fully grounded on the second pass, and one where it never
does and the run publishes anyway with the gap stated plainly in the
grounding report, rather than looping forever.

The deeper lesson generalizes past insider trading: **whatever you judge has
to be the literal bytes you ship.** If there's a model call anywhere between
"this passed the check" and "this is what the user sees," you don't have a
grounding guarantee — you have a grounding check on something the user never
reads.
