import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Boxes, FolderKanban, GitBranch, ScanSearch, ShieldAlert } from "lucide-react";
import Shell from "../components/Shell";
import { Badge, GlassCard } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const modules = [
  { icon: FolderKanban, title: "Case Workspace", text: "Create cases, ingest UFDR exports, track chain of custody.", sprint: "Sprint 2" },
  { icon: Boxes, title: "Evidence Explorer", text: "Browse chats, media and metadata as unified evidence records.", sprint: "Sprint 2" },
  { icon: GitBranch, title: "Cross-Modal Search", text: "Natural-language retrieval across every modality.", sprint: "Sprint 3" },
  { icon: ShieldAlert, title: "Consistency Heat-Map", text: "Tamper scores and evidence-gap flags on the case timeline.", sprint: "Sprint 4" },
  { icon: ScanSearch, title: "Agent Console", text: "Ask the investigation agent; receive artifact-cited answers.", sprint: "Sprint 3" },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [dbUp, setDbUp] = useState<boolean | null>(null);

  useEffect(() => {
    api.get("/health").then(() => setApiUp(true)).catch(() => setApiUp(false));
    api.get("/health/db").then(() => setDbUp(true)).catch(() => setDbUp(false));
  }, []);

  return (
    <Shell>
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div className="mb-8 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold">Command Deck</h1>
            <p className="mt-1 text-sm text-mist">Welcome back, {user?.full_name.split(" ")[0]}. The evidence is waiting.</p>
          </div>
          <GlassCard className="flex items-center gap-4 px-5 py-3">
            <Activity className="h-4 w-4 text-neon" />
            <div className="mono flex items-center gap-3 text-[11px] uppercase tracking-wider">
              <span>api {apiUp === null ? "…" : apiUp ? <Badge tone="green">online</Badge> : <Badge tone="red">down</Badge>}</span>
              <span>db {dbUp === null ? "…" : dbUp ? <Badge tone="green">online</Badge> : <Badge tone="red">down</Badge>}</span>
            </div>
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {modules.map(({ icon: Icon, title, text, sprint }, i) => (
            <motion.div key={title} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
              <GlassCard className="h-full p-6 opacity-80 transition hover:opacity-100">
                <div className="mb-4 flex items-center justify-between">
                  <div className="rounded-xl bg-pulse/10 p-3 text-pulse"><Icon className="h-5 w-5" /></div>
                  <Badge tone="amber">{sprint}</Badge>
                </div>
                <h3 className="mb-1 font-semibold">{title}</h3>
                <p className="text-sm text-mist">{text}</p>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </Shell>
  );
}
