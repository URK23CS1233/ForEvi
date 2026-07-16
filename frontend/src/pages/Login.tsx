import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Fingerprint, LockKeyhole } from "lucide-react";
import GraphBackground from "../components/GraphBackground";
import { Field, GlassCard, NeonButton } from "../components/ui";
import { useAuth } from "../lib/auth";
import { apiErrorMessage } from "../lib/api";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      nav("/dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-4">
      <div className="grid-floor absolute inset-0" />
      <GraphBackground density={40} />
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="relative z-10 w-full max-w-md">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2">
          <Fingerprint className="h-7 w-7 text-neon" />
          <span className="text-2xl font-bold">For<span className="neon-text">Evi</span></span>
        </Link>
        <GlassCard className="p-8">
          <div className="mb-6 flex items-center gap-3">
            <div className="rounded-xl bg-neon/10 p-2.5 text-neon"><LockKeyhole className="h-5 w-5" /></div>
            <div>
              <h1 className="text-lg font-semibold">Investigator sign-in</h1>
              <p className="mono text-[11px] uppercase tracking-widest text-mist">restricted system · all actions audited</p>
            </div>
          </div>
          <form onSubmit={(e) => { void onSubmit(e); }} className="space-y-4">
            <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
            <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            {error && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
            )}
            <NeonButton type="submit" disabled={busy} className="w-full">
              {busy ? "Authenticating…" : "Access console"}
            </NeonButton>
          </form>
          <p className="mt-6 text-center text-sm text-mist">
            No account? <Link to="/register" className="text-neon hover:underline">Request access</Link>
          </p>
        </GlassCard>
      </motion.div>
    </div>
  );
}
