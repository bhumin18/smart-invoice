const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000/api";
const TOKEN_KEY = "smart-invoice-auth-token";

type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  message: string;
  errors?: Record<string, string>;
};

export class ApiError extends Error {
  errors: Record<string, string>;

  constructor(message: string, errors: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.errors = errors;
  }
}

export type InvoiceItem = {
  name: string;
  quantity: number;
  price: number;
  gst: number;
  hsnSac?: string;
  description?: string;
};

export type Invoice = {
  id?: string | number;
  _id?: string;
  invoiceNumber?: string;
  clientName: string;
  clientGSTIN?: string;
  clientAddress?: string;
  date?: string;
  dueDate?: string;
  paymentTerms?: string;
  supplyType?: string;
  placeOfSupply?: string;
  items: InvoiceItem[];
  subtotal?: number;
  gstAmount?: number;
  total?: number;
  amountPaid?: number;
  balanceDue?: number;
  status?: string;
  notes?: string;
  voidReason?: string;
  voidedAt?: string;
  payments?: InvoicePayment[];
  createdAt?: string;
};

export type InvoicePayment = {
  paymentId?: string | number;
  date: string;
  amount: number;
  mode: string;
  reference?: string;
  notes?: string;
  createdAt?: string;
};

export type Company = {
  businessName: string;
  legalName?: string;
  gstin: string;
  pan?: string;
  address: string;
  state?: string;
  phone: string;
  email: string;
  website?: string;
  invoicePrefix?: string;
  nextInvoiceNumber?: number;
  invoiceNumberPadding?: number;
  currencySymbol?: string;
  defaultPaymentTerms?: string;
  logoPath?: string;
  bankName?: string;
  bankAccountName?: string;
  bankAccountNumber?: string;
  bankIfsc?: string;
  upiId?: string;
  termsAndConditions?: string;
  authorizedSignatoryName?: string;
  signaturePath?: string;
};

export type GstReport = {
  rows: Array<{
    invoiceNumber: string;
    clientName: string;
    date: string;
    taxable: number;
    gst: number;
    total: number;
  }>;
  totalSales: number;
  totalGst: number;
};

export type Branding = {
  appName: string;
  developerName: string;
  developerSignature: string;
  developerProfileUrl: string;
};

export type Client = {
  id?: string | number;
  name: string;
  gstin?: string;
  address?: string;
  state?: string;
  phone?: string;
  email?: string;
  notes?: string;
};

export type Product = {
  id?: string | number;
  name: string;
  description?: string;
  hsnSac?: string;
  price: number;
  gstRate: number;
  unit?: string;
  active?: boolean;
};

export type DashboardSummary = {
  invoiceCount: number;
  voidCount: number;
  totalSales: number;
  totalGst: number;
  balanceDue: number;
  paidSales: number;
  recentInvoices: Invoice[];
};

export type AppUser = {
  id?: string | number;
  username: string;
  email?: string;
  role: "admin" | "user";
  active: boolean;
  canCreateInvoices: boolean;
  canManageCompany: boolean;
  canExportData: boolean;
};

function normalizeItem(item: any): InvoiceItem {
  return {
    name: item.item_name ?? item.name ?? "",
    quantity: Number(item.quantity ?? 0),
    price: Number(item.price ?? 0),
    gst: Number(item.gst_rate ?? item.gst ?? 0),
    hsnSac: item.hsn_sac ?? item.hsnSac ?? "",
    description: item.description ?? "",
  };
}

function normalizeInvoice(invoice: any): Invoice {
  return {
    id: invoice.id,
    _id: invoice._id,
    invoiceNumber: invoice.invoice_number ?? invoice.invoiceNumber,
    clientName: invoice.client_name ?? invoice.clientName ?? "",
    clientGSTIN: invoice.client_gstin ?? invoice.clientGSTIN ?? "",
    clientAddress: invoice.client_address ?? invoice.clientAddress ?? "",
    date: invoice.date,
    dueDate: invoice.due_date ?? invoice.dueDate,
    paymentTerms: invoice.payment_terms ?? invoice.paymentTerms ?? "",
    supplyType: invoice.supply_type ?? invoice.supplyType,
    placeOfSupply: invoice.place_of_supply ?? invoice.placeOfSupply,
    items: Array.isArray(invoice.items) ? invoice.items.map(normalizeItem) : [],
    subtotal: Number(invoice.subtotal ?? 0),
    gstAmount: Number(invoice.gst_amount ?? invoice.gstAmount ?? 0),
    total: Number(invoice.total ?? 0),
    amountPaid: Number(invoice.amount_paid ?? invoice.amountPaid ?? 0),
    balanceDue: Number(invoice.balance_due ?? invoice.balanceDue ?? 0),
    status: invoice.status,
    notes: invoice.notes,
    voidReason: invoice.void_reason ?? invoice.voidReason ?? "",
    voidedAt: invoice.voided_at ?? invoice.voidedAt ?? "",
    payments: Array.isArray(invoice.payments)
      ? invoice.payments.map((payment: any) => ({
          paymentId: payment.payment_id ?? payment.paymentId,
          date: payment.date ?? "",
          amount: Number(payment.amount ?? 0),
          mode: payment.mode ?? "",
          reference: payment.reference ?? "",
          notes: payment.notes ?? "",
          createdAt: payment.created_at ?? payment.createdAt ?? "",
        }))
      : [],
    createdAt: invoice.created_at ?? invoice.createdAt,
  };
}

function invoicePayload(invoice: Omit<Invoice, "id">) {
  return {
    invoice_number: invoice.invoiceNumber ?? "",
    client_name: invoice.clientName,
    client_gstin: invoice.clientGSTIN ?? "",
    client_address: invoice.clientAddress ?? "",
    date: invoice.date,
    due_date: invoice.dueDate,
    payment_terms: invoice.paymentTerms ?? "",
    supply_type: invoice.supplyType ?? "intrastate",
    place_of_supply: invoice.placeOfSupply ?? "",
    status: invoice.status ?? "sent",
    notes: invoice.notes ?? "",
    items: invoice.items.map((item) => ({
      item_name: item.name,
      description: item.description ?? "",
      hsn_sac: item.hsnSac ?? "",
      quantity: item.quantity,
      price: item.price,
      gst_rate: item.gst,
    })),
  };
}

function normalizeCompany(company: any): Company {
  return {
    businessName: company.name ?? company.businessName ?? "",
    legalName: company.legal_name ?? company.legalName ?? "",
    gstin: company.gstin ?? "",
    pan: company.pan ?? "",
    address: company.address ?? "",
    state: company.state ?? "",
    phone: company.phone ?? "",
    email: company.email ?? "",
    website: company.website ?? "",
    invoicePrefix: company.invoice_prefix ?? company.invoicePrefix ?? "INV",
    nextInvoiceNumber: Number(company.current_number ?? 0) + 1,
    invoiceNumberPadding: Number(company.invoice_number_padding ?? company.invoiceNumberPadding ?? 4),
    currencySymbol: company.currency_symbol ?? company.currencySymbol ?? "Rs.",
    defaultPaymentTerms: company.default_payment_terms ?? company.defaultPaymentTerms ?? "Due within 15 days",
    logoPath: company.logo_path ?? company.logoPath ?? "",
    bankName: company.bank_name ?? company.bankName ?? "",
    bankAccountName: company.bank_account_name ?? company.bankAccountName ?? "",
    bankAccountNumber: company.bank_account_number ?? company.bankAccountNumber ?? "",
    bankIfsc: company.bank_ifsc ?? company.bankIfsc ?? "",
    upiId: company.upi_id ?? company.upiId ?? "",
    termsAndConditions: company.terms_and_conditions ?? company.termsAndConditions ?? "",
    authorizedSignatoryName: company.authorized_signatory_name ?? company.authorizedSignatoryName ?? "",
    signaturePath: company.signature_path ?? company.signaturePath ?? "",
  };
}

function companyPayload(company: Company) {
  return {
    name: company.businessName,
    legal_name: company.legalName ?? "",
    gstin: company.gstin,
    pan: company.pan ?? "",
    address: company.address,
    state: company.state ?? "",
    phone: company.phone,
    email: company.email,
    website: company.website ?? "",
    invoice_prefix: company.invoicePrefix ?? "INV",
    current_number: Math.max(Number(company.nextInvoiceNumber ?? 1) - 1, 0),
    invoice_number_padding: Number(company.invoiceNumberPadding ?? 4),
    currency_symbol: company.currencySymbol ?? "Rs.",
    default_payment_terms: company.defaultPaymentTerms ?? "",
    logo_path: company.logoPath ?? "",
    bank_name: company.bankName ?? "",
    bank_account_name: company.bankAccountName ?? "",
    bank_account_number: company.bankAccountNumber ?? "",
    bank_ifsc: company.bankIfsc ?? "",
    upi_id: company.upiId ?? "",
    terms_and_conditions: company.termsAndConditions ?? "",
    authorized_signatory_name: company.authorizedSignatoryName ?? "",
    signature_path: company.signaturePath ?? "",
  };
}

function normalizeBranding(branding: any): Branding {
  return {
    appName: branding.app_name ?? branding.appName ?? "",
    developerName: branding.developer_name ?? branding.developerName ?? "",
    developerSignature: branding.developer_signature ?? branding.developerSignature ?? "",
    developerProfileUrl: branding.developer_profile_url ?? branding.developerProfileUrl ?? "",
  };
}

function normalizeClient(client: any): Client {
  return {
    id: client.id,
    name: client.name ?? "",
    gstin: client.gstin ?? "",
    address: client.address ?? "",
    state: client.state ?? "",
    phone: client.phone ?? "",
    email: client.email ?? "",
    notes: client.notes ?? "",
  };
}

function clientPayload(client: Client) {
  return {
    name: client.name,
    gstin: client.gstin ?? "",
    address: client.address ?? "",
    state: client.state ?? "",
    phone: client.phone ?? "",
    email: client.email ?? "",
    notes: client.notes ?? "",
  };
}

function normalizeProduct(product: any): Product {
  return {
    id: product.id,
    name: product.name ?? "",
    description: product.description ?? "",
    hsnSac: product.hsn_sac ?? product.hsnSac ?? "",
    price: Number(product.price ?? 0),
    gstRate: Number(product.gst_rate ?? product.gstRate ?? 0),
    unit: product.unit ?? "",
    active: Boolean(product.active ?? true),
  };
}

function productPayload(product: Product) {
  return {
    name: product.name,
    description: product.description ?? "",
    hsn_sac: product.hsnSac ?? "",
    price: Number(product.price ?? 0),
    gst_rate: Number(product.gstRate ?? 0),
    unit: product.unit ?? "",
    active: product.active ?? true,
  };
}

function normalizeDashboardSummary(summary: any): DashboardSummary {
  return {
    invoiceCount: Number(summary.invoice_count ?? summary.invoiceCount ?? 0),
    voidCount: Number(summary.void_count ?? summary.voidCount ?? 0),
    totalSales: Number(summary.total_sales ?? summary.totalSales ?? 0),
    totalGst: Number(summary.total_gst ?? summary.totalGst ?? 0),
    balanceDue: Number(summary.balance_due ?? summary.balanceDue ?? 0),
    paidSales: Number(summary.paid_sales ?? summary.paidSales ?? 0),
    recentInvoices: Array.isArray(summary.recent_invoices)
      ? summary.recent_invoices.map(normalizeInvoice)
      : [],
  };
}

function normalizeUser(user: any): AppUser {
  return {
    id: user.id,
    username: user.username ?? "",
    email: user.email ?? "",
    role: user.role === "admin" ? "admin" : "user",
    active: Boolean(user.active ?? true),
    canCreateInvoices: Boolean(user.can_create_invoices ?? user.canCreateInvoices ?? true),
    canManageCompany: Boolean(user.can_manage_company ?? user.canManageCompany ?? true),
    canExportData: Boolean(user.can_export_data ?? user.canExportData ?? true),
  };
}

function userPayload(user: AppUser) {
  return {
    role: user.role,
    active: user.active,
    can_create_invoices: user.canCreateInvoices,
    can_manage_company: user.canManageCompany,
    can_export_data: user.canExportData,
  };
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : "";
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
    ...opts,
  });
  const contentType = res.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? ((await res.json()) as ApiEnvelope<T>)
    : null;

  if (!res.ok || body?.success === false) {
    throw new ApiError(
      body?.message || `Request failed (${res.status})`,
      body?.errors || {},
    );
  }

  return (body ? body.data : (await res.text())) as T;
}

async function downloadBlob(path: string, fileName: string) {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : "";
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let message = `Download failed (${res.status})`;
    try {
      const body = await res.json();
      message = body.message || message;
      throw new ApiError(message, body.errors || {});
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(message);
    }
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function blobObjectUrl(path: string) {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_KEY) : "";
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let message = `Preview failed (${res.status})`;
    try {
      const body = await res.json();
      message = body.message || message;
      throw new ApiError(message, body.errors || {});
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(message);
    }
  }
  return URL.createObjectURL(await res.blob());
}

export const api = {
  tokenKey: TOKEN_KEY,
  login: async (username: string, password: string) => {
    const data = await request<{ token: string; user: { username: string }; expires_at: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    localStorage.setItem(TOKEN_KEY, data.token);
    return data;
  },
  register: (username: string, email: string, password: string) =>
    request<{ id: number; username: string; email: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),
  forgotPassword: (identifier: string) =>
    request<{ sent: boolean; reset_token?: string; expires_at?: string; note?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email: identifier, username: identifier }),
    }),
  resetPassword: (token: string, password: string) =>
    request<{ reset: boolean }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ changed: boolean }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
  },
  currentUser: async () => {
    const data = await request<{ user: any }>("/auth/me");
    return { user: normalizeUser(data.user) };
  },
  getBranding: async () => normalizeBranding(await request<any>("/branding")),
  getDashboardSummary: async () =>
    normalizeDashboardSummary(await request<any>("/dashboard/summary")),
  listInvoices: async (filters: Record<string, string> = {}) => {
    const query = new URLSearchParams(
      Object.entries(filters).filter(([, value]) => String(value || "").trim()),
    ).toString();
    const invoices = await request<any[]>(`/invoices${query ? `?${query}` : ""}`);
    return invoices.map(normalizeInvoice);
  },
  getInvoice: async (id: string) => normalizeInvoice(await request<any>(`/invoices/${id}`)),
  createInvoice: async (data: Omit<Invoice, "id">) =>
    normalizeInvoice(
      await request<any>("/invoices", {
        method: "POST",
        body: JSON.stringify(invoicePayload(data)),
      }),
    ),
  updateInvoice: async (id: string, data: Omit<Invoice, "id">) =>
    normalizeInvoice(
      await request<any>(`/invoices/${id}`, {
        method: "PUT",
        body: JSON.stringify(invoicePayload(data)),
      }),
    ),
  deleteInvoice: (id: string) =>
    request<{ id: number }>(`/invoices/${id}`, { method: "DELETE" }),
  voidInvoice: async (id: string, reason: string) =>
    normalizeInvoice(
      await request<any>(`/invoices/${id}/void`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    ),
  cloneInvoice: async (id: string) =>
    normalizeInvoice(
      await request<any>(`/invoices/${id}/clone`, {
        method: "POST",
      }),
    ),
  recordInvoicePayment: async (
    id: string,
    data: { date: string; amount: number; mode: string; reference?: string; notes?: string },
  ) =>
    normalizeInvoice(
      await request<any>(`/invoices/${id}/payments`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    ),
  emailInvoice: (id: string, data: { toEmail: string; subject?: string; message?: string }) =>
    request<{ to_email: string; subject: string; attachment: string }>(`/invoices/${id}/email`, {
      method: "POST",
      body: JSON.stringify({
        to_email: data.toEmail,
        subject: data.subject ?? "",
        message: data.message ?? "",
      }),
    }),
  nextInvoiceNumber: async () => {
    const data = await request<{ invoice_number: string }>("/invoices/next-number");
    return data.invoice_number;
  },
  invoicePdfUrl: (id: string) => `${API_BASE}/invoices/${id}/pdf`,
  previewInvoicePdf: (id: string) => blobObjectUrl(`/invoices/${id}/pdf`),
  downloadInvoicePdf: (id: string, invoiceNumber = "invoice") =>
    downloadBlob(`/invoices/${id}/pdf`, `${invoiceNumber}.pdf`),
  downloadPaymentReceipt: (invoiceId: string, paymentId: string, invoiceNumber = "invoice") =>
    downloadBlob(`/invoices/${invoiceId}/payments/${paymentId}/receipt`, `receipt_${invoiceNumber}_${paymentId}.pdf`),
  gstReport: async (month: number, year: number): Promise<GstReport> => {
    await downloadBlob(`/reports/gst?month=${month}&year=${year}`, `gst_report_${year}_${String(month).padStart(2, "0")}.xlsx`);
    return { rows: [], totalSales: 0, totalGst: 0 };
  },
  getCompany: async () => normalizeCompany(await request<any>("/company")),
  saveCompany: async (data: Company) =>
    normalizeCompany(
      await request<any>("/company", {
        method: "POST",
        body: JSON.stringify(companyPayload(data)),
      }),
    ),
  uploadCompanyLogo: async (file: File) => {
    const body = new FormData();
    body.append("logo", file);
    const res = await fetch(`${API_BASE}/company/logo`, {
      method: "POST",
      headers: localStorage.getItem(TOKEN_KEY)
        ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
        : {},
      body,
    });
    const payload = (await res.json()) as ApiEnvelope<any>;
    if (!res.ok || payload.success === false) {
      throw new ApiError(payload.message || "Logo upload failed", payload.errors || {});
    }
    return normalizeCompany(payload.data);
  },
  uploadCompanySignature: async (file: File) => {
    const body = new FormData();
    body.append("signature", file);
    const res = await fetch(`${API_BASE}/company/signature`, {
      method: "POST",
      headers: localStorage.getItem(TOKEN_KEY)
        ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
        : {},
      body,
    });
    const payload = (await res.json()) as ApiEnvelope<any>;
    if (!res.ok || payload.success === false) {
      throw new ApiError(payload.message || "Signature upload failed", payload.errors || {});
    }
    return normalizeCompany(payload.data);
  },
  listClients: async (search = "") => {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const clients = await request<any[]>(`/clients${query}`);
    return clients.map(normalizeClient);
  },
  createClient: async (data: Client) =>
    normalizeClient(
      await request<any>("/clients", {
        method: "POST",
        body: JSON.stringify(clientPayload(data)),
      }),
    ),
  updateClient: async (id: string, data: Client) =>
    normalizeClient(
      await request<any>(`/clients/${id}`, {
        method: "PUT",
        body: JSON.stringify(clientPayload(data)),
      }),
    ),
  deleteClient: (id: string) => request<{ id: number }>(`/clients/${id}`, { method: "DELETE" }),
  listProducts: async (search = "", activeOnly = false) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (activeOnly) params.set("active_only", "true");
    const query = params.toString();
    const products = await request<any[]>(`/products${query ? `?${query}` : ""}`);
    return products.map(normalizeProduct);
  },
  createProduct: async (data: Product) =>
    normalizeProduct(
      await request<any>("/products", {
        method: "POST",
        body: JSON.stringify(productPayload(data)),
      }),
    ),
  updateProduct: async (id: string, data: Product) =>
    normalizeProduct(
      await request<any>(`/products/${id}`, {
        method: "PUT",
        body: JSON.stringify(productPayload(data)),
      }),
    ),
  deleteProduct: (id: string) => request<{ id: number }>(`/products/${id}`, { method: "DELETE" }),
  listUsers: async () => {
    const users = await request<any[]>("/users");
    return users.map(normalizeUser);
  },
  updateUser: async (id: string, user: AppUser) =>
    normalizeUser(
      await request<any>(`/users/${id}`, {
        method: "PUT",
        body: JSON.stringify(userPayload(user)),
      }),
    ),
  downloadBackup: () => downloadBlob("/backups/export", `smart_invoice_backup_${new Date().toISOString().slice(0, 10)}.zip`),
  downloadDataExport: (format: "xlsx" | "json") =>
    downloadBlob(
      `/exports/data?format=${format}`,
      `smart_invoice_export_${new Date().toISOString().slice(0, 10)}.${format === "json" ? "json" : "xlsx"}`,
    ),
  restoreBackup: async (file: File) => {
    const body = new FormData();
    body.append("backup", file);
    const res = await fetch(`${API_BASE}/backups/restore`, {
      method: "POST",
      headers: localStorage.getItem(TOKEN_KEY)
        ? { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
        : {},
      body,
    });
    const payload = (await res.json()) as ApiEnvelope<any>;
    if (!res.ok || payload.success === false) {
      throw new ApiError(payload.message || "Backup restore failed", payload.errors || {});
    }
    return payload.data;
  },
};

export function formatINR(n: number | undefined | null) {
  const v = Number(n || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(v);
}
