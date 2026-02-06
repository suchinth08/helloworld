"use client";

import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Loader2, RefreshCw, UserCheck, Trash2 } from "lucide-react";
import {
  fetchAlerts,
  approveProposedAction,
  rejectProposedAction,
  deleteProposedAction,
  type AgentProposedAction,
} from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

function formatTime(iso: string) {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

interface PendingApprovalsProps {
  planId?: string;
  refreshTrigger?: number;
  onApproveOrReject?: () => void;
}

export default function PendingApprovals({
  planId = DEFAULT_PLAN_ID,
  refreshTrigger = 0,
  onApproveOrReject,
}: PendingApprovalsProps) {
  const [pending, setPending] = useState<AgentProposedAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actingId, setActingId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAlerts(planId);
      setPending(res.pending_actions || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [planId, refreshTrigger]);

  const handleApprove = async (actionId: number) => {
    setActingId(actionId);
    try {
      await approveProposedAction(planId, actionId);
      setPending((prev) => prev.filter((a) => a.id !== actionId));
      onApproveOrReject?.();
    } finally {
      setActingId(null);
    }
  };

  const handleReject = async (actionId: number) => {
    setActingId(actionId);
    try {
      await rejectProposedAction(planId, actionId);
      setPending((prev) => prev.filter((a) => a.id !== actionId));
      onApproveOrReject?.();
    } finally {
      setActingId(null);
    }
  };

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
        <button type="button" onClick={load} className="ml-2 underline hover:no-underline">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <UserCheck className="h-4 w-4 text-[#16a34a]" />
          Human-in-the-loop approvals
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
      {pending.length === 0 ? (
        <p className="text-sm text-[#6b7280]">No pending actions. Ingest an external event to see agent proposals.</p>
      ) : (
        <ul className="space-y-3">
          {pending.map((action) => (
            <li
              key={action.id}
              className="flex flex-col gap-2 p-3 rounded border border-amber-200 bg-amber-50/50"
            >
              <p className="text-sm font-medium text-[#111827]">{action.title}</p>
              {action.description && (
                <p className="text-xs text-[#6b7280]">{action.description}</p>
              )}
              <p className="text-xs text-[#9ca3af]">{formatTime(action.created_at)}</p>
              <div className="flex gap-2 mt-1">
                <button
                  type="button"
                  disabled={actingId === action.id}
                  onClick={() => handleApprove(action.id)}
                  className="inline-flex items-center gap-1 rounded bg-[#16a34a] text-white px-2.5 py-1.5 text-xs font-medium hover:bg-[#15803d] disabled:opacity-50"
                >
                  {actingId === action.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <CheckCircle className="h-3.5 w-3.5" />
                  )}
                  Approve
                </button>
                <button
                  type="button"
                  disabled={actingId === action.id}
                  onClick={() => handleReject(action.id)}
                  className="inline-flex items-center gap-1 rounded border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] hover:bg-[#f9fafb] disabled:opacity-50"
                >
                  <XCircle className="h-3.5 w-3.5" />
                  Reject
                </button>
                <button
                  type="button"
                  disabled={actingId === action.id}
                  onClick={async () => {
                    setActingId(action.id);
                    try {
                      await deleteProposedAction(planId, action.id);
                      setPending((prev) => prev.filter((a) => a.id !== action.id));
                      onApproveOrReject?.();
                    } finally {
                      setActingId(null);
                    }
                  }}
                  className="inline-flex items-center gap-1 rounded border border-[#fecaca] bg-white px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                  title="Delete action (testing)"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
