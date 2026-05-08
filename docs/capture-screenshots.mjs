import { chromium } from "../frontend/gst-gem-main/node_modules/playwright/index.mjs";
import fs from "node:fs/promises";
import path from "node:path";

const FRONTEND_URL = process.env.FRONTEND_URL || "http://127.0.0.1:5174";
const API_BASE = process.env.API_BASE || "http://localhost:5000/api";
const USERNAME = process.env.SCREENSHOT_USERNAME || "admin";
const PASSWORD = process.env.SCREENSHOT_PASSWORD || "admin123";
const OUT_DIR = path.resolve("docs/images");

async function api(pathname, token, options = {}) {
  const response = await fetch(`${API_BASE}${pathname}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.json();
  if (!response.ok || body.success === false) {
    throw new Error(body.message || `API failed: ${pathname}`);
  }
  return body.data;
}

async function ensureDemoInvoice(token) {
  const invoices = await api("/invoices", token);
  if (Array.isArray(invoices) && invoices.length > 0) {
    return invoices[0];
  }
  return api("/invoices", token, {
    method: "POST",
    body: JSON.stringify({
      client_name: "Screenshot Demo Client",
      client_gstin: "24ABCDE1234F1Z8",
      client_address: "Ahmedabad, Gujarat",
      date: "2026-05-08",
      due_date: "2026-05-23",
      supply_type: "intrastate",
      status: "sent",
      items: [
        { item_name: "Website Design", quantity: 1, price: 25000, gst_rate: 18 },
        { item_name: "Monthly Support", quantity: 2, price: 3500, gst_rate: 18 },
      ],
    }),
  });
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const login = await api("/auth/login", "", {
    method: "POST",
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  const token = login.token;
  const invoice = await ensureDemoInvoice(token);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 1 });
  await page.addInitScript((authToken) => {
    localStorage.setItem("smart-invoice-auth-token", authToken);
    localStorage.setItem("smart-invoice-theme", "light");
  }, token);

  const shots = [
    ["dashboard.png", "/"],
    ["invoice-form.png", "/invoices/new"],
    ["company-settings.png", "/company"],
    ["users-admin.png", "/users"],
    ["reports-recurring-reminders.png", "/reports"],
  ];

  for (const [file, route] of shots) {
    await page.goto(`${FRONTEND_URL}${route}`, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: true });
  }

  await page.goto(`${FRONTEND_URL}/invoices/${invoice.id}`, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: /preview/i }).click();
  await page.waitForSelector("iframe", { timeout: 15000 });
  await page.screenshot({ path: path.join(OUT_DIR, "invoice-pdf-preview.png"), fullPage: true });

  await browser.close();
  console.log(`Screenshots saved to ${OUT_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
