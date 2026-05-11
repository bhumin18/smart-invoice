import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck } from "lucide-react";
import { api, type AppUser } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/users")({
  component: UsersPage,
});

function UsersPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: api.listUsers,
  });
  const { data: adminOverview } = useQuery({
    queryKey: ["admin-overview"],
    queryFn: api.getAdminOverview,
    retry: false,
  });
  const { data: schedulerStatus } = useQuery({
    queryKey: ["scheduler-status"],
    queryFn: api.getSchedulerStatus,
    retry: false,
  });
  const save = useMutation({
    mutationFn: (user: AppUser) => api.updateUser(String(user.id ?? ""), user),
    onSuccess: () => {
      toast.success("User permissions updated");
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const settings = useMutation({
    mutationFn: api.updateAdminSettings,
    onSuccess: () => {
      toast.success("Admin settings updated");
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const runJobs = useMutation({
    mutationFn: api.runScheduledJobs,
    onSuccess: () => {
      toast.success("Scheduled jobs processed");
      qc.invalidateQueries({ queryKey: ["scheduler-status"] });
      qc.invalidateQueries({ queryKey: ["admin-overview"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const users = Array.isArray(data) ? data : [];
  if (error) {
    return (
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardHeader>
            <CardTitle>Users & Permissions</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {(error as Error).message}
          </CardContent>
        </Card>
      </div>
    );
  }

  function patch(user: AppUser, patchValue: Partial<AppUser>) {
    save.mutate({ ...user, ...patchValue });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Users & Permissions</h1>
        <p className="mt-1 text-muted-foreground">
          Control account access when the app is hosted for multiple users.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" /> User Accounts
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-destructive">{(error as Error).message}</p>}
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead>Create Invoice</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Export</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={String(user.id ?? user.username)}>
                    <TableCell>
                      <div className="font-medium">{user.username}</div>
                      <div className="text-xs text-muted-foreground">{user.email}</div>
                    </TableCell>
                    <TableCell>
                      <select
                        className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                        value={user.role}
                        onChange={(e) =>
                          patch(user, { role: e.target.value === "admin" ? "admin" : "user" })
                        }
                      >
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                      </select>
                    </TableCell>
                    <TableCell>
                      <Toggle
                        value={user.active}
                        onClick={() => patch(user, { active: !user.active })}
                      />
                    </TableCell>
                    <TableCell>
                      <Toggle
                        value={user.canCreateInvoices}
                        onClick={() => patch(user, { canCreateInvoices: !user.canCreateInvoices })}
                      />
                    </TableCell>
                    <TableCell>
                      <Toggle
                        value={user.canManageCompany}
                        onClick={() => patch(user, { canManageCompany: !user.canManageCompany })}
                      />
                    </TableCell>
                    <TableCell>
                      <Toggle
                        value={user.canExportData}
                        onClick={() => patch(user, { canExportData: !user.canExportData })}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {adminOverview && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Total Users</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-bold">{adminOverview.total_users}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Active Users</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-bold">{adminOverview.active_users}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Total Invoices</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-bold">{adminOverview.total_invoices}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Registration</CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  settings.mutate({ registrationEnabled: !adminOverview.registration_enabled })
                }
              >
                {adminOverview.registration_enabled ? "Enabled" : "Disabled"}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {adminOverview?.recent_activity?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Recent User Activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {adminOverview.recent_activity.slice(0, 8).map((event: any) => (
              <div key={event.id} className="flex justify-between rounded-md border p-3 text-sm">
                <span>
                  {event.actor_username || "system"} {String(event.action || "").replace(/_/g, " ")}{" "}
                  {event.entity_type}
                </span>
                <span className="text-muted-foreground">
                  {event.created_at ? new Date(event.created_at).toLocaleString("en-IN") : ""}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Scheduler & Job Logs</CardTitle>
            <Button
              type="button"
              variant="outline"
              onClick={() => runJobs.mutate()}
              disabled={runJobs.isPending}
            >
              {runJobs.isPending ? "Running..." : "Run Now"}
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-muted-foreground">
              Auto scheduler: {schedulerStatus?.enabled ? "Enabled" : "Disabled"} at{" "}
              {schedulerStatus?.daily_hour ?? 9}:
              {String(schedulerStatus?.daily_minute ?? 0).padStart(2, "0")}
            </div>
            {(schedulerStatus?.logs || adminOverview?.job_logs || [])
              .slice(0, 8)
              .map((job: any) => (
                <div key={job.id} className="rounded-md border p-3 text-sm">
                  <div className="flex justify-between gap-3">
                    <span className="font-medium">
                      {String(job.job_name || "").replace(/_/g, " ")}
                    </span>
                    <Badge variant={job.status === "success" ? "default" : "secondary"}>
                      {job.status}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {job.finished_at || job.created_at}
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Login Activity</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(adminOverview?.login_activity || []).slice(0, 8).map((event: any) => (
              <div key={event.id} className="flex justify-between rounded-md border p-3 text-sm">
                <span>
                  {event.username || "unknown"} -{" "}
                  {String(event.event_type || "").replace(/_/g, " ")}
                </span>
                <span className="text-muted-foreground">
                  {event.created_at ? new Date(event.created_at).toLocaleString("en-IN") : ""}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Public Portal Links</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(adminOverview?.public_links || []).slice(0, 8).map((link: any) => (
              <div key={link.id} className="rounded-md border p-3 text-sm">
                <div className="font-medium">
                  {link.invoice_number} - {link.client_name}
                </div>
                <div className="text-xs text-muted-foreground">
                  Expires {link.public_token_expires_at || "-"} - Proof{" "}
                  {link.payment_proof_status || "not_uploaded"}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Uploaded Files</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(adminOverview?.uploads || []).slice(0, 8).map((upload: any) => (
              <div key={upload.id} className="rounded-md border p-3 text-sm">
                <div className="font-medium">{upload.file_name}</div>
                <div className="text-xs text-muted-foreground">
                  {upload.invoice_number} - {upload.attachment_type} - {upload.created_at}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Toggle({ value, onClick }: { value: boolean; onClick: () => void }) {
  return (
    <Button type="button" variant="ghost" size="sm" onClick={onClick}>
      <Badge variant={value ? "default" : "secondary"}>{value ? "Yes" : "No"}</Badge>
    </Button>
  );
}
