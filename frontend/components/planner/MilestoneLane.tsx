"use client";

import { useEffect, useState } from "react";
import { Calendar, AlertTriangle, CheckCircle, Loader2, RefreshCw } from "lucide-react";
import {
  fetchMilestoneAnalysis,
  type MilestoneAnalysisResponse,
} from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

interface MilestoneLaneProps {
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

export default function MilestoneLane({ refreshTrigger = 0 }: MilestoneLaneProps) {
  const [data, setData] = useState<MilestoneAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventDateInput, setEventDateInput] = useState("");

  const load = async (eventDate?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchMilestoneAnalysis(DEFAULT_PLAN_ID, eventDate);
      setData(res);
      if (!eventDateInput && res.event_date) {
        const d = new Date(res.event_date);
        setEventDateInput(d.toISOString().slice(0, 10));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load milestone analysis");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshTrigger]);

  const handleEventDateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (eventDateInput) load(`${eventDateInput}T12:00:00Z`);
  };

  if (loading && !data) {
    return (
      <div className="ct-card p-4 flex items-center gap-2 text-[#6b7280] text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading milestone analysis…
      </div>
    );
  }
  if (error && !data) {
    return (
      <div className="ct-card border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
        <button
          type="button"
          onClick={() => load()}
          className="ml-2 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="ct-card p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <div className="rounded p-1.5 bg-[#dcfce7]">
            <Calendar className="h-4 w-4 text-[#16a34a]" />
          </div>
          Milestone / Event date
        </h2>
        <div className="flex items-center gap-2">
          <form onSubmit={handleEventDateSubmit} className="flex items-center gap-2">
            <label htmlFor="event-date" className="text-sm text-[#6b7280]">
              Event date:
            </label>
            <input
              id="event-date"
              type="date"
              value={eventDateInput}
              onChange={(e) => setEventDateInput(e.target.value)}
              className="rounded border border-[#e5e7eb] px-2 py-1.5 text-sm bg-white"
            />
            <button
              type="submit"
              className="rounded bg-[#16a34a] px-3 py-1.5 text-sm font-medium text-white hover:bg-[#15803d]"
            >
              Update
            </button>
          </form>
          <button
            type="button"
            onClick={() => load(eventDateInput ? `${eventDateInput}T12:00:00Z` : undefined)}
            className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
            aria-label="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
      <p className="text-sm text-[#6b7280] mb-4">
        Event date: <strong className="text-[#111827]">{formatDate(data.event_date)}</strong> — tasks due before this date vs at risk.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-[#e5e7eb] bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="rounded p-1.5 bg-[#dcfce7]">
              <CheckCircle className="h-4 w-4 text-[#16a34a]" />
            </div>
            <span className="font-semibold text-[#111827]">Tasks before event</span>
          </div>
          <div className="text-2xl font-bold text-[#111827]">{data.tasks_before_event.length}</div>
          {data.tasks_before_event.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-[#6b7280]">
              {data.tasks_before_event.slice(0, 5).map((t) => (
                <li key={t.id} className="flex items-center gap-2 truncate">
                  <span className="truncate" title={t.title}>{t.title}</span>
                  {t.on_critical_path && (
                    <span className="shrink-0 rounded bg-[#dcfce7] px-1.5 py-0.5 text-[#166534] font-medium">CP</span>
                  )}
                </li>
              ))}
              {data.tasks_before_event.length > 5 && (
                <li className="text-[#9ca3af]">+{data.tasks_before_event.length - 5} more</li>
              )}
            </ul>
          )}
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <div className="rounded p-1.5 bg-amber-100">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
            </div>
            <span className="font-semibold text-amber-800">At risk (due after event)</span>
          </div>
          <div className="text-2xl font-bold text-amber-800">{data.at_risk_count}</div>
          {data.at_risk_tasks.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-amber-900">
              {data.at_risk_tasks.slice(0, 5).map((t) => (
                <li key={t.id} className="truncate" title={t.title}>
                  {t.title}
                  {t.days_after_event != null && (
                    <span className="ml-1 text-amber-700">(+{t.days_after_event}d)</span>
                  )}
                </li>
              ))}
              {data.at_risk_tasks.length > 5 && (
                <li className="text-amber-600">+{data.at_risk_tasks.length - 5} more</li>
              )}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
