"use client";

import { useEffect, useState } from "react";
import { MessageSquare, Loader2, RefreshCw, ArrowRight } from "lucide-react";
import { fetchMitigationFeed, type MitigationIntervention } from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

interface AgentMitigationFeedProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function AgentMitigationFeed({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: AgentMitigationFeedProps) {
  const [data, setData] = useState<{ interventions: MitigationIntervention[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchMitigationFeed(planId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [planId, refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-6 flex items-center justify-center min-h-[160px] text-[#6b7280]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card p-4 border-red-200 bg-red-50 text-sm text-red-700">
        {error}
        <button type="button" onClick={load} className="ml-2 underline hover:no-underline">Retry</button>
      </div>
    );
  }
  if (!data || data.interventions.length === 0) {
    return (
      <div className="ct-card p-5">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2 mb-2">
          <MessageSquare className="h-4 w-4 text-[#16a34a]" />
          Agent Mitigation Feed
        </h3>
        <p className="text-sm text-[#6b7280]">No interventions yet.</p>
      </div>
    );
  }

  const actionStyle: Record<string, string> = {
    shifted: "bg-[#dcfce7] text-[#166534]",
    updated: "bg-[#dbeafe] text-[#1e40af]",
    flagged: "bg-[#fef3c7] text-amber-800",
  };

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-[#16a34a]" />
          Agent Mitigation Feed
        </h3>
        <button
          type="button"
          onClick={load}
          className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
          aria-label="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      <p className="text-sm text-[#6b7280] mb-4">
        Interventions and reasoning from OptimizationAgent, MonitorAgent, VeevaAgent.
      </p>
      <ul className="space-y-3">
        {data.interventions.map((int) => (
          <li
            key={int.id}
            className="rounded-lg border border-[#e5e7eb] bg-white p-3 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${actionStyle[int.action] ?? "bg-[#f3f4f6] text-[#374151]"}`}>
                {int.action}
              </span>
              <span className="text-sm font-medium text-[#111827]">{int.task_title}</span>
              <ArrowRight className="h-3 w-3 text-[#9ca3af]" />
            </div>
            <p className="text-sm text-[#6b7280]">{int.reason}</p>
            <p className="mt-1 text-xs text-[#9ca3af]">{formatTime(int.at)}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
