"use client";

import { useEffect, useState } from "react";
import { ArrowUp, ArrowDown, CheckCircle, Circle, Loader2 } from "lucide-react";
import {
  fetchExecutionTasks,
  fetchTaskDependencies,
  type ExecutionTask,
  type TaskDependenciesResponse,
} from "@/lib/congressTwinApi";

import { DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

const STATUS_LABEL: Record<string, string> = {
  notStarted: "Not started",
  inProgress: "In progress",
  completed: "Done",
};

const RISK_LABEL: Record<string, string> = {
  blocked: "Blocked",
  blocking: "Blocking",
  at_risk: "At risk",
  overdue: "Overdue",
};

interface DependencyLensProps {
  planId?: string;
  refreshTrigger?: number;
}

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

export default function DependencyLens({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: DependencyLensProps) {
  const [tasks, setTasks] = useState<ExecutionTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTask, setSelectedTask] = useState<ExecutionTask | null>(null);
  const [deps, setDeps] = useState<TaskDependenciesResponse | null>(null);
  const [depsLoading, setDepsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchExecutionTasks(DEFAULT_PLAN_ID)
      .then((res) => {
        if (!cancelled) setTasks(res.tasks);
      })
      .catch(() => {
        if (!cancelled) setTasks([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [planId, refreshTrigger]);

  useEffect(() => {
    if (!selectedTask) {
      setDeps(null);
      return;
    }
    setDepsLoading(true);
    setDeps(null);
    fetchTaskDependencies(DEFAULT_PLAN_ID, selectedTask.id)
      .then(setDeps)
      .catch(() => setDeps(null))
      .finally(() => setDepsLoading(false));
  }, [planId, selectedTask?.id]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center ct-card text-[#6b7280]">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-[32rem] gap-0 ct-card overflow-hidden">
      {/* Left: execution task list */}
      <div className="w-1/2 flex flex-col border-r border-[#e5e7eb] overflow-hidden">
        <div className="border-b border-[#e5e7eb] bg-[#f9fafb] px-4 py-3">
          <h3 className="font-bold text-[#111827]">Task list</h3>
          <p className="text-sm text-[#6b7280]">{tasks.length} tasks</p>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-[#f3f4f6]">
          {tasks.map((task) => {
            const onCriticalPath = task.on_critical_path ?? false;
            return (
              <button
                key={task.id}
                type="button"
                onClick={() => setSelectedTask(task)}
                className={`w-full text-left px-4 py-3 hover:bg-[#f9fafb] transition-colors ${
                  selectedTask?.id === task.id
                    ? "bg-[#dcfce7] border-l-4 border-l-[#16a34a]"
                    : onCriticalPath
                      ? "border-l-2 border-l-[#16a34a] bg-[#dcfce7]/30"
                      : ""
                }`}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  {task.status === "completed" ? (
                    <CheckCircle className="h-4 w-4 text-[#16a34a] shrink-0" />
                  ) : (
                    <Circle className="h-4 w-4 text-[#9ca3af] shrink-0" />
                  )}
                  <span className="font-medium text-[#111827] truncate">{task.title}</span>
                  {onCriticalPath && (
                    <span className="shrink-0 rounded bg-[#dcfce7] px-1.5 py-0.5 text-xs font-medium text-[#166534]" title="On critical path">
                      CP
                    </span>
                  )}
                  {task.risk_badges?.length > 0 && (
                    <span className="flex flex-wrap gap-0.5 shrink-0">
                      {task.risk_badges.map((badge) => (
                        <span
                          key={badge}
                          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                            badge === "blocked" ? "bg-red-100 text-red-700" :
                            badge === "blocking" ? "bg-amber-100 text-amber-800" :
                            badge === "at_risk" ? "bg-orange-100 text-orange-800" :
                            "bg-rose-100 text-rose-800"
                          }`}
                          title={RISK_LABEL[badge]}
                        >
                          {RISK_LABEL[badge]}
                        </span>
                      ))}
                    </span>
                  )}
                  {(task.upstream_count > 0 || task.downstream_count > 0) && (
                    <span className="shrink-0 flex items-center gap-1 text-xs text-[#6b7280]">
                      <span title="Upstream count">↑ {task.upstream_count}</span>
                      <span title="Downstream count">↓ {task.downstream_count}</span>
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-3 text-xs text-[#6b7280] ml-6">
                  <span>{task.bucketName ?? task.bucketId}</span>
                  {task.assigneeNames?.length ? (
                    <span>{task.assigneeNames.join(", ")}</span>
                  ) : null}
                  {task.dueDateTime && (
                    <span>{formatDate(task.dueDateTime)}</span>
                  )}
                  <span>{STATUS_LABEL[task.status] ?? task.status}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right: dependency inspector */}
      <div className="w-1/2 flex flex-col overflow-hidden">
        <div className="border-b border-[#e5e7eb] bg-[#f9fafb] px-4 py-3">
          <h3 className="font-bold text-[#111827]">Dependency inspector</h3>
          {selectedTask && (
            <p className="text-sm text-[#6b7280] truncate">{selectedTask.title}</p>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {!selectedTask && (
            <p className="text-sm text-[#6b7280]">Select a task to see upstream and downstream dependencies.</p>
          )}
          {selectedTask && depsLoading && (
            <div className="flex items-center gap-2 text-[#6b7280]">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading…</span>
            </div>
          )}
          {selectedTask && deps && !depsLoading && (
            <>
              {deps.impact_statement && (
                <div className="mb-4 rounded-lg border-l-4 border-l-[#16a34a] bg-[#dcfce7]/30 p-3 text-sm text-[#166534]">
                  {deps.impact_statement}
                </div>
              )}
              <div className="mb-4">
                <h4 className="flex items-center gap-2 text-sm font-semibold text-[#111827] mb-2">
                  <ArrowUp className="h-4 w-4 text-[#16a34a]" />
                  Upstream (must finish before this)
                </h4>
                {deps.upstream.length === 0 ? (
                  <p className="text-sm text-[#6b7280]">None</p>
                ) : (
                  <ul className="space-y-2">
                    {deps.upstream.map((t) => (
                      <li
                        key={t.id}
                        className="rounded border border-[#e5e7eb] bg-[#f9fafb] p-2 text-sm"
                      >
                        <div className="font-medium text-[#111827]">{t.title}</div>
                        <div className="text-xs text-[#6b7280] mt-1">
                          {t.assigneeNames?.length ? `${t.assigneeNames.join(", ")} · ` : ""}
                          Due: {formatDate(t.dueDateTime)} · {t.status}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <h4 className="flex items-center gap-2 text-sm font-semibold text-[#111827] mb-2">
                  <ArrowDown className="h-4 w-4 text-[#16a34a]" />
                  Downstream (impacted if this slips)
                </h4>
                {deps.downstream.length === 0 ? (
                  <p className="text-sm text-[#6b7280]">None</p>
                ) : (
                  <ul className="space-y-2">
                    {deps.downstream.map((t) => (
                      <li
                        key={t.id}
                        className="rounded border border-[#e5e7eb] bg-[#f9fafb] p-2 text-sm"
                      >
                        <div className="font-medium text-[#111827]">{t.title}</div>
                        <div className="text-xs text-[#6b7280] mt-1">
                          {t.assigneeNames?.length ? `${t.assigneeNames.join(", ")} · ` : ""}
                          Due: {formatDate(t.dueDateTime)} · {t.status}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
