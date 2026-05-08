import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PackageSearch, Pencil, Plus, Search, Trash2, Upload } from "lucide-react";
import { api, formatINR, type Product } from "@/lib/api";
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

export const Route = createFileRoute("/products")({
  component: ProductsPage,
});

const emptyProduct: Product = {
  name: "",
  description: "",
  hsnSac: "",
  price: 0,
  gstRate: 18,
  unit: "",
  active: true,
};

function ProductsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState<Product>(emptyProduct);
  const { data, isLoading, error } = useQuery({
    queryKey: ["products", search],
    queryFn: () => api.listProducts(search),
  });

  const save = useMutation({
    mutationFn: (payload: Product) =>
      editingId ? api.updateProduct(editingId, payload) : api.createProduct(payload),
    onSuccess: () => {
      toast.success(editingId ? "Product updated" : "Product added");
      setForm(emptyProduct);
      setEditingId("");
      qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: api.deleteProduct,
    onSuccess: () => {
      toast.success("Product deleted");
      qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const importData = useMutation({
    mutationFn: api.importProducts,
    onSuccess: (result) => {
      toast.success(`Imported ${result.created_count || 0} products`);
      qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function edit(product: Product) {
    setEditingId(String(product.id ?? ""));
    setForm({ ...emptyProduct, ...product });
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Product or service name is required");
      return;
    }
    save.mutate(form);
  }

  const products = Array.isArray(data) ? data : [];

  return (
    <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[380px_1fr]">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle>{editingId ? "Edit Product" : "Add Product/Service"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <Field label="Name *">
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Description">
              <Textarea rows={3} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="HSN/SAC">
                <Input value={form.hsnSac || ""} onChange={(e) => setForm({ ...form, hsnSac: e.target.value })} />
              </Field>
              <Field label="Unit">
                <Input value={form.unit || ""} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Price">
                <Input type="number" min={0} step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: Number(e.target.value) })} />
              </Field>
              <Field label="GST %">
                <Input type="number" min={0} max={28} step="0.01" value={form.gstRate} onChange={(e) => setForm({ ...form, gstRate: Number(e.target.value) })} />
              </Field>
            </div>
            <div className="flex gap-2">
              <Button type="submit" disabled={save.isPending}>
                <Plus className="h-4 w-4" />
                {editingId ? "Save Product" : "Add Product"}
              </Button>
              {editingId && (
                <Button type="button" variant="outline" onClick={() => { setEditingId(""); setForm(emptyProduct); }}>
                  Cancel
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Products & Services</h1>
          <p className="mt-1 text-muted-foreground">Create reusable invoice items with HSN/SAC, price, and GST rate.</p>
        </div>
        <Card>
          <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
            <CardTitle className="flex items-center gap-2">
              <PackageSearch className="h-5 w-5" /> Product Master
            </CardTitle>
            <div className="relative w-full md:w-80">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search products..." />
            </div>
            <div>
              <Input
                id="product-import"
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) importData.mutate(file);
                }}
              />
              <Button type="button" variant="outline" onClick={() => document.getElementById("product-import")?.click()}>
                <Upload className="h-4 w-4" /> Import
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {error && <p className="text-sm text-destructive">{(error as Error).message}</p>}
            {isLoading ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
            ) : products.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">No products or services found.</div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>HSN/SAC</TableHead>
                    <TableHead>Price</TableHead>
                    <TableHead>GST</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.map((product) => {
                    const id = String(product.id ?? "");
                    return (
                      <TableRow key={id}>
                        <TableCell>
                          <div className="font-medium">{product.name}</div>
                          <div className="text-xs text-muted-foreground">{product.description}</div>
                        </TableCell>
                        <TableCell>{product.hsnSac || "-"}</TableCell>
                        <TableCell>{formatINR(product.price)}</TableCell>
                        <TableCell>{product.gstRate}%</TableCell>
                        <TableCell className="text-right">
                          <Button size="icon" variant="ghost" onClick={() => edit(product)}>
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
