const REGULATORY_BASIS_URL =
  "https://github.com/zarreh/trade_sureillance_agent/blob/main/docs/regulatory-basis.md";

export function PrototypeBanner() {
  return (
    <div className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
      Research prototype, synthetic data only — not a supervisory system of
      record, and not legal or compliance advice. See{" "}
      <a className="underline" href={REGULATORY_BASIS_URL}>
        regulatory basis
      </a>
      .
    </div>
  );
}
