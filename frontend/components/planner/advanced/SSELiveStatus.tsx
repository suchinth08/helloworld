"use client";

import { useEffect, useState } from "react";
import { Radio, Loader2, WifiOff } from "lucide-react";
import { getStreamUrl, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface SSELiveStatusProps {
  planId?: string;
}

export default function SSELiveStatus({ planId = DEFAULT_PLAN_ID }: SSELiveStatusProps) {
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("disconnected");
  const [lastMessage, setLastMessage] = useState<string | null>(null);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    const url = getStreamUrl(planId);
    setStatus("connecting");
    setLastMessage(null);

    try {
      eventSource = new EventSource(url);
      eventSource.onopen = () => setStatus("connected");
      eventSource.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          setLastMessage(d.message || d.type || "Update");
        } catch {
          setLastMessage("Update");
        }
      };
      eventSource.onerror = () => {
        setStatus("error");
        eventSource?.close();
      };
    } catch {
      setStatus("error");
    }

    return () => {
      eventSource?.close();
      setStatus("disconnected");
    };
  }, [planId]);

  return (
    <div className="ct-card p-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        {status === "connecting" && <Loader2 className="h-5 w-5 animate-spin text-[#6b7280]" />}
        {status === "connected" && <Radio className="h-5 w-5 text-[#16a34a]" />}
        {(status === "disconnected" || status === "error") && <WifiOff className="h-5 w-5 text-[#6b7280]" />}
        <div>
          <p className="text-sm font-medium text-[#111827]">
            {status === "connected" ? "Live" : status === "connecting" ? "Connecting…" : "Plan vs Reality"}
          </p>
          <p className="text-xs text-[#6b7280]">
            {status === "connected" ? "SSE connected — real-time updates" : lastMessage || "Connect for live updates"}
          </p>
        </div>
      </div>
      <span
        className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          status === "connected"
            ? "bg-[#dcfce7] text-[#166534]"
            : status === "connecting"
              ? "bg-[#fef3c7] text-amber-800"
              : "bg-[#f3f4f6] text-[#6b7280]"
        }`}
      >
        {status === "connected" ? "Live" : status === "connecting" ? "…" : "Off"}
      </span>
    </div>
  );
}
