import { test, expect } from "@playwright/test";
import { SUCCESS_INVESTIGATION, mockRun, mockStart, watchConsole } from "./fixtures";

// The states an investigation can render, plus the recorded example and the
// evaluation page. The backend is fully mocked at the network layer, so no live
// model or Python process is needed.

const RUN_LIVE = { name: "Run it live" };

test("home: shows a recorded example on first paint, with no request to the API", async ({
  page,
}) => {
  const problems = watchConsole(page);
  const apiCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/investigations")) apiCalls.push(request.url());
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("second look");
  await expect(page.getByRole("region", { name: "How it works" })).toBeVisible();
  await expect(page.getByText("Recorded example")).toBeVisible();
  await expect(page.getByLabel("Investigation trace", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Finding", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Process audit", { exact: true })).toBeVisible();
  await expect(page.getByText("10b5-1 status: not established")).toBeVisible();
  expect(apiCalls).toEqual([]);
  expect(problems).toEqual([]);
});

test("loading: shows a starting message before the run begins", async ({ page }) => {
  await mockStart(page, "run-loading", 1000);
  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(page.getByText("Starting the investigation")).toBeVisible();
});

test("success: renders the trace, the checks, the process audit and the cost", async ({ page }) => {
  const problems = watchConsole(page);
  await mockStart(page, "run-success");
  await mockRun(page, "run-success", SUCCESS_INVESTIGATION);

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();

  await expect(page.getByLabel("Investigation trace", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Finding", { exact: true })).toBeVisible();
  await expect(page.getByText("1/1 claims supported")).toBeVisible();
  await expect(page.getByLabel("Claims check", { exact: true })).toContainText("seeded blackout window");
  await expect(page.getByLabel("Cost", { exact: true })).toBeVisible();
  await expect(page.getByText("$0.0021")).toBeVisible();
  // The 10b5-1 tri-state renders as "not established", never as "no plan".
  await expect(page.getByText("10b5-1 status: not established")).toBeVisible();

  const audit = page.getByLabel("Process audit", { exact: true });
  await expect(audit).toContainText("6 of 6 tools");
  await expect(audit).toContainText("The first call was get_transaction_details.");
  await expect(audit).toContainText("Every claim cites a tool call from this run.");
  await expect(audit).toContainText("The finding claims no exemption.");
  expect(problems).toEqual([]);
});

test("reload: a finished run is replayed from the stored events, not started again", async ({
  page,
}) => {
  await mockStart(page, "run-success");
  await mockRun(page, "run-success", SUCCESS_INVESTIGATION);

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(page.getByLabel("Cost", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\?run=run-success/);

  let posts = 0;
  page.on("request", (request) => {
    if (request.method() === "POST") posts += 1;
  });
  await page.reload();

  await expect(page.getByLabel("Finding", { exact: true })).toBeVisible();
  await expect(page.getByText("$0.0021")).toBeVisible();
  expect(posts).toBe(0);
});

test("a failed audit is shown, not hidden", async ({ page }) => {
  const failing = {
    ...SUCCESS_INVESTIGATION,
    id: "run-bad",
    finding: {
      ...SUCCESS_INVESTIGATION.finding,
      process_audit: {
        ...SUCCESS_INVESTIGATION.finding.process_audit,
        mandatory_tools_called: ["get_transaction_details"],
        mandatory_tools_missing: ["get_compliance_rules"],
        details_first: false,
        fabricated_citation_ids: ["ghost-1"],
        citation_validity: 0,
        claimed_exemptions: [{ kind: "reported_under_10b5_1" }],
        unsupported_exemptions: [{ kind: "reported_under_10b5_1" }],
      },
    },
  };
  await mockStart(page, "run-bad");
  await mockRun(page, "run-bad", failing);

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();

  const audit = page.getByLabel("Process audit", { exact: true });
  await expect(audit).toContainText("Missing: get_compliance_rules.");
  await expect(audit).toContainText("Another tool was called before the transaction details.");
  await expect(audit).toContainText("Cited calls that never happened: ghost-1.");
  await expect(audit).toContainText("Not backed by the filing: reported under 10b5 1.");
});

test("empty: renders a defensive message when a completed run has no finding", async ({ page }) => {
  await mockStart(page, "run-empty");
  await mockRun(page, "run-empty", {
    ...SUCCESS_INVESTIGATION,
    id: "run-empty",
    finding_kind: null,
    finding: null,
    costs: [],
    total_cost_usd: 0,
  });

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(page.getByText("produced no finding")).toBeVisible();
});

test("error: renders an alert when the investigation cannot be started", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Could not start the investigation" })
  ).toBeVisible();
});

test("error: shows the API's actionable detail for an unknown accession", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Accession 'X' is not in the facts database." }),
    });
  });

  await page.goto("/");
  await page.getByLabel("Accession number").fill("X");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "is not in the facts database" })
  ).toBeVisible();
});

test("error: a failed run shows the stored error", async ({ page }) => {
  await mockStart(page, "run-failed");
  await mockRun(page, "run-failed", {
    ...SUCCESS_INVESTIGATION,
    id: "run-failed",
    status: "failed",
    error: "interrupted by a server restart",
    finding_kind: null,
    finding: null,
  });

  await page.goto("/");
  await page.getByRole("button", RUN_LIVE).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "interrupted by a server restart" })
  ).toBeVisible();
});

test("evaluation: explains the result and discloses what the numbers are", async ({ page }) => {
  const problems = watchConsole(page);
  await page.goto("/");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: /How we know/ }).click();

  await expect(page).toHaveURL(/\/evaluation$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("cutting corners");
  await expect(page.getByText("Key finding")).toBeVisible();
  await expect(page.getByText("scripted stand-in", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("synthetic", { exact: false }).first()).toBeVisible();

  const table = page.getByRole("table");
  await expect(table.getByRole("row", { name: /reference\s+1\.00/ })).toBeVisible();
  await expect(table.getByRole("row", { name: /always_flag\s+0\.25\s+0\.25\s+100%/ })).toBeVisible();
  await expect(table.getByRole("row", { name: /tool_spammer\s+-0\.50\s+n\/a\s+n\/a/ })).toBeVisible();
  expect(problems).toEqual([]);
});
