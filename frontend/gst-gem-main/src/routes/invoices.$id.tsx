import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, formatINR, type Invoice, type InvoiceItem } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ArrowLeft, Copy, Download, Eye, Mail, Pencil, Plus, Receipt, Save, Trash2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export const Route = createFileRoute("/invoices/$id")({
  component: InvoiceDetail,
});

type Row = InvoiceItem;

function emptyRow(): Row {
  return { name: "", hsnSac: "", description: "", quantity: 1, price: 0, gst: 18 };
}

function statusVariant(status?: string) {
  return status === "paid" ? "default" : "secondary";
}

function InvoiceDetail() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: inv, isLoading, error } = useQuery({
    queryKey: ["invoice", id],
    queryFn: () => api.getInvoice(id),
  });
  const [isEditing, setIsEditing] = useState(false);
  const [voidReason, setVoidReason] = useState("");
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10));
  const [paymentAmount, setPaymentAmount] = useState(0);
  const [paymentMode, setPaymentMode] = useState("Bank Transfer");
  const [paymentReference, setPaymentReference] = useState("");
  const [paymentNotes, setPaymentNotes] = useState("");
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailMessage, setEmailMessage] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [form, setForm] = useState<Invoice>({
    clientName: "",
    items: [emptyRow()],
    invoiceNumber: "",
    clientGSTIN: "",
    clientAddress: "",
    date: "",
    dueDate: "",
    paymentTerms: "",
    supplyType: "intrastate",
    placeOfSupply: "",
    status: "sent",
    notes: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!inv) return;
    setForm({
      ...inv,
      items: inv.items?.length ? inv.items : [emptyRow()],
    });
    setPaymentAmount(Number(inv.balanceDue ?? inv.total ?? 0));
    setEmailSubject(`Invoice ${inv.invoiceNumber || ""}`);
    setEmailMessage(`Dear ${inv.clientName},\n\nPlease find attached invoice ${inv.invoiceNumber || ""}.\n\nThank you.`);
  }, [inv]);

  const updateInvoice = useMutation({
    mutationFn: (data: Omit<Invoice, "id">) => api.updateInvoice(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(["invoice", id], updated);
      qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice updated");
      setIsEditing(false);
    },
    onError: handleApiError,
  });

  const deleteInvoice = useMutation({
    mutationFn: api.deleteInvoice,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice deleted");
      navigate({ to: "/invoices" });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cloneInvoice = useMutation({
    mutationFn: api.cloneInvoice,
    onSuccess: async (cloned) => {
      await qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success(`Cloned as ${cloned.invoiceNumber}`);
      navigate({ to: "/invoices/$id", params: { id: String(cloned.id ?? "") } });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const voidInvoice = useMutation({
    mutationFn: () => api.voidInvoice(id, voidReason),
    onSuccess: (updated) => {
      qc.setQueryData(["invoice", id], updated);
      qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice voided");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const recordPayment = useMutation({
    mutationFn: () =>
      api.recordInvoicePayment(id, {
        date: paymentDate,
        amount: paymentAmount,
        mode: paymentMode,
        reference: paymentReference,
        notes: paymentNotes,
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["invoice", id], updated);
      qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Payment recorded");
      setPaymentReference("");
      setPaymentNotes("");
    },
    onError: handleApiError,
  });

  const emailInvoice = useMutation({
    mutationFn: () => api.emailInvoice(id, { toEmail: emailTo, subject: emailSubject, message: emailMessage }),
    onSuccess: () => {
      toast.success("Invoice email sent");
      setEmailOpen(false);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  async function openPreview() {
    try {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const url = await api.previewInvoicePdf(id);
      setPreviewUrl(url);
      setPreviewOpen(true);
    } catch (previewError) {
      toast.error(previewError instanceof Error ? previewError.message : "Preview failed");
    }
  }

  function handleApiError(e: Error) {
    if (e instanceof ApiError) {
      setErrors(e.errors);
    }
    toast.error(e.message);
  }

  function set<K extends keyof Invoice>(key: K, value: Invoice[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateItem(index: number, patch: Partial<Row>) {
    setForm((prev) => ({
      ...prev,
      items: (prev.items || []).map((item, idx) => (idx === index ? { ...item, ...patch } : item)),
    }));
  }

  function validate() {
    const nextErrors: Record<string, string> = {};
    if (!String(form.invoiceNumber || "").trim()) nextErrors.invoice_number = "Invoice number is required";
    if (!String(form.clientName || "").trim()) nextErrors.client_name = "Client name is required";
    if (!(form.items || []).length) nextErrors.items = "At least one item is required";
    (form.items || []).forEach((item, index) => {
      if (!item.name.trim()) nextErrors[`items[${index}].item_name`] = "Item name is required";
      if (Number(item.quantity || 0) <= 0) nextErrors[`items[${index}].quantity`] = "Quantity must be greater than zero";
      if (Number(item.price || 0) < 0) nextErrors[`items[${index}].price`] = "Price must be zero or more";
      if (Number(item.gst || 0) < 0 || Number(item.gst || 0) > 28) nextErrors[`items[${index}].gst_rate`] = "GST must be between 0 and 28";
    });
    return nextErrors;
  }

  function submitEdit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    updateInvoice.mutate(form as Omit<Invoice, "id">);
  }

  const subtotal = (form.items || []).reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.price || 0), 0);
  const gstAmount = (form.items || []).reduce(
    (sum, item) => sum + (Number(item.quantity || 0) * Number(item.price || 0) * Number(item.gst || 0)) / 100,
    0,
  );
  const total = subtotal + gstAmount;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <Button asChild variant="ghost">
          <Link to="/invoices">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
        </Button>
        {inv && (
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              onClick={() => setIsEditing((current) => !current)}
              disabled={String(inv.status || "").toLowerCase() === "void"}
            >
              <Pencil className="h-4 w-4" /> {isEditing ? "Cancel Edit" : "Edit Invoice"}
            </Button>
            <Button variant="outline" onClick={() => cloneInvoice.mutate(id)} disabled={cloneInvoice.isPending}>
              <Copy className="h-4 w-4" /> Clone
            </Button>
            <Button
              onClick={() =>
                api.downloadInvoicePdf(id, inv.invoiceNumber || "invoice").catch((downloadError: Error) => {
                  toast.error(downloadError.message);
                })
              }
            >
              <Download className="h-4 w-4" /> Download PDF
            </Button>
            <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" onClick={openPreview}>
                  <Eye className="h-4 w-4" /> Preview
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-5xl">
                <DialogHeader>
                  <DialogTitle>Invoice PDF Preview</DialogTitle>
                </DialogHeader>
                {previewUrl ? (
                  <iframe title="Invoice PDF Preview" src={previewUrl} className="h-[75vh] w-full rounded-md border" />
                ) : (
                  <div className="flex h-[75vh] items-center justify-center text-sm text-muted-foreground">
                    Loading preview...
                  </div>
                )}
              </DialogContent>
            </Dialog>
            <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <Mail className="h-4 w-4" /> Email
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Email Invoice</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <Field label="To Email">
                    <Input type="email" value={emailTo} onChange={(e) => setEmailTo(e.target.value)} placeholder="client@example.com" />
                  </Field>
                  <Field label="Subject">
                    <Input value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} />
                  </Field>
                  <Field label="Message">
                    <Textarea rows={6} value={emailMessage} onChange={(e) => setEmailMessage(e.target.value)} />
                  </Field>
                  <p className="text-xs text-muted-foreground">
                    Email must be enabled in backend/config.yaml under the email section.
                  </p>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setEmailOpen(false)}>Cancel</Button>
                  <Button onClick={() => emailInvoice.mutate()} disabled={emailInvoice.isPending}>
                    {emailInvoice.isPending ? "Sending..." : "Send Email"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="py-4 text-sm text-destructive">{(error as Error).message}</CardContent>
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-96 w-full rounded-xl" />
      ) : inv ? (
        <>
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <CardTitle className="text-2xl">{inv.invoiceNumber || `#${id.slice(-6)}`}</CardTitle>
                  <p className="text-muted-foreground mt-1">
                    Invoice date: {inv.date ? new Date(inv.date).toLocaleDateString("en-IN") : ""}
                  </p>
                </div>
                <Badge variant={statusVariant(inv.status)}>{inv.status || "pending"}</Badge>
              </div>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Metric label="Subtotal" value={formatINR(inv.subtotal)} />
              <Metric label="GST" value={formatINR(inv.gstAmount)} />
              <Metric label="Total" value={formatINR(inv.total)} />
              <Metric label="Balance Due" value={formatINR(inv.balanceDue ?? inv.total)} />
            </CardContent>
          </Card>

          {String(inv.status || "").toLowerCase() === "void" && (
            <Card className="border-amber-300 bg-amber-50">
              <CardContent className="py-4 text-sm text-amber-900">
                This invoice is void{inv.voidReason ? `: ${inv.voidReason}` : "."}
              </CardContent>
            </Card>
          )}

          {isEditing ? (
            <form onSubmit={submitEdit} className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Edit Invoice</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Field label="Invoice Number">
                    <Input value={form.invoiceNumber || ""} onChange={(e) => set("invoiceNumber", e.target.value)} />
                    {errors.invoice_number && <ErrorText message={errors.invoice_number} />}
                  </Field>
                  <Field label="Invoice Date">
                    <Input type="date" value={form.date || ""} onChange={(e) => set("date", e.target.value)} />
                  </Field>
                  <Field label="Due Date">
                    <Input type="date" value={form.dueDate || ""} onChange={(e) => set("dueDate", e.target.value)} />
                  </Field>
                  <Field label="Client Name">
                    <Input value={form.clientName || ""} onChange={(e) => set("clientName", e.target.value)} />
                    {errors.client_name && <ErrorText message={errors.client_name} />}
                  </Field>
                  <Field label="Client GSTIN">
                    <Input value={form.clientGSTIN || ""} onChange={(e) => set("clientGSTIN", e.target.value)} />
                  </Field>
                  <Field label="Payment Terms">
                    <Input value={form.paymentTerms || ""} onChange={(e) => set("paymentTerms", e.target.value)} />
                  </Field>
                  <Field label="Place of Supply">
                    <Input value={form.placeOfSupply || ""} onChange={(e) => set("placeOfSupply", e.target.value)} />
                  </Field>
                  <Field label="Supply Type">
                    <select
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      value={form.supplyType || "intrastate"}
                      onChange={(e) => set("supplyType", e.target.value)}
                    >
                      <option value="intrastate">Intrastate</option>
                      <option value="interstate">Interstate</option>
                    </select>
                  </Field>
                  <Field label="Status">
                    <select
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      value={form.status || "sent"}
                      onChange={(e) => set("status", e.target.value)}
                    >
                      <option value="draft">Draft</option>
                      <option value="sent">Sent</option>
                      <option value="paid">Paid</option>
                      <option value="overdue">Overdue</option>
                    </select>
                  </Field>
                  <div className="md:col-span-3">
                    <Field label="Client Address">
                      <Textarea rows={3} value={form.clientAddress || ""} onChange={(e) => set("clientAddress", e.target.value)} />
                    </Field>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Items</CardTitle>
                  <Button type="button" variant="outline" size="sm" onClick={() => set("items", [...(form.items || []), emptyRow()])}>
                    <Plus className="h-4 w-4" /> Add Item
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {errors.items && <ErrorText message={errors.items} />}
                  {(form.items || []).map((item, index) => (
                    <div key={index} className="rounded-lg border p-3 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start">
                        <div className="md:col-span-4">
                          <Input value={item.name} onChange={(e) => updateItem(index, { name: e.target.value })} placeholder="Item name" />
                          {errors[`items[${index}].item_name`] && <ErrorText message={errors[`items[${index}].item_name`]} />}
                        </div>
                        <div className="md:col-span-2">
                          <Input value={item.hsnSac || ""} onChange={(e) => updateItem(index, { hsnSac: e.target.value })} placeholder="HSN/SAC" />
                        </div>
                        <div className="md:col-span-2">
                          <Input type="number" min={0} step="0.01" value={item.quantity} onChange={(e) => updateItem(index, { quantity: Number(e.target.value) })} />
                          {errors[`items[${index}].quantity`] && <ErrorText message={errors[`items[${index}].quantity`]} />}
                        </div>
                        <div className="md:col-span-2">
                          <Input type="number" min={0} step="0.01" value={item.price} onChange={(e) => updateItem(index, { price: Number(e.target.value) })} />
                          {errors[`items[${index}].price`] && <ErrorText message={errors[`items[${index}].price`]} />}
                        </div>
                        <div className="md:col-span-1">
                          <Input type="number" min={0} max={28} step="0.01" value={item.gst} onChange={(e) => updateItem(index, { gst: Number(e.target.value) })} />
                          {errors[`items[${index}].gst_rate`] && <ErrorText message={errors[`items[${index}].gst_rate`]} />}
                        </div>
                        <Button
                          type="button"
                          size="icon"
                          variant="ghost"
                          className="text-destructive"
                          onClick={() => set("items", (form.items || []).filter((_, idx) => idx !== index))}
                          disabled={(form.items || []).length === 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <Textarea rows={2} value={item.description || ""} onChange={(e) => updateItem(index, { description: e.target.value })} placeholder="Optional item description" />
                    </div>
                  ))}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Metric label="Subtotal" value={formatINR(subtotal)} />
                    <Metric label="GST" value={formatINR(gstAmount)} />
                    <Metric label="Total" value={formatINR(total)} />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <Textarea rows={3} value={form.notes || ""} onChange={(e) => set("notes", e.target.value)} />
                </CardContent>
              </Card>

              <div className="flex justify-end">
                <Button type="submit" disabled={updateInvoice.isPending}>
                  <Save className="h-4 w-4" /> {updateInvoice.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Invoice Details</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <div className="text-xs uppercase text-muted-foreground mb-1">Bill To</div>
                    <div className="font-semibold">{inv.clientName}</div>
                    {inv.clientGSTIN && <div className="text-sm text-muted-foreground">GSTIN: {inv.clientGSTIN}</div>}
                    {inv.clientAddress && <div className="mt-2 whitespace-pre-line text-sm text-muted-foreground">{inv.clientAddress}</div>}
                  </div>
                  <div className="space-y-2 text-sm">
                    <DetailRow label="Invoice Date" value={inv.date || "-"} />
                    <DetailRow label="Due Date" value={inv.dueDate || "-"} />
                    <DetailRow label="Payment Terms" value={inv.paymentTerms || "-"} />
                    <DetailRow label="Supply Type" value={inv.supplyType || "-"} />
                    <DetailRow label="Place of Supply" value={inv.placeOfSupply || "-"} />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground whitespace-pre-line">
                  {inv.notes || "No notes added."}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Items</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Item</TableHead>
                        <TableHead className="text-right">Qty</TableHead>
                        <TableHead className="text-right">Price</TableHead>
                        <TableHead className="text-right">GST %</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(inv.items || []).map((item, index) => {
                        const taxable = Number(item.quantity || 0) * Number(item.price || 0);
                        const tax = (taxable * Number(item.gst || 0)) / 100;
                        return (
                          <TableRow key={index}>
                            <TableCell>
                              <div className="font-medium">{item.name}</div>
                              {item.description && <div className="text-xs text-muted-foreground mt-1">{item.description}</div>}
                            </TableCell>
                            <TableCell className="text-right">{item.quantity}</TableCell>
                            <TableCell className="text-right">{formatINR(item.price)}</TableCell>
                            <TableCell className="text-right">{item.gst}%</TableCell>
                            <TableCell className="text-right">{formatINR(taxable + tax)}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Payments</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {(inv.payments || []).length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Mode</TableHead>
                      <TableHead>Reference</TableHead>
                      <TableHead className="text-right">Amount</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(inv.payments || []).map((payment, index) => (
                      <TableRow key={String(payment.paymentId || index)}>
                        <TableCell>{payment.date}</TableCell>
                        <TableCell>{payment.mode}</TableCell>
                        <TableCell>{payment.reference || "-"}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <span>{formatINR(payment.amount)}</span>
                            {payment.paymentId && (
                              <Button
                                size="icon"
                                variant="ghost"
                                title="Download receipt"
                                onClick={() =>
                                  api
                                    .downloadPaymentReceipt(id, String(payment.paymentId), inv.invoiceNumber || "invoice")
                                    .catch((receiptError: Error) => toast.error(receiptError.message))
                                }
                              >
                                <Receipt className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">No payments recorded yet.</p>
              )}

              {String(inv.status || "").toLowerCase() !== "void" && (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
                  <Field label="Payment Amount">
                    <Input type="number" min={0} step="0.01" value={paymentAmount} onChange={(e) => setPaymentAmount(Number(e.target.value))} />
                  </Field>
                  <Field label="Payment Date">
                    <Input type="date" value={paymentDate} onChange={(e) => setPaymentDate(e.target.value)} />
                  </Field>
                  <Field label="Mode">
                    <select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={paymentMode} onChange={(e) => setPaymentMode(e.target.value)}>
                      <option>Bank Transfer</option>
                      <option>UPI</option>
                      <option>Cash</option>
                      <option>Cheque</option>
                      <option>Card</option>
                      <option>Other</option>
                    </select>
                  </Field>
                  <Field label="Reference">
                    <Input value={paymentReference} onChange={(e) => setPaymentReference(e.target.value)} />
                  </Field>
                  <Button onClick={() => recordPayment.mutate()} disabled={recordPayment.isPending}>
                    Record Payment
                  </Button>
                </div>
              )}
              {String(inv.status || "").toLowerCase() !== "void" && (
                <Field label="Payment Notes">
                  <Textarea rows={2} value={paymentNotes} onChange={(e) => setPaymentNotes(e.target.value)} />
                </Field>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" disabled={String(inv.status || "").toLowerCase() === "void"}>
                    Void Invoice
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Void this invoice?</AlertDialogTitle>
                    <AlertDialogDescription>
                      The invoice will stay in the system, but it will be marked void and excluded from GST reports.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <div className="space-y-2">
                    <Label htmlFor="void-reason">Void reason</Label>
                    <Input id="void-reason" value={voidReason} onChange={(e) => setVoidReason(e.target.value)} placeholder="Optional reason" />
                  </div>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={() => voidInvoice.mutate()}>
                      Confirm Void
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>

              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    Delete Invoice
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete this invoice?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This permanently removes the invoice and its payments.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={() => deleteInvoice.mutate(id)} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}

function ErrorText({ message }: { message: string }) {
  return <p className="text-xs text-destructive mt-1">{message}</p>;
}
