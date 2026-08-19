import { test } from "@playwright/test";
import path from "node:path";
import { SUCCESS_INVESTIGATION, sseBody } from "./fixtures";

// Captures the screenshots docs/how-it-works/the-investigation.md embeds.
// Reuses the exact same network mocks as investigation.spec.ts so a
// screenshot can never silently drift from what the smoke test actually
// proves the UI does (`make docs-screenshots`).
const SCREENSHOTS_DIR = path.join(__dirname, "..", "..", "docs", "assets");

test("capture: success — trace, grounding status, and evidence panel", async ({ page }) => {
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
  await page.getByLabel("Finding").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-success.png"),
    fullPage: true,
  });
});

test("capture: loading — before the run begins", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await new Promise((resolve) => setTimeout(resolve, 5000));
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ id: "run-loading", status: "running" }),
    });
  });

  await page.goto("/");
  await page.getByText("Starting the investigation").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-loading.png"),
    fullPage: true,
  });
});

test("capture: error — the investigation could not be started", async ({ page }) => {
  await page.route("**/investigations", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({ status: 500, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  await page.getByText("Could not start the investigation").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-error.png"),
    fullPage: true,
  });
});

test("capture: empty — a completed run with no finding", async ({ page }) => {
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
  await page.getByText("produced no finding").waitFor();
  await page.screenshot({
    path: path.join(SCREENSHOTS_DIR, "screenshot-empty.png"),
    fullPage: true,
  });
});
