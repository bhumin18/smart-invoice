import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, formatINR } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BarChart3, DatabaseBackup, Plus, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/reports")({
  component: ReportsPage,
});

const months = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

type RecurringItem = {
  productId: string;
  name: string;
  quantity: number;
  price: number;
  gst: number;
  hsnSac: string;
  description: string;
};

function emptyRecurringItem(): RecurringItem {
  return { productId: "", name: "", quantity: 1, price: 0, gst: 18, hsnSac: "", description: "" };
}

function ReportsPage() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [recurringName, setRecurringName] = useState("Monthly Service Invoice");
  const [recurringClientId, setRecurringClientId] = useState("");
  const [recurringFrequency, setRecurringFrequency] = useState("monthly");
  const [recurringNextDate, setRecurringNextDate] = useState(now.toISOString().slice(0, 10));
  const [recurringActive, setRecurringActive] = useState("true");
  const [recurringItems, setRecurringItems] = useState<RecurringItem[]>([emptyRecurringItem()]);
  const [reminderDays, setReminderDays] = useState(7);
  const [autoReminders, setAutoReminders] = useState(false);
  const [reminderTemplate, setReminderTemplate] = useState("");

  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: api.currentUser,
    retry: false,
    staleTime: 60 * 1000,
  });
  const canExportData =
    currentUser?.user.role === "admin" || Boolean(currentUser?.user.canExportData);

  const gstReport = useMutation({
    mutationFn: () => api.gstReport(month, year),
    onSuccess: () => toast.success("GST report downloaded"),
    onError: (e: Error) => toast.error(e.message),
  });

  const backup = useMutation({
    mutationFn: api.downloadBackup,
    onSuccess: () => toast.success("Backup downloaded"),
    onError: (e: Error) => toast.error(e.message),
  });

  const restore = useMutation({
    mutationFn: api.restoreBackup,
    onSuccess: (result) => toast.success(result?.message || "Backup restored"),
    onError: (e: Error) => toast.error(e.message),
  });

  const exportData = useMutation({
    mutationFn: (format: "xlsx" | "json") => api.downloadDataExport(format),
    onSuccess: () => toast.success("Data export downloaded"),
    onError: (e: Error) => toast.error(e.message),
  });

  const recurring = useQuery({
    queryKey: ["recurring-invoices"],
    queryFn: api.listRecurringInvoices,
  });
  const clients = useQuery({
    queryKey: ["clients", "recurring-form"],
    queryFn: () => api.listClients(),
  });
  const products = useQuery({
    queryKey: ["products", "recurring-form"],
    queryFn: () => api.listProducts("", true),
  });
  const reminders = useQuery({
    queryKey: ["payment-reminders"],
    queryFn: () => api.getPaymentReminders(7),
  });
  const reminderSettings = useQuery({
    queryKey: ["reminder-settings"],
    queryFn: api.getReminderSettings,
  });

  useEffect(() => {
    if (!reminderSettings.data) return;
    setReminderDays(Number(reminderSettings.data.days_ahead ?? 7));
    setAutoReminders(Boolean(reminderSettings.data.auto_enabled));
    setReminderTemplate(String(reminderSettings.data.email_template || ""));
  }, [reminderSettings.data]);

  const createRecurring = useMutation({
    mutationFn: () => {
      const client = (clients.data || []).find((row) => String(row.id) === recurringClientId);
      if (!client) throw new Error("Select a client for recurring invoice");
      const items = recurringItems
        .filter((item) => item.name.trim())
        .map((item) => ({
          name: item.name,
          quantity: Number(item.quantity || 0),
          price: Number(item.price || 0),
          gst: Number(item.gst || 0),
          hsnSac: item.hsnSac,
          description: item.description,
        }));
      if (!items.length) throw new Error("Add at least one recurring item");
      return api.createRecurringInvoice({
        name: recurringName,
        frequency: recurringFrequency,
        nextRunDate: recurringNextDate,
        active: recurringActive === "true",
        invoice: {
          clientName: client.name,
          clientGSTIN: client.gstin || "",
          clientAddress: client.address || "",
          date: recurringNextDate,
          dueDate: recurringNextDate,
          supplyType: "intrastate",
          status: "sent",
          items,
        },
      });
    },
    onSuccess: () => {
      toast.success("Recurring invoice profile created");
      recurring.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const runRecurring = useMutation({
    mutationFn: api.runDueRecurringInvoices,
    onSuccess: (result) => {
      toast.success(`Generated ${result.generated_count || 0} recurring invoices`);
      recurring.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const sendReminders = useMutation({
    mutationFn: () => api.sendPaymentReminders(7),
    onSuccess: (result) => {
      toast.success(`Sent ${result.sent_count || 0} reminders`);
      reminderSettings.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const saveReminderSettings = useMutation({
    mutationFn: () =>
      api.saveReminderSettings({
        autoEnabled: autoReminders,
        daysAhead: reminderDays,
        emailTemplate: reminderTemplate,
      }),
    onSuccess: () => {
      toast.success("Reminder settings saved");
      reminderSettings.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const runAutoReminders = useMutation({
    mutationFn: api.runAutoReminders,
    onSuccess: (result) => {
      toast.success(`Auto reminders processed: ${result.sent_count || 0} sent`);
      reminders.refetch();
      reminderSettings.refetch();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function patchRecurringItem(index: number, patch: Partial<RecurringItem>) {
    setRecurringItems((items) =>
      items.map((item, idx) => (idx === index ? { ...item, ...patch } : item)),
    );
  }

  const data = gstReport.data;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">GST Report</h1>
        <p className="text-muted-foreground mt-1">
          Generate monthly GST summaries, recurring invoices, and payment reminders.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-2">
            <Label>Month</Label>
            <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {months.map((mo, i) => (
                  <SelectItem key={mo} value={String(i + 1)}>
                    {mo}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Year</Label>
            <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 5 }).map((_, i) => {
                  const y = now.getFullYear() - 2 + i;
                  return (
                    <SelectItem key={y} value={String(y)}>
                      {y}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>
          <Button
            onClick={() => gstReport.mutate()}
            disabled={gstReport.isPending}
            className="rounded-full"
            style={{ boxShadow: "var(--shadow-elegant)" }}
          >
            <BarChart3 className="h-4 w-4" />
            {gstReport.isPending ? "Generating..." : "Generate Report"}
          </Button>
        </CardContent>
      </Card>

      {canExportData && (
        <Card>
          <CardHeader>
            <CardTitle>Backup & Restore</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row md:items-center">
            <Button
              variant="outline"
              onClick={() => exportData.mutate("xlsx")}
              disabled={exportData.isPending}
            >
              <DatabaseBackup className="h-4 w-4" />
              Export Excel
            </Button>
            <Button
              variant="outline"
              onClick={() => exportData.mutate("json")}
              disabled={exportData.isPending}
            >
              <DatabaseBackup className="h-4 w-4" />
              Export JSON
            </Button>
            <Button variant="outline" onClick={() => backup.mutate()} disabled={backup.isPending}>
              <DatabaseBackup className="h-4 w-4" />
              {backup.isPending ? "Preparing..." : "Download Full Backup"}
            </Button>
            <div>
              <Input
                id="backup-restore"
                type="file"
                accept=".zip"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) restore.mutate(file);
                }}
              />
              <Button
                type="button"
                variant="outline"
                disabled={restore.isPending}
                onClick={() => document.getElementById("backup-restore")?.click()}
              >
                <Upload className="h-4 w-4" />
                {restore.isPending ? "Restoring..." : "Restore Backup Zip"}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Restore replaces local SQLite/output data. Restart backend after restore.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recurring Invoices</CardTitle>
            <Button
              type="button"
              variant="outline"
              onClick={() => runRecurring.mutate()}
              disabled={runRecurring.isPending}
            >
              Run Due
            </Button>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="rounded-md border p-4 space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Profile Name</Label>
                  <Input value={recurringName} onChange={(e) => setRecurringName(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Client</Label>
                  <Select value={recurringClientId} onValueChange={setRecurringClientId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select client" />
                    </SelectTrigger>
                    <SelectContent>
                      {(clients.data || []).map((client) => (
                        <SelectItem key={String(client.id)} value={String(client.id)}>
                          {client.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Frequency</Label>
                  <Select value={recurringFrequency} onValueChange={setRecurringFrequency}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="monthly">Monthly</SelectItem>
                      <SelectItem value="quarterly">Quarterly</SelectItem>
                      <SelectItem value="yearly">Yearly</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Next Run Date</Label>
                  <Input
                    type="date"
                    value={recurringNextDate}
                    onChange={(e) => setRecurringNextDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Items</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setRecurringItems((items) => [...items, emptyRecurringItem()])}
                  >
                    <Plus className="h-4 w-4" />
                    Add Item
                  </Button>
                </div>
                {recurringItems.map((item, index) => (
                  <div key={index} className="grid gap-2 md:grid-cols-[1.4fr_.6fr_.7fr_.6fr_auto]">
                    <Select
                      value={item.productId}
                      onValueChange={(value) => {
                        const product = (products.data || []).find(
                          (row) => String(row.id) === value,
                        );
                        patchRecurringItem(index, {
                          productId: value,
                          name: product?.name || item.name,
                          price: Number(product?.price || item.price),
                          gst: Number(product?.gstRate || item.gst),
                          hsnSac: product?.hsnSac || item.hsnSac,
                          description: product?.description || item.description,
                        });
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Product or service" />
                      </SelectTrigger>
                      <SelectContent>
                        {(products.data || []).map((product) => (
                          <SelectItem key={String(product.id)} value={String(product.id)}>
                            {product.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      type="number"
                      min={0.01}
                      step="0.01"
                      value={item.quantity}
                      onChange={(e) =>
                        patchRecurringItem(index, { quantity: Number(e.target.value) })
                      }
                    />
                    <Input
                      type="number"
                      min={0}
                      step="0.01"
                      value={item.price}
                      onChange={(e) => patchRecurringItem(index, { price: Number(e.target.value) })}
                    />
                    <Input
                      type="number"
                      min={0}
                      max={28}
                      step="0.01"
                      value={item.gst}
                      onChange={(e) => patchRecurringItem(index, { gst: Number(e.target.value) })}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      disabled={recurringItems.length === 1}
                      onClick={() =>
                        setRecurringItems((items) => items.filter((_, idx) => idx !== index))
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <Select value={recurringActive} onValueChange={setRecurringActive}>
                  <SelectTrigger className="w-44">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Active</SelectItem>
                    <SelectItem value="false">Inactive</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  type="button"
                  onClick={() => createRecurring.mutate()}
                  disabled={createRecurring.isPending}
                >
                  {createRecurring.isPending ? "Creating..." : "Create Recurring Profile"}
                </Button>
              </div>
            </div>

            {(recurring.data || []).length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No recurring profiles yet.
              </p>
            ) : (
              <div className="space-y-3">
                {(recurring.data || []).map((profile) => (
                  <div key={String(profile.id)} className="rounded-md border p-3">
                    <div className="font-medium">{profile.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {profile.clientName} - {profile.frequency} - next {profile.nextRunDate}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Payment Reminders</CardTitle>
            <Button
              type="button"
              variant="outline"
              onClick={() => sendReminders.mutate()}
              disabled={sendReminders.isPending}
            >
              Send Emails
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Due Soon</div>
                <div className="text-2xl font-bold">{reminders.data?.due_soon?.length || 0}</div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-xs text-muted-foreground">Overdue</div>
                <div className="text-2xl font-bold">{reminders.data?.overdue?.length || 0}</div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Reminder emails require SMTP configuration and client email data.
            </p>
            <div className="rounded-md border p-4 space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Days Before Due Date</Label>
                  <Input
                    type="number"
                    min={0}
                    value={reminderDays}
                    onChange={(e) => setReminderDays(Number(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Auto Scheduler</Label>
                  <Select
                    value={String(autoReminders)}
                    onValueChange={(value) => setAutoReminders(value === "true")}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">Enabled</SelectItem>
                      <SelectItem value="false">Disabled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Email Template</Label>
                <Textarea
                  rows={5}
                  value={reminderTemplate}
                  onChange={(e) => setReminderTemplate(e.target.value)}
                  placeholder="Dear {client_name}, invoice {invoice_number} balance {balance_due} is due on {due_date}."
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => saveReminderSettings.mutate()}
                  disabled={saveReminderSettings.isPending}
                >
                  Save Reminder Settings
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => runAutoReminders.mutate()}
                  disabled={runAutoReminders.isPending}
                >
                  Run Auto Scheduler
                </Button>
              </div>
            </div>
            <div>
              <h3 className="mb-2 text-sm font-semibold">Reminder History</h3>
              {(reminderSettings.data?.history || []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No reminder history yet.</p>
              ) : (
                <div className="space-y-2">
                  {(reminderSettings.data?.history || []).slice(0, 6).map((row: any) => (
                    <div
                      key={row.id}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
                    >
                      <span>{row.invoice_number || `Invoice #${row.invoice_id}`}</span>
                      <span className="text-muted-foreground">
                        {row.status} - {row.recipient_email || "no email"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground font-medium">
                  Total Sales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatINR(data.totalSales)}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground font-medium">
                  Total GST
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{formatINR(data.totalGst)}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              {data.rows.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">
                  No data for this period.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invoice #</TableHead>
                      <TableHead>Client</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Taxable</TableHead>
                      <TableHead className="text-right">GST</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.rows.map((r, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{r.invoiceNumber}</TableCell>
                        <TableCell>{r.clientName}</TableCell>
                        <TableCell>
                          {r.date ? new Date(r.date).toLocaleDateString("en-IN") : ""}
                        </TableCell>
                        <TableCell className="text-right">{formatINR(r.taxable)}</TableCell>
                        <TableCell className="text-right">{formatINR(r.gst)}</TableCell>
                        <TableCell className="text-right">{formatINR(r.total)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
