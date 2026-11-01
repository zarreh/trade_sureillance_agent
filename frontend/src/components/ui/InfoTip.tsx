import { Info } from "lucide-react";

// CSS-only (hover + keyboard focus), so it works inside server components.
export function InfoTip({ text, label = "What does this mean?" }: { text: string; label?: string }) {
  return (
    <span className="group relative inline-flex align-middle">
      <button
        type="button"
        aria-label={`${label} ${text}`}
        className="ml-1 inline-flex rounded-full text-muted hover:text-accent-700 focus:text-accent-700 dark:hover:text-accent-300 dark:focus:text-accent-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
      >
        <Info className="h-3.5 w-3.5" aria-hidden />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 hidden w-64 max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-lg bg-fg px-3 py-2 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-background shadow-lg group-hover:block group-focus-within:block"
      >
        {text}
      </span>
    </span>
  );
}
