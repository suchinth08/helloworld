"use client";

import { useEffect, useState } from "react";
import { ListTodo, Loader2, RefreshCw } from "lucide-react";
import { fetchPlannerTasks, type PlannerTask } from "@/lib/congressTwinApi";
import TaskDetailPanel from "./TaskDetailPanel";

const DEFAULT_PLAN_ID = "uc31-plan";

const STATUS_LABEL: Record<string, string> = {
  notStarted: "Not started",
  inProgress: "In progress",
  completed: "Done",
};

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

interface TaskListTableProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function TaskListTable({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: TaskListTableProps) {
  const [data, setData] = useState<{ tasks: PlannerTask[]; count: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchPlannerTasks(planId);
      setData({ tasks: res.tasks, count: res.count });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [planId, refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-6 flex items-center justify-center min-h-[200px] text-[#6b7280]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
        <button type="button" onClick={load} className="ml-2 underline hover:no-underline">Retry</button>
      </div>
    );
  }
  if (!data || data.tasks.length === 0) {
    return (
      <div className="ct-card p-5">
        <h2 className="text-base font-bold text-[#111827] mb-2 flex items-center gap-2">
          <ListTodo className="h-4 w-4" />
          Task list
        </h2>
        <p className="text-sm text-[#6b7280]">No tasks for this plan.</p>
      </div>
    );
  }

  return (
    <div className="ct-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-[#111827] flex items-center gap-2">
          <ListTodo className="h-4 w-4" />
          Task list
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-sm text-[#6b7280]">{data.count} tasks</span>
          <button
            type="button"
            onClick={load}
            className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
            aria-label="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-[#e5e7eb] text-left text-xs font-semibold text-[#6b7280] uppercase tracking-wide">
              <th className="py-3 pr-4">Task</th>
              <th className="py-3 pr-4">Bucket</th>
              <th className="py-3 pr-4">Owner</th>
              <th className="py-3 pr-4">Due date</th>
              <th className="py-3 pr-4">Status</th>
              <th className="py-3 pr-4 text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {data.tasks.map((t) => (
              <tr
                key={t.id}
                className="border-b border-[#f3f4f6] hover:bg-[#f9fafb] cursor-pointer transition-colors"
                onClick={() => setSelectedTaskId(t.id)}
              >
                <td className="py-2.5 pr-4">
                  <span className="font-medium text-[#111827]">{t.title}</span>
                </td>
                <td className="py-2.5 pr-4 text-[#6b7280]">{t.bucketName ?? t.bucketId ?? "—"}</td>
                <td className="py-2.5 pr-4 text-[#6b7280]">
                  {t.assigneeNames?.length ? t.assigneeNames.join(", ") : "—"}
                </td>
                <td className="py-2.5 pr-4 text-[#6b7280]">{formatDate(t.dueDateTime)}</td>
                <td className="py-2.5 pr-4">
                  <span
                    className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${
                      t.status === "completed"
                        ? "bg-[#dcfce7] text-[#166534]"
                        : t.status === "inProgress"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-[#f3f4f6] text-[#6b7280]"
                    }`}
                  >
                    {STATUS_LABEL[t.status ?? ""] ?? t.status ?? "—"}
                  </span>
                </td>
                <td className="py-2.5 text-right font-medium text-[#111827]">{t.percentComplete ?? 0}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <TaskDetailPanel
        taskId={selectedTaskId}
        planId={planId}
        onClose={() => setSelectedTaskId(null)}
      />
    </div>
  );
}
