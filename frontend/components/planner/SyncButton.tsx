"use client";

import { useState } from "react";
import { RefreshCw, Loader2, Check, AlertCircle } from "lucide-react";
import { syncPlannerPlan, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface SyncButtonProps {
  onSyncSuccess?: () => void;
}

export default function SyncButton({ onSyncSuccess }: SyncButtonProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    status: "ok" | "error";
    source: string;
    tasks_synced: number;
    message: string;
  } | null>(null);

  const handleSync = async () => {
    setLoading(true);
    setResult(null);
    try {
      const data = await syncPlannerPlan(DEFAULT_PLAN_ID);
      setResult({
        status: data.status,
        source: data.source,
        tasks_synced: data.tasks_synced,
        message: data.message,
      });
      if (data.status === "ok") onSyncSuccess?.();
    } catch (e) {
      setResult({
        status: "error",
        source: "—",
        tasks_synced: 0,
        message: e instanceof Error ? e.message : "Sync failed",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {result && (
        <span
          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm ${
            result.status === "ok"
              ? "bg-[#dcfce7] text-[#166534]"
              : "bg-red-50 text-red-700"
          }`}
        >
          {result.status === "ok" ? (
            <Check className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <span>
            {result.status === "ok"
              ? `Synced ${result.tasks_synced} tasks (${result.source})`
              : result.message}
          </span>
        </span>
      )}
      <button
        type="button"
        onClick={handleSync}
        disabled={loading}
        className="inline-flex items-center gap-2 rounded-lg bg-[#16a34a] px-3 py-2 text-sm font-medium text-white shadow-sm hover:bg-[#15803d] disabled:opacity-60"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <RefreshCw className="h-4 w-4" />
        )}
        Sync from Planner
      </button>
    </div>
  );
}
