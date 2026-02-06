"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import ViewToggle from "@/components/planner/ViewToggle";
import SyncButton from "@/components/planner/SyncButton";
import PlanOverviewCharts from "@/components/planner/PlanOverviewCharts";
import AttentionDashboard from "@/components/planner/AttentionDashboard";
import CriticalPathSection from "@/components/planner/CriticalPathSection";
import MilestoneLane from "@/components/planner/MilestoneLane";
import DependencyLens from "@/components/planner/DependencyLens";
import TaskListTable from "@/components/planner/TaskListTable";
import CommanderView from "@/components/planner/advanced/CommanderView";
import AlertsDashboard from "@/components/planner/AlertsDashboard";
import { useSidebarCollapsed } from "@/components/AppShell";

function PlannerContent() {
  const searchParams = useSearchParams();
  const view = (searchParams.get("view") || "base") as "base" | "advanced";
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const { collapsed } = useSidebarCollapsed();

  return (
    <div className={collapsed ? "w-full max-w-full" : "max-w-6xl"}>
      <div className="mb-4">
        <AlertsDashboard refreshTrigger={refreshTrigger} compact />
      </div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center rounded-md bg-[#dcfce7] px-2.5 py-0.5 text-xs font-medium text-[#166534]">
            Active
          </span>
          <span className="text-sm text-[#6b7280]">
            Planner — {view === "advanced" ? "Advanced view" : "Base view"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <SyncButton onSyncSuccess={() => setRefreshTrigger((t) => t + 1)} />
          <ViewToggle />
        </div>
      </div>

      {view === "advanced" && (
        <CommanderView refreshTrigger={refreshTrigger} />
      )}

      {view === "base" && (
        <div className="space-y-6">
          <PlanOverviewCharts refreshTrigger={refreshTrigger} />
          <AttentionDashboard refreshTrigger={refreshTrigger} />
          <CriticalPathSection refreshTrigger={refreshTrigger} />
          <MilestoneLane refreshTrigger={refreshTrigger} />
          <DependencyLens refreshTrigger={refreshTrigger} />
          <TaskListTable refreshTrigger={refreshTrigger} />
        </div>
      )}
    </div>
  );
}

export default function PlannerPage() {
  return (
    <Suspense fallback={<div className="py-4 text-[#6b7280]">Loading…</div>}>
      <PlannerContent />
    </Suspense>
  );
}
