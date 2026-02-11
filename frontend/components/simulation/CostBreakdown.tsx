"use client";

import { useEffect, useState } from "react";
import { DollarSign, Loader2, Sliders } from "lucide-react";
import { computeCost, type CostAnalysis, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface CostBreakdownProps {
  planId?: string;
}

export default function CostBreakdown({ planId = DEFAULT_PLAN_ID }: CostBreakdownProps) {
  const [result, setResult] = useState<CostAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [weights, setWeights] = useState({
    w1: 1.0,
    w2: 0.8,
    w3: 1.2,
    w4: 0.5,
    w5: 0.3,
  });

  const loadCost = async () => {
    setLoading(true);
    try {
      const data = await computeCost(planId, weights);
      setResult(data);
    } catch (e) {
      console.error("Cost analysis failed:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCost();
  }, [planId, weights]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-sky-500" />
      </div>
    );
  }

  if (!result) {
    return null;
  }

  const breakdown = result.cost_breakdown;
  const maxCost = Math.max(
    breakdown.schedule,
    breakdown.resource,
    breakdown.risk,
    breakdown.quality,
    breakdown.disruption
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <DollarSign className="h-5 w-5" />
          Cost Analysis
        </h2>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Sliders className="h-4 w-4" />
          Total Cost: <span className="font-bold text-slate-900">{result.total_cost.toFixed(2)}</span>
        </div>
      </div>

      {/* Cost Components */}
      <div className="space-y-3">
        {[
          { key: "schedule", label: "Schedule Cost", value: breakdown.schedule, weight: weights.w1 },
          { key: "resource", label: "Resource Cost", value: breakdown.resource, weight: weights.w2 },
          { key: "risk", label: "Risk Cost", value: breakdown.risk, weight: weights.w3 },
          { key: "quality", label: "Quality Cost", value: breakdown.quality, weight: weights.w4 },
          { key: "disruption", label: "Disruption Cost", value: breakdown.disruption, weight: weights.w5 },
        ].map(({ key, label, value, weight }) => (
          <div key={key} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{label}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">Weight: {weight.toFixed(1)}</span>
                <span className="font-medium text-slate-900">{value.toFixed(2)}</span>
              </div>
            </div>
            <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-sky-500 transition-all"
                style={{ width: `${(value / maxCost) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Weight Sliders */}
      <div className="mt-6 p-4 bg-slate-50 rounded-lg">
        <h3 className="text-sm font-semibold mb-3">Adjust Weights</h3>
        <div className="space-y-3">
          {[
            { key: "w1", label: "Schedule", value: weights.w1 },
            { key: "w2", label: "Resource", value: weights.w2 },
            { key: "w3", label: "Risk", value: weights.w3 },
            { key: "w4", label: "Quality", value: weights.w4 },
            { key: "w5", label: "Disruption", value: weights.w5 },
          ].map(({ key, label, value }) => (
            <div key={key} className="flex items-center gap-3">
              <label className="w-24 text-sm text-slate-700">{label}</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={value}
                onChange={(e) => setWeights({ ...weights, [key]: parseFloat(e.target.value) })}
                className="flex-1"
              />
              <span className="w-12 text-sm font-medium text-slate-900">{value.toFixed(1)}</span>
            </div>
          ))}
        </div>
        <button
          onClick={loadCost}
          className="mt-4 px-4 py-2 bg-sky-500 text-white rounded-lg hover:bg-sky-600 text-sm"
        >
          Recalculate
        </button>
      </div>
    </div>
  );
}
