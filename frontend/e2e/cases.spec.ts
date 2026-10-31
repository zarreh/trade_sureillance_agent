import { test, expect, type Locator } from "@playwright/test";
import { watchConsole } from "./fixtures";

// The home page and the sample case pages render from the committed
// cases.json, so none of this needs the API, a live model, or any network mock.

function option(quiz: Locator, name: string) {
  return quiz.locator("label", { hasText: new RegExp(`^${name}$`) });
}

test("home: states the problem, lets you try it, and links every sample case", async ({ page }) => {
  const problems = watchConsole(page);
  const apiCalls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/investigations")) apiCalls.push(request.url());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Which insider trades deserve an investigation?"
  );

  const quiz = page.getByLabel("Spot the difference", { exact: true });
  await expect(quiz).toContainText("Filing A");
  await expect(quiz).toContainText("Filing B");
  // What separates the two filings stays hidden until the visitor answers.
  await expect(quiz).not.toContainText("Rule 10b5-1");

  await option(quiz, "Only filing B").click();
  await expect(quiz).toContainText("That matches the answer key.");
  await expect(quiz).toContainText("Rule 10b5-1 plan");
  await expect(quiz.getByRole("link", { name: /Same sale, pre-arranged plan/ })).toBeVisible();

  await option(quiz, "Both").click();
  await expect(quiz).toContainText("The answer key differs.");
  await quiz.getByRole("button", { name: "Try again" }).click();
  await expect(quiz).not.toContainText("The answer key differs.");

  const failures = page.getByLabel("Three ways surveillance goes wrong", { exact: true });
  await expect(failures.getByRole("heading", { level: 3 })).toHaveText([
    "Crying wolf",
    "One excuse covering everything",
    "Confident but unsupported",
  ]);
  await expect(failures).toContainText("claims were judged unsupported");

  await expect(page.getByLabel("Sample cases", { exact: true }).getByRole("link")).toHaveCount(3);
  await expect(page.getByRole("region", { name: "How it works" })).toBeVisible();
  expect(apiCalls).toEqual([]);
  expect(problems).toEqual([]);
});

test("home: the quiz can be answered with the keyboard alone", async ({ page }) => {
  await page.goto("/");
  const quiz = page.getByLabel("Spot the difference", { exact: true });
  await quiz.getByRole("radio", { name: "Only filing B" }).focus();
  await page.keyboard.press("Space");
  await expect(quiz).toContainText("That matches the answer key.");
});

test("case: a pre-earnings sale shows the evidence, both investigations, and links claims to evidence", async ({
  page,
}) => {
  const problems = watchConsole(page);
  await page.goto("/cases/blackout-sale");

  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "sells $400,000 of stock 2 days before earnings"
  );
  await expect(page.getByText("A synthetic trade checked against synthetic firm policy")).toBeVisible();

  const outcome = page.getByLabel("Outcome", { exact: true });
  await expect(outcome).toContainText("Answer key");
  await expect(outcome).toContainText("Differs from the answer key");
  await expect(outcome).toContainText("Human review required");

  // The AI run is the default view, and it shows its unverified claims plainly.
  const aiTab = page.getByRole("tab", { name: "What the AI investigator did" });
  await expect(aiTab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByLabel("Claims check", { exact: true })).toContainText("Cites no evidence");
  await expect(page.getByText("human review required").first()).toBeVisible();

  const timeline = page.getByLabel("Was news about to come out?", { exact: true }).first();
  await expect(timeline).toContainText("The blackout runs Jul 10, 2025 to Jul 22, 2025");
  await timeline.getByText("View source result").click();
  await expect(timeline).toContainText('"in_blackout": true');

  // Arrow keys move between the two investigations.
  await aiTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Reference investigation" })).toHaveAttribute(
    "aria-selected",
    "true"
  );
  await expect(page.getByLabel("Finding", { exact: true })).toContainText("blackout window");

  // A citation in the reference run jumps to the evidence card it names.
  await page
    .getByLabel("Claims check", { exact: true })
    .getByRole("link", { name: "call_get_transaction_details" })
    .click();
  await expect(page).toHaveURL(/#evidence-call_get_transaction_details$/);
  await expect(page.locator("#evidence-call_get_transaction_details")).toBeInViewport();
  expect(problems).toEqual([]);
});

test("case: the same sale under a reported plan reads as a plan, not as an absence of one", async ({
  page,
}) => {
  await page.goto("/cases/planned-sale");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("sells $400,000 of stock");
  await expect(page.getByText("The filing reports the sale was made under a Rule 10b5-1 plan")).toBeVisible();

  await page.getByRole("tab", { name: "Reference investigation" }).click();
  await expect(page.getByLabel("The trade as filed", { exact: true })).toContainText(
    "Reported under a 10b5-1 plan"
  );
  await expect(page.getByRole("link", { name: "Sale just before earnings" })).toBeVisible();
});

test("case: an exempt tax line does not hide a very large sale in the same filing", async ({ page }) => {
  await page.goto("/cases/mixed-filing");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "$60,000,000 sale next to a $30,000 tax withholding"
  );
  await expect(page.getByText("6 times the $10,000,000 single-trade limit")).toBeVisible();

  await page.getByRole("tab", { name: "Reference investigation" }).click();
  const filed = page.getByLabel("The trade as filed", { exact: true });
  await expect(filed).toContainText("Shares withheld for tax");
  await expect(filed).toContainText("Sale");
});

test("case: an unknown case is a 404", async ({ page }) => {
  const response = await page.goto("/cases/does-not-exist");
  expect(response?.status()).toBe(404);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 800 } });

  for (const path of ["/", "/cases/blackout-sale", "/cases/mixed-filing"]) {
    test(`${path} does not scroll sideways`, async ({ page }) => {
      await page.goto(path);
      await page.getByRole("heading", { level: 1 }).waitFor();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      );
      expect(overflow).toBeLessThanOrEqual(1);
    });
  }
});
