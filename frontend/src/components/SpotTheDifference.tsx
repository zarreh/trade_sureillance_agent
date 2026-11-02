"use client";

import Link from "next/link";
import { useState } from "react";

import { DispositionBadge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";

type Disposition = "clear" | "flag" | "escalate";
type Choice = "A" | "B" | "both" | "neither";

export interface QuizFiling {
  label: "A" | "B";
  slug: string;
  title: string;
  rows: { label: string; value: string }[];
  answerKey: Disposition;
  /** What the filing itself says that settles it. */
  decisive: string;
}

const OPTIONS: { value: Choice; label: string }[] = [
  { value: "A", label: "Only filing A" },
  { value: "B", label: "Only filing B" },
  { value: "both", label: "Both" },
  { value: "neither", label: "Neither" },
];

/** Two filings that look the same on the surface. The visitor chooses before seeing what separates them. */
export function SpotTheDifference({ filings }: { filings: [QuizFiling, QuizFiling] }) {
  const [choice, setChoice] = useState<Choice | null>(null);
  const flagged = filings.filter((f) => f.answerKey !== "clear").map((f) => f.label);
  const correct: Choice = flagged.length === 2 ? "both" : flagged.length === 1 ? flagged[0] : "neither";

  return (
    <Card aria-label="Spot the difference" tone="accent" className="space-y-5">
      <div className="space-y-1">
        <CardTitle>Try it yourself</CardTitle>
        <h2 className="text-xl font-semibold text-fg">
          Which of these filings deserves a second look?
        </h2>
        <p className="text-sm text-muted">
          Two insiders, the same sale, the same day, shortly before the same announcement.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {filings.map((filing) => (
          <div
            key={filing.label}
            className="rounded-xl border border-line bg-surface p-4"
          >
            <h3 className="mb-2 text-sm font-semibold text-fg">Filing {filing.label}</h3>
            <dl className="space-y-1">
              {filing.rows.map((row) => (
                <div key={row.label} className="flex flex-wrap justify-between gap-x-4 text-sm">
                  <dt className="text-muted">{row.label}</dt>
                  <dd className="text-right text-fg">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>

      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium text-fg">
          Which would you send to an analyst?
        </legend>
        <div className="flex flex-wrap gap-2">
          {OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent-500 ${
                choice === option.value
                  ? "border-accent-400 bg-accent-400 text-accent-fg"
                  : "border-line bg-surface text-fg hover:border-accent-500"
              }`}
            >
              <input
                type="radio"
                name="spot-the-difference"
                value={option.value}
                checked={choice === option.value}
                onChange={() => setChoice(option.value)}
                className="sr-only"
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div aria-live="polite">
        {choice && (
          <div className="space-y-4 rounded-xl border border-line bg-surface p-4">
            <p className="font-medium text-fg">
              {choice === correct ? "That matches the answer key." : "The answer key differs."} A simple rule that
              flags every sale before earnings would send both. Here is what separates them:
            </p>
            <ul className="space-y-3">
              {filings.map((filing) => (
                <li key={filing.label} className="space-y-1 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-fg">Filing {filing.label}</span>
                    <DispositionBadge disposition={filing.answerKey} />
                  </div>
                  <p className="text-fg">{filing.decisive}</p>
                  <Link
                    href={`/cases/${filing.slug}`}
                    className="font-medium text-accent-700 hover:underline dark:text-accent-300"
                  >
                    See the full investigation: {filing.title}
                  </Link>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => setChoice(null)}
              className="text-sm font-medium text-accent-700 hover:underline dark:text-accent-300"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}
