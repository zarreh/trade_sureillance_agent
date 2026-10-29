// One plain-language sentence per term, so a term is explained identically
// everywhere an InfoTip uses it.
export const GLOSSARY = {
  form4:
    "The SEC filing in which a company insider reports a trade in their own company's shares, due within two business days.",
  plan10b5_1:
    "A pre-arranged trading plan an insider sets up in advance. A filing that reports one is a signal that a sale may have been scheduled, not a proof that it was legitimate.",
  reportedUnder10b5_1:
    "Whether the filing reported the trade as made under a 10b5-1 plan. 'Not established' means the filing did not say either way. It never means there was no plan.",
  blackoutWindow:
    "A period before a material event, such as earnings, when insiders should not trade.",
  rolling90dLimit:
    "A firm-policy cap on how much an insider may trade over the 90 days ending on the transaction date.",
  grounding:
    "Checking each claim in the draft against the evidence the investigation actually retrieved, before anything is published.",
  claim: "One factual sentence pulled out of the draft so it can be checked on its own.",
  exculpatoryFactor:
    "A fact from the filing that explains a trade innocently, such as tax withholding or an option exercise. Each one applies to a single transaction line, never to the whole filing.",
  processAudit:
    "A check, done in code, of how the investigation got to its finding: whether it gathered all the evidence, cited only real tool calls and claimed only supported exemptions.",
  disposition:
    "The investigation's outcome. Clear means nothing to follow up, flag means an analyst should look, escalate means it needs urgent review.",
  severity: "How serious the cited rule is, from the seeded firm-policy table.",
  scriptedStandIn:
    "A fixed, rules-based stand-in for the AI model, used so results can be reproduced exactly. It is not a measure of how a real model performs.",
  syntheticPolicy:
    "The trades are real SEC filings. The role limits, rules and corporate calendar the investigation checks them against are synthetic.",
} as const;

export type GlossaryTerm = keyof typeof GLOSSARY;
