"use client";

import { useEffect, useState } from "react";
import { GitBranch, Loader2, RefreshCw } from "lucide-react";
import { fetchCriticalPath, type CriticalPathResponse, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface CriticalPathSectionProps {
  planId?: string;
  refreshTrigger?: number;
}

function formatDate(iso: string | undefined) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function CriticalPathSection({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: CriticalPathSectionProps) {
  const [data, setData] = useState<CriticalPathResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCriticalPath(planId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load critical path");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [planId, refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-4 flex items-center gap-2 text-[#6b7280] text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading critical path…
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
        <button
          type="button"
          onClick={load}
          className="ml-2 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }
  if (!data || data.critical_path.length === 0) {
    return (
      <div className="ct-card p-5">
        <h2 className="text-base font-bold text-[#111827] mb-2 flex items-center gap-2">
          <div className="rounded p-1.5 bg-[#dcfce7]">
            <GitBranch className="h-4 w-4 text-[#16a34a]" />
          </div>
          Critical path
        </h2>
        <p className="text-sm text-[#6b7280]">No critical path for this plan.</p>
      </div>
    );
  }

  return (
    <div className="ct-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <div className="rounded p-1.5 bg-[#dcfce7]">
            <GitBranch className="h-4 w-4 text-[#16a34a]" />
          </div>
          Critical path
        </h2>
        <button
          type="button"
          onClick={load}
          className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
          aria-label="Refresh critical path"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      <p className="text-sm text-[#6b7280] mb-3">
        Longest dependency chain — delays here affect the plan end date.
      </p>
      <ol className="flex flex-wrap gap-2 items-center">
        {data.critical_path.map((task, i) => (
          <li key={task.id} className="flex items-center gap-2">
            {i > 0 && (
              <span className="text-[#d1d5db] text-xs font-medium">→</span>
            )}
            <span
              className="inline-flex flex-wrap items-center gap-1.5 rounded-full border border-[#bbf7d0] bg-[#dcfce7] px-3 py-1.5 text-sm text-[#166534] font-medium"
              title={[task.assigneeNames?.length ? `Owner: ${task.assigneeNames.join(", ")}` : null, `Due: ${formatDate(task.dueDateTime)}`, task.status ? `Status: ${task.status}` : null].filter(Boolean).join(" · ")}
            >
              <span className="truncate max-w-[12rem]">{task.title}</span>
              <span className="text-[#16a34a] text-xs shrink-0">
                {formatDate(task.dueDateTime)}
              </span>
              {task.assigneeNames?.length ? (
                <span className="text-[#15803d] text-xs shrink-0">· {task.assigneeNames.join(", ")}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
