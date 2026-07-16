import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Link2, RefreshCw, ShieldCheck, ShieldX } from "lucide-react";
import Shell from "../components/Shell";
import { Badge, GlassCard, NeonButton } from "../components/ui";
import { api, apiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Role, User } from "../lib/auth";

interface AuditEntry {
  id: string; created_at: string; actor_email: string | null;
  action: string; resource: string; ip_address: string; entry_hash: string;
}

const STATUS_TONE = { PENDING: "amber", ACTIVE: "green", DISABLED: "red" } as const;

export default function AdminUsers() {
  const { user: me } = useAuth();
  const isAdmin = me?.role === "ADMIN";
  const [users, setUsers] = useState<User[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [chain, setChain] = useState<{ chain_intact: boolean; entries_checked: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [u, a, v] = await Promise.all([
        api.get<User[]>("/users"),
        api.get<AuditEntry[]>("/users/audit/log?limit=25"),
        api.get("/users/audit/verify"),
      ]);
      setUsers(u.data);
      setAudit(a.data);
      setChain(v.data);
      setError(null);
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function update(id: string, patch: Partial<{ status: string; role: Role }>) {
    try {
      await api.patch(`/users/${id}`, patch);
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  return (
    <Shell>
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold">Access Control</h1>
            <p className="mt-1 text-sm text-mist">{isAdmin ? "Approve, disable and re-role personnel." : "Read-only auditor view."}</p>
          </div>
          <div className="flex items-center gap-3">
            {chain && (
              <GlassCard className="flex items-center gap-2 px-4 py-2.5">
                <Link2 className={`h-4 w-4 ${chain.chain_intact ? "text-emerald-400" : "text-red-400"}`} />
                <span className="mono text-[11px] uppercase tracking-wider">
                  audit chain {chain.chain_intact ? "intact" : "BROKEN"} · {chain.entries_checked} entries
                </span>
              </GlassCard>
            )}
            <NeonButton variant="ghost" onClick={() => { void load(); }}><RefreshCw className="h-4 w-4" /></NeonButton>
          </div>
        </div>

        {error && <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

        <GlassCard className="mb-8 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-[11px] uppercase tracking-widest text-mist">
              <tr>
                <th className="px-5 py-3.5">Officer</th>
                <th className="px-5 py-3.5">Role</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Registered</th>
                {isAdmin && <th className="px-5 py-3.5 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-line/40 transition hover:bg-white/[0.03]">
                  <td className="px-5 py-3.5">
                    <div className="font-medium">{u.full_name}</div>
                    <div className="mono text-xs text-mist">{u.email}</div>
                  </td>
                  <td className="px-5 py-3.5">
                    {isAdmin && u.id !== me?.id ? (
                      <select
                        value={u.role}
                        onChange={(e) => { void update(u.id, { role: e.target.value as Role }); }}
                        className="rounded-lg border border-line bg-abyss px-2 py-1.5 text-xs"
                      >
                        <option value="ADMIN">ADMIN</option>
                        <option value="INVESTIGATING_OFFICER">INVESTIGATING OFFICER</option>
                        <option value="FORENSIC_ANALYST">FORENSIC ANALYST</option>
                        <option value="AUDITOR">AUDITOR</option>
                      </select>
                    ) : (
                      <Badge tone="violet">{u.role.replaceAll("_", " ")}</Badge>
                    )}
                  </td>
                  <td className="px-5 py-3.5"><Badge tone={STATUS_TONE[u.status]}>{u.status}</Badge></td>
                  <td className="mono px-5 py-3.5 text-xs text-mist">{new Date(u.created_at).toLocaleString()}</td>
                  {isAdmin && (
                    <td className="px-5 py-3.5 text-right">
                      {u.status === "PENDING" && (
                        <NeonButton className="!px-3 !py-1.5 text-xs" onClick={() => { void update(u.id, { status: "ACTIVE" }); }}>
                          <span className="flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5" /> Approve</span>
                        </NeonButton>
                      )}
                      {u.status === "ACTIVE" && u.id !== me?.id && (
                        <NeonButton variant="danger" className="!px-3 !py-1.5 text-xs" onClick={() => { void update(u.id, { status: "DISABLED" }); }}>
                          <span className="flex items-center gap-1.5"><ShieldX className="h-3.5 w-3.5" /> Disable</span>
                        </NeonButton>
                      )}
                      {u.status === "DISABLED" && (
                        <NeonButton variant="ghost" className="!px-3 !py-1.5 text-xs" onClick={() => { void update(u.id, { status: "ACTIVE" }); }}>
                          Re-activate
                        </NeonButton>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </GlassCard>

        <h2 className="mb-3 text-lg font-semibold">Recent audit trail</h2>
        <GlassCard className="overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-line text-[10px] uppercase tracking-widest text-mist">
              <tr>
                <th className="px-5 py-3">Time</th><th className="px-5 py-3">Actor</th>
                <th className="px-5 py-3">Action</th><th className="px-5 py-3">Resource</th>
                <th className="px-5 py-3">IP</th><th className="px-5 py-3">Entry hash</th>
              </tr>
            </thead>
            <tbody className="mono">
              {audit.map((a) => (
                <tr key={a.id} className="border-b border-line/30">
                  <td className="px-5 py-2.5 text-mist">{new Date(a.created_at).toLocaleTimeString()}</td>
                  <td className="px-5 py-2.5">{a.actor_email ?? "—"}</td>
                  <td className="px-5 py-2.5 text-neon">{a.action}</td>
                  <td className="px-5 py-2.5 text-mist">{a.resource}</td>
                  <td className="px-5 py-2.5 text-mist">{a.ip_address || "—"}</td>
                  <td className="px-5 py-2.5 text-mist">{a.entry_hash.slice(0, 16)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </GlassCard>
      </motion.div>
    </Shell>
  );
}
