import { test, expect } from "@playwright/test";
import { SUCCESS_INVESTIGATION, caseRow, mockCases, mockRun, mockStart, watchConsole } from "./fixtures";

// Case queue, analyst decision and theme. The backend is mocked at the network layer.

const SCENARIO = "SCENARIO-0000000001-25-000001";
const UNTOUCHED = "SCENARIO-0000000001-25-000002";

test("queue: lists cases with the AI suggestion, audit score and decision state", async ({ page }) => {
  const problems = watchConsole(page);
  const stale = caseRow("0000000001-25-000001", "run-old", "clear");
  stale.decision = {
    run_id: "run-older",
    decision: "accept",
    override_disposition: null,
    note: "",
    updated_at: "2026-08-19T00:01:00Z",
    stale: true,
  };
  await mockCases(page, [caseRow(SCENARIO, "run-success"), stale, caseRow(UNTOUCHED)]);

  await page.goto("/queue");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Case queue");
  await expect(page.getByText("AI suggestion. The analyst decides.")).toBeVisible();
  const rows = page.getByTestId("case-row");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("Flag for review");
  await expect(rows.nth(0)).toContainText("1.00");
  await expect(rows.nth(0)).toContainText("Pending");
  await expect(rows.nth(1)).toContainText("Stale: newer run");
  await expect(rows.nth(2)).toContainText("Not investigated");
  await expect(page.getByRole("link", { name: "Case queue" })).toHaveAttribute("aria-current", "page");

  await page.getByLabel("Filter by analyst decision").selectOption("stale");
  await expect(rows).toHaveCount(1);
  await page.getByLabel("Filter by analyst decision").selectOption("all");
  await page.getByLabel("Filter by AI suggestion").selectOption("none");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText(UNTOUCHED);
  expect(problems).toEqual([]);
});

test("queue: re-run starts an investigation and opens it", async ({ page }) => {
  await mockCases(page, [caseRow(SCENARIO, "run-success")]);
  await mockStart(page, "run-success");
  await mockRun(page, "run-success", SUCCESS_INVESTIGATION);

  await page.goto("/queue");
  await page.getByRole("button", { name: `Re-run ${SCENARIO}` }).click();
  await expect(page).toHaveURL(/\/investigate\?run=run-success/);
  await expect(page.getByLabel("Analyst decision", { exact: true })).toBeVisible();
});

test("decision: accept, then override with a note, both tied to the run", async ({ page }) => {
  const problems = watchConsole(page);
  await mockRun(page, "run-success", SUCCESS_INVESTIGATION);
  const puts = await mockCases(page, [caseRow(SCENARIO, "run-success")]);

  await page.goto("/investigate?run=run-success");
  const card = page.getByLabel("Analyst decision", { exact: true });
  await expect(card).toBeVisible();

  await card.getByRole("button", { name: "Accept AI suggestion" }).click();
  await expect(card.getByRole("status")).toContainText("Accepted");

  await card.getByLabel("Note (optional)").fill("rolling volume matters here");
  await card.getByRole("button", { name: "Override…" }).click();
  await card.getByLabel("Your disposition").selectOption("escalate");
  await card.getByRole("button", { name: "Save override" }).click();
  await expect(card.getByRole("status")).toContainText("Overridden");
  await expect(card.getByRole("status")).toContainText("rolling volume matters here");

  expect(puts).toEqual([
    { run_id: "run-success", decision: "accept", override_disposition: null, note: "" },
    {
      run_id: "run-success",
      decision: "override",
      override_disposition: "escalate",
      note: "rolling volume matters here",
    },
  ]);
  expect(problems).toEqual([]);
});

test("theme: dark by default, the toggle persists across reloads", async ({ page }) => {
  await page.goto("/");
  const html = page.locator("html");
  await expect(html).toHaveClass(/\bdark\b/);

  await page.getByRole("button", { name: "Switch to light theme" }).click();
  await expect(html).not.toHaveClass(/\bdark\b/);

  await page.reload();
  await expect(html).not.toHaveClass(/\bdark\b/);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(html).toHaveClass(/\bdark\b/);
});

test("evaluation: explains the RL part and shows every recorded live run, newest first", async ({ page }) => {
  const problems = watchConsole(page);
  await page.goto("/evaluation");
  await expect(page.getByLabel("What the RL part is for", { exact: true })).toContainText("A regression guard");
  const runs = page.getByRole("table", { name: "Live-model runs" }).locator("tbody tr");
  await expect(runs.first()).toContainText("2026-11-01");
  await expect(runs.first()).toContainText("0/10");
  await expect(runs.last()).toContainText("2026-10-29");
  await page.getByText(/why each one lost points/).click();
  await expect(page.getByRole("table", { name: "Per-scenario live results" })).toContainText("expected flag");
  expect(problems).toEqual([]);
});
