"use client";

import { useEffect, useState } from "react";
import { BarChart3, Loader2, TrendingUp } from "lucide-react";
import { runMonteCarlo, type MonteCarloResult, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface MonteCarloResultsProps {
  planId?: string;
}

export default function MonteCarloResults({ planId = DEFAULT_PLAN_ID }: MonteCarloResultsProps) {
  const [result, setResult] = useState<MonteCarloResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runMonteCarlo(planId, 10000);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation();
  }, [planId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-sky-500" />
        <span className="ml-2 text-slate-600">Running Monte Carlo simulation...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
        Error: {error}
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Monte Carlo Simulation Results
        </h2>
        <button
          onClick={runSimulation}
          className="px-4 py-2 bg-sky-500 text-white rounded-lg hover:bg-sky-600 text-sm"
        >
          Re-run Simulation
        </button>
      </div>

      {/* Percentiles */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-500">P50 (Median)</div>
          <div className="text-2xl font-bold text-slate-900">
            {result.percentiles.p50 ? new Date(result.percentiles.p50).toLocaleDateString() : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-500">P75</div>
          <div className="text-2xl font-bold text-slate-900">
            {result.percentiles.p75 ? new Date(result.percentiles.p75).toLocaleDateString() : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-500">P95 (Worst Case)</div>
          <div className="text-2xl font-bold text-red-600">
            {result.percentiles.p95 ? new Date(result.percentiles.p95).toLocaleDateString() : "—"}
          </div>
        </div>
      </div>

      {/* Risk Heatmap */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Risk Heatmap (Bucket-Level Variance)</h3>
        <div className="space-y-2">
          {Object.entries(result.risk_heatmap)
            .sort(([, a], [, b]) => b - a)
            .map(([bucket, variance]) => (
              <div key={bucket} className="flex items-center justify-between">
                <span className="text-sm text-slate-700">{bucket}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500"
                      style={{ width: `${Math.min(100, (variance / 10) * 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-900">{variance.toFixed(1)} days</span>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Top Bottlenecks */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Top Bottlenecks</h3>
        <div className="space-y-2">
          {result.bottlenecks.slice(0, 10).map((bottleneck) => (
            <div
              key={bottleneck.task_id}
              className="flex items-center justify-between p-2 rounded border border-slate-100"
            >
              <div>
                <div className="font-medium text-slate-900">{bottleneck.title}</div>
                <div className="text-xs text-slate-500">{bottleneck.bucket}</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-slate-900">
                  Variance: {bottleneck.variance_days.toFixed(1)} days
                </div>
                <div className="text-xs text-slate-500">
                  CP Probability: {(bottleneck.critical_path_probability || 0).toFixed(1)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
