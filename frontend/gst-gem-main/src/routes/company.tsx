import { createFileRoute } from "@tanstack/react-router";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Upload } from "lucide-react";
import { api, type Company } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

export const Route = createFileRoute("/company")({
  component: CompanyPage,
});

const emptyCompany: Company = {
  businessName: "",
  legalName: "",
  gstin: "",
  pan: "",
  address: "",
  state: "",
  phone: "",
  email: "",
  website: "",
  invoicePrefix: "INV",
  nextInvoiceNumber: 1,
  invoiceNumberPadding: 4,
  currencySymbol: "Rs.",
  defaultPaymentTerms: "Due within 15 days",
  logoPath: "",
  bankName: "",
  bankAccountName: "",
  bankAccountNumber: "",
  bankIfsc: "",
  upiId: "",
  termsAndConditions: "",
  authorizedSignatoryName: "",
  signaturePath: "",
};

const demoCompany: Company = {
  businessName: "Bright Ledger Studio",
  legalName: "Bright Ledger Studio Private Limited",
  gstin: "24ABCDE1234F1Z8",
  pan: "ABCDE1234F",
  address: "42, Business Park Road\nAhmedabad\nGujarat - 380015",
  state: "Gujarat",
  phone: "+91 98765 43210",
  email: "billing@brightledger.test",
  website: "www.brightledger.test",
  invoicePrefix: "INV",
  nextInvoiceNumber: 1,
  invoiceNumberPadding: 4,
  currencySymbol: "Rs.",
  defaultPaymentTerms: "Due within 15 days",
  logoPath: "",
  bankName: "HDFC Bank",
  bankAccountName: "Bright Ledger Studio Pvt Ltd",
  bankAccountNumber: "123456789012",
  bankIfsc: "HDFC0001234",
  upiId: "brightledger@upi",
  termsAndConditions: "Please make the payment by the due date.",
  authorizedSignatoryName: "Authorized Signatory",
  signaturePath: "",
};

function CompanyPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["company"], queryFn: api.getCompany });
  const [form, setForm] = useState<Company>(emptyCompany);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (data) setForm({ ...emptyCompany, ...data });
  }, [data]);

  const save = useMutation({
    mutationFn: api.saveCompany,
    onSuccess: () => {
      toast.success("Company settings saved");
      qc.invalidateQueries({ queryKey: ["company"] });
      qc.invalidateQueries({ queryKey: ["next-invoice-number"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const uploadLogo = useMutation({
    mutationFn: api.uploadCompanyLogo,
    onSuccess: (company) => {
      setForm((prev) => ({ ...prev, logoPath: company.logoPath || "" }));
      toast.success("Logo uploaded");
      qc.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const uploadSignature = useMutation({
    mutationFn: api.uploadCompanySignature,
    onSuccess: (company) => {
      setForm((prev) => ({ ...prev, signaturePath: company.signaturePath || "" }));
      toast.success("Authorized signature uploaded");
      qc.invalidateQueries({ queryKey: ["company"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function set<K extends keyof Company>(key: K, value: Company[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const nextErrors: Record<string, string> = {};
    if (!form.businessName.trim()) nextErrors.businessName = "Display name is required";
    if (form.email && !/^\S+@\S+\.\S+$/.test(form.email)) nextErrors.email = "Invalid email";
    if (Number(form.nextInvoiceNumber || 0) < 1) nextErrors.nextInvoiceNumber = "Next sequence must be at least 1";
    if (Number(form.invoiceNumberPadding || 0) < 1) nextErrors.invoiceNumberPadding = "Padding must be at least 1";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    save.mutate(form);
  }

  function useDemoProfile() {
    setForm(demoCompany);
    toast.success("Demo company profile filled. Save when ready.");
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Company Settings</h1>
          <p className="text-muted-foreground mt-1">
            These details appear on invoices, PDFs, GST reports, and invoice numbering.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={useDemoProfile}>
          Use Demo Company Profile
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Business Profile</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                <Field label="Display Name *" error={errors.businessName}>
                  <Input value={form.businessName} onChange={(e) => set("businessName", e.target.value)} />
                </Field>
                <Field label="Legal Name">
                  <Input value={form.legalName || ""} onChange={(e) => set("legalName", e.target.value)} />
                </Field>
              </div>

              <Field label="Business Address">
                <Textarea rows={3} value={form.address} onChange={(e) => set("address", e.target.value)} />
              </Field>

              <div className="grid md:grid-cols-3 gap-4">
                <Field label="GSTIN">
                  <Input value={form.gstin} onChange={(e) => set("gstin", e.target.value)} />
                </Field>
                <Field label="PAN">
                  <Input value={form.pan || ""} onChange={(e) => set("pan", e.target.value)} />
                </Field>
                <Field label="State">
                  <Input value={form.state || ""} onChange={(e) => set("state", e.target.value)} />
                </Field>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <Field label="Email" error={errors.email}>
                  <Input type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
                </Field>
                <Field label="Phone">
                  <Input value={form.phone} onChange={(e) => set("phone", e.target.value)} />
                </Field>
                <Field label="Website">
                  <Input value={form.website || ""} onChange={(e) => set("website", e.target.value)} />
                </Field>
              </div>

              <section className="space-y-4">
                <h2 className="text-lg font-semibold">Invoice Branding</h2>
                <div className="grid md:grid-cols-3 gap-4">
                  <Field label="Invoice Prefix">
                    <Input value={form.invoicePrefix || "INV"} onChange={(e) => set("invoicePrefix", e.target.value)} />
                  </Field>
                  <Field label="Next Sequence Number" error={errors.nextInvoiceNumber}>
                    <Input
                      type="number"
                      min={1}
                      value={form.nextInvoiceNumber || 1}
                      onChange={(e) => set("nextInvoiceNumber", Number(e.target.value))}
                    />
                  </Field>
                  <Field label="Number Padding" error={errors.invoiceNumberPadding}>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={form.invoiceNumberPadding || 4}
                      onChange={(e) => set("invoiceNumberPadding", Number(e.target.value))}
                    />
                  </Field>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <Field label="Currency Symbol">
                    <Input value={form.currencySymbol || "Rs."} onChange={(e) => set("currencySymbol", e.target.value)} />
                  </Field>
                  <Field label="Default Payment Terms">
                    <Input
                      value={form.defaultPaymentTerms || ""}
                      onChange={(e) => set("defaultPaymentTerms", e.target.value)}
                    />
                  </Field>
                </div>

                <div className="grid md:grid-cols-[1fr_auto] gap-4 items-end">
                  <Field label="Logo Path">
                    <Input value={form.logoPath || ""} onChange={(e) => set("logoPath", e.target.value)} />
                  </Field>
                  <div>
                    <Label htmlFor="logo-upload" className="sr-only">Upload Logo</Label>
                    <Input
                      id="logo-upload"
                      type="file"
                      accept="image/png,image/jpeg"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) uploadLogo.mutate(file);
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={uploadLogo.isPending}
                      onClick={() => document.getElementById("logo-upload")?.click()}
                    >
                      <Upload className="h-4 w-4" />
                      {uploadLogo.isPending ? "Uploading..." : "Upload Logo"}
                    </Button>
                  </div>
                </div>
              </section>

              <section className="space-y-4">
                <h2 className="text-lg font-semibold">Payment Details</h2>
                <div className="grid md:grid-cols-2 gap-4">
                  <Field label="Bank Name">
                    <Input value={form.bankName || ""} onChange={(e) => set("bankName", e.target.value)} />
                  </Field>
                  <Field label="Account Name">
                    <Input value={form.bankAccountName || ""} onChange={(e) => set("bankAccountName", e.target.value)} />
                  </Field>
                </div>
                <div className="grid md:grid-cols-3 gap-4">
                  <Field label="Account Number">
                    <Input
                      value={form.bankAccountNumber || ""}
                      onChange={(e) => set("bankAccountNumber", e.target.value)}
                    />
                  </Field>
                  <Field label="IFSC">
                    <Input value={form.bankIfsc || ""} onChange={(e) => set("bankIfsc", e.target.value)} />
                  </Field>
                  <Field label="UPI ID">
                    <Input value={form.upiId || ""} onChange={(e) => set("upiId", e.target.value)} />
                  </Field>
                </div>
                <Field label="Terms and Conditions">
                  <Textarea
                    rows={3}
                    value={form.termsAndConditions || ""}
                    onChange={(e) => set("termsAndConditions", e.target.value)}
                  />
                </Field>
              </section>

              <section className="space-y-4">
                <h2 className="text-lg font-semibold">Authorized Signature</h2>
                <div className="grid md:grid-cols-2 gap-4">
                  <Field label="Authorized Signatory Name">
                    <Input
                      value={form.authorizedSignatoryName || ""}
                      onChange={(e) => set("authorizedSignatoryName", e.target.value)}
                      placeholder="Name printed below signature"
                    />
                  </Field>
                  <Field label="Signature Image Path">
                    <Input
                      value={form.signaturePath || ""}
                      onChange={(e) => set("signaturePath", e.target.value)}
                      placeholder="Upload below or paste local server path"
                    />
                  </Field>
                </div>
                <div>
                  <Label htmlFor="signature-upload" className="sr-only">Upload Signature</Label>
                  <Input
                    id="signature-upload"
                    type="file"
                    accept="image/png,image/jpeg"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) uploadSignature.mutate(file);
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={uploadSignature.isPending}
                    onClick={() => document.getElementById("signature-upload")?.click()}
                  >
                    <Upload className="h-4 w-4" />
                    {uploadSignature.isPending ? "Uploading..." : "Upload Signature Image"}
                  </Button>
                </div>
              </section>

              <div className="flex justify-end">
                <Button type="submit" disabled={save.isPending} className="rounded-full" style={{ boxShadow: "var(--shadow-elegant)" }}>
                  {save.isPending ? "Saving..." : "Save Company Settings"}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
