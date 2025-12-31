import { Outlet, Link } from "react-router-dom";
import { Building2, LogIn } from "lucide-react";

export default function ClientLayout() {
  return (
    <div className="min-h-screen text-zinc-900">
      <header className="sticky top-0 z-20 border-b bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Building2 className="h-5 w-5" />
            <span>PlanO</span>
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm hover:bg-zinc-50"
            >
              <LogIn className="h-4 w-4" />
              Sign in
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-10">
        <Outlet />
      </main>

      <footer className="border-t bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-zinc-500">
          © {new Date().getFullYear()} PlanO
        </div>
      </footer>
    </div>
  );
}
