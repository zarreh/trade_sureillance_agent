# In plain language

!!! info "In one paragraph"
    Imagine a compliance officer who has to check whether an executive's
    stock sale was suspicious. They would look up who the person is, what
    they're allowed to trade, how much they've traded recently, and whether
    anything about the timing looks wrong. This system automates exactly
    that checklist over real SEC filings — and shows its work at every step,
    checking its own conclusion against the evidence before it tells you
    anything.

## The problem

Executives, directors, and large shareholders have to publicly report their
own stock trades within two business days. Regulators and compliance teams
watch these reports for patterns that warrant a closer look — a sale timed
suspiciously close to upcoming news, a trade far larger than someone
normally makes, a filing that showed up late. Doing this by hand, for every
filing, does not scale; doing it with an AI system that can quietly
hallucinate a plausible-sounding but wrong conclusion is arguably worse than
not doing it at all.

## What this system does about it

1. **Plans** which pieces of evidence it needs (who is this person, what are
   they allowed to trade, what rules apply, how does this compare to their
   own history, is there a blackout window) — checked by code, not trusted
   blindly.
2. **Investigates** by calling real tools against real data — never
   inventing a fact it hasn't actually looked up.
3. **Drafts a conclusion**, then **decomposes that conclusion into
   individual claims** and checks each one against the evidence it actually
   gathered — not the conversation, the evidence.
4. If a claim isn't backed by anything real, the draft is **thrown out** and
   the investigation goes back to gather more evidence, up to two extra
   tries, before it's willing to publish anything.
5. Only then does it **publish** — and the published text is provably the
   exact text that passed that check, never rewritten afterward.

## Why this matters more than the trading rules themselves

The insider-trading domain here is realistic, but it is a vehicle for the
actual point: **an AI system that can show, for any claim it makes, exactly
which piece of real evidence backs it up** — and that refuses to publish a
claim it can't back. That pattern generalizes far beyond insider trading.

See [How it works → Grounding](grounding.md) for the mechanism, and
[What it won't do](what-it-wont-do.md) for this system's honest limits.
