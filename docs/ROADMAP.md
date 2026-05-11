# Smart Invoice Roadmap

This roadmap tracks the next production and portfolio upgrades. Items marked done are implemented in the current codebase; staged items are intentionally kept visible so the README does not overpromise.

## Highest Value Next

- [ ] Real PostgreSQL migration: replace direct `sqlite3` model helpers with SQLAlchemy repositories, then enable `DATABASE_ENGINE=postgresql`.
- [ ] Live deployment: publish frontend on Vercel/Netlify, backend on Render/Railway, and connect PostgreSQL after the repository migration.
- [x] Demo seed mode: load realistic demo users, company, clients, products, invoices, recurring profile, and PDF output.
- [x] Architecture diagram in README.
- [x] Email verification delivery when SMTP is enabled.
- [ ] Lint/typecheck clean gate in CI after frontend historical typing debt is cleared.

## Product Features

- [x] Client master.
- [x] Product/service master.
- [x] Recurring invoice UI and scheduler hook.
- [x] Payment reminders with history and custom template.
- [x] Client portal with payment proof and messages.
- [x] Attachment uploads.
- [x] Quotation/estimate API with convert-to-invoice flow.
- [x] Expense tracking API with GST input credit fields.
- [ ] Frontend estimate workspace.
- [ ] Frontend expense workspace.
- [ ] Payment gateway links for Razorpay/Stripe.
- [ ] Multi-company profiles per user.
- [ ] Subscription plan limits.

## Security and SaaS

- [x] Multi-user accounts.
- [x] Admin permissions.
- [x] Login rate limiting and lockout.
- [x] Email verification token support.
- [ ] Optional TOTP two-factor authentication.
- [ ] API keys for integrations.
- [ ] Session/device management.
- [ ] Full SaaS subscription enforcement.

## Portfolio Polish

- [x] Real screenshots in README.
- [x] MIT license.
- [x] Docker setup.
- [x] CI backend tests, frontend build, and Playwright E2E.
- [x] OpenAPI JSON and API docs.
- [ ] Short demo video/GIF.
- [ ] Public live demo URL.

