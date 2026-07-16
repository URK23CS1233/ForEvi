import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FolderKanban, FolderPlus, Boxes } from "lucide-react";
import Shell from "../components/Shell";
import { Badge, Field, GlassCard, NeonButton } from "../components/ui";
import { api, apiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

interface Case {
  id: string; title: string; description: string; status: string;
  artifact_count: number; created_at: string;
}

const STATUS_TONE = { OPEN: "green", CLOSED: "amber", ARCHIVED: "violet" } as const;

export default function Cases() {
  const { user } = useAuth();
  const canWrite = user?.role !== "AUDITOR";
  const [cases, setCases] = useState<Case[]>([]);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setCases((await api.get<Case[]>("/cases")).data); }
    catch (e) { setError(apiErrorMessage(e)); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      await api.post("/cases", { title, description: desc });
      setTitle(""); setDesc(""); setCreating(false);
      await load();
    } catch (err) { setError(apiErrorMessage(err)); }
  }

  return (
    <Shell>
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold">Cases</h1>
          <p className="mt-1 text-sm text-mist">Every case is an isolated evidence workspace.</p>
        </div>
        {canWrite && (
          <NeonButton onClick={() => setCreating((v) => !v)}>
            <span className="flex items-center gap-2"><FolderPlus className="h-4 w-4" /> New case</span>
          </NeonButton>
        )}
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {creating && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mb-6">
          <GlassCard className="p-6">
            <form onSubmit={(e) => { void create(e); }} className="space-y-4">
              <Field label="Case title" value={title} onChange={(e) => setTitle(e.target.value)} required minLength={2} />
              <Field label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
              <div className="flex gap-3">
                <NeonButton type="submit">Create case</NeonButton>
                <NeonButton variant="ghost" onClick={() => setCreating(false)}>Cancel</NeonButton>
              </div>
            </form>
          </GlassCard>
        </motion.div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cases.map((c, i) => (
          <motion.div key={c.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
            <Link to={`/cases/${c.id}`}>
              <GlassCard className="h-full p-6 transition hover:border-neon/40">
                <div className="mb-3 flex items-center justify-between">
                  <div className="rounded-xl bg-neon/10 p-2.5 text-neon"><FolderKanban className="h-5 w-5" /></div>
                  <Badge tone={STATUS_TONE[c.status as keyof typeof STATUS_TONE]}>{c.status}</Badge>
                </div>
                <h3 className="mb-1 font-semibold">{c.title}</h3>
                <p className="mb-4 line-clamp-2 text-sm text-mist">{c.description || "No description"}</p>
                <div className="flex items-center gap-2 text-xs text-mist">
                  <Boxes className="h-3.5 w-3.5" /> {c.artifact_count} artifacts
                </div>
              </GlassCard>
            </Link>
          </motion.div>
        ))}
        {cases.length === 0 && (
          <GlassCard className="col-span-full p-10 text-center text-mist">
            No cases yet.{canWrite ? " Create one to begin ingesting a UFDR." : ""}
          </GlassCard>
        )}
      </div>
    </Shell>
  );
}
