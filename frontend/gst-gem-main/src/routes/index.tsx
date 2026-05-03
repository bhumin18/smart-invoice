import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api, formatINR } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, IndianRupee, Receipt, Plus, ArrowUpRight, WalletCards } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}) {
  return (
    <Card className="relative overflow-hidden border-border/60" style={{ boxShadow: "var(--shadow-card)" }}>
      <div className="absolute inset-x-0 top-0 h-1" style={{ background: accent }} />
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <div className="h-9 w-9 rounded-lg bg-accent/60 flex items-center justify-center text-accent-foreground">
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tracking-tight">{value}</div>
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.getDashboardSummary,
  });

  const invoices = data?.recentInvoices || [];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Overview of your invoicing & GST.</p>
        </div>
        <Button asChild size="lg" className="rounded-full shadow-elegant" style={{ boxShadow: "var(--shadow-elegant)" }}>
          <Link to="/invoices/new">
            <Plus className="h-4 w-4" /> New Invoice
          </Link>
        </Button>
      </div>

      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="py-4 text-sm text-destructive">
            Couldn't reach API: {(error as Error).message}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {isLoading ? (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-32 rounded-xl" />)
        ) : (
          <>
            <StatCard label="Total Invoices" value={String(data?.invoiceCount || 0)} icon={FileText} accent="var(--gradient-primary)" />
            <StatCard label="Total Sales" value={formatINR(data?.totalSales)} icon={IndianRupee} accent="linear-gradient(135deg, oklch(0.7 0.18 155), oklch(0.78 0.16 175))" />
            <StatCard label="Total GST" value={formatINR(data?.totalGst)} icon={Receipt} accent="linear-gradient(135deg, oklch(0.78 0.16 75), oklch(0.7 0.2 35))" />
            <StatCard label="Balance Due" value={formatINR(data?.balanceDue)} icon={WalletCards} accent="linear-gradient(135deg, oklch(0.66 0.16 25), oklch(0.72 0.14 55))" />
          </>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Invoices</CardTitle>
          </div>
          <Button asChild variant="ghost" size="sm">
            <Link to="/invoices">
              View all <ArrowUpRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : invoices.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No invoices yet. Create your first one.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {invoices.slice(0, 5).map((inv) => {
                const id = String(inv.id ?? inv._id ?? "");
                return (
                  <Link
                    key={id}
                    to="/invoices/$id"
                    params={{ id }}
                    className="flex items-center justify-between py-3 hover:bg-muted/50 -mx-2 px-2 rounded-md transition"
                  >
                    <div>
                      <div className="font-medium">{inv.invoiceNumber || `#${id.slice(-6)}`}</div>
                      <div className="text-sm text-muted-foreground">{inv.clientName}</div>
                    </div>
                    <div className="font-semibold">{formatINR(inv.total)}</div>
                  </Link>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
