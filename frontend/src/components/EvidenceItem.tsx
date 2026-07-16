import { Image, MessageSquare, Phone, User, FileText, ShieldAlert } from "lucide-react";
import { Badge } from "./ui";

export interface Evidence {
  id: string; modality: string; source_app: string; sender: string; recipient: string;
  content: string; timestamp: string | null; consistency_score: number | null;
}

const ICON = { CHAT: MessageSquare, CALL: Phone, IMAGE: Image, CONTACT: User, FILE: FileText, METADATA: FileText };

export default function EvidenceItem({ e }: { e: Evidence }) {
  const Icon = ICON[e.modality as keyof typeof ICON] ?? FileText;
  const flagged = (e.consistency_score ?? 0) > 0.62;
  return (
    <div className={`flex gap-3 rounded-xl border p-3 transition ${flagged ? "border-red-500/40 bg-red-500/5" : "border-line bg-abyss/40"}`}>
      <div className={`mt-0.5 rounded-lg p-2 ${flagged ? "bg-red-500/10 text-red-300" : "bg-neon/10 text-neon"}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-mist">
          <Badge tone="cyan">{e.modality}</Badge>
          {e.source_app && <span className="mono">{e.source_app}</span>}
          {e.sender && <span className="mono">{e.sender}</span>}
          {e.recipient && <span className="mono">→ {e.recipient}</span>}
          {e.timestamp && <span className="mono">{new Date(e.timestamp).toLocaleString()}</span>}
          {flagged && (
            <span className="flex items-center gap-1 text-red-300">
              <ShieldAlert className="h-3 w-3" /> inconsistent {e.consistency_score?.toFixed(2)}
            </span>
          )}
        </div>
        <div className="break-words text-sm text-white/90">{e.content || <span className="text-mist italic">no text</span>}</div>
      </div>
    </div>
  );
}
