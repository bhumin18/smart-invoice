import {
  Outlet,
  Link,
  createRootRouteWithContext,
  HeadContent,
  Scripts,
  useRouterState,
} from "@tanstack/react-router";
import { Moon, Sun } from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { AppSidebar } from "@/components/AppSidebar";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { APP_NAME, FALLBACK_BRANDING } from "@/lib/app-signature";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "GST Invoice Pro — India" },
      {
        name: "description",
        content: "Modern GST invoicing for Indian freelancers and small businesses.",
      },
      { property: "og:title", content: "GST Invoice Pro — India" },
      {
        property: "og:description",
        content: "Modern GST invoicing for Indian freelancers and small businesses.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "twitter:site", content: "@Lovable" },
      { name: "twitter:title", content: "GST Invoice Pro — India" },
      {
        name: "twitter:description",
        content: "Modern GST invoicing for Indian freelancers and small businesses.",
      },
      {
        property: "og:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/bc5a27bc-934a-49a9-82e7-c69c9046df2f/id-preview-dd3b984e--e6bc349b-8365-4469-afde-1a1a55bba321.lovable.app-1777738344950.png",
      },
      {
        name: "twitter:image",
        content:
          "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/bc5a27bc-934a-49a9-82e7-c69c9046df2f/id-preview-dd3b984e--e6bc349b-8365-4469-afde-1a1a55bba321.lovable.app-1777738344950.png",
      },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                const theme = localStorage.getItem("smart-invoice-theme");
                const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
                if (theme === "dark" || (!theme && prefersDark)) {
                  document.documentElement.classList.add("dark");
                }
              } catch (_) {}
            `,
          }}
        />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const path = useRouterState({ select: (state) => state.location.pathname });
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
    api
      .getBranding()
      .then((branding) => {
        console.info(
          `${branding.appName || APP_NAME} | ${branding.developerSignature || FALLBACK_BRANDING.developerSignature}`,
        );
      })
      .catch(() => {
        console.info(`${APP_NAME} | ${FALLBACK_BRANDING.developerSignature}`);
      });
    const token = localStorage.getItem(api.tokenKey);
    if (!token) {
      setCheckingAuth(false);
      return;
    }
    api
      .currentUser()
      .then(() => setIsAuthenticated(true))
      .catch(() => api.logout())
      .finally(() => setCheckingAuth(false));
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.classList.toggle("dark", nextTheme === "dark");
    localStorage.setItem("smart-invoice-theme", nextTheme);
    setTheme(nextTheme);
  }

  function logout() {
    api.logout();
    queryClient.clear();
    setIsAuthenticated(false);
  }

  if (checkingAuth) {
    return (
      <QueryClientProvider client={queryClient}>
        <div className="flex min-h-screen items-center justify-center bg-background">
          <div className="text-sm text-muted-foreground">Loading...</div>
        </div>
      </QueryClientProvider>
    );
  }

  if (path.startsWith("/portal/")) {
    return (
      <QueryClientProvider client={queryClient}>
        <main className="min-h-screen bg-background p-4 md:p-8">
          <Outlet />
        </main>
        <Toaster richColors position="top-right" />
      </QueryClientProvider>
    );
  }

  if (!isAuthenticated) {
    return (
      <QueryClientProvider client={queryClient}>
        <LoginScreen onLogin={() => setIsAuthenticated(true)} />
        <Toaster richColors position="top-right" />
      </QueryClientProvider>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SidebarProvider>
        <div className="min-h-screen flex w-full bg-background">
          <AppSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <header className="h-14 flex items-center gap-3 border-b border-border px-4 bg-card/50 backdrop-blur sticky top-0 z-10">
              <SidebarTrigger />
              <span className="text-sm font-medium text-muted-foreground">{APP_NAME}</span>
              <div className="ml-auto flex items-center gap-3">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                  title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                  {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={logout}>
                  Logout
                </Button>
              </div>
            </header>
            <main className="flex-1 p-6 lg:p-8 overflow-x-hidden">
              <Outlet />
            </main>
          </div>
        </div>
        <Toaster richColors position="top-right" />
      </SidebarProvider>
    </QueryClientProvider>
  );
}

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [mode, setMode] = useState<"login" | "register" | "forgot" | "reset">("login");
  const [username, setUsername] = useState("admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setNotice("");
    try {
      if (mode === "login") {
        await api.login(username, password);
        onLogin();
      } else if (mode === "register") {
        await api.register(username, email, password);
        setNotice("Account created. You can login now.");
        setMode("login");
      } else if (mode === "forgot") {
        const result = await api.forgotPassword(email || username);
        setResetToken(result.reset_token || "");
        setNotice(
          result.reset_token
            ? "Reset token generated below."
            : "If the account exists, reset instructions were created.",
        );
        setMode("reset");
      } else {
        await api.resetPassword(resetToken, password);
        setNotice("Password reset. You can login now.");
        setMode("login");
      }
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const title =
    mode === "register"
      ? "Create Account"
      : mode === "forgot"
        ? "Forgot Password"
        : mode === "reset"
          ? "Reset Password"
          : "Admin Login";

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            Access invoices and company data securely.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            {mode !== "forgot" && mode !== "reset" && (
              <div className="space-y-2">
                <Label htmlFor="login-username">Username</Label>
                <Input
                  id="login-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </div>
            )}
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="login-email">Email</Label>
                <Input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
            )}
            {mode === "forgot" && (
              <div className="space-y-2">
                <Label htmlFor="forgot-email">Email or Username</Label>
                <Input id="forgot-email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            )}
            {mode === "reset" && (
              <div className="space-y-2">
                <Label htmlFor="reset-token">Reset Token</Label>
                <TextareaLike value={resetToken} onChange={setResetToken} />
              </div>
            )}
            {mode !== "forgot" && (
              <div className="space-y-2">
                <Label htmlFor="login-password">
                  {mode === "reset" ? "New Password" : "Password"}
                </Label>
                <Input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
              </div>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            {notice && <p className="text-sm text-success">{notice}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Working..." : title}
            </Button>
            <div className="flex flex-wrap justify-center gap-3 text-xs">
              {mode !== "login" && (
                <button type="button" className="text-primary" onClick={() => setMode("login")}>
                  Login
                </button>
              )}
              {mode !== "register" && (
                <button type="button" className="text-primary" onClick={() => setMode("register")}>
                  Create account
                </button>
              )}
              {mode !== "forgot" && (
                <button type="button" className="text-primary" onClick={() => setMode("forgot")}>
                  Forgot password
                </button>
              )}
              {mode !== "reset" && (
                <button type="button" className="text-primary" onClick={() => setMode("reset")}>
                  Use reset token
                </button>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Default local credentials: admin / admin123. Change them in backend/config.yaml.
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function TextareaLike({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <textarea
      className="min-h-20 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
