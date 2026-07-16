import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Upload, Search, ShieldAlert, Coins, Phone, Loader2, Boxes } from "lucide-react";
import Shell from "../components/Shell";
import { Badge, GlassCard, NeonButton } from "../components/ui";
import EvidenceItem from "../components/EvidenceItem";
import type { Evidence } from "../components/EvidenceItem";
import { api, apiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useRealtime } from "../lib/useRealtime";

interface CaseT { id: string; title: string; description: string; status: string; artifact_count: number; }
interface Job { id: string; filename: string; status: string; progress: number; processed: number; total: number; message: string; }
interface Entity { id: string; entity_type: string; value: string; normalized: string; is_foreign: boolean; }

export default function CaseDetail() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const canWrite = user?.role !== "AUDITOR";
  const [cas, setCas] = useState<CaseT | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("keyword");
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadAll = useCallback(async () => {
    try {
      const [c, ev, en] = await Promise.all([
        api.get<CaseT>(`/cases/${id}`),
        api.get<Evidence[]>(`/cases/${id}/evidence?limit=300`),
        api.get<Entity[]>(`/cases/${id}/entities`),
      ]);
      setCas(c.data); setEvidence(ev.data); setEntities(en.data);
    } catch (e) { setError(apiErrorMessage(e)); }
  }, [id]);
  useEffect(() => { void loadAll(); }, [loadAll]);

  // realtime ingestion progress
  useRealtime(id, (e) => {
    if (e.type === "ingestion_progress") {
      setJob({
        id: e.job_id as string, filename: (e.filename as string) ?? "upload",
        status: e.status as string, progress: (e.progress as number) ?? 0,
        processed: (e.processed as number) ?? 0, total: (e.total as number) ?? 0,
        message: (e.message as string) ?? "",
      });
      if (e.status === "done") void loadAll();
    }
  });

  async function onUpload(file: File) {
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await api.post<Job>(`/cases/${id}/upload`, form);
      setJob({ ...data, progress: 0 });
    } catch (e) { setError(apiErrorMessage(e)); }
  }

  async function runSearch() {
    if (!q.trim()) { void loadAll(); return; }
    setSearching(true);
    try {
      const { data } = await api.get(`/cases/${id}/search`, { params: { q, mode, limit: 100 } });
      setEvidence(data.results);
    } catch (e) { setError(apiErrorMessage(e)); }
    finally { setSearching(false); }
  }

  async function recompute() {
    try { await api.post(`/cases/${id}/consistency`); await loadAll(); }
    catch (e) { setError(apiErrorMessage(e)); }
  }

  const crypto = entities.filter((e) => e.entity_type === "CRYPTO");
  const foreign = entities.filter((e) => e.entity_type === "PHONE" && e.is_foreign);
  const running = job && job.status === "running";

  return (
    <Shell>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold">{cas?.title ?? "Case"}</h1>
          <p className="mt-1 text-sm text-mist">{cas?.description}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone="cyan">{cas?.artifact_count ?? 0} artifacts</Badge>
          {canWrite && <NeonButton variant="ghost" onClick={() => { void recompute(); }}>
            <span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> Score consistency</span>
          </NeonButton>}
          {canWrite && <>
            <input ref={fileRef} type="file" className="hidden"
              accept=".json,.xml,.csv,.tsv,.sqlite,.db,.sqlite3"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) void onUpload(f); e.target.value = ""; }} />
            <NeonButton onClick={() => fileRef.current?.click()}>
              <span className="flex items-center gap-2"><Upload className="h-4 w-4" /> Ingest UFDR</span>
            </NeonButton>
          </>}
        </div>
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {job && (job.status !== "done" || running) && (
        <GlassCard className="mb-6 p-5">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 font-medium">
              {running ? <Loader2 className="h-4 w-4 animate-spin text-neon" /> : <Boxes className="h-4 w-4 text-neon" />}
              Ingesting {job.filename}
            </span>
            <span className="mono text-mist">{job.processed} / {job.total} · {job.progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-abyss">
            <motion.div className="h-full bg-gradient-to-r from-neon to-pulse"
              animate={{ width: `${job.progress}%` }} transition={{ ease: "easeOut" }} />
          </div>
          <div className="mono mt-2 text-xs text-mist">{job.message}</div>
        </GlassCard>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-3 flex gap-2">
            <div className="flex flex-1 items-center gap-2 rounded-xl border border-line bg-abyss/60 px-3">
              <Search className="h-4 w-4 text-mist" />
              <input value={q} onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void runSearch(); }}
                placeholder="Ask: dock, crypto address, threatening message..."
                className="w-full bg-transparent py-2.5 text-sm text-white outline-none" />
            </div>
            <select value={mode} onChange={(e) => setMode(e.target.value)}
              className="rounded-xl border border-line bg-abyss px-3 text-sm text-white">
              <option value="keyword">keyword</option>
              <option value="semantic">semantic</option>
              <option value="entity">entity</option>
            </select>
            <NeonButton onClick={() => { void runSearch(); }}>{searching ? "..." : "Search"}</NeonButton>
          </div>
          <div className="space-y-2">
            {evidence.map((e) => <EvidenceItem key={e.id} e={e} />)}
            {evidence.length === 0 && <GlassCard className="p-8 text-center text-mist">No evidence. Ingest a UFDR to populate this case.</GlassCard>}
          </div>
        </div>

        <div className="space-y-4">
          <GlassCard className="p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Coins className="h-4 w-4 text-ember" /> Cryptocurrency ({crypto.length})</div>
            <div className="space-y-1">
              {crypto.slice(0, 12).map((e) => <div key={e.id} className="mono truncate text-xs text-mist">{e.value}</div>)}
              {crypto.length === 0 && <div className="text-xs text-mist">none detected</div>}
            </div>
          </GlassCard>
          <GlassCard className="p-5">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><Phone className="h-4 w-4 text-neon" /> Foreign numbers ({foreign.length})</div>
            <div className="space-y-1">
              {foreign.slice(0, 12).map((e) => <div key={e.id} className="mono text-xs text-mist">{e.normalized}</div>)}
              {foreign.length === 0 && <div className="text-xs text-mist">none detected</div>}
            </div>
          </GlassCard>
        </div>
      </div>
    </Shell>
  );
}
