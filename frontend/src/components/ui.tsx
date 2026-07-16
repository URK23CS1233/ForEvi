import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { motion } from "framer-motion";

export function GlassCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`glass rounded-2xl ${className}`}>{children}</div>;
}

export function NeonButton({
  children, onClick, type = "button", disabled, variant = "primary", className = "",
}: {
  children: ReactNode; onClick?: () => void; type?: "button" | "submit";
  disabled?: boolean; variant?: "primary" | "ghost" | "danger"; className?: string;
}) {
  const styles = {
    primary: "bg-gradient-to-r from-neon/90 to-pulse/90 text-void font-semibold shadow-[0_0_24px_rgba(34,211,238,0.35)] hover:shadow-[0_0_36px_rgba(139,92,246,0.5)]",
    ghost: "border border-line text-mist hover:border-neon/50 hover:text-white",
    danger: "border border-red-500/40 text-red-300 hover:bg-red-500/10",
  } as const;
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      whileHover={{ y: -1 }}
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-xl px-5 py-2.5 text-sm transition-all disabled:opacity-40 disabled:pointer-events-none ${styles[variant]} ${className}`}
    >
      {children}
    </motion.button>
  );
}

export function Field(props: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-widest text-mist">{label}</span>
      <input
        {...rest}
        className="w-full rounded-xl border border-line bg-abyss/80 px-4 py-2.5 text-sm text-white outline-none transition focus:border-neon/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.12)]"
      />
    </label>
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement> & { label: string; children: ReactNode }) {
  const { label, children, ...rest } = props;
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-widest text-mist">{label}</span>
      <select
        {...rest}
        className="w-full rounded-xl border border-line bg-abyss/80 px-4 py-2.5 text-sm text-white outline-none transition focus:border-neon/60"
      >
        {children}
      </select>
    </label>
  );
}

export function Badge({ children, tone = "cyan" }: { children: ReactNode; tone?: "cyan" | "violet" | "amber" | "red" | "green" }) {
  const tones = {
    cyan: "border-neon/40 text-neon",
    violet: "border-pulse/40 text-pulse",
    amber: "border-ember/40 text-ember",
    red: "border-red-500/40 text-red-400",
    green: "border-emerald-500/40 text-emerald-400",
  } as const;
  return (
    <span className={`mono inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] uppercase tracking-wider ${tones[tone]}`}>
      {children}
    </span>
  );
}
