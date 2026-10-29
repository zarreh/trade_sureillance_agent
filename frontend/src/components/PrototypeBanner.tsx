import { Callout } from "@/components/ui/Callout";
import { docsLink } from "@/lib/docs";

export function PrototypeBanner() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 pt-4 sm:px-6">
      <Callout variant="warning" title="Research prototype">
        Synthetic firm policy, not a supervisory system of record, and not legal or compliance
        advice. See the{" "}
        <a className="underline" href={docsLink("regulatoryBasis")} target="_blank" rel="noreferrer">
          regulatory basis
        </a>
        .
      </Callout>
    </div>
  );
}
