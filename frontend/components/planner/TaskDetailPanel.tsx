"use client";

import { useEffect, useState } from "react";
import { X, Calendar, User, Tag, CheckSquare, Link as LinkIcon, GitBranch, FileText, Clock, AlertTriangle, TrendingUp, Users, Target, Zap, BarChart3, Pencil, Trash2, Plus } from "lucide-react";
import {
  fetchTaskDetails,
  fetchTaskIntelligence,
  fetchTaskDependencies,
  updateTask,
  deleteTask,
  addSubtask,
  updateSubtask,
  deleteSubtask,
  analyzeImpact,
  type PlannerTask,
  type TaskIntelligence,
  type ImpactAnalysisResult,
} from "@/lib/congressTwinApi";
import { Loader2 } from "lucide-react";
import { DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface TaskDetailPanelProps {
  taskId: string | null;
  planId?: string;
  onClose: () => void;
  onSaved?: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  notStarted: "Not started",
  inProgress: "In progress",
  completed: "Done",
};

const STATUS_COLOR: Record<string, string> = {
  notStarted: "bg-[#f3f4f6] text-[#6b7280]",
  inProgress: "bg-blue-100 text-blue-800",
  completed: "bg-[#dcfce7] text-[#166534]",
};

function formatDate(iso: string | undefined) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatPriority(priority: number | undefined) {
  if (priority === undefined || priority === null) return "—";
  if (priority <= 3) return "Low";
  if (priority <= 6) return "Medium";
  return "High";
}

/** Convert ISO date string to local datetime string for input[type="datetime-local"] (YYYY-MM-DDTHH:mm). */
function toLocalDatetime(iso: string | undefined): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const h = String(d.getHours()).padStart(2, "0");
    const min = String(d.getMinutes()).padStart(2, "0");
    return `${y}-${m}-${day}T${h}:${min}`;
  } catch {
    return "";
  }
}

export default function TaskDetailPanel({ taskId, planId = DEFAULT_PLAN_ID, onClose }: TaskDetailPanelProps) {
  const [task, setTask] = useState<PlannerTask | null>(null);
  const [intelligence, setIntelligence] = useState<TaskIntelligence | null>(null);
  const [loading, setLoading] = useState(false);
  const [intelligenceLoading, setIntelligenceLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editStatus, setEditStatus] = useState<string>("notStarted");
  const [editDueDateTime, setEditDueDateTime] = useState("");
  const [editStartDateTime, setEditStartDateTime] = useState("");
  const [newSubtaskTitle, setNewSubtaskTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [impactResult, setImpactResult] = useState<ImpactAnalysisResult | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [dependencies, setDependencies] = useState<{ upstream: { id: string; title: string }[]; downstream: { id: string; title: string }[]; impact_statement: string } | null>(null);

  useEffect(() => {
    if (!taskId) {
      setTask(null);
      setIntelligence(null);
      setEditMode(false);
      setNewSubtaskTitle("");
      return;
    }

    setLoading(true);
    setIntelligenceLoading(true);
    setError(null);
    setEditMode(false);
    setNewSubtaskTitle("");

    // Fetch task details and intelligence in parallel
    Promise.all([
      fetchTaskDetails(planId, taskId),
      fetchTaskIntelligence(planId, taskId, true).catch(() => null),
      fetchTaskDependencies(planId, taskId).catch(() => null),
    ])
      .then(([taskRes, intelligenceRes, depsRes]) => {
        const t = taskRes.task;
        setTask(t);
        setIntelligence(intelligenceRes);
        setDependencies(depsRes ? { upstream: depsRes.upstream, downstream: depsRes.downstream, impact_statement: depsRes.impact_statement } : null);
        setImpactResult(null);
        setEditTitle(t.title || "");
        setEditDescription(t.description ?? "");
        setEditStatus(t.status || "notStarted");
        setEditDueDateTime(toLocalDatetime(t.dueDateTime));
        setEditStartDateTime(toLocalDatetime(t.startDateTime));
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load task details");
      })
      .finally(() => {
        setLoading(false);
        setIntelligenceLoading(false);
      });
  }, [taskId, planId]);

  if (!taskId) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Sidebar */}
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white shadow-xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#e5e7eb]">
          <h2 className="text-lg font-bold text-[#111827]">Task Details</h2>
          <div className="flex items-center gap-1">
            {!editMode ? (
              <button
                type="button"
                onClick={() => setEditMode(true)}
                className="rounded p-2 text-[#6b7280] hover:bg-[#f3f4f6]"
                title="Edit"
              >
                <Pencil className="h-4 w-4" />
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6]"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-[#6b7280]" />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && task && (
            <div className="space-y-6">
              {/* Title and Status */}
              <div>
                {editMode ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full text-xl font-bold text-[#111827] mb-3 rounded border border-[#d1d5db] px-3 py-2"
                  />
                ) : (
                  <h1 className="text-2xl font-bold text-[#111827] mb-3">{task.title}</h1>
                )}
                <div className="flex items-center gap-3 flex-wrap">
                  {editMode ? (
                    <select
                      value={editStatus}
                      onChange={(e) => setEditStatus(e.target.value)}
                      className="rounded border border-[#d1d5db] px-2 py-1 text-sm"
                    >
                      {(["notStarted", "inProgress", "completed"] as const).map((s) => (
                        <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                      ))}
                    </select>
                  ) : (
                    <span className={`inline-flex rounded px-2.5 py-1 text-xs font-medium ${STATUS_COLOR[task.status ?? ""] ?? STATUS_COLOR.notStarted}`}>
                      {STATUS_LABEL[task.status ?? ""] ?? task.status ?? "—"}
                    </span>
                  )}
                  {!editMode && task.priority !== undefined && (
                    <span className="inline-flex items-center gap-1.5 text-sm text-[#6b7280]">
                      <Tag className="h-4 w-4" />
                      {formatPriority(task.priority)}
                    </span>
                  )}
                  {!editMode && (
                    <span className="text-sm text-[#6b7280]">
                      {task.percentComplete ?? 0}% complete
                    </span>
                  )}
                </div>
                {editMode && (
                  <div className="flex gap-2 mt-3 flex-wrap">
                    <button
                      type="button"
                      onClick={async () => {
                        setSaving(true);
                        setError(null);
                        try {
                          const toIso = (s: string) => (s ? (s.endsWith("Z") || s.includes("+") ? s : `${s}Z`) : undefined);
                          const res = await updateTask(planId, taskId, {
                            title: editTitle.trim(),
                            status: editStatus,
                            description: editDescription || undefined,
                            dueDateTime: toIso(editDueDateTime),
                            startDateTime: toIso(editStartDateTime),
                          });
                          setTask(res.task);
                          setEditMode(false);
                          onSaved?.();
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Failed to save");
                        } finally {
                          setSaving(false);
                        }
                      }}
                      disabled={saving}
                      className="inline-flex items-center gap-2 rounded-lg bg-[#16a34a] px-3 py-2 text-sm font-medium text-white hover:bg-[#15803d] disabled:opacity-60"
                    >
                      {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditMode(false);
                        setEditTitle(task.title || "");
                        setEditDescription(task.description || "");
                        setEditStatus(task.status || "notStarted");
                        setEditDueDateTime(toLocalDatetime(task.dueDateTime));
                        setEditStartDateTime(toLocalDatetime(task.startDateTime));
                      }}
                      className="rounded-lg border border-[#d1d5db] px-3 py-2 text-sm font-medium text-[#374151] hover:bg-[#f3f4f6]"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={async () => {
                        if (!confirm("Delete this task?")) return;
                        try {
                          await deleteTask(planId, taskId);
                          onSaved?.();
                          onClose();
                        } catch (e) {
                          setError(e instanceof Error ? e.message : "Failed to delete");
                        }
                      }}
                      className="rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 ml-auto"
                    >
                      <Trash2 className="h-4 w-4 inline mr-1" />
                      Delete
                    </button>
                  </div>
                )}
                {editMode && (dependencies?.upstream?.length || dependencies?.downstream?.length || dependencies?.impact_statement) && (
                  <div className="mt-4 p-3 rounded-lg bg-[#f0fdf4] border border-[#bbf7d0] text-sm">
                    <h4 className="font-medium text-[#166534] mb-2 flex items-center gap-2">
                      <GitBranch className="h-4 w-4" />
                      Dependencies & impact
                    </h4>
                    {dependencies.impact_statement && (
                      <p className="text-[#15803d] mb-2">{dependencies.impact_statement}</p>
                    )}
                    {dependencies.upstream?.length > 0 && (
                      <p className="text-[#6b7280]">Upstream: {dependencies.upstream.map((u) => u.title).join(", ")}</p>
                    )}
                    {dependencies.downstream?.length > 0 && (
                      <p className="text-[#6b7280]">Downstream: {dependencies.downstream.map((d) => d.title).join(", ")}</p>
                    )}
                  </div>
                )}
                {editMode && (
                  <div className="mt-4 p-3 rounded-lg bg-[#eff6ff] border border-[#bfdbfe] text-sm">
                    <h4 className="font-medium text-[#1e40af] mb-2 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Impact of this change
                    </h4>
                    <button
                      type="button"
                      onClick={async () => {
                        setImpactLoading(true);
                        setImpactResult(null);
                        try {
                          const toIso = (s: string) => (s ? (s.endsWith("Z") || s.includes("+") ? s : `${s}Z`) : undefined);
                          const res = await analyzeImpact(planId, taskId, {
                            dueDateTime: toIso(editDueDateTime),
                            startDateTime: toIso(editStartDateTime),
                          });
                          setImpactResult(res);
                        } catch (e) {
                          setImpactResult({ message: e instanceof Error ? e.message : "Impact check failed" });
                        } finally {
                          setImpactLoading(false);
                        }
                      }}
                      disabled={impactLoading}
                      className="inline-flex items-center gap-2 rounded-lg border border-[#3b82f6] px-3 py-1.5 text-sm font-medium text-[#1e40af] hover:bg-[#dbeafe] disabled:opacity-60"
                    >
                      {impactLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                      Check impact
                    </button>
                    {impactResult && (
                      <div className="mt-2 p-2 rounded bg-white/80 text-[#374151]">
                        {impactResult.message && <p>{impactResult.message}</p>}
                        {impactResult.affected_task_ids && impactResult.affected_task_ids.length > 0 && (
                          <p className="mt-1">Affected tasks: {impactResult.affected_task_ids.join(", ")}</p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Description */}
              {editMode ? (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Description
                  </h3>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-[#d1d5db] px-3 py-2 text-sm resize-none"
                  />
                </div>
              ) : task.description ? (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Description
                  </h3>
                  <p className="text-sm text-[#374151] whitespace-pre-wrap">{task.description}</p>
                </div>
              ) : null}

              {/* Dates */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {editMode ? (
                  <>
                    <div>
                      <label className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 block">Start Date</label>
                      <input
                        type="datetime-local"
                        value={editStartDateTime}
                        onChange={(e) => setEditStartDateTime(e.target.value)}
                        className="w-full rounded border border-[#d1d5db] px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 block">Due Date</label>
                      <input
                        type="datetime-local"
                        value={editDueDateTime}
                        onChange={(e) => setEditDueDateTime(e.target.value)}
                        className="w-full rounded border border-[#d1d5db] px-3 py-2 text-sm"
                      />
                    </div>
                  </>
                ) : (
                  <>
                {task.startDateTime && (
                  <div>
                    <h3 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" />
                      Start Date
                    </h3>
                    <p className="text-sm text-[#111827]">{formatDate(task.startDateTime)}</p>
                  </div>
                )}
                {task.dueDateTime && (
                  <div>
                    <h3 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 flex items-center gap-1.5">
                      <Calendar className="h-3.5 w-3.5" />
                      Due Date
                    </h3>
                    <p className="text-sm text-[#111827]">{formatDate(task.dueDateTime)}</p>
                  </div>
                )}
                  </>
                )}
                {task.completedDateTime && (
                  <div>
                    <h3 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Completed Date
                    </h3>
                    <p className="text-sm text-[#111827]">{formatDate(task.completedDateTime)}</p>
                  </div>
                )}
                {task.createdDateTime && (
                  <div>
                    <h3 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-1 flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      Created Date
                    </h3>
                    <p className="text-sm text-[#111827]">{formatDate(task.createdDateTime)}</p>
                  </div>
                )}
              </div>

              {/* Assignees */}
              {task.assigneeNames && task.assigneeNames.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Assignees
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {task.assigneeNames.map((name, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#f3f4f6] text-sm text-[#374151]"
                      >
                        <User className="h-3.5 w-3.5" />
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Bucket */}
              {task.bucketName && (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2">Bucket</h3>
                  <span className="inline-flex px-2.5 py-1 rounded bg-blue-50 text-sm text-blue-700">
                    {task.bucketName}
                  </span>
                </div>
              )}

              {/* Categories */}
              {task.appliedCategories && task.appliedCategories.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Categories
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {task.appliedCategories.map((cat, idx) => (
                      <span
                        key={idx}
                        className="inline-flex px-2.5 py-1 rounded bg-purple-50 text-sm text-purple-700"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Checklist */}
              <div>
                <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                  <CheckSquare className="h-4 w-4" />
                  Checklist
                </h3>
                {task.checklist && task.checklist.length > 0 ? (
                  <ul className="space-y-2">
                    {task.checklist.map((item) => (
                      <li key={item.id} className="flex items-start gap-2 group">
                        <input
                          type="checkbox"
                          checked={item.isChecked}
                          onChange={async () => {
                            try {
                              await updateSubtask(planId, taskId, item.id, { isChecked: !item.isChecked });
                              setTask((t) => t ? {
                                ...t,
                                checklist: (t.checklist || []).map((c) =>
                                  c.id === item.id ? { ...c, isChecked: !c.isChecked } : c
                                ),
                              } : null);
                              onSaved?.();
                            } catch {}
                          }}
                          className="mt-0.5 h-4 w-4 rounded border-[#d1d5db] text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span className={`flex-1 text-sm ${item.isChecked ? "text-[#6b7280] line-through" : "text-[#374151]"}`}>
                          {item.title}
                        </span>
                        <button
                          type="button"
                          onClick={async () => {
                            try {
                              await deleteSubtask(planId, taskId, item.id);
                              setTask((t) => t ? { ...t, checklist: (t.checklist || []).filter((c) => c.id !== item.id) } : null);
                              onSaved?.();
                            } catch {}
                          }}
                          className="opacity-0 group-hover:opacity-100 p-0.5 text-red-500 hover:bg-red-50 rounded"
                          title="Delete subtask"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-[#6b7280]">No subtasks</p>
                )}
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={newSubtaskTitle}
                    onChange={(e) => setNewSubtaskTitle(e.target.value)}
                    placeholder="Add subtask..."
                    className="flex-1 rounded border border-[#d1d5db] px-3 py-1.5 text-sm"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        if (newSubtaskTitle.trim()) {
                          addSubtask(planId, taskId, { title: newSubtaskTitle.trim() })
                            .then((r) => {
                              setTask((t) => t ? { ...t, checklist: [...(t.checklist || []), r.subtask] } : null);
                              setNewSubtaskTitle("");
                              onSaved?.();
                            })
                            .catch(() => {});
                        }
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (newSubtaskTitle.trim()) {
                        addSubtask(planId, taskId, { title: newSubtaskTitle.trim() })
                          .then((r) => {
                            setTask((t) => t ? { ...t, checklist: [...(t.checklist || []), r.subtask] } : null);
                            setNewSubtaskTitle("");
                            onSaved?.();
                          })
                          .catch(() => {});
                      }
                    }}
                    className="rounded px-2 py-1.5 text-sm font-medium text-[#16a34a] hover:bg-[#dcfce7]"
                  >
                    <Plus className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Dependencies - Show basic list, detailed analysis in Intelligence section */}
              {task.dependencies && task.dependencies.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    Dependencies ({task.dependencies.length})
                  </h3>
                  <ul className="space-y-2">
                    {task.dependencies.map((dep, idx) => (
                      <li key={idx} className="text-sm text-[#374151]">
                        <span className="font-medium">Depends on:</span> {dep.dependsOnTaskId}
                        {dep.dependencyType && (
                          <span className="ml-2 text-xs text-[#6b7280]">({dep.dependencyType})</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  {intelligence && intelligence.dependency_risks && intelligence.dependency_risks.length > 0 && (
                    <div className="mt-2 text-xs text-blue-600">
                      See detailed dependency analysis below ↓
                    </div>
                  )}
                </div>
              )}

              {/* References */}
              {task.references && task.references.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                    <LinkIcon className="h-4 w-4" />
                    References
                  </h3>
                  <ul className="space-y-2">
                    {task.references.map((ref, idx) => (
                      <li key={idx} className="text-sm">
                        {ref.href ? (
                          <a
                            href={ref.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline flex items-center gap-1.5"
                          >
                            <LinkIcon className="h-3.5 w-3.5" />
                            {ref.alias || ref.href}
                          </a>
                        ) : (
                          <span className="text-[#374151]">{ref.alias || `Reference ${idx + 1}`}</span>
                        )}
                        {ref.type && (
                          <span className="ml-2 text-xs text-[#6b7280]">({ref.type})</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Intelligence & Suggestions */}
              {intelligenceLoading && (
                <div className="pt-4 border-t border-[#e5e7eb]">
                  <div className="flex items-center gap-2 text-sm text-[#6b7280]">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing task intelligence...
                  </div>
                </div>
              )}

              {!intelligenceLoading && !intelligence && task && (
                <div className="pt-4 border-t border-[#e5e7eb]">
                  <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
                    <h3 className="text-sm font-semibold text-amber-800 mb-1 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Simulations & suggestions
                    </h3>
                    <p className="text-xs text-amber-700 mb-3">
                      Monte Carlo and Markov Chain suggestions could not be loaded. This can happen if the server is busy or the plan has no simulation data yet.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setIntelligenceLoading(true);
                        fetchTaskIntelligence(planId, taskId, true)
                          .then(setIntelligence)
                          .catch(() => setIntelligence(null))
                          .finally(() => setIntelligenceLoading(false));
                      }}
                      className="text-xs font-medium text-amber-800 underline hover:no-underline"
                    >
                      Retry loading suggestions
                    </button>
                  </div>
                </div>
              )}

              {!intelligenceLoading && intelligence && (
                <div className="pt-4 border-t border-[#e5e7eb] space-y-6">
                  {/* Risk Score */}
                  <div>
                    <h3 className="text-sm font-semibold text-[#111827] mb-3 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Risk Assessment
                    </h3>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-[#6b7280]">Overall Risk Score</span>
                          <span className={`text-sm font-bold ${
                            intelligence.risk_score >= 70 ? "text-red-600" :
                            intelligence.risk_score >= 40 ? "text-yellow-600" :
                            "text-green-600"
                          }`}>
                            {intelligence.risk_score}/100
                          </span>
                        </div>
                        <div className="w-full bg-[#f3f4f6] rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              intelligence.risk_score >= 70 ? "bg-red-500" :
                              intelligence.risk_score >= 40 ? "bg-yellow-500" :
                              "bg-green-500"
                            }`}
                            style={{ width: `${intelligence.risk_score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    {intelligence.risk_factors.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {intelligence.risk_factors.map((factor, idx) => (
                          <div key={idx} className="text-xs text-[#6b7280] flex items-center gap-1.5">
                            <span className="text-red-500">•</span>
                            {factor}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Dependency Risks */}
                  {intelligence.dependency_risks && intelligence.dependency_risks.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <GitBranch className="h-4 w-4" />
                        Dependency Analysis
                      </h3>
                      <div className="space-y-3">
                        {intelligence.dependency_risks.map((risk, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border ${
                              risk.risk_level === "high" ? "bg-red-50 border-red-200" :
                              risk.risk_level === "medium" ? "bg-yellow-50 border-yellow-200" :
                              "bg-blue-50 border-blue-200"
                            }`}
                          >
                            <div className="flex items-start justify-between mb-1">
                              <span className="text-sm font-medium text-[#111827]">
                                {risk.dependency_task_title || risk.dependency_task_id}
                              </span>
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                risk.risk_level === "high" ? "bg-red-100 text-red-700" :
                                risk.risk_level === "medium" ? "bg-yellow-100 text-yellow-700" :
                                "bg-blue-100 text-blue-700"
                              }`}>
                                {risk.risk_level.toUpperCase()}
                              </span>
                            </div>
                            <div className="text-xs text-[#6b7280] space-y-1">
                              <div>Status: {risk.dependency_status}</div>
                              {risk.is_delayed && (
                                <div className="text-red-600">Delayed by {risk.delay_days} days</div>
                              )}
                              {risk.is_critical && (
                                <div className="text-orange-600 font-medium">On critical path</div>
                              )}
                              <div className="mt-2 text-[#374151]">{risk.suggestion}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timeline Suggestions */}
                  {intelligence.timeline_suggestions && intelligence.timeline_suggestions.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        Timeline Optimization
                      </h3>
                      <div className="space-y-2">
                        {intelligence.timeline_suggestions.map((suggestion, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border-l-4 ${
                              suggestion.severity === "high" ? "border-red-500 bg-red-50" :
                              suggestion.severity === "medium" ? "border-yellow-500 bg-yellow-50" :
                              "border-blue-500 bg-blue-50"
                            }`}
                          >
                            <div className="text-sm font-medium text-[#111827] mb-1">
                              {suggestion.title}
                            </div>
                            <div className="text-xs text-[#6b7280] mb-2">
                              {suggestion.description}
                            </div>
                            <div className="text-xs font-medium text-[#374151]">
                              💡 {suggestion.action}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Resource & Reassignment Suggestions */}
                  {intelligence.resource_suggestions && intelligence.resource_suggestions.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        Resource Optimization
                      </h3>
                      <div className="space-y-2">
                        {intelligence.resource_suggestions.map((suggestion, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-lg border-l-4 ${
                              suggestion.severity === "high" ? "border-red-500 bg-red-50" :
                              suggestion.severity === "medium" ? "border-yellow-500 bg-yellow-50" :
                              "border-green-500 bg-green-50"
                            }`}
                          >
                            <div className="text-sm font-medium text-[#111827] mb-1">
                              {suggestion.title}
                            </div>
                            <div className="text-xs text-[#6b7280] mb-2">
                              {suggestion.description}
                            </div>
                            {suggestion.recommended_assignee && (
                              <div className="text-xs font-medium text-green-700 mb-1">
                                ✨ Recommended: {suggestion.recommended_assignee} (Score: {(suggestion.recommendation_score || 0).toFixed(2)})
                              </div>
                            )}
                            <div className="text-xs font-medium text-[#374151]">
                              💡 {suggestion.action}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Optimal Assignees */}
                  {intelligence.optimal_assignees && intelligence.optimal_assignees.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <Target className="h-4 w-4" />
                        Recommended Assignees
                      </h3>
                      <div className="space-y-2">
                        {intelligence.optimal_assignees.slice(0, 3).map((opt, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-green-50 border border-green-200"
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-[#111827]">
                                {opt.assignee}
                              </span>
                              <span className="text-xs text-green-700 font-medium">
                                Score: {opt.score.toFixed(2)}
                              </span>
                            </div>
                            <div className="text-xs text-[#6b7280] space-y-1">
                              <div>Active tasks: {opt.workload.active_tasks}</div>
                              <div>Historical completion: {(opt.historical_completion_rate * 100).toFixed(0)}%</div>
                              <div className="mt-1 text-[#374151]">{opt.reason}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Critical Path Alerts */}
                  {intelligence.critical_path_suggestions && intelligence.critical_path_suggestions.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <Zap className="h-4 w-4" />
                        Critical Path
                      </h3>
                      <div className="space-y-2">
                        {intelligence.critical_path_suggestions.map((suggestion, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg bg-orange-50 border border-orange-200"
                          >
                            <div className="text-sm font-medium text-[#111827] mb-1">
                              {suggestion.title}
                            </div>
                            <div className="text-xs text-[#6b7280] mb-2">
                              {suggestion.description}
                            </div>
                            <div className="text-xs font-medium text-[#374151]">
                              💡 {suggestion.action}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Simulation Summaries */}
                  {(intelligence.monte_carlo_summary || intelligence.markov_summary) && (
                    <div>
                      <h3 className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" />
                        Simulation Insights
                      </h3>
                      <div className="space-y-3">
                        {intelligence.monte_carlo_summary && (
                          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
                            <div className="text-xs font-semibold text-[#111827] mb-2">Monte Carlo Predictions</div>
                            <div className="text-xs text-[#6b7280] space-y-1">
                              {intelligence.monte_carlo_summary.p50_completion && (
                                <div>P50 Completion: {formatDate(intelligence.monte_carlo_summary.p50_completion)}</div>
                              )}
                              {intelligence.monte_carlo_summary.p95_completion && (
                                <div>P95 Completion: {formatDate(intelligence.monte_carlo_summary.p95_completion)}</div>
                              )}
                              <div>Critical Path Probability: {(intelligence.monte_carlo_summary.critical_path_probability || 0).toFixed(0)}%</div>
                            </div>
                          </div>
                        )}
                        {intelligence.markov_summary && (
                          <div className="p-3 rounded-lg bg-purple-50 border border-purple-200">
                            <div className="text-xs font-semibold text-[#111827] mb-2">Markov Chain Analysis</div>
                            <div className="text-xs text-[#6b7280] space-y-1">
                              {intelligence.markov_summary.current_state && (
                                <div>Current State: {intelligence.markov_summary.current_state}</div>
                              )}
                              {intelligence.markov_summary.expected_completion_days && (
                                <div>Expected Completion: {intelligence.markov_summary.expected_completion_days.toFixed(1)} days</div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Metadata */}
              <div className="pt-4 border-t border-[#e5e7eb]">
                <h3 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide mb-2">
                  Metadata
                </h3>
                <dl className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <div>
                    <dt className="text-[#6b7280]">Task ID</dt>
                    <dd className="text-[#111827] font-mono text-xs">{task.id}</dd>
                  </div>
                  {task.orderHint && (
                    <div>
                      <dt className="text-[#6b7280]">Order Hint</dt>
                      <dd className="text-[#111827] font-mono text-xs">{task.orderHint}</dd>
                    </div>
                  )}
                  {task.lastModifiedAt && (
                    <div>
                      <dt className="text-[#6b7280]">Last Modified</dt>
                      <dd className="text-[#111827]">{formatDate(task.lastModifiedAt)}</dd>
                    </div>
                  )}
                  {task.createdBy && (
                    <div>
                      <dt className="text-[#6b7280]">Created By</dt>
                      <dd className="text-[#111827]">{task.createdBy}</dd>
                    </div>
                  )}
                  {task.completedBy && (
                    <div>
                      <dt className="text-[#6b7280]">Completed By</dt>
                      <dd className="text-[#111827]">{task.completedBy}</dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
