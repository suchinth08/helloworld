"use client";

import { useMemo } from "react";
import { AlertTriangle } from "lucide-react";
import { type MonteCarloResult } from "@/lib/congressTwinApi";

interface RiskHeatmapProps {
  result: MonteCarloResult;
}

export default function RiskHeatmap({ result }: RiskHeatmapProps) {
  const riskData = useMemo(() => {
    const entries = Object.entries(result.risk_heatmap);
    const maxVariance = Math.max(...entries.map(([, v]) => v), 1);
    return entries.map(([bucket, variance]) => ({
      bucket,
      variance,
      riskLevel: variance / maxVariance,
    })).sort((a, b) => b.variance - a.variance);
  }, [result.risk_heatmap]);

  const getRiskColor = (riskLevel: number) => {
    if (riskLevel < 0.3) return "bg-green-500";
    if (riskLevel < 0.6) return "bg-yellow-500";
    if (riskLevel < 0.8) return "bg-orange-500";
    return "bg-red-500";
  };

  const getRiskLabel = (riskLevel: number) => {
    if (riskLevel < 0.3) return "Low";
    if (riskLevel < 0.6) return "Medium";
    if (riskLevel < 0.8) return "High";
    return "Critical";
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="h-5 w-5 text-red-500" />
        <h3 className="font-semibold">Risk Heatmap</h3>
      </div>
      <div className="space-y-3">
        {riskData.map(({ bucket, variance, riskLevel }) => (
          <div key={bucket} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-700">{bucket}</span>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskColor(riskLevel)} text-white`}>
                  {getRiskLabel(riskLevel)}
                </span>
                <span className="text-slate-600">{variance.toFixed(1)} days variance</span>
              </div>
            </div>
            <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${getRiskColor(riskLevel)} transition-all`}
                style={{ width: `${riskLevel * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
