import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, Upload } from "lucide-react";
import { toast } from "sonner";
import { api, formatINR } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/portal/$token")({
  component: ClientPortalPage,
});

function ClientPortalPage() {
  const { token } = Route.useParams();
  const invoice = useQuery({
    queryKey: ["public-invoice", token],
    queryFn: () => api.getPublicInvoice(token),
    retry: false,
  });
  const uploadProof = useMutation({
    mutationFn: (file: File) => api.uploadPaymentProof(token, file),
    onSuccess: () => toast.success("Payment proof uploaded"),
    onError: (e: Error) => toast.error(e.message),
  });

  if (invoice.isLoading) {
    return <div className="mx-auto max-w-4xl text-sm text-muted-foreground">Loading invoice...</div>;
  }

  if (invoice.error || !invoice.data) {
    return (
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Invoice unavailable</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          This secure invoice link is invalid or no longer available.
        </CardContent>
      </Card>
    );
  }

  const inv = invoice.data;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-2xl">{inv.invoiceNumber}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Invoice for {inv.clientName}</p>
          </div>
          <Badge variant={String(inv.status).toLowerCase() === "paid" ? "default" : "secondary"}>
            {inv.status || "sent"}
          </Badge>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <Metric label="Invoice Date" value={inv.date || "-"} />
          <Metric label="Due Date" value={inv.dueDate || "-"} />
          <Metric label="Total" value={formatINR(inv.total)} />
          <Metric label="Balance Due" value={formatINR(inv.balanceDue)} />
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
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">GST</TableHead>
                <TableHead className="text-right">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inv.items.map((item, index) => {
                const taxable = Number(item.quantity || 0) * Number(item.price || 0);
                const tax = (taxable * Number(item.gst || 0)) / 100;
                return (
                  <TableRow key={index}>
                    <TableCell>
                      <div className="font-medium">{item.name}</div>
                      {item.description && <div className="text-xs text-muted-foreground">{item.description}</div>}
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

      <Card>
        <CardHeader>
          <CardTitle>Downloads & Payment Proof</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-center">
          <Button
            type="button"
            onClick={() => api.downloadPublicInvoicePdf(token, inv.invoiceNumber).catch((e: Error) => toast.error(e.message))}
          >
            <Download className="h-4 w-4" />
            Download PDF
          </Button>
          <div>
            <Label htmlFor="payment-proof" className="sr-only">Upload Payment Proof</Label>
            <Input
              id="payment-proof"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadProof.mutate(file);
              }}
            />
            <Button type="button" variant="outline" disabled={uploadProof.isPending} onClick={() => document.getElementById("payment-proof")?.click()}>
              <Upload className="h-4 w-4" />
              {uploadProof.isPending ? "Uploading..." : "Upload Payment Proof"}
            </Button>
          </div>
        </CardContent>
      </Card>
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
