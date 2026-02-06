"use client";

import { useState, useEffect, useRef } from "react";
import { BarChart3, Loader2, RefreshCw, Lightbulb, Wrench, Play, Clock } from "lucide-react";
import { fetchMonteCarlo, type MonteCarloResponse, type MonteCarloSuggestion } from "@/lib/congressTwinApi";

const DEFAULT_PLAN_ID = "uc31-plan";

const TRACE_MESSAGES = [
  "Loading task graph and dependencies…",
  "Building critical path…",
  "Running Monte Carlo simulations…",
  "Sampling task durations…",
  "Computing plan end dates…",
  "Calculating P(on-time)…",
  "Identifying risk tasks…",
  "Generating agent suggestions…",
  "Finalizing results…",
];
const TRACE_INTERVAL_MS = 900;
const MIN_DELAY_MS = 9000;

interface TraceEntry {
  msg: string;
  atMs: number;
}

function SuggestionRow({ s }: { s: MonteCarloSuggestion }) {
  const Icon = s.type === "enhancement" ? Lightbulb : Wrench;
  const priorityColor =
    s.priority === "high" ? "text-rose-600" : s.priority === "medium" ? "text-amber-600" : "text-[#6b7280]";
  return (
    <div className="flex gap-2 items-start p-3 rounded border border-[#e5e7eb] bg-[#fafafa]">
      <Icon className={`h-4 w-4 mt-0.5 flex-shrink-0 ${priorityColor}`} />
      <div className="min-w-0">
        <p className="text-sm font-medium text-[#111827]">{s.title}</p>
        <p className="text-xs text-[#6b7280] mt-1">{s.detail}</p>
        {s.action_hint && (
          <p className="text-xs text-[#16a34a] mt-1 font-medium">{s.action_hint}</p>
        )}
      </div>
    </div>
  );
}

interface MonteCarloSuggestionsProps {
  planId?: string;
  refreshTrigger?: number;
  nSimulations?: number;
}

export default function MonteCarloSuggestions({
  planId = DEFAULT_PLAN_ID,
  refreshTrigger = 0,
  nSimulations = 500,
}: MonteCarloSuggestionsProps) {
  const [data, setData] = useState<MonteCarloResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [traces, setTraces] = useState<TraceEntry[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const traceRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamContainerRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!loading) return;
    startTimeRef.current = Date.now();
    setElapsedMs(0);
    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 100);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [loading]);

  useEffect(() => {
    if (!loading) return;
    setTraces([{ msg: TRACE_MESSAGES[0], atMs: 0 }]);
    let idx = 0;
    traceRef.current = setInterval(() => {
      const now = Date.now() - startTimeRef.current;
      idx += 1;
      if (idx < TRACE_MESSAGES.length) {
        setTraces((t) => [...t, { msg: TRACE_MESSAGES[idx], atMs: now }]);
      }
    }, TRACE_INTERVAL_MS);
    return () => {
      if (traceRef.current) clearInterval(traceRef.current);
    };
  }, [loading]);

  useEffect(() => {
    const el = streamContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [traces]);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setTraces([]);
    const start = Date.now();
    try {
      const res = await fetchMonteCarlo(planId, nSimulations);
      const elapsed = Date.now() - start;
      const remaining = Math.max(0, MIN_DELAY_MS - elapsed);
      if (remaining > 0) {
        await new Promise((r) => setTimeout(r, remaining));
      }
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run Monte Carlo");
    } finally {
      setLoading(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (traceRef.current) {
        clearInterval(traceRef.current);
        traceRef.current = null;
      }
    }
  };

  const formatTimer = (ms: number) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="ct-card p-6 flex flex-col h-[320px] shrink-0 overflow-hidden">
        <div className="flex items-center justify-between mb-3 shrink-0">
          <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[#16a34a]" />
            Monte Carlo &amp; agent suggestions
          </h3>
          <div className="flex items-center gap-2 rounded-lg bg-[#f0fdf4] border border-[#bbf7d0] px-3 py-1.5">
            <Clock className="h-4 w-4 text-[#16a34a]" />
            <span className="text-sm font-semibold tabular-nums text-[#166534]">
              {formatTimer(elapsedMs)}
            </span>
          </div>
        </div>
        <p className="text-sm text-[#6b7280] mb-2 shrink-0">Background stream — simulation in progress</p>
        <div className="flex items-start gap-3 flex-1 min-h-0 overflow-hidden">
          <Loader2 className="h-6 w-6 animate-spin text-[#16a34a] shrink-0 mt-1" />
          <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
            <div
              ref={streamContainerRef}
              className="h-[180px] rounded-lg bg-[#1e293b] text-[#e2e8f0] font-mono text-xs overflow-y-auto overflow-x-hidden p-3 border border-[#334155]"
              role="log"
              aria-live="polite"
            >
              {traces.map((entry, i) => (
                <div
                  key={i}
                  className="flex gap-2 py-0.5 items-baseline"
                >
                  <span className="shrink-0 text-[#94a3b8] tabular-nums">
                    [{formatTimer(entry.atMs)}]
                  </span>
                  <span className="text-[#22c55e]">●</span>
                  <span className="break-words">{entry.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card p-4 border-red-200 bg-red-50 text-sm text-red-700">
        {error}
        <button type="button" onClick={runSimulation} className="ml-2 underline hover:no-underline">
          Retry
        </button>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="ct-card p-6 flex flex-col items-center justify-center min-h-[180px]">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2 mb-2">
          <BarChart3 className="h-4 w-4 text-[#16a34a]" />
          Monte Carlo &amp; agent suggestions
        </h3>
        <p className="text-sm text-[#6b7280] mb-4 text-center max-w-md">
          Run a Monte Carlo simulation to see P(on-time), risk tasks, and agent suggestions for enhancements and modifications.
        </p>
        <button
          type="button"
          onClick={runSimulation}
          className="inline-flex items-center gap-2 rounded-lg bg-[#16a34a] text-white px-4 py-2.5 text-sm font-medium hover:bg-[#15803d]"
        >
          <Play className="h-4 w-4" />
          Run Monte Carlo simulation
        </button>
      </div>
    );
  }

  const p = data.probability_on_time_percent;
  const suggestions = data.agent_suggestions || [];

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-[#16a34a]" />
          Monte Carlo &amp; agent suggestions
        </h3>
        <button
          type="button"
          onClick={runSimulation}
          className="inline-flex items-center gap-1.5 rounded border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-xs font-medium text-[#374151] hover:bg-[#f9fafb]"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Run again
        </button>
      </div>
      <p className="text-sm text-[#6b7280] mb-4">
        {data.n_simulations} runs — P(on-time) to event date: <strong>{p}%</strong>
        {data.percentile_end_dates?.p50 && (
          <span className="ml-2 text-xs">
            (median end: {new Date(data.percentile_end_dates.p50).toLocaleDateString()})
          </span>
        )}
      </p>
      <div className="space-y-3">
        <p className="text-xs font-medium text-[#6b7280] uppercase tracking-wide">
          Agent suggestions (enhancements &amp; modifications)
        </p>
        {suggestions.length === 0 ? (
          <p className="text-sm text-[#6b7280]">No suggestions. Schedule is within target.</p>
        ) : (
          suggestions.map((s) => <SuggestionRow key={s.id} s={s} />)
        )}
      </div>
    </div>
  );
}
