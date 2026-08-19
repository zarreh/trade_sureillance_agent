# Regulatory basis

!!! danger "This is a research prototype, not legal or compliance advice"
    Nothing on this page or produced by this system has been reviewed by a
    licensed attorney or compliance professional. It is a portfolio
    engineering project demonstrating a grounded-AI architecture over a
    realistic regulatory domain — not a system of record, not investment or
    legal advice, and not a substitute for a firm's actual compliance
    program. Every rule, threshold, and role limit this system applies
    (except where explicitly cited below) is **synthetic data invented for
    this project**. Do not rely on any output of this system for a real
    compliance decision.

## What this system actually investigates

This system reasons over **SEC Form 4 filings** — reports of changes in
beneficial ownership that officers, directors, and beneficial owners of more
than 10% of a registered class of equity securities must file under
**Section 16(a) of the Securities Exchange Act of 1934** (15 U.S.C. § 78p(a)).
Since the Sarbanes-Oxley Act of 2002, Section 16(a) generally requires these
transactions to be reported within **two business days** of the transaction.
`filing_lag_trading_days` (`data/build_store.py`) measures exactly this gap,
computed against the **NYSE trading calendar**
(`pandas-market-calendars`, `data/dates.py::nyse_trading_days_between`) —
business-day counting must use the calendar the exchanges actually observe,
not a generic weekday count, since the two differ around exchange holidays.
This is this repository's implementation choice of calendar source, not
itself a citation to a specific rule text.

**SEC Rule 10b-5** (17 CFR § 240.10b-5), adopted under Section 10(b) of the
Exchange Act, is the general anti-fraud provision most insider-trading
enforcement is built on — it prohibits fraud and deception in connection
with the purchase or sale of any security, including trading on material
nonpublic information. This system does not implement Rule 10b-5 itself; it
implements a **surveillance heuristic** (transaction value against a role
limit, timing against a seeded corporate-events calendar, rolling volume
against the insider's own history) that a human compliance reviewer would
use as a starting point for the kind of inquiry Rule 10b-5 concerns.

## Rule 10b5-1 as a reported, not verified, signal

**Rule 10b5-1** (17 CFR § 240.10b5-1) provides an **affirmative defense**
against insider-trading liability for trades made under a written trading
plan adopted in good faith, before the person was aware of material
nonpublic information, and (following the SEC's 2022 amendments) subject to
a cooling-off period and related conditions. This system's
`reported_under_10b5_1` field (tri-state: `true` / `false` / `unknown`,
`store/models.py::Transaction`) reflects **only whether the filing itself
reported the indicator** — never whether a plan was independently verified
against these conditions. `unknown` is rendered everywhere in this system,
including the UI, as **"not established"**, never as an absence of a plan
(D-A2-5) — the distinction matters because a plan can be real and simply not
captured by this field's encoding (SEC's own bulk data shows the field
encoded inconsistently across filers, `docs/PLAN.md` §4.3).

## Why a human reviewer stays in the loop

**FINRA Rule 3110** requires broker-dealers to establish and maintain a
system to supervise the activities of their associated persons, including
review of the kinds of transactions this system investigates. This system
does not implement or replace that supervisory obligation — it is not a
broker-dealer's compliance system, has not been reviewed by one, and every
finding it produces is a **research artifact for a human reviewer**, never a
supervisory determination on its own (`docs/how-it-works/what-it-wont-do.md`).
Rule 3110 is cited here as the reason a system like this belongs *inside* a
supervised compliance workflow with a human decision-maker, not as a
claim that this prototype satisfies it.

## What is synthetic

- **Role-based trading limits** (`role_limits` table,
  `data/generate_compliance_db.py::ROLE_LIMITS`) — invented thresholds by
  relationship and authorization level, not any real firm's policy.
- **Compliance rule table** (`compliance_rules`,
  `data/generate_compliance_db.py::COMPLIANCE_RULES`) — a synthetic
  severity-tiered rule table, not a real firm's rule book or SEC rule text.
- **Corporate-events calendar** (`material_events`,
  seeded per issuer with a fixed random seed) — a synthetic earnings
  calendar and blackout window, not any real company's actual event dates.
- **The transaction data itself** is real: fetched from **SEC EDGAR's bulk
  Insider Transactions Data Sets** (`data/fetch_edgar.py`), which is public
  domain. See `docs/evidence/data-profile.md` for known data-quality
  limitations in that source (approximately 0.4% of dates show
  filer-entered typos, e.g. a four-digit year off by one — SEC's own bulk
  data disclaims this).

## Scope this system does not claim

See [What it won't do](how-it-works/what-it-wont-do.md) for the complete
list. In summary: it does not watch live trades or price feeds, it does not
decide anything on its own, and it is not investment, legal, or compliance
advice.

