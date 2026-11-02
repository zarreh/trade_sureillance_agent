import type { ReactNode } from "react";

const TONES = {
  default: "border-line bg-surface",
  accent: "border-accent-400 bg-surface ring-1 ring-accent-200 dark:border-accent-500/50 dark:ring-accent-400/10",
  red: "border-red-300 bg-red-50/60 dark:border-red-900 dark:bg-red-950/30",
  amber: "border-amber-300 bg-amber-50/60 dark:border-amber-900 dark:bg-amber-950/30",
  emerald: "border-emerald-300 bg-emerald-50/60 dark:border-emerald-900 dark:bg-emerald-950/30",
} as const;

export type CardTone = keyof typeof TONES;

export function Card({
  children,
  className = "",
  padded = true,
  tone = "default",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
  tone?: CardTone;
} & Omit<React.HTMLAttributes<HTMLElement>, "className" | "children">) {
  return (
    <section className={`rounded-lg border shadow-sm dark:shadow-none ${TONES[tone]} ${padded ? "p-5" : ""} ${className}`} {...rest}>
      {children}
    </section>
  );
}

export function CardTitle({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted">
      {icon}
      {children}
    </h2>
  );
}
