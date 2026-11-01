"use client";

import { BookOpen, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { DOCS_URL } from "@/lib/docs";

const NAV = [
  { href: "/queue", label: "Case queue" },
  { href: "/", label: "Sample cases" },
  { href: "/investigate", label: "Investigate a filing" },
  { href: "/evaluation", label: "How we know it works" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/" || pathname.startsWith("/cases");
  return pathname.startsWith(href);
}

export function AppHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold text-fg">
          <span className="rounded-md bg-accent-400 p-1.5 text-accent-fg">
            <ShieldCheck className="h-4 w-4" aria-hidden />
          </span>
          Trade Surveillance Agent
        </Link>
        <nav aria-label="Main" className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`whitespace-nowrap rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-accent-500/60 bg-accent-50 text-accent-800 dark:bg-accent-400/10 dark:text-accent-300"
                    : "border-transparent text-muted hover:bg-surface-2 hover:text-fg"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-accent-600 px-2.5 py-1.5 text-sm font-medium text-accent-700 hover:bg-accent-400 hover:text-accent-fg dark:border-accent-500 dark:text-accent-300 dark:hover:text-accent-fg"
          >
            <BookOpen className="h-4 w-4" aria-hidden />
            Docs
          </a>
        </div>
      </div>
    </header>
  );
}
