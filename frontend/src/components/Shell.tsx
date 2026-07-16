import type { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Fingerprint, FolderKanban, LayoutDashboard, LogOut, ShieldCheck, Users } from "lucide-react";
import { useAuth } from "../lib/auth";
import { Badge } from "./ui";

const ROLE_TONE = { ADMIN: "violet", INVESTIGATING_OFFICER: "cyan", FORENSIC_ANALYST: "green", AUDITOR: "amber" } as const;

export default function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();

  const items = [
    { to: "/dashboard", label: "Command Deck", icon: LayoutDashboard, show: true },
    { to: "/cases", label: "Cases", icon: FolderKanban, show: true },
    { to: "/admin/users", label: "Access Control", icon: Users, show: user?.role === "ADMIN" || user?.role === "AUDITOR" },
  ].filter((i) => i.show);

  return (
    <div className="flex min-h-screen bg-void">
      <aside className="glass fixed inset-y-3 left-3 z-20 flex w-60 flex-col rounded-2xl p-4">
        <Link to="/" className="mb-8 flex items-center gap-2 px-2 pt-1">
          <Fingerprint className="h-6 w-6 text-neon" />
          <span className="text-lg font-bold tracking-tight">
            For<span className="neon-text">Evi</span>
          </span>
        </Link>
        <nav className="flex flex-1 flex-col gap-1">
          {items.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                pathname === to ? "bg-neon/10 text-neon" : "text-mist hover:bg-white/5 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" /> {label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-line pt-3">
          <div className="mb-2 px-2">
            <div className="truncate text-sm font-medium">{user?.full_name}</div>
            <div className="mt-1"><Badge tone={ROLE_TONE[user?.role ?? "INVESTIGATING_OFFICER"]}>{user?.role.replaceAll("_", " ")}</Badge></div>
          </div>
          <button
            onClick={() => { void logout().then(() => nav("/")); }}
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-mist transition hover:bg-red-500/10 hover:text-red-300"
          >
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>
      <main className="ml-[17rem] flex-1 p-6">
        <div className="mono mb-4 flex items-center gap-2 text-[11px] uppercase tracking-widest text-mist">
          <ShieldCheck className="h-3.5 w-3.5 text-neon" /> secure session · api-only data plane · audit chain active
        </div>
        {children}
      </main>
    </div>
  );
}
