import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Brain, FileSearch, Fingerprint, GitBranch, Languages, MessageSquareText, ScanSearch, ShieldAlert,
} from "lucide-react";
import GraphBackground from "../components/GraphBackground";
import { GlassCard } from "../components/ui";

const features = [
  { icon: MessageSquareText, title: "Natural-Language Querying", text: "Ask in plain words — “chats containing crypto addresses”, “calls to foreign numbers” — and get artifact-cited answers." },
  { icon: GitBranch, title: "Cross-Modal Correlation", text: "Chats, images and metadata live in one evidence space. A photo is linked to the conversation that references it." },
  { icon: ShieldAlert, title: "Tamper Detection", text: "Predictive consistency scoring flags timestamp edits, planted media and EXIF contradictions." },
  { icon: ScanSearch, title: "Evidence-Gap Detection", text: "Confident predictions at empty timeline slots expose deleted artifacts referenced in surrounding chatter." },
  { icon: Brain, title: "Agentic Investigation", text: "A ReAct agent drives deterministic forensic tools — every claim in every report cites artifact IDs." },
  { icon: Languages, title: "Multilingual Evidence", text: "BGE-M3 embeddings understand Hindi, Tamil and code-mixed chats — built for Indian casework." },
];

const stats = [
  ["100%", "on-premise · evidence never leaves the machine"],
  ["0", "generative claims in the analysis core"],
  ["4", "role-based access tiers with hash-chained audit"],
];

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-void">
      <div className="grid-floor absolute inset-0" />
      <GraphBackground />
      <div className="scanline pointer-events-none absolute inset-0" />

      <header className="relative z-10 flex items-center justify-between px-8 py-6">
        <div className="flex items-center gap-2">
          <Fingerprint className="h-7 w-7 text-neon" />
          <span className="text-xl font-bold tracking-tight">For<span className="neon-text">Evi</span></span>
        </div>
        <nav className="flex items-center gap-3">
          <Link to="/login" className="rounded-xl border border-line px-4 py-2 text-sm text-mist transition hover:border-neon/50 hover:text-white">
            Sign in
          </Link>
          <Link to="/register" className="rounded-xl bg-gradient-to-r from-neon to-pulse px-4 py-2 text-sm font-semibold text-void shadow-[0_0_24px_rgba(34,211,238,0.35)] transition hover:shadow-[0_0_36px_rgba(139,92,246,0.5)]">
            Request access
          </Link>
        </nav>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl px-8">
        <motion.section
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="pt-16 pb-20 text-center"
        >
          <div className="mono mb-6 inline-block rounded-full border border-neon/30 px-4 py-1.5 text-[11px] uppercase tracking-[0.3em] text-neon">
            forensic evidence intelligence
          </div>
          <h1 className="mx-auto max-w-4xl text-5xl font-bold leading-tight tracking-tight md:text-7xl">
            The UFDR speaks in <span className="neon-text">every modality.</span><br />Now you can listen.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-mist">
            Agentic AI-based investigation of Universal Forensic Extraction Device Reports —
            correlating chats, images and metadata into court-ready, artifact-cited intelligence.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Link to="/login" className="rounded-xl bg-gradient-to-r from-neon to-pulse px-8 py-3.5 font-semibold text-void shadow-[0_0_30px_rgba(34,211,238,0.4)] transition hover:shadow-[0_0_44px_rgba(139,92,246,0.55)]">
              Enter the console
            </Link>
            <a href="#capabilities" className="rounded-xl border border-line px-8 py-3.5 text-mist transition hover:border-neon/40 hover:text-white">
              See capabilities
            </a>
          </div>

          <div className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-3">
            {stats.map(([n, label]) => (
              <GlassCard key={label} className="px-5 py-4">
                <div className="neon-text text-3xl font-bold">{n}</div>
                <div className="mt-1 text-xs leading-relaxed text-mist">{label}</div>
              </GlassCard>
            ))}
          </div>
        </motion.section>

        <section id="capabilities" className="pb-24">
          <div className="mb-10 flex items-center gap-3">
            <FileSearch className="h-5 w-5 text-neon" />
            <h2 className="text-2xl font-semibold">Capabilities</h2>
            <div className="h-px flex-1 bg-gradient-to-r from-line to-transparent" />
          </div>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, text }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.5, delay: i * 0.07 }}
              >
                <GlassCard className="group h-full p-6 transition hover:border-neon/30">
                  <div className="mb-4 inline-flex rounded-xl bg-neon/10 p-3 text-neon transition group-hover:bg-neon/20">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mb-2 font-semibold">{title}</h3>
                  <p className="text-sm leading-relaxed text-mist">{text}</p>
                </GlassCard>
              </motion.div>
            ))}
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-line/60 px-8 py-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between text-xs text-mist">
          <span className="mono">FOREVI · project 23CS2999 · SIH PS 25198 (MHA/NIA)</span>
          <span>Karunya Institute of Technology and Sciences</span>
        </div>
      </footer>
    </div>
  );
}
