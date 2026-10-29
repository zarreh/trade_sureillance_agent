import { FlaskConical } from "lucide-react";

import { PolicyScores } from "@/components/PolicyScores";
import { Callout } from "@/components/ui/Callout";
import { Card, CardTitle } from "@/components/ui/Card";
import { InfoTip } from "@/components/ui/InfoTip";
import { PageHeader } from "@/components/ui/PageHeader";
import rlPolicies from "@/generated/rl-policies.json";
import { docsLink } from "@/lib/docs";
import { GLOSSARY } from "@/lib/glossary";
import { RlPoliciesSchema } from "@/lib/schemas";

export const metadata = { title: "How we know it works · Trade Surveillance Agent" };

const data = RlPoliciesSchema.parse(rlPolicies);

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

      <Card tone="sky" className="space-y-2">
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
            The trades are real SEC filings; the limits, rules and calendar they are checked
            against are synthetic.
            <InfoTip text={GLOSSARY.syntheticPolicy} label="Synthetic firm policy." />
          </li>
          <li>Run date: {data.run_date}.</li>
        </ul>
      </Callout>

      <Card className="space-y-4">
        <CardTitle>Score per strategy</CardTitle>
        <PolicyScores data={data} />
      </Card>

      <p className="text-sm text-slate-600 dark:text-slate-300">
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
