"use client";

import { useEffect, useState } from "react";
import { fetchPlannerTasks } from "@/lib/congressTwinApi";

interface WorkstreamProgressProps {
  planId: string;
  refreshTrigger?: number;
}

export default function WorkstreamProgress({ planId, refreshTrigger = 0 }: WorkstreamProgressProps) {
  const [tasks, setTasks] = useState<{ bucketName?: string; status?: string }[]>([]);

  useEffect(() => {
    fetchPlannerTasks(planId)
      .then((r) => setTasks(r.tasks))
      .catch(() => setTasks([]));
  }, [planId, refreshTrigger]);

  const byBucket: Record<string, { total: number; completed: number }> = {};
  for (const t of tasks) {
    const bucket = t.bucketName || "Other";
    if (!byBucket[bucket]) byBucket[bucket] = { total: 0, completed: 0 };
    byBucket[bucket].total += 1;
    if (t.status === "completed") byBucket[bucket].completed += 1;
  }

  return (
    <div className="ct-card p-4">
      <h3 className="text-sm font-semibold text-[#111827] mb-3">Workstream progress</h3>
      <div className="space-y-3">
        {Object.entries(byBucket).map(([name, { total, completed }]) => {
          const pct = total ? Math.round((completed / total) * 100) : 0;
          return (
            <div key={name}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#374151]">{name}</span>
                <span className="text-[#6b7280]">{completed}/{total}</span>
              </div>
              <div className="h-2 bg-[#f3f4f6] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#16a34a] rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
