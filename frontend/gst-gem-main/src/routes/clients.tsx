import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Plus, Search, Trash2, Upload, Users } from "lucide-react";
import { api, type Client } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const Route = createFileRoute("/clients")({
  component: ClientsPage,
});

const emptyClient: Client = {
  name: "",
  gstin: "",
  address: "",
  state: "",
  phone: "",
  email: "",
  notes: "",
};

function ClientsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<Client>(emptyClient);
  const [editingId, setEditingId] = useState<string>("");
  const { data, isLoading, error } = useQuery({
    queryKey: ["clients", search],
    queryFn: () => api.listClients(search),
  });

  const save = useMutation({
    mutationFn: (payload: Client) =>
      editingId ? api.updateClient(editingId, payload) : api.createClient(payload),
    onSuccess: () => {
      toast.success(editingId ? "Client updated" : "Client added");
      setForm(emptyClient);
      setEditingId("");
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: api.deleteClient,
    onSuccess: () => {
      toast.success("Client deleted");
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const importData = useMutation({
    mutationFn: api.importClients,
    onSuccess: (result) => {
      toast.success(`Imported ${result.created_count || 0} clients`);
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function edit(client: Client) {
    setEditingId(String(client.id ?? ""));
    setForm({ ...emptyClient, ...client });
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Client name is required");
      return;
    }
    save.mutate(form);
  }

  const clients = Array.isArray(data) ? data : [];

  return (
    <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[380px_1fr]">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle>{editingId ? "Edit Client" : "Add Client"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <Field label="Client Name *">
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="GSTIN">
              <Input value={form.gstin || ""} onChange={(e) => setForm({ ...form, gstin: e.target.value })} />
            </Field>
            <Field label="Address">
              <Textarea rows={3} value={form.address || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="State">
                <Input value={form.state || ""} onChange={(e) => setForm({ ...form, state: e.target.value })} />
              </Field>
              <Field label="Phone">
                <Input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </Field>
            </div>
            <Field label="Email">
              <Input type="email" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Notes">
              <Textarea rows={2} value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            <div className="flex gap-2">
              <Button type="submit" disabled={save.isPending}>
                <Plus className="h-4 w-4" />
                {editingId ? "Save Client" : "Add Client"}
              </Button>
              {editingId && (
                <Button type="button" variant="outline" onClick={() => { setEditingId(""); setForm(emptyClient); }}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Clients</h1>
          <p className="mt-1 text-muted-foreground">Save client details once and reuse them while creating invoices.</p>
        </div>
        <Card>
          <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" /> Client Master
            </CardTitle>
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search clients..." />
            </div>
            <div>
              <Input
                id="client-import"
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) importData.mutate(file);
                }}
              />
              <Button type="button" variant="outline" onClick={() => document.getElementById("client-import")?.click()}>
                <Upload className="h-4 w-4" /> Import
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {error && <p className="text-sm text-destructive">{(error as Error).message}</p>}
            {isLoading ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
            ) : clients.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">No clients found.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>GSTIN</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((client) => {
                    const id = String(client.id ?? "");
                    return (
                      <TableRow key={id}>
                        <TableCell className="font-medium">{client.name}</TableCell>
                        <TableCell>{client.gstin || "-"}</TableCell>
                        <TableCell>
                          <div>{client.phone || "-"}</div>
                          <div className="text-xs text-muted-foreground">{client.email}</div>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button size="icon" variant="ghost" onClick={() => edit(client)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button size="icon" variant="ghost" className="text-destructive" onClick={() => remove.mutate(id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
