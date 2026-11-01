import { ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  icon: Icon,
  eyebrow,
  title,
  children,
  docsHref,
  docsLabel = "Learn more in the docs",
}: {
  icon: LucideIcon;
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  docsHref?: string;
  docsLabel?: string;
}) {
  return (
    <header className="mb-8">
      <div className="flex items-start gap-4">
        <div className="hidden rounded-lg bg-accent-400 p-3 text-accent-fg sm:block">
          <Icon className="h-6 w-6" aria-hidden />
        </div>
        <div className="min-w-0">
          {eyebrow && (
            <p className="text-xs font-semibold uppercase tracking-wider text-accent-700 dark:text-accent-300">{eyebrow}</p>
          )}
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-fg sm:text-3xl">{title}</h1>
          {children && (
            <div className="mt-3 max-w-3xl space-y-2 text-[15px] leading-relaxed text-muted">
              {children}
            </div>
          )}
          {docsHref && (
            <a
              href={docsHref}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-accent-700 hover:text-accent-900 dark:text-accent-300 dark:hover:text-accent-200"
            >
              {docsLabel}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
