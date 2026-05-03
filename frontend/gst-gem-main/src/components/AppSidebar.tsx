import { Link, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  FilePlus2,
  FileText,
  BarChart3,
  Building2,
  Receipt,
  Users,
  PackageSearch,
  ShieldCheck,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { api } from "@/lib/api";
import { FALLBACK_BRANDING } from "@/lib/app-signature";

const items = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard, permission: "always" },
  { title: "Create Invoice", url: "/invoices/new", icon: FilePlus2, permission: "canCreateInvoices" },
  { title: "Invoices", url: "/invoices", icon: FileText, permission: "always" },
  { title: "Clients", url: "/clients", icon: Users, permission: "canCreateInvoices" },
  { title: "Products", url: "/products", icon: PackageSearch, permission: "canCreateInvoices" },
  { title: "Users", url: "/users", icon: ShieldCheck, permission: "admin" },
  { title: "GST Report", url: "/reports", icon: BarChart3, permission: "canExportData" },
  { title: "Company", url: "/company", icon: Building2, permission: "canManageCompany" },
] as const;

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const path = useRouterState({ select: (r) => r.location.pathname });
  const { data: backendBranding } = useQuery({
    queryKey: ["app-branding"],
    queryFn: api.getBranding,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
  const { data: currentUser } = useQuery({
    queryKey: ["current-user"],
    queryFn: api.currentUser,
    retry: false,
    staleTime: 60 * 1000,
  });
  const branding = backendBranding || FALLBACK_BRANDING;
  const isActive = (url: string) => (url === "/" ? path === "/" : path.startsWith(url));
  const user = currentUser?.user;
  const visibleItems = items.filter((item) => {
    if (item.permission === "always") return true;
    if (item.permission === "admin") return user?.role === "admin";
    if (user?.role === "admin") return true;
    return Boolean(user?.[item.permission]);
  });

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <Link to="/" className="flex items-center gap-2 px-2 py-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary to-primary-glow flex items-center justify-center text-primary-foreground shadow-elegant">
            <Receipt className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold">{branding.appName || FALLBACK_BRANDING.appName}</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">India</span>
            </div>
          )}
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {visibleItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)} tooltip={item.title}>
                    <Link to={item.url} className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      {!collapsed && <span>{item.title}</span>}
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border p-3">
        {!collapsed && (
          <a
            href={branding.developerProfileUrl || FALLBACK_BRANDING.developerProfileUrl}
            target="_blank"
            rel="noreferrer"
            className="block rounded-md bg-sidebar-accent px-3 py-2 text-[11px] text-sidebar-accent-foreground transition-colors hover:bg-sidebar-accent/80"
            title="Open developer profile"
          >
            Developed by
            <div className="text-sm font-semibold">
              {branding.developerName || FALLBACK_BRANDING.developerName}
            </div>
          </a>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
