import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, formatINR } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { BarChart3, DatabaseBackup, Upload } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/reports")({
  component: ReportsPage,
});

const months = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

function ReportsPage() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: api.currentUser,
    retry: false,
    staleTime: 60 * 1000,
  });
  const canExportData =
    currentUser?.user.role === "admin" || Boolean(currentUser?.user.canExportData);

  const m = useMutation({
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

  const data = m.data;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">GST Report</h1>
        <p className="text-muted-foreground mt-1">Generate monthly GST summaries.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="space-y-2">
            <Label>Month</Label>
            <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {months.map((mo, i) => (
                  <SelectItem key={i} value={String(i + 1)}>{mo}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Year</Label>
            <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Array.from({ length: 5 }).map((_, i) => {
                  const y = now.getFullYear() - 2 + i;
                  return <SelectItem key={y} value={String(y)}>{y}</SelectItem>;
                })}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={() => m.mutate()} disabled={m.isPending} className="rounded-full" style={{ boxShadow: "var(--shadow-elegant)" }}>
            <BarChart3 className="h-4 w-4" />
            {m.isPending ? "Generating..." : "Generate Report"}
          </Button>
        </CardContent>
      </Card>

      {canExportData && (
        <Card>
          <CardHeader>
            <CardTitle>Backup & Restore</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 md:flex-row md:items-center">
            <Button variant="outline" onClick={() => exportData.mutate("xlsx")} disabled={exportData.isPending}>
              <DatabaseBackup className="h-4 w-4" />
              Export Excel
            </Button>
            <Button variant="outline" onClick={() => exportData.mutate("json")} disabled={exportData.isPending}>
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

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground font-medium">Total Sales</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-bold">{formatINR(data.totalSales)}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground font-medium">Total GST</CardTitle></CardHeader>
              <CardContent><div className="text-2xl font-bold text-primary">{formatINR(data.totalGst)}</div></CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Breakdown</CardTitle></CardHeader>
            <CardContent>
              {data.rows.length === 0 ? (
                <div className="py-12 text-center text-muted-foreground">No data for this period.</div>
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
                        <TableCell>{r.date ? new Date(r.date).toLocaleDateString("en-IN") : ""}</TableCell>
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
