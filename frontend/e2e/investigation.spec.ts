import { test, expect } from "@playwright/test";
import { SUCCESS_INVESTIGATION, sseBody } from "./fixtures";

// All four states an investigation can render (docs/PLAN.md §7 Phase 6: "Tested
// loading, success, empty and error states"). The backend is fully mocked at
// the network layer — no live LLM or Python process needed to run this.

test("loading: shows a starting message before the run begins", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 1000));
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id: "run-loading", status: "running" }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("Starting the investigation")).toBeVisible();
});

test("success: renders the trace, the grounding status, and clickable evidence", async ({
  page,
}) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id: "run-success", status: "running" }),
    });
  });
  await page.route("**/investigations/run-success/events", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody({ status: "completed", finding: SUCCESS_INVESTIGATION.finding }),
    });
  });
  await page.route("**/investigations/run-success", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(SUCCESS_INVESTIGATION),
    });
  });

  await page.goto("/");
  await expect(page.getByLabel("Investigation trace")).toBeVisible();
  await expect(page.getByLabel("Finding")).toBeVisible();
  await expect(page.getByText("flag")).toBeVisible();
  await expect(page.getByText("1/1 claims supported")).toBeVisible();
  await expect(page.getByLabel("Cost")).toBeVisible();
  await expect(page.getByText("$0.0021")).toBeVisible();
  // The 10b5-1 tri-state renders as "not established", never as "no plan".
  await expect(page.getByText("not established")).toBeVisible();
});

test("empty: renders a defensive message when a completed run has no finding", async ({
  page,
}) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id: "run-empty", status: "running" }),
    });
  });
  await page.route("**/investigations/run-empty/events", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody({ status: "completed", finding: null }),
    });
  });
  await page.route("**/investigations/run-empty", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...SUCCESS_INVESTIGATION,
        id: "run-empty",
        finding_kind: null,
        finding: null,
        costs: [],
        total_cost_usd: 0,
      }),
    });
  });

  await page.goto("/");
  await expect(page.getByText("produced no finding")).toBeVisible();
});

test("error: renders an alert when the investigation cannot be started", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  await expect(page.getByText("Could not start the investigation")).toBeVisible();
});
