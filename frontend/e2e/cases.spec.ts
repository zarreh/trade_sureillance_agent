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

  const samples = page.getByLabel("Sample cases", { exact: true });
  await expect(samples.getByRole("heading", { name: /^(Worth an analyst's time|Should not be alarms)$/ })).toHaveText([
    "Worth an analyst's time",
    "Should not be alarms",
  ]);
  await expect(samples.getByRole("link")).toHaveCount(10);
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

const ALL_SLUGS = [
  "blackout-sale",
  "first-large-sale",
  "over-limit-sale",
  "late-filing",
  "planned-sale",
  "tax-withholding",
  "mixed-filing",
  "rolling-volume",
  "amended-filing",
  "ordinary-purchase",
];

for (const slug of ALL_SLUGS) {
  test(`case ${slug}: renders its evidence, both investigations and no console errors`, async ({ page }) => {
    const problems = watchConsole(page);
    await page.goto(`/cases/${slug}`);
    await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
    await expect(page.getByText("A synthetic trade checked against synthetic firm policy")).toBeVisible();
    await expect(page.getByLabel("Outcome", { exact: true })).toContainText("Answer key");
    await expect(page.getByRole("article").first()).toBeVisible();
    await page.getByRole("tab", { name: "Reference investigation" }).click();
    await expect(page.getByLabel("Finding", { exact: true })).toBeVisible();
    expect(problems).toEqual([]);
  });
}

// The wording below is derived from each case's evidence, so these pin the numbers to the data.
const DERIVED_WORDING: [string, string, string][] = [
  ["first-large-sale", "sells 200,000 shares for $1,000,000, with no trading history to compare", "above the 150,000-share level"],
  ["over-limit-sale", "sells $25,000,000 of stock in one trade", "2.5 times the $10,000,000 single-trade limit"],
  ["late-filing", "was reported 10 trading days after the trade", "The Section 16(a) deadline is 2"],
  ["tax-withholding", "$5,000,000 of shares withheld to pay tax", "Code F means shares were withheld"],
  ["rolling-volume", "bringing the last 90 days to $16,000,000", "includes an earlier $14,000,000 trade"],
  ["amended-filing", "files an amendment (Form 4/A) for a $3,000 sale", "Replaced filings are kept on record"],
  ["ordinary-purchase", "Ten Percent Owner buys $10,000 of stock", "The evidence raised no specific concern"],
];
for (const [slug, headline, detail] of DERIVED_WORDING) {
  test(`case ${slug}: wording matches the evidence`, async ({ page }) => {
    await page.goto(`/cases/${slug}`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(headline);
    await expect(page.getByText(detail).first()).toBeVisible();
  });
}

test("case: a late filing says how far past the deadline it was, not just how long it took", async ({ page }) => {
  await page.goto("/cases/late-filing");
  await page.getByRole("tab", { name: "Reference investigation" }).click();
  await expect(page.getByText("Filed 8 trading days late")).toBeVisible();
});

test("case: with no history, it says so instead of inventing a comparison", async ({ page }) => {
  await page.goto("/cases/first-large-sale");
  // The recorded live run answered wrongly and left a claim unsupported, so it must be sent to a human.
  await expect(page.getByLabel("Outcome", { exact: true })).toContainText("Human review required");
  await page.getByRole("tab", { name: "Reference investigation" }).click();
  const history = page.getByLabel("Their own trading history", { exact: true });
  await expect(history).toContainText("No history to compare");
  await expect(history).not.toContainText("×");
});

test("case: previous and next links walk the cases in order", async ({ page }) => {
  await page.goto("/cases/blackout-sale");
  const other = page.getByLabel("Other cases", { exact: true });
  await expect(other.getByRole("link")).toHaveCount(1);
  await other.getByRole("link", { name: /Case 2: Large sale, no history/ }).click();
  await expect(page).toHaveURL(/\/cases\/first-large-sale$/);
  await expect(other.getByRole("link")).toHaveCount(2);
  await expect(other.getByRole("link", { name: /Case 1: Sale just before earnings/ })).toBeVisible();
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 800 } });

  for (const path of ["/", ...ALL_SLUGS.map((s) => `/cases/${s}`)]) {
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
