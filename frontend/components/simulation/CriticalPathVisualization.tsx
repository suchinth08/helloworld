"use client";

import { useMemo } from "react";
import { GitBranch } from "lucide-react";
import { type MonteCarloResult } from "@/lib/congressTwinApi";

interface CriticalPathVisualizationProps {
  result: MonteCarloResult;
  tasks: Array<{ id: string; title: string; bucketName?: string }>;
}

export default function CriticalPathVisualization({ result, tasks }: CriticalPathVisualizationProps) {
  const criticalTasks = useMemo(() => {
    const cpProb = result.critical_path_probability;
    return Object.entries(cpProb)
      .map(([taskId, probability]) => {
        const task = tasks.find((t) => t.id === taskId);
        return task ? { ...task, probability } : null;
      })
      .filter((t): t is NonNullable<typeof t> => t !== null)
      .sort((a, b) => (b.probability || 0) - (a.probability || 0))
      .slice(0, 20);
  }, [result.critical_path_probability, tasks]);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2 mb-4">
        <GitBranch className="h-5 w-5 text-sky-500" />
        <h3 className="font-semibold">Critical Path Probability</h3>
      </div>
      <div className="space-y-2">
        {criticalTasks.map((task) => {
          const prob = task.probability || 0;
          return (
            <div key={task.id} className="flex items-center justify-between p-2 rounded border border-slate-100">
              <div className="flex-1">
                <div className="font-medium text-slate-900">{task.title}</div>
                {task.bucketName && (
                  <div className="text-xs text-slate-500">{task.bucketName}</div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-sky-500 transition-all"
                    style={{ width: `${prob}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-slate-900 w-12 text-right">
                  {prob.toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-4 text-xs text-slate-500">
        Shows probability that each task appears on the critical path across {result.n_iterations.toLocaleString()} simulation runs.
      </div>
    </div>
  );
}
