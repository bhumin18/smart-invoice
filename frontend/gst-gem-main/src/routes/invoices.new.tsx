import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api, formatINR, type Client, type Invoice, type InvoiceItem, type Product } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2, Download, CheckCircle2, Wand2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/invoices/new")({
  component: NewInvoice,
});

type Row = InvoiceItem;

function today() {
  return new Date().toISOString().slice(0, 10);
}

function addDays(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function emptyRow(): Row {
  return { name: "", hsnSac: "", description: "", quantity: 1, price: 0, gst: 18 };
}

function demoRows(): Row[] {
  return [
    {
      name: "Website design and landing page setup",
      hsnSac: "9983",
      description: "One-time design and implementation service",
      quantity: 1,
      price: 25000,
      gst: 18,
    },
    {
      name: "Monthly SEO and analytics support",
      hsnSac: "9983",
      description: "Search optimization, analytics review, and reporting",
      quantity: 2,
      price: 7500,
      gst: 18,
    },
    {
      name: "Domain consultation",
      hsnSac: "9983",
      description: "Technical consulting and purchase guidance",
      quantity: 1,
      price: 3500,
      gst: 5,
    },
  ];
}

function NewInvoice() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: company } = useQuery({
    queryKey: ["company"],
    queryFn: api.getCompany,
  });
  const { data: suggestedInvoiceNumber } = useQuery({
    queryKey: ["next-invoice-number"],
    queryFn: api.nextInvoiceNumber,
  });
  const { data: clients = [] } = useQuery({
    queryKey: ["clients"],
    queryFn: () => api.listClients(),
  });
  const { data: products = [] } = useQuery({
    queryKey: ["products", "active"],
    queryFn: () => api.listProducts("", true),
  });
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [invoiceDate, setInvoiceDate] = useState(today());
  const [dueDate, setDueDate] = useState(addDays(15));
  const [status, setStatus] = useState("sent");
  const [paymentTerms, setPaymentTerms] = useState("Due within 15 days");
  const [supplyType, setSupplyType] = useState("intrastate");
  const [placeOfSupply, setPlaceOfSupply] = useState("Gujarat");
  const [clientName, setClientName] = useState("");
  const [clientGSTIN, setClientGSTIN] = useState("");
  const [clientAddress, setClientAddress] = useState("");
  const [notes, setNotes] = useState("Thanks for your business.");
  const [items, setItems] = useState<Row[]>([emptyRow()]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [createdInvoice, setCreatedInvoice] = useState<Invoice | null>(null);

  useEffect(() => {
    if (suggestedInvoiceNumber && !invoiceNumber) {
      setInvoiceNumber(suggestedInvoiceNumber);
    }
  }, [suggestedInvoiceNumber, invoiceNumber]);

  useEffect(() => {
    if (!company) return;
    setPaymentTerms((current) =>
      current === "Due within 15 days"
        ? company.defaultPaymentTerms || "Due within 15 days"
        : current,
    );
    setPlaceOfSupply((current) =>
      current === "Gujarat" ? company.state || current : current,
    );
  }, [company]);

  const subtotal = items.reduce((s, i) => s + (i.quantity || 0) * (i.price || 0), 0);
  const gstAmount = items.reduce(
    (s, i) => s + ((i.quantity || 0) * (i.price || 0) * (i.gst || 0)) / 100,
    0,
  );
  const total = subtotal + gstAmount;

  const create = useMutation({
    mutationFn: api.createInvoice,
    onSuccess: (data) => {
      setCreatedInvoice(data);
      qc.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice created successfully");
    },
    onError: (e: Error) => {
      if (e instanceof ApiError) {
        const apiErrors: Record<string, string> = {};
        for (const [field, message] of Object.entries(e.errors)) {
          if (field === "client_name") apiErrors.clientName = message;
          else if (field === "invoice_number") apiErrors.invoiceNumber = message;
          else if (field === "items") apiErrors.items = message;
          else {
            const match = field.match(/^items\[(\d+)\]\.(.+)$/);
            if (match) apiErrors[`item-${match[1]}-${match[2]}`] = message;
          }
        }
        setErrors(apiErrors);
      }
      toast.error(e.message);
    },
  });

  function update(i: number, patch: Partial<Row>) {
    setItems((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  function applyClient(clientId: string) {
    const selected = clients.find((client: Client) => String(client.id ?? "") === clientId);
    if (!selected) return;
    setClientName(selected.name);
    setClientGSTIN(selected.gstin || "");
    setClientAddress(selected.address || "");
    setPlaceOfSupply(selected.state || placeOfSupply);
  }

  function applyProduct(rowIndex: number, productId: string) {
    const selected = products.find((product: Product) => String(product.id ?? "") === productId);
    if (!selected) return;
    update(rowIndex, {
      name: selected.name,
      description: selected.description || "",
      hsnSac: selected.hsnSac || "",
      price: selected.price,
      gst: selected.gstRate,
    });
  }

  function fillDemo() {
    setInvoiceDate(today());
    setDueDate(addDays(15));
    setStatus("sent");
    setPaymentTerms(company?.defaultPaymentTerms || "Due within 15 days");
    setSupplyType("intrastate");
    setPlaceOfSupply("Karnataka");
    setClientName("Acme Digital Services Pvt Ltd");
    setClientGSTIN("29ABCDE1234F1Z5");
    setClientAddress("221, MG Road\nBengaluru\nKarnataka - 560001\nIndia");
    setNotes("Please make the payment by the due date. Thanks for your business.");
    setItems(demoRows());
    setErrors({});
    setInvoiceNumber(suggestedInvoiceNumber || "");
  }

  function validate() {
    const errs: Record<string, string> = {};
    if (!invoiceNumber.trim()) errs.invoiceNumber = "Invoice number is required";
    if (!clientName.trim()) errs.clientName = "Client name is required";
    if (!invoiceDate) errs.invoiceDate = "Invoice date is required";
    if (items.length === 0) errs.items = "Add at least one item";
    items.forEach((it, i) => {
      if (!it.name.trim()) errs[`item-${i}-item_name`] = "Item name required";
      if (!it.quantity || it.quantity <= 0) errs[`item-${i}-quantity`] = "Quantity must be greater than 0";
      if (it.price < 0) errs[`item-${i}-price`] = "Price cannot be negative";
      if (it.gst < 0 || it.gst > 28) errs[`item-${i}-gst_rate`] = "GST must be between 0 and 28";
    });
    return errs;
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length) return;
    create.mutate({
      clientName,
      invoiceNumber,
      clientGSTIN,
      clientAddress,
      date: invoiceDate,
      dueDate,
      paymentTerms,
      supplyType,
      placeOfSupply,
      status,
      notes,
      items,
      subtotal,
      gstAmount,
      total,
    });
  }

  if (createdInvoice) {
    const createdId = String(createdInvoice.id ?? createdInvoice._id ?? "");
    return (
      <div className="max-w-xl mx-auto">
        <Card>
          <CardContent className="py-12 text-center space-y-4">
            <div className="mx-auto h-14 w-14 rounded-full bg-success/15 flex items-center justify-center">
              <CheckCircle2 className="h-7 w-7 text-success" />
            </div>
            <h2 className="text-2xl font-bold">Invoice Created</h2>
            <p className="text-muted-foreground">
              {createdInvoice.invoiceNumber} for {clientName}
            </p>
            <p className="text-xl font-semibold">{formatINR(createdInvoice.total || total)}</p>
            <div className="flex justify-center gap-3 pt-4">
              <Button asChild>
                <a
                  href="#"
                  onClick={(event) => {
                    event.preventDefault();
                    api
                      .downloadInvoicePdf(createdId, createdInvoice.invoiceNumber || "invoice")
                      .catch((error: Error) => toast.error(error.message));
                  }}
                >
                  <Download className="h-4 w-4" /> Download PDF
                </a>
              </Button>
              <Button variant="outline" asChild>
                <Link to="/invoices">View All</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Create Invoice</h1>
          <p className="text-muted-foreground mt-1">Fill in the details to generate a GST invoice.</p>
        </div>
        <Button type="button" variant="outline" onClick={fillDemo}>
          <Wand2 className="h-4 w-4" /> Fill Demo
        </Button>
      </div>

      <form onSubmit={submit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Invoice Details</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="number">Invoice Number *</Label>
              <div className="flex gap-2">
                <Input
                  id="number"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  placeholder={suggestedInvoiceNumber || "INV-0001"}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setInvoiceNumber(suggestedInvoiceNumber || "")}
                >
                  Use Next
                </Button>
              </div>
              {errors.invoiceNumber && <p className="text-xs text-destructive">{errors.invoiceNumber}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="date">Invoice Date *</Label>
              <Input id="date" type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} />
              {errors.invoiceDate && <p className="text-xs text-destructive">{errors.invoiceDate}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="due">Due Date</Label>
              <Input id="due" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="paid">Paid</option>
                <option value="overdue">Overdue</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="terms">Payment Terms</Label>
              <Input id="terms" value={paymentTerms} onChange={(e) => setPaymentTerms(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="supply">Supply Type</Label>
              <select
                id="supply"
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={supplyType}
                onChange={(e) => setSupplyType(e.target.value)}
              >
                <option value="intrastate">Intrastate (CGST + SGST)</option>
                <option value="interstate">Interstate (IGST)</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="place">Place of Supply</Label>
              <Input id="place" value={placeOfSupply} onChange={(e) => setPlaceOfSupply(e.target.value)} placeholder="Karnataka" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Client Details</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {clients.length > 0 && (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="saved-client">Use Saved Client</Label>
                <select
                  id="saved-client"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue=""
                  onChange={(e) => applyClient(e.target.value)}
                >
                  <option value="">Select saved client...</option>
                  {clients.map((client: Client) => (
                    <option key={String(client.id ?? client.name)} value={String(client.id ?? "")}>
                      {client.name}{client.gstin ? ` - ${client.gstin}` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="cn">Client Name *</Label>
              <Input id="cn" value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Acme Pvt Ltd" />
              {errors.clientName && <p className="text-xs text-destructive">{errors.clientName}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="gstin">Client GSTIN</Label>
              <Input id="gstin" value={clientGSTIN} onChange={(e) => setClientGSTIN(e.target.value)} placeholder="22AAAAA0000A1Z5" />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="address">Billing Address</Label>
              <Textarea id="address" rows={3} value={clientAddress} onChange={(e) => setClientAddress(e.target.value)} placeholder="Client address" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Items</CardTitle>
            <Button type="button" size="sm" variant="outline" onClick={() => setItems((p) => [...p, emptyRow()])}>
              <Plus className="h-4 w-4" /> Add Item
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {errors.items && <p className="text-sm text-destructive">{errors.items}</p>}
            <div className="hidden md:grid grid-cols-12 gap-3 text-xs font-medium text-muted-foreground px-1">
              <div className="col-span-4">Item</div>
              <div className="col-span-2">HSN/SAC</div>
              <div className="col-span-1">Qty</div>
              <div className="col-span-2">Price</div>
              <div className="col-span-2">GST %</div>
              <div />
            </div>
            {items.map((it, i) => (
              <div key={i} className="space-y-2 rounded-lg border border-border/60 p-3 md:border-0 md:p-0">
                {products.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-2">
                    <select
                      className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                      defaultValue=""
                      onChange={(e) => applyProduct(i, e.target.value)}
                    >
                      <option value="">Use saved product/service...</option>
                      {products.map((product: Product) => (
                        <option key={String(product.id ?? product.name)} value={String(product.id ?? "")}>
                          {product.name} - {formatINR(product.price)} - GST {product.gstRate}%
                        </option>
                      ))}
                    </select>
                    <Button type="button" variant="outline" asChild>
                      <Link to="/products">Manage Products</Link>
                    </Button>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-start">
                  <div className="md:col-span-4">
                    <Input value={it.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="Item name" />
                    {errors[`item-${i}-item_name`] && <p className="text-xs text-destructive mt-1">{errors[`item-${i}-item_name`]}</p>}
                  </div>
                  <Input className="md:col-span-2" value={it.hsnSac || ""} onChange={(e) => update(i, { hsnSac: e.target.value })} placeholder="9983" />
                  <div className="md:col-span-1">
                    <Input type="number" min={0} step="0.01" value={it.quantity} onChange={(e) => update(i, { quantity: Number(e.target.value) })} />
                    {errors[`item-${i}-quantity`] && <p className="text-xs text-destructive mt-1">{errors[`item-${i}-quantity`]}</p>}
                  </div>
                  <div className="md:col-span-2">
                    <Input type="number" min={0} step="0.01" value={it.price} onChange={(e) => update(i, { price: Number(e.target.value) })} />
                    {errors[`item-${i}-price`] && <p className="text-xs text-destructive mt-1">{errors[`item-${i}-price`]}</p>}
                  </div>
                  <div className="md:col-span-2">
                    <Input type="number" min={0} max={28} step="0.01" value={it.gst} onChange={(e) => update(i, { gst: Number(e.target.value) })} />
                    {errors[`item-${i}-gst_rate`] && <p className="text-xs text-destructive mt-1">{errors[`item-${i}-gst_rate`]}</p>}
                  </div>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => setItems((p) => p.filter((_, idx) => idx !== i))}
                    disabled={items.length === 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <Textarea
                  rows={2}
                  value={it.description || ""}
                  onChange={(e) => update(i, { description: e.target.value })}
                  placeholder="Optional item description"
                />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Payment terms or customer note" />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-muted-foreground uppercase">Subtotal</div>
              <div className="text-lg font-semibold">{formatINR(subtotal)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">GST</div>
              <div className="text-lg font-semibold">{formatINR(gstAmount)}</div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground uppercase">Total</div>
              <div className="text-2xl font-bold text-primary">{formatINR(total)}</div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={() => navigate({ to: "/invoices" })}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending} className="rounded-full" style={{ boxShadow: "var(--shadow-elegant)" }}>
            {create.isPending ? "Generating..." : "Generate Invoice"}
          </Button>
        </div>
      </form>
    </div>
  );
}
