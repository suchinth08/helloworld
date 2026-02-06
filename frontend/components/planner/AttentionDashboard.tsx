"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Clock,
  Calendar,
  RefreshCw,
  GitBranch,
  FileEdit,
  ExternalLink,
} from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import {
  fetchAttentionDashboard,
  fetchChangesSinceSync,
  fetchPlanLink,
  type AttentionDashboardResponse,
} from "@/lib/congressTwinApi";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

const DEFAULT_PLAN_ID = "uc31-plan";

interface AttentionDashboardProps {
  refreshTrigger?: number;
}

export default function AttentionDashboard({ refreshTrigger = 0 }: AttentionDashboardProps) {
  const [data, setData] = useState<AttentionDashboardResponse | null>(null);
  const [changes, setChanges] = useState<{ count: number; changes: { id: string; title: string; lastModifiedAt?: string; assigneeNames?: string[] }[] }>({ count: 0, changes: [] });
  const [planLink, setPlanLink] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, changesRes, linkRes] = await Promise.all([
        fetchAttentionDashboard(DEFAULT_PLAN_ID),
        fetchChangesSinceSync(DEFAULT_PLAN_ID).catch(() => ({ plan_id: DEFAULT_PLAN_ID, count: 0, changes: [] })),
        fetchPlanLink(DEFAULT_PLAN_ID).catch(() => ({ url: "" })),
      ]);
      setData(res);
      setChanges({ count: changesRes.count, changes: changesRes.changes });
      setPlanLink(linkRes.url || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-4 text-sm text-[#6b7280]">
        Loading attention dashboard…
      </div>
    );
  }
  if (error) {
    return (
      <div className="ct-card border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
        <button
          type="button"
          onClick={load}
          className="ml-2 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }
  if (!data) return null;

  const sections = [
    {
      key: "blockers",
      label: "Blockers",
      count: data.blockers.count,
      tasks: data.blockers.tasks,
      icon: AlertTriangle,
      iconBg: "bg-red-100",
      iconColor: "text-red-600",
      border: "border-red-200",
      bg: "bg-white",
      countColor: "text-[#111827]",
      subColor: "text-[#6b7280]",
    },
    {
      key: "overdue",
      label: "Overdue",
      count: data.overdue.count,
      tasks: data.overdue.tasks,
      icon: Clock,
      iconBg: "bg-amber-100",
      iconColor: "text-amber-600",
      border: "border-amber-200",
      bg: "bg-white",
      countColor: "text-[#111827]",
      subColor: "text-[#6b7280]",
    },
    {
      key: "due_next_7_days",
      label: "Due next 7 days",
      count: data.due_next_7_days.count,
      tasks: data.due_next_7_days.tasks,
      icon: Calendar,
      iconBg: "bg-blue-100",
      iconColor: "text-blue-600",
      border: "border-[#e5e7eb]",
      bg: "bg-white",
      countColor: "text-[#111827]",
      subColor: "text-[#6b7280]",
    },
    {
      key: "critical_path_due_next",
      label: "Critical path due next",
      count: data.critical_path_due_next?.count ?? 0,
      tasks: data.critical_path_due_next?.tasks ?? [],
      icon: GitBranch,
      iconBg: "bg-violet-100",
      iconColor: "text-violet-600",
      border: "border-[#e5e7eb]",
      bg: "bg-white",
      countColor: "text-[#111827]",
      subColor: "text-[#6b7280]",
    },
    {
      key: "recently_changed",
      label: "Recently changed",
      count: data.recently_changed.count,
      tasks: data.recently_changed.tasks,
      icon: RefreshCw,
      iconBg: "bg-[#dcfce7]",
      iconColor: "text-[#16a34a]",
      border: "border-[#e5e7eb]",
      bg: "bg-white",
      countColor: "text-[#111827]",
      subColor: "text-[#6b7280]",
    },
  ];

  return (
    <div className="ct-card p-5">
      <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-base font-bold text-[#111827]">
          What needs attention
        </h2>
        <div className="flex items-center gap-2">
          {planLink && (
            <a
              href={planLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-sm font-medium text-[#374151] hover:bg-[#f9fafb]"
            >
              <ExternalLink className="h-4 w-4" />
              Open in Planner
            </a>
          )}
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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {sections.map(({ key, label, count, tasks, icon: Icon, iconBg, iconColor, border, bg, countColor, subColor }) => (
          <div
            key={key}
            className={`rounded-lg border ${border} ${bg} p-4 shadow-sm`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div className={`rounded p-1.5 ${iconBg}`}>
                <Icon className={`h-4 w-4 ${iconColor}`} />
              </div>
              <span className="text-xs font-semibold uppercase tracking-wide text-[#6b7280]">{label}</span>
            </div>
            <div className={`text-2xl font-bold ${countColor}`}>{count}</div>
            {tasks.length > 0 && (
              <ul className="mt-2 space-y-2 text-xs">
                {tasks.slice(0, 4).map((t) => (
                  <li key={t.id} className="rounded border border-[#f3f4f6] bg-[#fafafa] p-2">
                    <p className="font-medium text-[#111827] truncate" title={t.title}>{t.title}</p>
                    {t.assigneeNames?.length ? (
                      <p className="text-[#6b7280] mt-0.5">Owner: {t.assigneeNames.join(", ")}</p>
                    ) : null}
                    {t.dueDateTime && (
                      <p className="text-[#6b7280] mt-0.5">Due: {new Date(t.dueDateTime).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</p>
                    )}
                    {t.status && (
                      <p className="text-[#9ca3af] mt-0.5 capitalize">{t.status.replace(/([A-Z])/g, " $1").trim()}</p>
                    )}
                  </li>
                ))}
                {tasks.length > 4 && <li className="text-[#9ca3af] pt-1">+{tasks.length - 4} more</li>}
              </ul>
            )}
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-[#e5e7eb]">
        <p className="text-sm font-semibold text-[#111827] mb-2 flex items-center gap-2">
          <FileEdit className="h-4 w-4 text-[#6b7280]" />
          Changes since publish
        </p>
        {changes.count > 0 ? (
            <ul className="space-y-2 text-sm">
              {changes.changes.slice(0, 5).map((c) => (
                <li key={c.id} className="rounded border border-[#f3f4f6] bg-[#fafafa] p-2">
                  <p className="font-medium text-[#111827] truncate" title={c.title}>{c.title}</p>
                  {c.assigneeNames?.length ? <p className="text-[#6b7280] text-xs mt-0.5">Owner: {c.assigneeNames.join(", ")}</p> : null}
                  {c.lastModifiedAt ? <p className="text-[#9ca3af] text-xs mt-0.5">Updated: {new Date(c.lastModifiedAt).toLocaleString()}</p> : null}
                </li>
              ))}
              {changes.changes.length > 5 && <li className="text-[#9ca3af]">+{changes.changes.length - 5} more</li>}
            </ul>
          ) : (
            <p className="text-sm text-[#9ca3af]">No changes since last sync.</p>
          )}
        </div>
      <div className="mt-4 pt-4 border-t border-[#e5e7eb]">
        <p className="text-sm text-[#6b7280] mb-2">Attention summary</p>
        <div className="h-[120px]">
          <Bar
            data={{
              labels: sections.map((s) => s.label),
              datasets: [
                {
                  label: "Count",
                  data: sections.map((s) => s.count),
                  backgroundColor: [
                    "rgba(220, 38, 38, 0.7)",
                    "rgba(245, 158, 11, 0.7)",
                    "rgba(37, 99, 235, 0.7)",
                    "rgba(139, 92, 246, 0.7)",
                    "rgba(22, 163, 74, 0.7)",
                  ],
                },
              ],
            }}
            options={{
              indexAxis: "y",
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1 } },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
}
