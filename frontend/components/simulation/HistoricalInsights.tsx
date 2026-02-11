"use client";

import { useEffect, useState } from "react";
import { History, Loader2, TrendingDown, TrendingUp } from "lucide-react";
import { getHistoricalInsights, type HistoricalInsight, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface HistoricalInsightsProps {
  planId?: string;
}

export default function HistoricalInsights({ planId = DEFAULT_PLAN_ID }: HistoricalInsightsProps) {
  const [insights, setInsights] = useState<HistoricalInsight | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getHistoricalInsights(planId)
      .then(setInsights)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [planId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin text-sky-500" />
      </div>
    );
  }

  if (!insights) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <History className="h-5 w-5" />
        <h2 className="text-xl font-semibold">Historical Insights</h2>
      </div>

      {/* Duration Bias */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Duration Bias by Bucket</h3>
        <div className="space-y-2">
          {Object.entries(insights.duration_bias.bucket_stats).map(([bucket, stats]) => (
            <div key={bucket} className="flex items-center justify-between p-2 rounded border border-slate-100">
              <span className="font-medium text-slate-700">{bucket}</span>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-slate-600">
                  Bias: {stats.bias_factor > 1 ? (
                    <span className="text-red-600 flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      {stats.bias_factor.toFixed(2)}x
                    </span>
                  ) : (
                    <span className="text-green-600 flex items-center gap-1">
                      <TrendingDown className="h-3 w-3" />
                      {stats.bias_factor.toFixed(2)}x
                    </span>
                  )}
                </span>
                <span className="text-slate-500">
                  PERT: {stats.optimistic.toFixed(1)} / {stats.most_likely.toFixed(1)} / {stats.pessimistic.toFixed(1)} days
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resource Throughput */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Resource Throughput</h3>
        <div className="space-y-2">
          {Object.entries(insights.resource_throughput).map(([assignee, stats]) => (
            <div key={assignee} className="flex items-center justify-between p-2 rounded border border-slate-100">
              <span className="font-medium text-slate-700">{assignee}</span>
              <div className="text-sm text-slate-600">
                {stats.tasks_per_week.toFixed(1)} tasks/week • {stats.avg_duration_days.toFixed(1)} days avg
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Bottlenecks */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Historical Bottlenecks</h3>
        <div className="space-y-2">
          {insights.bottlenecks.slice(0, 10).map((bottleneck) => (
            <div key={bottleneck.task_id} className="flex items-center justify-between p-2 rounded border border-slate-100">
              <div>
                <div className="font-medium text-slate-900">{bottleneck.title}</div>
                <div className="text-xs text-slate-500">{bottleneck.bucket}</div>
              </div>
              <div className="text-sm text-slate-600">
                {bottleneck.downstream_count} downstream tasks
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Block Frequency */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold mb-3">Block Frequency by Bucket</h3>
        <div className="space-y-2">
          {Object.entries(insights.block_frequency.block_rate_by_bucket)
            .sort(([, a], [, b]) => b - a)
            .map(([bucket, rate]) => (
              <div key={bucket} className="flex items-center justify-between">
                <span className="text-sm text-slate-700">{bucket}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-red-500"
                      style={{ width: `${rate * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-900">{(rate * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
