"use client";

import { useEffect, useState } from "react";
import { BarChart3, Loader2, RefreshCw } from "lucide-react";
import { fetchProbabilityGantt, type ProbabilityGanttBar } from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}

function parseDate(iso: string | null): number {
  if (!iso) return 0;
  try {
    return new Date(iso).getTime();
  } catch {
    return 0;
  }
}

interface ProbabilityGanttProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function ProbabilityGantt({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: ProbabilityGanttProps) {
  const [data, setData] = useState<{ bars: ProbabilityGanttBar[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchProbabilityGantt(planId);
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
      <div className="ct-card p-6 flex items-center justify-center min-h-[200px] text-[#6b7280]">
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
  if (!data || data.bars.length === 0) {
    return (
      <div className="ct-card p-5">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2 mb-2">
          <BarChart3 className="h-4 w-4 text-[#16a34a]" />
          Probability Gantt
        </h3>
        <p className="text-sm text-[#6b7280]">No schedule data.</p>
      </div>
    );
  }

  const bars = data.bars;
  const minStart = Math.min(...bars.map((b) => parseDate(b.start_date)).filter(Boolean)) || Date.now();
  const maxEnd = Math.max(...bars.map((b) => parseDate(b.end_date))) || Date.now();
  const totalRange = maxEnd - minStart || 1;
  const totalDays = totalRange / (24 * 60 * 60 * 1000);
  const pxPerDay = Math.max(3, Math.min(12, 400 / totalDays));
  const timelineWidthPx = Math.round(totalDays * pxPerDay);
  const timelineWidth = Math.max(320, timelineWidthPx);

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-[#16a34a]" />
          Probability Gantt
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
        Monte Carlo variance — gradient reflects confidence. Delays on critical path affect plan end.
      </p>
      <div className="space-y-3 overflow-x-auto">
        {bars.map((bar) => {
          const start = parseDate(bar.start_date) || minStart;
          const end = parseDate(bar.end_date) || start;
          const leftPx = Math.round(((start - minStart) / totalRange) * timelineWidth);
          const widthPx = Math.max(20, Math.round(((end - start) / totalRange) * timelineWidth));
          const confidence = bar.confidence_percent;
          const isCritical = bar.on_critical_path;
          return (
            <div key={bar.id} className="flex items-center gap-3 min-w-0">
              <div className="w-40 shrink-0">
                <p className="text-sm font-medium text-[#111827] truncate" title={bar.title}>{bar.title}</p>
                <p className="text-xs text-[#6b7280]">
                  {formatDate(bar.start_date)} → {formatDate(bar.end_date)} · {confidence}%
                </p>
              </div>
              <div
                className="h-8 rounded-md bg-[#e5e7eb] relative shrink-0 overflow-visible"
                style={{ width: timelineWidth, minWidth: timelineWidth }}
              >
                <div
                  className="absolute top-0 bottom-0 rounded-md flex items-center justify-end pr-1 min-w-[20px]"
                  style={{
                    left: leftPx,
                    width: widthPx,
                    background: isCritical
                      ? `linear-gradient(90deg, rgba(22, 163, 74, ${confidence / 100}), rgba(21, 128, 61, 0.9))`
                      : `linear-gradient(90deg, rgba(37, 99, 235, ${confidence / 100}), rgba(37, 99, 235, 0.7))`,
                    color: "white",
                    fontSize: "11px",
                  }}
                >
                  {bar.variance_days}d
                </div>
              </div>
              {isCritical && (
                <span className="shrink-0 rounded bg-[#dcfce7] px-1.5 py-0.5 text-xs font-medium text-[#166534]">CP</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
