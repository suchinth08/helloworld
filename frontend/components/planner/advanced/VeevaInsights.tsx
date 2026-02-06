"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Users, Activity, Loader2, RefreshCw } from "lucide-react";
import { fetchVeevaInsights } from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

interface VeevaInsightsProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function VeevaInsights({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: VeevaInsightsProps) {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchVeevaInsights>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchVeevaInsights(planId);
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
  if (!data) return null;

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-[#16a34a]" />
          Veeva Insights
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
      <p className="text-sm text-[#6b7280] mb-4">{data.summary}</p>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] p-4">
          <div className="flex items-center gap-2 mb-1">
            <Users className="h-4 w-4 text-[#16a34a]" />
            <span className="text-xs font-semibold uppercase tracking-wide text-[#6b7280]">KOL alignment</span>
          </div>
          <p className="text-2xl font-bold text-[#111827]">{data.kol_alignment_score}%</p>
          <p className="text-xs text-[#6b7280]">{data.kol_alignment_trend === "up" ? "Trending up" : "Stable"}</p>
        </div>
        <div className="rounded-lg border border-[#e5e7eb] bg-[#f9fafb] p-4">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="h-4 w-4 text-[#16a34a]" />
            <span className="text-xs font-semibold uppercase tracking-wide text-[#6b7280]">Staff fatigue</span>
          </div>
          <p className="text-2xl font-bold text-[#111827]">{data.staff_fatigue_index}</p>
          <p className="text-xs text-[#6b7280]">{data.staff_fatigue_trend === "down" ? "Within target" : "Monitor"}</p>
        </div>
      </div>
      <ul className="space-y-2">
        {data.insights.map((ins) => (
          <li key={ins.id} className="flex items-start gap-2 rounded border border-[#e5e7eb] bg-white p-2 text-sm">
            <span className="font-medium text-[#111827]">{ins.title}:</span>
            <span className="text-[#16a34a] font-semibold">{ins.value}</span>
            <span className="text-[#6b7280]">— {ins.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
