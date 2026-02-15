"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import ViewToggle from "@/components/planner/ViewToggle";
import SyncButton from "@/components/planner/SyncButton";
import PlanSelector from "@/components/planner/PlanSelector";
import TemplateModal from "@/components/planner/TemplateModal";
import PlanOverviewCharts from "@/components/planner/PlanOverviewCharts";
import AttentionDashboard from "@/components/planner/AttentionDashboard";
import CriticalPathSection from "@/components/planner/CriticalPathSection";
import MilestoneLane from "@/components/planner/MilestoneLane";
import DependencyLens from "@/components/planner/DependencyLens";
import TaskListTable from "@/components/planner/TaskListTable";
import GanttChart from "@/components/planner/GanttChart";
import KanbanBoard from "@/components/planner/KanbanBoard";
import CongressTimeline from "@/components/planner/CongressTimeline";
import WorkstreamProgress from "@/components/planner/WorkstreamProgress";
import CommanderView from "@/components/planner/advanced/CommanderView";
import AlertsDashboard from "@/components/planner/AlertsDashboard";
import ChatPanel from "@/components/planner/ChatPanel";
import { PlanProvider, usePlanId } from "@/components/planner/PlanContext";
import { useSidebarCollapsed } from "@/components/AppShell";

function PlannerContent() {
  const searchParams = useSearchParams();
  const view = (searchParams.get("view") || "base") as "base" | "advanced";
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const { collapsed } = useSidebarCollapsed();
  const planId = usePlanId();

  return (
    <div className={collapsed ? "w-full max-w-full" : "max-w-6xl"}>
      <div className="mb-4">
        <AlertsDashboard planId={planId} refreshTrigger={refreshTrigger} compact />
      </div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <PlanSelector />
          <span className="inline-flex items-center rounded-md bg-[#dcfce7] px-2.5 py-0.5 text-xs font-medium text-[#166534]">
            Active
          </span>
          <span className="text-sm text-[#6b7280]">
            Planner — {view === "advanced" ? "Advanced view" : "Base view"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-[#d1d5db] px-3 py-2 text-sm font-medium text-[#374151] hover:bg-[#f3f4f6]"
          >
            Chat
          </button>
          <button
            type="button"
            onClick={async () => {
              try {
                const { publishPlan } = await import("@/lib/congressTwinApi");
                const res = await publishPlan(planId);
                alert(res.published ? `Published ${res.tasks_pushed} tasks` : res.message);
              } catch (e) {
                alert(e instanceof Error ? e.message : "Publish failed");
              }
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-[#d1d5db] px-3 py-2 text-sm font-medium text-[#374151] hover:bg-[#f3f4f6]"
          >
            Publish
          </button>
          <SyncButton planId={planId} onSyncSuccess={() => setRefreshTrigger((t) => t + 1)} />
          <ViewToggle />
        </div>
      </div>

      {view === "advanced" && (
        <CommanderView planId={planId} refreshTrigger={refreshTrigger} />
      )}

      {view === "base" && (
        <div className={chatOpen ? "flex gap-0 min-h-[70vh]" : undefined}>
          {chatOpen && (
            <div className="w-1/2 min-w-[380px] flex-shrink-0 border-r border-[#e5e7eb] bg-white flex flex-col h-[70vh] sticky top-4">
              <ChatPanel onClose={() => setChatOpen(false)} halfPage />
            </div>
          )}
          <div className={chatOpen ? "flex-1 min-w-0 pl-4 overflow-auto space-y-6" : "space-y-6"}>
            <PlanOverviewCharts planId={planId} refreshTrigger={refreshTrigger} />
            <div className="grid gap-4 lg:grid-cols-2">
              <CongressTimeline />
              <WorkstreamProgress planId={planId} refreshTrigger={refreshTrigger} />
            </div>
            <AttentionDashboard planId={planId} refreshTrigger={refreshTrigger} />
            <CriticalPathSection planId={planId} refreshTrigger={refreshTrigger} />
            <MilestoneLane planId={planId} refreshTrigger={refreshTrigger} />
            <DependencyLens planId={planId} refreshTrigger={refreshTrigger} />
            <GanttChart planId={planId} refreshTrigger={refreshTrigger} />
            <KanbanBoard planId={planId} refreshTrigger={refreshTrigger} />
            <TaskListTable planId={planId} refreshTrigger={refreshTrigger} />
          </div>
        </div>
      )}
      {templateModalOpen && (
        <TemplateModal
          onClose={() => setTemplateModalOpen(false)}
          onCreated={() => {
            setRefreshTrigger((t) => t + 1);
            setTemplateModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

export default function PlannerPage() {
  return (
    <PlanProvider>
      <Suspense fallback={<div className="py-4 text-[#6b7280]">Loading…</div>}>
        <PlannerContent />
      </Suspense>
    </PlanProvider>
  );
}
