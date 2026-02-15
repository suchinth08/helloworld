"use client";

import { useState } from "react";
import { MessageCircle, Send, Loader2, X } from "lucide-react";
import { sendChatMessage } from "@/lib/congressTwinApi";
import { usePlanId } from "./PlanContext";

const SUGGESTIONS = [
  "What needs attention today?",
  "Critical path status",
  "Assignees with high workload",
  "Impact of delaying task",
];

interface ChatPanelProps {
  onClose?: () => void;
  halfPage?: boolean;
}

export default function ChatPanel({ onClose, halfPage }: ChatPanelProps) {
  const planId = usePlanId();
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<{ type: string; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const send = async () => {
    if (!message.trim()) return;
    setLoading(true);
    setResponse(null);
    try {
      const res = await sendChatMessage(planId, message.trim());
      setResponse({ type: res.type || "response", text: res.text || JSON.stringify(res) });
    } catch (e) {
      setResponse({ type: "error", text: e instanceof Error ? e.message : "Failed" });
    } finally {
      setLoading(false);
    }
  };

  const containerClass = halfPage
    ? "flex flex-col h-full border-r border-[#e5e7eb] bg-white"
    : "ct-card p-4";

  return (
    <div className={containerClass}>
      <div className="flex items-center justify-between p-4 border-b border-[#e5e7eb] flex-shrink-0">
        <h3 className="text-sm font-semibold text-[#111827] flex items-center gap-2">
          <MessageCircle className="h-4 w-4" />
          Chat
        </h3>
        {halfPage && onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
            aria-label="Close chat"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
      <div className={`flex flex-col ${halfPage ? "flex-1 min-h-0 p-4" : "space-y-2"}`}>
        {halfPage && (
          <p className="text-xs text-[#6b7280] mb-3">
            Ask about tasks, critical path, impacts, or assignees.
          </p>
        )}
        <div className="flex gap-2 flex-shrink-0">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask about your plan..."
            className="flex-1 rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={send}
            disabled={loading}
            className="rounded-lg bg-[#16a34a] px-3 py-2 text-white hover:bg-[#15803d] disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
        {!halfPage && (
          <p className="text-xs text-[#6b7280]">Try: {SUGGESTIONS.slice(0, 2).join(", ")}</p>
        )}
        {halfPage && (
          <p className="text-xs text-[#9ca3af] mt-2">
            Suggestions: {SUGGESTIONS.join(" · ")}
          </p>
        )}
        <div className={`mt-3 flex-1 min-h-0 overflow-auto ${halfPage ? "rounded-lg bg-[#f9fafb] border border-[#e5e7eb] p-3" : ""}`}>
          {response && (
            <div className="text-sm text-[#374151] whitespace-pre-wrap">
              {response.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
