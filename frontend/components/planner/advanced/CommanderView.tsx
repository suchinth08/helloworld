"use client";

import { useState } from "react";
import ProbabilityGantt from "./ProbabilityGantt";
import AgentMitigationFeed from "./AgentMitigationFeed";
import VeevaInsights from "./VeevaInsights";
import SSELiveStatus from "./SSELiveStatus";
import MonteCarloSuggestions from "./MonteCarloSuggestions";
import PendingApprovals from "./PendingApprovals";
import AlertsDashboard from "@/components/planner/AlertsDashboard";
import { DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

interface CommanderViewProps {
  planId?: string;
  refreshTrigger?: number;
}

export default function CommanderView({ planId = DEFAULT_PLAN_ID, refreshTrigger = 0 }: CommanderViewProps) {
  const [alertsRefresh, setAlertsRefresh] = useState(0);

  return (
    <div className="space-y-6">
      {/* Top: Monte Carlo & agent suggestions, Human-in-the-loop approvals */}
      <MonteCarloSuggestions planId={planId} refreshTrigger={refreshTrigger} />
      <PendingApprovals
        planId={planId}
        refreshTrigger={refreshTrigger + alertsRefresh}
        onApproveOrReject={() => setAlertsRefresh((n) => n + 1)}
      />
      <AlertsDashboard
        planId={planId}
        refreshTrigger={refreshTrigger + alertsRefresh}
        onDeleteEvent={() => setAlertsRefresh((n) => n + 1)}
      />
      <SSELiveStatus planId={planId} />
      <div className="grid gap-6 lg:grid-cols-2">
        <AgentMitigationFeed planId={planId} refreshTrigger={refreshTrigger} />
        <VeevaInsights planId={planId} refreshTrigger={refreshTrigger} />
      </div>
      {/* Gantt at the end */}
      <ProbabilityGantt planId={planId} refreshTrigger={refreshTrigger} />
    </div>
  );
}
