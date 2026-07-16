import { useEffect, useRef } from "react";
import { connectRealtime } from "./realtime";
import type { RealtimeEvent } from "./realtime";

export function useRealtime(caseId: string | null, onEvent: (e: RealtimeEvent) => void) {
  const cb = useRef(onEvent);
  cb.current = onEvent;
  useEffect(() => {
    const disconnect = connectRealtime(caseId, (e) => cb.current(e));
    return disconnect;
  }, [caseId]);
}
