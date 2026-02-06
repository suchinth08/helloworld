"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, RefreshCw, CalendarX, UserX, Trash2, CheckCircle, XCircle } from "lucide-react";
import {
  fetchAlerts,
  deleteExternalEvent,
  approveProposedAction,
  rejectProposedAction,
  deleteProposedAction,
  type AlertsResponse,
  type ExternalEvent,
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

function EventIcon({ eventType }: { eventType: string }) {
  if (eventType === "flight_cancellation") return <CalendarX className="h-4 w-4 text-amber-600" />;
  if (eventType === "participant_meeting_cancelled") return <UserX className="h-4 w-4 text-rose-600" />;
  return <AlertTriangle className="h-4 w-4 text-[#6b7280]" />;
}

interface AlertsDashboardProps {
  planId?: string;
  refreshTrigger?: number;
  compact?: boolean;
  onDeleteEvent?: () => void;
}

export default function AlertsDashboard({
  planId = DEFAULT_PLAN_ID,
  refreshTrigger = 0,
  compact = false,
  onDeleteEvent,
}: AlertsDashboardProps) {
  const [data, setData] = useState<AlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [actingActionId, setActingActionId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAlerts(planId);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [planId, refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-4 flex items-center gap-2 text-[#6b7280]">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading alerts…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card p-4 border-red-200 bg-red-50 text-sm text-red-700 flex items-center justify-between">
        <span>{error}</span>
        <button type="button" onClick={load} className="underline hover:no-underline">
          Retry
        </button>
      </div>
    );
  }

  const events = data?.external_events ?? [];
  const pending = data?.pending_actions ?? [];
  const hasAny = events.length > 0 || pending.length > 0;

  if (compact) {
    return (
      <div className="ct-card p-3 flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          <span className="text-sm font-medium text-[#111827]">Alerts &amp; pending actions</span>
          <span className="text-sm text-[#6b7280]">
            {events.length} event(s), {pending.length} pending approval(s)
          </span>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
          aria-label="Refresh"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          Alerts &amp; external events
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
      {!hasAny && (
        <p className="text-sm text-[#6b7280]">No external events or pending actions. Ingest an event (e.g. flight cancellation) to see agent proposals.</p>
      )}
      {events.length > 0 && (
        <div className="space-y-2 mb-4">
          <p className="text-xs font-medium text-[#6b7280] uppercase tracking-wide">External events (delete for testing)</p>
          {events.slice(0, 10).map((ev: ExternalEvent) => (
            <div
              key={ev.id}
              className="flex gap-2 items-start p-2 rounded bg-[#f9fafb] border border-[#e5e7eb]"
            >
              <EventIcon eventType={ev.event_type} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#111827]">{ev.title}</p>
                {ev.description && <p className="text-xs text-[#6b7280] mt-0.5">{ev.description}</p>}
                <p className="text-xs text-[#9ca3af] mt-1">{formatTime(ev.created_at)}</p>
              </div>
              <button
                type="button"
                disabled={deletingId === ev.id}
                onClick={async () => {
                  setDeletingId(ev.id);
                  try {
                    await deleteExternalEvent(planId, ev.id);
                    await load();
                    onDeleteEvent?.();
                  } finally {
                    setDeletingId(null);
                  }
                }}
                className="shrink-0 rounded p-1.5 text-[#6b7280] hover:bg-red-100 hover:text-red-700"
                title="Delete event and its proposed actions"
              >
                {deletingId === ev.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              </button>
            </div>
          ))}
        </div>
      )}
      {pending.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-[#6b7280] uppercase tracking-wide">
            Pending human approval ({pending.length})
          </p>
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
                <div className="flex flex-wrap gap-2 mt-1">
                  <button
                    type="button"
                    disabled={actingActionId === action.id}
                    onClick={async () => {
                      setActingActionId(action.id);
                      try {
                        await approveProposedAction(planId, action.id);
                        await load();
                        onDeleteEvent?.();
                      } finally {
                        setActingActionId(null);
                      }
                    }}
                    className="inline-flex items-center gap-1 rounded bg-[#16a34a] text-white px-2.5 py-1.5 text-xs font-medium hover:bg-[#15803d] disabled:opacity-50"
                  >
                    {actingActionId === action.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CheckCircle className="h-3.5 w-3.5" />
                    )}
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={actingActionId === action.id}
                    onClick={async () => {
                      setActingActionId(action.id);
                      try {
                        await rejectProposedAction(planId, action.id);
                        await load();
                        onDeleteEvent?.();
                      } finally {
                        setActingActionId(null);
                      }
                    }}
                    className="inline-flex items-center gap-1 rounded border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] hover:bg-[#f9fafb] disabled:opacity-50"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    Reject
                  </button>
                  <button
                    type="button"
                    disabled={actingActionId === action.id}
                    onClick={async () => {
                      setActingActionId(action.id);
                      try {
                        await deleteProposedAction(planId, action.id);
                        await load();
                        onDeleteEvent?.();
                      } finally {
                        setActingActionId(null);
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
        </div>
      )}
    </div>
  );
}
