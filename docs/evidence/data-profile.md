# Data profile

!!! info "In one paragraph, for a non-engineer"
    Before writing any investigation logic, we looked at what the real SEC data
    actually contains. That look changed the design in several places — most
    importantly, it caught a bug in the original source material that would
    have made two of five tools silently useless.

Generated from a real, live fetch of three SEC EDGAR quarters (2025 Q4 – 2026
Q2), 273,482 transactions, via `make docs-assets` (`docs/generate_plots.py`).
CI fails if regenerating these charts produces a diff, so they can never drift
from the data they describe.

## Transaction codes are not just "buy" and "sell"

<figure markdown>
![Transaction code distribution](../assets/transaction-code-distribution-light.svg#only-light)
![Transaction code distribution](../assets/transaction-code-distribution-dark.svg#only-dark)
</figure>

`F` (tax withholding) and `M` (option exercise) are the third and fourth most
common codes — more common than ordinary purchases. Both are routinely
non-suspicious. A naive value-threshold rule would flag tens of thousands of
these every quarter, which is exactly how a surveillance system gets switched
off from alert fatigue. See
[docs/PLAN.md](https://github.com/PLACEHOLDER/trade-surveillance-agent/blob/main/docs/PLAN.md)
§3.3.8.

## Most sales are not made under a 10b5-1 plan

<figure markdown>
![Reported 10b5-1 distribution](../assets/reported-10b5-1-distribution-light.svg#only-light)
![Reported 10b5-1 distribution](../assets/reported-10b5-1-distribution-dark.svg#only-dark)
</figure>

The minority that are reported under a plan are the exculpatory cases this
system must never flag.

## Filing lag against the Section 16(a) deadline

<figure markdown>
![Filing lag distribution](../assets/filing-lag-distribution-light.svg#only-light)
![Filing lag distribution](../assets/filing-lag-distribution-dark.svg#only-dark)
</figure>

Measured in NYSE trading days, not calendar days — the two diverge around
exchange holidays, which is exactly where a generic business-day calendar would
misjudge lateness.

## Transaction value by relationship

<figure markdown>
![Value by relationship](../assets/value-by-relationship-light.svg#only-light)
![Value by relationship](../assets/value-by-relationship-dark.svg#only-dark)
</figure>

## Why three quarters of data, not one

<figure markdown>
![Data coverage timeline](../assets/data-coverage-timeline-light.svg#only-light)
![Data coverage timeline](../assets/data-coverage-timeline-dark.svg#only-dark)
</figure>

A rolling 90-day volume check and a 180-day trading-history baseline both need
real history behind the target quarter. Fetching only the target quarter would
silently starve both checks for every transaction early in that quarter.

## A real data-quality finding

The live fetch surfaced something the reference sample didn't: SEC's own
disclaimer states filer-submitted data "cannot guarantee accuracy," and in
practice roughly 0.4% of transaction dates in this dataset are implausible
(e.g. a year typo shifting a date by decades, or into the future). This is a
known EDGAR data-quality limitation, not a bug in this pipeline — the
zero-null-date assertion catches *unparseable* dates; implausible-but-parseable
dates are a distinct problem, tracked for a future plausibility-bound filter
rather than blocking Phase 1.
