import { BookOpen, Code, Scale } from "lucide-react";

import { DOCS_URL, REPO_URL, docsLink } from "@/lib/docs";

const LINK =
  "inline-flex items-center gap-1 hover:text-accent-700 dark:hover:text-accent-300";

export function AppFooter() {
  return (
    <footer className="mt-16 border-t border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-6 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>
          The sample cases are synthetic trades; firm policy and the corporate calendar are synthetic
          too. Other filings come from public SEC data. A research prototype, not a supervisory system
          of record.
        </p>
        <div className="flex flex-wrap gap-4">
          <a className={LINK} href={DOCS_URL} target="_blank" rel="noreferrer">
            <BookOpen className="h-4 w-4" aria-hidden /> Documentation
          </a>
          <a className={LINK} href={docsLink("regulatoryBasis")} target="_blank" rel="noreferrer">
            <Scale className="h-4 w-4" aria-hidden /> Regulatory basis
          </a>
          <a className={LINK} href={REPO_URL} target="_blank" rel="noreferrer">
            <Code className="h-4 w-4" aria-hidden /> Source code
          </a>
        </div>
      </div>
    </footer>
  );
}
