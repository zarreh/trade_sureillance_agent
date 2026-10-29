// The MkDocs site (docs/). Overridable at build time so a fork or staging deploy
// can point at its own copy (NEXT_PUBLIC_* is inlined into the bundle).
export const DOCS_URL = (
  process.env.NEXT_PUBLIC_DOCS_URL ?? "https://zarreh.github.io/trade_sureillance_agent/"
).replace(/\/?$/, "/");

export const REPO_URL = "https://github.com/zarreh/trade_sureillance_agent";

export const DOC_PAGES = {
  home: "",
  plainLanguage: "how-it-works/in-plain-language/",
  theInvestigation: "how-it-works/the-investigation/",
  grounding: "how-it-works/grounding/",
  whatItWontDo: "how-it-works/what-it-wont-do/",
  architecture: "architecture/overview/",
  evaluation: "evidence/evaluation/",
  rlEnvironment: "evidence/rl-environment/",
  regulatoryBasis: "regulatory-basis/",
  runItYourself: "run-it-yourself/",
  processAudit: "architecture/decisions/D-A2-7-process-audit/",
  rewardDesign: "architecture/decisions/D-A2-8-reward-design/",
  deterministicPublication: "architecture/decisions/D-A2-1-deterministic-publication/",
  vocabulary: "architecture/decisions/D-A2-5-vocabulary-discipline/",
} as const;

export type DocPage = keyof typeof DOC_PAGES;

export function docsLink(page: DocPage): string {
  return `${DOCS_URL}${DOC_PAGES[page]}`;
}
