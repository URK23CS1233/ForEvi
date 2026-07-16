import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, Fingerprint, UserPlus } from "lucide-react";
import GraphBackground from "../components/GraphBackground";
import { Field, GlassCard, NeonButton, Select } from "../components/ui";
import { api, apiErrorMessage } from "../lib/api";

export default function Register() {
  const [form, setForm] = useState({ full_name: "", email: "", password: "", requested_role: "INVESTIGATING_OFFICER" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/register", form);
      setDone(true);
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
          {done ? (
            <div className="py-6 text-center">
              <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-400" />
              <h1 className="mb-2 text-lg font-semibold">Request submitted</h1>
              <p className="text-sm leading-relaxed text-mist">
                Your account is <span className="text-ember">awaiting administrator approval</span>.
                You will be able to sign in once an admin activates it.
              </p>
              <Link to="/login" className="mt-6 inline-block text-sm text-neon hover:underline">Back to sign-in</Link>
            </div>
          ) : (
            <>
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-pulse/10 p-2.5 text-pulse"><UserPlus className="h-5 w-5" /></div>
                <div>
                  <h1 className="text-lg font-semibold">Request access</h1>
                  <p className="mono text-[11px] uppercase tracking-widest text-mist">admin approval required</p>
                </div>
              </div>
              <form onSubmit={(e) => { void onSubmit(e); }} className="space-y-4">
                <Field label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required minLength={2} />
                <Field label="Official email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
                <Select label="Requested role" value={form.requested_role} onChange={(e) => setForm({ ...form, requested_role: e.target.value })}>
                  <option value="INVESTIGATING_OFFICER">Investigating Officer</option>
                  <option value="FORENSIC_ANALYST">Forensic Analyst</option>
                  <option value="AUDITOR">Auditor</option>
                </Select>
                <Field label="Password (min 10 chars)" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={10} />
                {error && <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
                <NeonButton type="submit" disabled={busy} className="w-full">
                  {busy ? "Submitting…" : "Submit request"}
                </NeonButton>
              </form>
            </>
          )}
        </GlassCard>
      </motion.div>
    </div>
  );
}
