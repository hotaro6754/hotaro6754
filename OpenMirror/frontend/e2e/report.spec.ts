import { expect, test } from "@playwright/test";
import path from "node:path";

// Fictional sample shipped with the repository: Asha 2,420 messages, Ravi 1,951.
const SAMPLE = path.resolve(__dirname, "../../samples/synthetic-android-pair.txt");

test("upload, read the report, inspect evidence, delete", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /The story behind the messages/ })).toBeVisible();

  // 1–2. Upload a WhatsApp export.
  await page.setInputFiles("[data-testid=file-input]", SAMPLE);
  await expect(page.getByTestId("selected-file")).toHaveText("synthetic-android-pair.txt");
  await page.getByTestId("analyze").click();
  await page.waitForURL(/\/c\/[0-9a-f]+$/);

  // 3. Correct participants and message counts.
  const participants = page.getByTestId("participants");
  await expect(participants).toContainText("Asha");
  await expect(participants).toContainText("2,420");
  await expect(participants).toContainText("Ravi");
  await expect(participants).toContainText("1,951");

  // 4. Analytics are present.
  await expect(page.getByTestId("chapter-dynamics")).toContainText("Who started each month’s conversations");
  await expect(page.getByTestId("topic-table")).toContainText("trip");

  // 5–6. Open a finding and inspect its supporting messages and counterexamples.
  await page.locator('[data-finding-id="F-DY-initiation"]').click();
  const drawer = page.getByTestId("evidence-drawer");
  await expect(drawer).toContainText("Who starts conversations");
  await expect(drawer).toContainText("Supporting messages");
  await expect(drawer).toContainText("Against this");
  expect(await drawer.getByTestId("evidence-message").count()).toBeGreaterThan(5);
  await drawer.getByTestId("show-context").first().click();
  await expect(drawer.locator(".bg-highlight")).toHaveCount(1);
  await page.keyboard.press("Escape");

  // Full-text search reaches the stored messages.
  await page.getByTestId("search-input").fill("goa");
  await page.getByTestId("search-input").press("Enter");
  await expect(page.getByTestId("message-browser")).toContainText(/messages/);
  await page.keyboard.press("Escape");

  // 7. Delete the conversation and everything derived from it.
  await page.goto("/");
  await expect(page.getByTestId("conversation-list")).toContainText("synthetic-android-pair");
  await page.getByTestId("delete-conversation").click();
  await page.getByTestId("confirm-delete").click();
  await expect(page.getByText("Nothing here yet")).toBeVisible();
});

test("rejects a file that is not a WhatsApp export", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles("[data-testid=file-input]", {
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("shopping list\nmilk\n"),
  });
  await page.getByTestId("analyze").click();
  await expect(page.getByTestId("upload-error")).toContainText("WhatsApp");
});
