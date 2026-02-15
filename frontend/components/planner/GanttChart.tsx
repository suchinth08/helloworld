"use client";

import { useEffect, useState } from "react";
import { fetchPlannerTasks } from "@/lib/congressTwinApi";

interface GanttChartProps {
  planId: string;
  refreshTrigger?: number;
}

function parseDate(iso: string | undefined): Date | null {
  if (!iso) return null;
  try {
    return new Date(iso);
  } catch {
    return null;
  }
}

export default function GanttChart({ planId, refreshTrigger = 0 }: GanttChartProps) {
  const [tasks, setTasks] = useState<{ id: string; title: string; startDateTime?: string; dueDateTime?: string; status?: string; bucketName?: string }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlannerTasks(planId)
      .then((r) => setTasks(r.tasks))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, [planId, refreshTrigger]);

  if (loading) return <div className="ct-card p-6 text-[#6b7280]">Loading Gantt…</div>;

  const withDates = tasks.filter((t) => t.startDateTime || t.dueDateTime);
  if (withDates.length === 0) {
    return (
      <div className="ct-card p-5">
        <h2 className="text-base font-bold text-[#111827] mb-2">Gantt Chart</h2>
        <p className="text-sm text-[#6b7280]">No tasks with dates.</p>
      </div>
    );
  }

  const starts = withDates.map((t) => parseDate(t.startDateTime || t.dueDateTime)?.getTime()).filter(Boolean) as number[];
  const ends = withDates.map((t) => parseDate(t.dueDateTime)?.getTime()).filter(Boolean) as number[];
  const minDate = Math.min(...starts, ...ends);
  const maxDate = Math.max(...starts, ...ends);
  const range = maxDate - minDate || 1;

  return (
    <div className="ct-card p-5">
      <h2 className="text-base font-bold text-[#111827] mb-4">Gantt Chart</h2>
      <div className="overflow-x-auto">
        <div className="min-w-[600px]">
          {withDates.slice(0, 15).map((t) => {
            const start = parseDate(t.startDateTime || t.dueDateTime)?.getTime() ?? minDate;
            const end = parseDate(t.dueDateTime)?.getTime() ?? start + 86400000 * 5;
            const left = ((start - minDate) / range) * 100;
            const width = Math.max(2, ((end - start) / range) * 100);
            return (
              <div key={t.id} className="flex items-center gap-4 mb-2">
                <div className="w-40 shrink-0 truncate text-sm text-[#374151]" title={t.title}>
                  {t.title}
                </div>
                <div className="flex-1 h-6 bg-[#f3f4f6] rounded relative">
                  <div
                    className={`absolute h-5 top-0.5 rounded ${
                      t.status === "completed" ? "bg-green-500" : t.status === "inProgress" ? "bg-blue-500" : "bg-gray-400"
                    }`}
                    style={{ left: `${left}%`, width: `${width}%`, minWidth: 4 }}
                    title={`${t.startDateTime || ""} - ${t.dueDateTime || ""}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
