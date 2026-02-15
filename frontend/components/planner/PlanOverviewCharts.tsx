"use client";

import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";
import { fetchPlannerTasks, DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";
import { Loader2 } from "lucide-react";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: "bottom" as const },
  },
  scales: {
    y: { beginAtZero: true, ticks: { stepSize: 1 } },
  },
};

const statusColors = {
  notStarted: "rgba(107, 114, 128, 0.8)",
  inProgress: "rgba(37, 99, 235, 0.8)",
  completed: "rgba(22, 163, 74, 0.8)",
};

interface PlanOverviewChartsProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function PlanOverviewCharts({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: PlanOverviewChartsProps) {
  const [tasks, setTasks] = useState<{ status: string; percentComplete: number }[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchPlannerTasks(planId)
      .then((res) => {
        if (!cancelled) setTasks(res.tasks.map((t) => ({ status: t.status, percentComplete: t.percentComplete })));
      })
      .catch(() => {
        if (!cancelled) setTasks([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [planId, refreshTrigger]);

  if (loading) {
    return (
      <div className="ct-card p-6 flex items-center justify-center min-h-[200px] text-[#6b7280]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  const notStarted = tasks.filter((t) => t.status === "notStarted").length;
  const inProgress = tasks.filter((t) => t.status === "inProgress").length;
  const completed = tasks.filter((t) => t.status === "completed").length;
  const total = tasks.length;
  const overallPercent = total ? Math.round(tasks.reduce((s, t) => s + t.percentComplete, 0) / total) : 0;

  const statusBarData = {
    labels: ["Not started", "In progress", "Completed"],
    datasets: [
      {
        label: "Tasks",
        data: [notStarted, inProgress, completed],
        backgroundColor: [statusColors.notStarted, statusColors.inProgress, statusColors.completed],
      },
    ],
  };

  const statusDoughnutData = {
    labels: ["Not started", "In progress", "Completed"],
    datasets: [
      {
        data: [notStarted, inProgress, completed],
        backgroundColor: [statusColors.notStarted, statusColors.inProgress, statusColors.completed],
        borderWidth: 0,
      },
    ],
  };

  return (
    <div className="ct-card p-5">
      <h2 className="text-base font-bold text-[#111827] mb-4">Plan overview</h2>
      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <p className="text-sm text-[#6b7280] mb-2">Task status</p>
          <div className="h-[200px]">
            <Bar data={statusBarData} options={chartOptions} />
          </div>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="h-[180px] w-full sm:w-[180px] shrink-0">
            <Doughnut
              data={statusDoughnutData}
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
              }}
            />
          </div>
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[#6b7280]">Overall progress</p>
              <div className="mt-1 h-3 w-full rounded-full bg-[#e5e7eb] overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#16a34a] transition-all duration-500"
                  style={{ width: `${overallPercent}%` }}
                />
              </div>
              <p className="mt-1 text-lg font-bold text-[#111827]">{overallPercent}%</p>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg bg-[#f3f4f6] p-2">
                <p className="text-lg font-bold text-[#111827]">{total}</p>
                <p className="text-xs text-[#6b7280]">Total</p>
              </div>
              <div className="rounded-lg bg-[#dcfce7]/50 p-2">
                <p className="text-lg font-bold text-[#16a34a]">{completed}</p>
                <p className="text-xs text-[#6b7280]">Done</p>
              </div>
              <div className="rounded-lg bg-[#fef3c7]/50 p-2">
                <p className="text-lg font-bold text-amber-600">{inProgress + notStarted}</p>
                <p className="text-xs text-[#6b7280]">Open</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
