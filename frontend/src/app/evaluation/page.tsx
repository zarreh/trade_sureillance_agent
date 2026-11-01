import { FlaskConical } from "lucide-react";

import { LiveRuns } from "@/components/LiveRuns";
import { PolicyScores } from "@/components/PolicyScores";
import { Callout } from "@/components/ui/Callout";
import { Card, CardTitle } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { PageHeader } from "@/components/ui/PageHeader";
import liveRuns from "@/generated/live-runs.json";
import rlPolicies from "@/generated/rl-policies.json";
import { docsLink } from "@/lib/docs";
import { GLOSSARY } from "@/lib/glossary";
import { LiveRunsSchema, RlPoliciesSchema } from "@/lib/schemas";

export const metadata = { title: "How we know it works · Trade Surveillance Agent" };

const data = RlPoliciesSchema.parse(rlPolicies);
const live = LiveRunsSchema.parse(liveRuns);

const RL_PURPOSE = [
  {
    title: "A process audit on every real run",
    body: "Plain code checks that all six evidence sources were consulted, transaction details came first, every citation points at a real tool call, and any exemption is backed by the filing. It is shown on every run.",
  },
  {
    title: "A score that shortcuts can't win",
    body: "Scoring only the final answer rewards always flagging. The reward multiplies a correct answer by the audit score and has no AI judge in it, so each tested shortcut scores far below a proper investigation.",
  },
  {
    title: "A regression guard",
    body: "CI fails if any shortcut gets within 0.5 of the reference, so weakening a check is caught before it ships.",
  },
  {
    title: "A ready environment, not a trained model",
    body: "The same loop is a Gymnasium environment that could drive prompt optimisation or fine-tuning later. Nothing is trained on it today.",
  },
];

export default function EvaluationPage() {
  const reference = data.policies.find((p) => p.policy === "reference");
  const flagAll = data.policies.find((p) => p.policy === "always_flag");
  return (
    <div className="space-y-8">
      <PageHeader
        icon={FlaskConical}
        eyebrow="Evaluation"
        title="How we know the investigator isn't cutting corners"
        docsHref={docsLink("rlEnvironment")}
        docsLabel="Read the full write-up"
      >
        <p>
          A finding can look right while the investigation behind it skipped evidence, cited things
          it never retrieved, or claimed an exemption the filing doesn&apos;t support. So the same
          investigation loop is turned into a small practice environment with a scoring rule, and
          scripted shortcut strategies are run through it.
        </p>
      </PageHeader>

      <Card className="space-y-4" aria-label="What the RL part is for">
        <CardTitle>What the RL part is for</CardTitle>
        <ol className="grid gap-4 sm:grid-cols-2">
          {RL_PURPOSE.map((item, i) => (
            <li key={item.title} className="flex gap-3">
              <span className="font-mono text-sm text-accent-700 dark:text-accent-300">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="text-sm font-semibold text-fg">{item.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      <Card tone="accent" className="space-y-2">
        <CardTitle>Key finding</CardTitle>
        <p className="text-[15px] leading-relaxed text-slate-800 dark:text-slate-100">
          Every shortcut scores at least {data.gate_margin} below a proper investigation, and a
          test in CI keeps it that way. Always flagging gets{" "}
          <strong>{Math.round((flagAll?.flag_recall ?? 0) * 100)}% flag recall</strong> on outcome
          alone, yet scores only <strong>{flagAll?.reward_mean.toFixed(2)}</strong> against the
          reference&apos;s <strong>{reference?.reward_mean.toFixed(2)}</strong> once the process is
          counted.
        </p>
      </Card>

      <Callout variant="warning" title="What these numbers are">
        <ul className="list-disc space-y-1 pl-4">
          <li>
            n={data.n} canonical scenarios, with labels designed alongside them. n={data.n} supports
            no precision claim, and no uncertainty is computed.
          </li>
          <li>
            Scored by a <strong>scripted stand-in</strong>
            <InfoTip text={GLOSSARY.scriptedStandIn} label="Scripted stand-in." />, not a live
            model. Model version: {data.model_version}.
          </li>
          <li>
            The reference reaching 1.00 is a consistency check of the environment, not a
            performance claim.
          </li>
          <li>
            The scenarios are synthetic trades, and the limits, rules and calendar they are
            checked against are synthetic too.
            <InfoTip text={GLOSSARY.syntheticPolicy} label="Synthetic firm policy." />
          </li>
          <li>Run date: {data.run_date}.</li>
        </ul>
      </Callout>

      <Card className="space-y-4">
        <CardTitle>Score per strategy</CardTitle>
        <PolicyScores data={data} />
      </Card>

      <Card className="space-y-4" aria-label="Live model">
        <CardTitle>The real model, on the same ruler</CardTitle>
        <p className="text-sm leading-relaxed text-muted">
          The same ten scenarios run through the real graph with real models, scored with the same reward. The
          audit caught a real defect: the claim extractor saw only opaque tool-call ids, so on most runs it cited
          nothing and every claim failed the citation check. Giving it the tool name and a result excerpt per id
          (extractor v2) took audit failures from 8 of 10 runs to 0. It did not fix the answers: the model still
          clears cases it should flag.
        </p>
        <LiveRuns data={live} />
      </Card>

      <p className="text-sm text-muted">
        Read more:{" "}
        <a className="underline" href={docsLink("rlEnvironment")} target="_blank" rel="noreferrer">
          the environment and its gate
        </a>
        ,{" "}
        <a className="underline" href={docsLink("processAudit")} target="_blank" rel="noreferrer">
          the process audit decision
        </a>
        ,{" "}
        <a className="underline" href={docsLink("rewardDesign")} target="_blank" rel="noreferrer">
          the reward design decision
        </a>
        .
      </p>
    </div>
  );
}
