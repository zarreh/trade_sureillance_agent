import { test, expect } from "@playwright/test";
import path from "node:path";
import { SUCCESS_INVESTIGATION, mockRun, mockStart, watchConsole } from "./fixtures";

// Captures every page and state in light and dark for the docs
// (`make docs-screenshots`). Reuses the same network mocks as
// investigation.spec.ts so a screenshot cannot drift from what the smoke test
// proves, and fails on any console error. Light files keep their original
// names; dark ones end in `-dark`.
const SCREENSHOTS_DIR = path.join(__dirname, "..", "..", "docs", "assets");
const RUN_LIVE = { name: "Run it live" };

for (const scheme of ["light", "dark"] as const) {
  const suffix = scheme === "dark" ? "-dark" : "";
  const shot = (name: string) => path.join(SCREENSHOTS_DIR, `screenshot-${name}${suffix}.png`);

  test.describe(scheme, () => {
    test.use({ colorScheme: scheme, viewport: { width: 1100, height: 800 } });

    // The theme is class-based and dark by default, so the OS colour scheme alone
    // does not pick it: store the preference the app reads before first paint.
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((value) => localStorage.setItem("theme", value), scheme);
    });

    test("home: the problem, the quiz and the sample cases", async ({ page }) => {
      const problems = watchConsole(page);
      await page.goto("/");
      await page.getByRole("heading", { name: "Explore sample cases" }).waitFor();
      await page.screenshot({ path: shot("home"), fullPage: true });
      expect(problems).toEqual([]);
    });

    test("case: evidence, both investigations and the safeguards", async ({ page }) => {
      const problems = watchConsole(page);
      await page.goto("/cases/blackout-sale");
      await page.getByLabel("Claims check", { exact: true }).waitFor();
      await page.screenshot({ path: shot("case"), fullPage: true });
      expect(problems).toEqual([]);
    });

    test("loading: before the run begins", async ({ page }) => {
      await mockStart(page, "run-loading", 5000);
      await page.goto("/investigate");
      await page.getByRole("button", RUN_LIVE).click();
      await page.getByText("Starting the investigation").waitFor();
      await page.screenshot({ path: shot("loading"), fullPage: true });
    });

    test("running: waiting for the first step", async ({ page }) => {
      await mockStart(page, "run-running");
      await mockRun(page, "run-running", SUCCESS_INVESTIGATION, 5000);
      await page.goto("/investigate");
      await page.getByRole("button", RUN_LIVE).click();
      await page.getByText("Waiting for the first step").waitFor();
      await page.screenshot({ path: shot("running"), fullPage: true });
    });

    test("success: full investigation with the process audit", async ({ page }) => {
      const problems = watchConsole(page);
      await mockStart(page, "run-success");
      await mockRun(page, "run-success", SUCCESS_INVESTIGATION);
      await page.goto("/investigate");
      await page.getByRole("button", RUN_LIVE).click();
      await page.getByLabel("Cost", { exact: true }).waitFor();
      await page.screenshot({ path: shot("success"), fullPage: true });
      expect(problems).toEqual([]);
    });

    test("error: the investigation could not be started", async ({ page }) => {
      await page.route("**/investigations", async (route) => {
        if (route.request().method() !== "POST") return route.fallback();
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Accession 'X' is not in the facts database." }),
        });
      });
      await page.goto("/investigate");
      await page.getByRole("button", RUN_LIVE).click();
      await page.getByRole("alert").filter({ hasText: "facts database" }).waitFor();
      await page.screenshot({ path: shot("error"), fullPage: true });
    });

    test("empty: a completed run with no finding", async ({ page }) => {
      await mockStart(page, "run-empty");
      await mockRun(page, "run-empty", {
        ...SUCCESS_INVESTIGATION,
        id: "run-empty",
        finding_kind: null,
        finding: null,
        costs: [],
        total_cost_usd: 0,
      });
      await page.goto("/investigate");
      await page.getByRole("button", RUN_LIVE).click();
      await page.getByText("produced no finding").waitFor();
      await page.screenshot({ path: shot("empty"), fullPage: true });
    });

    test("evaluation: how we know it works", async ({ page }) => {
      const problems = watchConsole(page);
      await page.goto("/evaluation");
      await page.getByText("Key finding").waitFor();
      await page.screenshot({ path: shot("evaluation"), fullPage: true });
      expect(problems).toEqual([]);
    });
  });
}
