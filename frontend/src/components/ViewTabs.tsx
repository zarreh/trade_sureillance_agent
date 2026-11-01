"use client";

import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export interface TabSpec {
  id: string;
  label: string;
  content: ReactNode;
}

/** Only the active panel is rendered, so ids inside a panel stay unique on the page. */
export function ViewTabs({ tabs, label }: { tabs: TabSpec[]; label: string }) {
  const [active, setActive] = useState(tabs[0].id);
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(event: KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    const next = tabs[(index + step + tabs.length) % tabs.length];
    setActive(next.id);
    buttons.current[next.id]?.focus();
  }

  const current = tabs.find((t) => t.id === active) ?? tabs[0];
  return (
    <div className="space-y-5">
      <div role="tablist" aria-label={label} className="flex flex-wrap gap-1 border-b border-line">
        {tabs.map((tab, i) => {
          const selected = tab.id === current.id;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                buttons.current[tab.id] = el;
              }}
              role="tab"
              id={`tab-${tab.id}`}
              type="button"
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(tab.id)}
              onKeyDown={(e) => onKeyDown(e, i)}
              className={`-mb-px rounded-t-lg border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                selected
                  ? "border-accent-600 text-accent-800 dark:border-accent-400 dark:text-accent-200"
                  : "border-transparent text-muted hover:text-fg"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div role="tabpanel" id={`panel-${current.id}`} aria-labelledby={`tab-${current.id}`}>
        {current.content}
      </div>
    </div>
  );
}
