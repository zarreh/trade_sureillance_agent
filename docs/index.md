# Trade Surveillance Agent

> Insider-trading surveillance that has to show its work.

!!! info "In one paragraph, for a non-engineer"
    This system reads a securities transaction reported to the SEC and investigates
    whether it looks like insider trading. It only concludes something once every
    claim in its report is backed by a specific piece of retrieved evidence — and
    it says so when it isn't sure.

**Status:** in development. This site is being built alongside the code, phase by
phase — see the [build plan](https://github.com/PLACEHOLDER/trade-surveillance-agent/blob/main/docs/PLAN.md)
for what exists today.

## What it does

Takes a securities transaction in SEC Form 4 shape and runs an investigation: it
pulls the transaction record, checks the insider's applicable trading limits,
retrieves compliance rules with severity tiers, computes trading volume against
thresholds, and compares against the insider's own history. It issues a finding —
**clear / flag / escalate** — where every assertion traces to a retrieved fact.

## The centrepiece: a grounding judge that rejects its own draft

Most systems like this write a conclusion and hope it is supported. This one
writes a **draft**, decomposes it into individual claims, checks every claim
against the evidence actually retrieved, and — if anything is unsupported — sends
the investigation back for another evidence pass. Only a fully grounded draft is
ever published, and the published finding is guaranteed to be byte-identical to
the one that passed the check. See [Grounding](how-it-works/grounding.md).

## Try it

A live demo link will appear here once Phase 6 (frontend) ships.

---

*Research prototype. Built on public SEC data plus synthetic firm policy. Not a
supervisory system of record.*
