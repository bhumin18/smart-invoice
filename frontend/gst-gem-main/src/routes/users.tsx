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
  const save = useMutation({
    mutationFn: (user: AppUser) => api.updateUser(String(user.id ?? ""), user),
    onSuccess: () => {
      toast.success("User permissions updated");
      qc.invalidateQueries({ queryKey: ["users"] });
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
            <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
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
                        onChange={(e) => patch(user, { role: e.target.value === "admin" ? "admin" : "user" })}
                      >
                        <option value="admin">Admin</option>
                        <option value="user">User</option>
                      </select>
                    </TableCell>
                    <TableCell><Toggle value={user.active} onClick={() => patch(user, { active: !user.active })} /></TableCell>
                    <TableCell><Toggle value={user.canCreateInvoices} onClick={() => patch(user, { canCreateInvoices: !user.canCreateInvoices })} /></TableCell>
                    <TableCell><Toggle value={user.canManageCompany} onClick={() => patch(user, { canManageCompany: !user.canManageCompany })} /></TableCell>
                    <TableCell><Toggle value={user.canExportData} onClick={() => patch(user, { canExportData: !user.canExportData })} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
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
