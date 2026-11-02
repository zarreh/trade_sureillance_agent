import type { ReactNode } from "react";

const VARIANTS = {
  red: "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-950 dark:text-red-300 dark:ring-red-400/30",
  orange:
    "bg-orange-50 text-orange-800 ring-orange-600/25 dark:bg-orange-950/60 dark:text-orange-300 dark:ring-orange-400/30",
  amber:
    "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-400/30",
  accent: "bg-accent-50 text-accent-700 ring-accent-600/20 dark:bg-accent-950 dark:text-accent-300 dark:ring-accent-400/30",
  indigo:
    "bg-indigo-50 text-indigo-700 ring-indigo-600/20 dark:bg-indigo-950 dark:text-indigo-300 dark:ring-indigo-400/30",
  green:
    "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-400/30",
  slate: "bg-surface-2 text-muted ring-line",
} as const;

export type BadgeVariant = keyof typeof VARIANTS;

export function Badge({
  children,
  variant = "slate",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${VARIANTS[variant]}`}
    >
      {children}
    </span>
  );
}

const DISPOSITION: Record<string, { label: string; variant: BadgeVariant }> = {
  clear: { label: "Clear", variant: "green" },
  flag: { label: "Flag for review", variant: "orange" },
  escalate: { label: "Escalate", variant: "red" },
};

export function DispositionBadge({ disposition }: { disposition: string }) {
  const d = DISPOSITION[disposition] ?? { label: disposition, variant: "slate" as const };
  return <Badge variant={d.variant}>{d.label}</Badge>;
}

/** Who owns a step: the AI model, plain code, or both. */
const OWNERS = {
  ai: { label: "AI", variant: "indigo" },
  code: { label: "Code", variant: "slate" },
  both: { label: "AI + code", variant: "accent" },
} as const;

export type Owner = keyof typeof OWNERS;

export function OwnerBadge({ owner }: { owner: Owner }) {
  const o = OWNERS[owner];
  return <Badge variant={o.variant}>{o.label}</Badge>;
}

/** A pass/fail check result. */
export function CheckBadge({ ok, okLabel, failLabel }: { ok: boolean; okLabel: string; failLabel: string }) {
  return <Badge variant={ok ? "green" : "red"}>{ok ? okLabel : failLabel}</Badge>;
}
