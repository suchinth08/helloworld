"use client";

import { useEffect, useState } from "react";
import { fetchPlannerTasks, updateTask } from "@/lib/congressTwinApi";
import type { PlannerTask } from "@/lib/congressTwinApi";

interface KanbanBoardProps {
  planId: string;
  refreshTrigger?: number;
}

const COLUMNS = [
  { id: "notStarted", label: "Not Started", color: "bg-gray-100" },
  { id: "inProgress", label: "In Progress", color: "bg-blue-100" },
  { id: "completed", label: "Completed", color: "bg-green-100" },
];

export default function KanbanBoard({ planId, refreshTrigger = 0 }: KanbanBoardProps) {
  const [tasks, setTasks] = useState<PlannerTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlannerTasks(planId)
      .then((r) => setTasks(r.tasks))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, [planId, refreshTrigger]);

  const handleDrop = async (taskId: string, newStatus: string) => {
    try {
      await updateTask(planId, taskId, { status: newStatus });
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: newStatus as any } : t)));
    } catch {}
  };

  if (loading) return <div className="ct-card p-6 text-[#6b7280]">Loading Kanban…</div>;

  return (
    <div className="ct-card p-5">
      <h2 className="text-base font-bold text-[#111827] mb-4">Kanban</h2>
      <div className="flex gap-4 overflow-x-auto pb-2">
        {COLUMNS.map((col) => {
          const colTasks = tasks.filter((t) => (t.status || "notStarted") === col.id);
          return (
            <div
              key={col.id}
              className={`shrink-0 w-64 rounded-lg p-3 ${col.color}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const taskId = e.dataTransfer.getData("taskId");
                if (taskId) handleDrop(taskId, col.id);
              }}
            >
              <div className="font-medium text-sm text-[#374151] mb-2">
                {col.label} ({colTasks.length})
              </div>
              <div className="space-y-2">
                {colTasks.map((t) => (
                  <div
                    key={t.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("taskId", t.id)}
                    className="p-2 rounded bg-white shadow-sm text-sm cursor-move hover:shadow"
                  >
                    <div className="font-medium truncate">{t.title}</div>
                    <div className="text-xs text-[#6b7280]">
                      {t.assigneeNames?.join(", ") || "—"} · {t.dueDateTime ? new Date(t.dueDateTime).toLocaleDateString() : "—"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
