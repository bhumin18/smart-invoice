import { expect, test, type Page } from "@playwright/test";

const API_BASE = "http://127.0.0.1:5011/api";

async function api(path: string, token = "", init: RequestInit = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });
  const body = await response.json();
  if (!response.ok || body.success === false) {
    throw new Error(body.message || `API failed: ${path}`);
  }
  return body.data;
}

async function loginApi() {
  const data = await api("/auth/login", "", {
    method: "POST",
    body: JSON.stringify({ username: "admin", password: "admin123" }),
  });
  return data.token as string;
}

async function loginUi(page: Page) {
  await page.goto("/");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Admin Login" }).click();
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

async function createInvoice(token: string) {
  return api("/invoices", token, {
    method: "POST",
    body: JSON.stringify({
      client_name: `E2E Client ${Date.now()}`,
      client_gstin: "24ABCDE1234F1Z8",
      client_address: "Ahmedabad, Gujarat",
      date: "2026-05-11",
      due_date: "2026-05-26",
      supply_type: "intrastate",
      status: "sent",
      items: [{ item_name: "E2E Service", quantity: 1, price: 1000, gst_rate: 18 }],
    }),
  });
}

test("login and registration screens work", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Create account" }).click();
  const suffix = Date.now();
  await page.getByLabel("Username").fill(`user${suffix}`);
  await page.getByLabel("Email").fill(`user${suffix}@example.com`);
  await page.getByLabel("Password").fill("secret123");
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByText("Account created")).toBeVisible();
  await loginUi(page);
});

test("invoice form can create a demo invoice", async ({ page }) => {
  await loginUi(page);
  await page.goto("/invoices/new");
  await page.getByRole("button", { name: /fill demo/i }).click();
  await page.getByRole("button", { name: /generate invoice/i }).click();
  await expect(page.getByRole("heading", { name: "Invoice Created" })).toBeVisible();
});

test("invoice detail actions show PDF preview and client link", async ({ page }) => {
  const token = await loginApi();
  const invoice = await createInvoice(token);
  await page.addInitScript((authToken) => localStorage.setItem("smart-invoice-auth-token", authToken), token);
  await page.goto(`/invoices/${invoice.id}`);
  await expect(page.getByText(invoice.invoice_number)).toBeVisible();
  await page.getByRole("button", { name: "Client Link", exact: true }).click();
  await expect(page.getByText(/\/portal\//i)).toBeVisible();
  await page.getByRole("button", { name: /preview/i }).click();
  await expect(page.getByTitle("Invoice PDF Preview")).toBeVisible();
});

test("client portal supports message and payment proof upload", async ({ page }) => {
  const token = await loginApi();
  const invoice = await createInvoice(token);
  const link = await api(`/invoices/${invoice.id}/public-link`, token, {
    method: "POST",
    body: JSON.stringify({ expiry_days: 7 }),
  });
  await page.goto(`/portal/${link.token}`);
  await expect(page.getByText(invoice.invoice_number)).toBeVisible();
  await page.getByPlaceholder(/share payment details/i).fill("Payment will be sent today.");
  await page.getByRole("button", { name: /send message/i }).click();
  await expect(page.getByText("Message sent")).toBeVisible();
  await page.locator("#payment-proof").setInputFiles({
    name: "payment-proof.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n% e2e proof\n"),
  });
  await expect(page.getByText("Payment proof uploaded")).toBeVisible();
});
