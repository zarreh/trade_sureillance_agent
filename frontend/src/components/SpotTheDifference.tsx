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
    <Card aria-label="Spot the difference" tone="sky" className="space-y-5">
      <div className="space-y-1">
        <CardTitle>Try it yourself</CardTitle>
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
          Which of these filings deserves a second look?
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Two insiders, the same sale, the same day, shortly before the same announcement.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {filings.map((filing) => (
          <div
            key={filing.label}
            className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
          >
            <h3 className="mb-2 text-sm font-semibold text-slate-900 dark:text-white">Filing {filing.label}</h3>
            <dl className="space-y-1">
              {filing.rows.map((row) => (
                <div key={row.label} className="flex flex-wrap justify-between gap-x-4 text-sm">
                  <dt className="text-slate-500 dark:text-slate-400">{row.label}</dt>
                  <dd className="text-right text-slate-900 dark:text-slate-100">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>

      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-medium text-slate-800 dark:text-slate-100">
          Which would you send to an analyst?
        </legend>
        <div className="flex flex-wrap gap-2">
          {OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-sky-500 ${
                choice === option.value
                  ? "border-sky-600 bg-sky-600 text-white"
                  : "border-slate-300 bg-white text-slate-800 hover:border-sky-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
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
          <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
            <p className="font-medium text-slate-900 dark:text-white">
              {choice === correct ? "That matches the answer key." : "The answer key differs."} A simple rule that
              flags every sale before earnings would send both. Here is what separates them:
            </p>
            <ul className="space-y-3">
              {filings.map((filing) => (
                <li key={filing.label} className="space-y-1 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-900 dark:text-white">Filing {filing.label}</span>
                    <DispositionBadge disposition={filing.answerKey} />
                  </div>
                  <p className="text-slate-700 dark:text-slate-200">{filing.decisive}</p>
                  <Link
                    href={`/cases/${filing.slug}`}
                    className="font-medium text-sky-700 hover:underline dark:text-sky-300"
                  >
                    See the full investigation: {filing.title}
                  </Link>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => setChoice(null)}
              className="text-sm font-medium text-sky-700 hover:underline dark:text-sky-300"
            >
              Try again
            </button>
          </div>
        )}
      </div>
    </Card>
  );
}
