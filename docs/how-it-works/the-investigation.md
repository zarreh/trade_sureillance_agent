# The investigation, step by step

!!! info "In one paragraph"
    The screenshots below are the real UI, captured automatically
    (`make docs-screenshots`) against the same network-level mocks the
    Playwright smoke test uses, in light and dark. They are never hand-edited,
    so they can't drift from what the UI actually renders.

## What a visitor sees, without typing anything

The home page opens on a **recorded example**: canonical scenario 1, replayed
from a stored run, so a visitor sees a complete investigation the moment the
page loads and nothing is spent. It used the scripted stand-in for the AI model,
and the page says so. A **Run it live** button starts a real investigation
instead; its id goes into the URL (`?run=`), so a reload replays the stored run
rather than starting another.

<figure markdown>
![The home page with its recorded example](../assets/screenshot-home.png#only-light)
![The home page with its recorded example](../assets/screenshot-home-dark.png#only-dark)
<figcaption markdown>The home page: what it is, how it works with an owner for each step, and the recorded example</figcaption>
</figure>

### 1. Starting and running

<figure markdown>
![Loading state](../assets/screenshot-loading.png#only-light)
![Loading state](../assets/screenshot-loading-dark.png#only-dark)
<figcaption markdown>The request has been sent</figcaption>
</figure>

<figure markdown>
![Running state](../assets/screenshot-running.png#only-light)
![Running state](../assets/screenshot-running-dark.png#only-dark)
<figcaption markdown>Connected to the run, waiting for its first step</figcaption>
</figure>

### 2. The trace, step by step

Each step in the graph appears in `TraceTimeline` as it completes, in plain
language with the raw node name beneath and a badge saying who owns it: the AI
model, plain code, or both.

### 3. The grounding check and the claims

`ValidatorStrip` shows how many of the draft's claims were supported by the
evidence gathered, and `ClaimsCheck` lists each claim beside the judge's verdict
and the tool calls it cites. This is the check described in
[Grounding](grounding.md).

### 4. The published finding

`EvidencePanel` renders the disposition, severity, confidence, the rules cited,
any exculpatory factors, and the `reported_under_10b5_1` tri-state, shown as
"not established" for `unknown`, never as an absence of a plan (D-A2-5).

### 5. The process audit

`ProcessAuditPanel` shows how the investigation worked, checked in code: whether
all six tools were called, whether the transaction details came first, whether
every citation is a real tool call, and whether any exemption it states is backed
by the filing. Each row is a badge with a one-line explanation, never a bare
score. It records; it never changes the finding
([D-A2-7](../architecture/decisions/D-A2-7-process-audit.md)). `CostMeter` shows
what the run cost.

<figure markdown>
![Full investigation, published](../assets/screenshot-success.png#only-light)
![Full investigation, published](../assets/screenshot-success-dark.png#only-dark)
<figcaption markdown>A published finding with its claims check and process audit</figcaption>
</figure>

## When it doesn't go as planned

All of these states are tested by the same Playwright suite
(`frontend/e2e/investigation.spec.ts`).

**A run that can't be started.** The API rejects an unknown accession with a
`404` and an actionable message, which the page shows as is. A backend that is
unreachable or over its rate limit shows a generic message. A run that failed, or
was cut off by a server restart, shows its stored error.

<figure markdown>
![Error state](../assets/screenshot-error.png#only-light)
![Error state](../assets/screenshot-error-dark.png#only-dark)
<figcaption markdown>An accession that is not in the facts database</figcaption>
</figure>

**A completed run with no finding.** A defensive case the pipeline shouldn't
reach in practice (`draft_finding` and `budget_exceeded` both always produce a
finding), rendered explicitly rather than left blank:

<figure markdown>
![Empty state](../assets/screenshot-empty.png#only-light)
![Empty state](../assets/screenshot-empty-dark.png#only-dark)
<figcaption markdown>A completed run with no finding to show</figcaption>
</figure>

## How we know it works

The **How we know it works** page explains the RL environment and shows how each
scripted shortcut scores. See [RL environment](../evidence/rl-environment.md).

<figure markdown>
![The evaluation page](../assets/screenshot-evaluation.png#only-light)
![The evaluation page](../assets/screenshot-evaluation-dark.png#only-dark)
<figcaption markdown>The evaluation page, with what the numbers are and are not</figcaption>
</figure>
