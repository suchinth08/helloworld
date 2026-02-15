"use client";

import { useEffect, useState } from "react";
import { X, Loader2, FileStack } from "lucide-react";
import { usePlan } from "./PlanContext";

const CONGRESS_TWIN_API = process.env.NEXT_PUBLIC_CONGRESS_TWIN_API_URL || "http://localhost:8010";

interface TemplateModalProps {
  onClose: () => void;
  onCreated?: (planId: string) => void;
}

interface TemplateSource {
  plan_id: string;
  name: string;
  congress_date?: string;
}

export default function TemplateModal({ onClose, onCreated }: TemplateModalProps) {
  const { setPlanId } = usePlan();
  const [sources, setSources] = useState<TemplateSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourcePlanId, setSourcePlanId] = useState("");
  const [targetPlanId, setTargetPlanId] = useState("");
  const [congressDate, setCongressDate] = useState("");
  const [result, setResult] = useState<{
    tasks_created: number;
    p50_completion?: string;
    p95_completion?: string;
    probability_on_time?: number;
  } | null>(null);

  useEffect(() => {
    fetch(`${CONGRESS_TWIN_API}/api/v1/planner/template/sources`)
      .then((r) => r.json())
      .then((data) => setSources(data.plans || []))
      .catch(() => setSources([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourcePlanId || !targetPlanId) {
      setError("Source and target plan are required");
      return;
    }
    setCreating(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/template`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_plan_id: sourcePlanId,
          target_plan_id: targetPlanId,
          congress_date: congressDate || undefined,
          run_simulation: true,
        }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Template creation failed");
      setResult({
        tasks_created: data.tasks_created ?? 0,
        p50_completion: data.p50_completion,
        p95_completion: data.p95_completion,
        probability_on_time: data.probability_on_time,
      });
      setPlanId(targetPlanId);
      onCreated?.(targetPlanId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create from template");
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" aria-hidden onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-white rounded-xl shadow-xl">
        <div className="flex items-center justify-between p-4 border-b border-[#e5e7eb]">
          <h2 className="text-lg font-bold text-[#111827] flex items-center gap-2">
            <FileStack className="h-5 w-5" />
            Create from template
          </h2>
          <button type="button" onClick={onClose} className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
          )}
          {result && (
            <div className="p-3 rounded-lg bg-green-50 border border-green-200 text-sm text-green-800">
              Created {result.tasks_created} tasks.
              {result.p50_completion && (
                <div className="mt-1">P50: {new Date(result.p50_completion).toLocaleDateString()}</div>
              )}
              {result.probability_on_time != null && (
                <div>On-time probability: {result.probability_on_time}%</div>
              )}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Source template *</label>
            <select
              value={sourcePlanId}
              onChange={(e) => setSourcePlanId(e.target.value)}
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
            >
              <option value="">Select template</option>
              {sources.map((s) => (
                <option key={s.plan_id} value={s.plan_id}>
                  {s.name} ({s.plan_id})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Target plan name *</label>
            <input
              type="text"
              value={targetPlanId}
              onChange={(e) => setTargetPlanId(e.target.value)}
              placeholder="e.g. congress-2025"
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[#374151] mb-1">Congress date</label>
            <input
              type="date"
              value={congressDate}
              onChange={(e) => setCongressDate(e.target.value)}
              className="w-full rounded-lg border border-[#d1d5db] px-3 py-2 text-sm"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-[#6b7280] hover:bg-[#f3f4f6] rounded-lg"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={creating || !sourcePlanId || !targetPlanId}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#16a34a] rounded-lg hover:bg-[#15803d] disabled:opacity-60"
            >
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Create from template
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
