/**
 * Congress Twin API client (Planner execution + Base/Advanced view).
 * Backend runs on port 8010 by default.
 */

const CONGRESS_TWIN_API =
  process.env.NEXT_PUBLIC_CONGRESS_TWIN_API_URL || "http://localhost:8010";

export const DEFAULT_PLAN_ID = "uc31-plan";

export interface PlannerTask {
  id: string;
  title: string;
  bucketId: string;
  bucketName?: string;
  percentComplete: number;
  status: "notStarted" | "inProgress" | "completed";
  dueDateTime?: string;
  startDateTime?: string;
  completedDateTime?: string;
  createdDateTime?: string;
  assignees?: string[];
  assigneeNames?: string[];
  lastModifiedAt?: string;
  priority?: number;
  orderHint?: string;
  assigneePriority?: string;
  appliedCategories?: string[];
  conversationThreadId?: string;
  description?: string;
  previewType?: string;
  createdBy?: string;
  completedBy?: string;
  checklist?: Array<{
    id: string;
    title: string;
    isChecked: boolean;
    orderHint?: string;
  }>;
  references?: Array<{
    alias?: string;
    type?: string;
    href?: string;
  }>;
  dependencies?: Array<{
    taskId: string;
    dependsOnTaskId: string;
    dependencyType: string;
  }>;
}

export interface AttentionSection {
  count: number;
  tasks: { id: string; title: string; status?: string; dueDateTime?: string; assigneeNames?: string[] }[];
}

export interface AttentionDashboardResponse {
  plan_id: string;
  blockers: AttentionSection;
  overdue: AttentionSection;
  due_next_7_days: AttentionSection;
  recently_changed: AttentionSection;
}

export interface ExecutionTask extends PlannerTask {
  risk_badges?: string[];
  upstream_count?: number;
  downstream_count?: number;
  on_critical_path?: boolean;
}

export interface TaskDependenciesResponse {
  task_id: string;
  upstream: { id: string; title: string; status?: string; dueDateTime?: string; assigneeNames?: string[] }[];
  downstream: { id: string; title: string; status?: string; dueDateTime?: string; assigneeNames?: string[] }[];
  impact_statement: string;
}

export interface CriticalPathResponse {
  plan_id: string;
  critical_path: { id: string; title: string; status?: string; dueDateTime?: string }[];
  task_ids: string[];
}

export interface MilestoneAnalysisResponse {
  plan_id: string;
  event_date: string;
  tasks_before_event: {
    id: string;
    title: string;
    status?: string;
    dueDateTime?: string;
    assigneeNames?: string[];
    on_critical_path?: boolean;
  }[];
  at_risk_tasks: {
    id: string;
    title: string;
    status?: string;
    dueDateTime?: string;
    assigneeNames?: string[];
    days_after_event?: number | null;
  }[];
  at_risk_count: number;
}

// Plan listing (Phase 1.2)
export interface PlannerPlan {
  plan_id: string;
  name: string;
  congress_date?: string | null;
  source_plan_id?: string | null;
  created_at?: string | null;
}

export async function fetchPlans(): Promise<{ plans: PlannerPlan[]; count: number }> {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans`);
  if (!r.ok) throw new Error(`Plans: ${r.status}`);
  return r.json();
}

export interface PlannerBucket {
  id: string;
  name: string;
  order_hint?: string;
}

export async function fetchBuckets(planId: string): Promise<{ plan_id: string; buckets: PlannerBucket[] }> {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/buckets`);
  if (!r.ok) throw new Error(`Buckets: ${r.status}`);
  return r.json();
}

// Task CRUD (Phase 1.1)
export async function createTask(planId: string, body: { title: string; bucketId: string; startDateTime?: string; dueDateTime?: string; assignees?: string[]; priority?: number; description?: string }) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || `Create task: ${r.status}`);
  }
  return r.json() as Promise<{ plan_id: string; task: PlannerTask }>;
}

export async function updateTask(planId: string, taskId: string, body: Partial<{ title: string; bucketId: string; startDateTime: string; dueDateTime: string; assignees: string[]; assigneeNames: string[]; priority: number; description: string; status: string; percentComplete: number }>) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || `Update task: ${r.status}`);
  }
  return r.json() as Promise<{ plan_id: string; task: PlannerTask }>;
}

export async function deleteTask(planId: string, taskId: string) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}`, {
    method: "DELETE",
  });
  if (!r.ok) throw new Error(`Delete task: ${r.status}`);
  return r.json();
}

export async function addSubtask(planId: string, taskId: string, body: { title: string; isChecked?: boolean; orderHint?: string }) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}/subtasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Add subtask: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; task_id: string; subtask: { id: string; title: string; isChecked: boolean; orderHint?: string } }>;
}

export async function updateSubtask(planId: string, taskId: string, subtaskId: string, body: Partial<{ title: string; isChecked: boolean; orderHint: string }>) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}/subtasks/${subtaskId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Update subtask: ${r.status}`);
  return r.json();
}

export async function publishPlan(planId: string) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/publish`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`Publish: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; published: boolean; tasks_pushed: number }>;
}

export interface ImpactAnalysisBody {
  dueDateTime?: string;
  startDateTime?: string;
  assignees?: string[];
  percentComplete?: number;
  slippage_days?: number;
}

export interface ImpactAnalysisResult {
  plan_id?: string;
  task_id?: string;
  affected_task_ids?: string[];
  message?: string;
  impact_statement?: string;
}

export async function analyzeImpact(
  planId: string,
  taskId: string,
  body: ImpactAnalysisBody
): Promise<ImpactAnalysisResult> {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}/impact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Impact: ${r.status}`);
  return r.json();
}

export async function sendChatMessage(planId: string, message: string) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/chat?plan_id=${planId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) throw new Error(`Chat: ${r.status}`);
  return r.json();
}

export async function deleteSubtask(planId: string, taskId: string, subtaskId: string) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/plans/${planId}/tasks/${taskId}/subtasks/${subtaskId}`, {
    method: "DELETE",
  });
  if (!r.ok) throw new Error(`Delete subtask: ${r.status}`);
  return r.json();
}

export async function fetchPlannerTasks(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/tasks/${planId}`);
  if (!r.ok) throw new Error(`Planner tasks: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; tasks: PlannerTask[]; count: number }>;
}

export async function fetchTaskDetails(planId: string, taskId: string) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/tasks/${planId}/${taskId}`);
  if (!r.ok) throw new Error(`Task details: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; task: PlannerTask }>;
}

export interface TaskIntelligence {
  task_id: string;
  plan_id: string;
  risk_score: number;
  risk_factors: string[];
  dependency_risks: Array<{
    dependency_task_id: string;
    dependency_task_title: string;
    dependency_type: string;
    risk_level: "low" | "medium" | "high";
    is_critical: boolean;
    is_delayed: boolean;
    delay_days: number;
    dependency_status: string;
    suggestion: string;
  }>;
  timeline_suggestions: Array<{
    type: string;
    severity: "low" | "medium" | "high";
    title: string;
    description: string;
    action: string;
  }>;
  resource_suggestions: Array<{
    type: string;
    severity: "low" | "medium" | "high";
    title: string;
    description: string;
    action: string;
    recommended_assignee?: string;
    recommendation_score?: number;
  }>;
  critical_path_suggestions: Array<{
    type: string;
    severity: "low" | "medium" | "high";
    title: string;
    description: string;
    action: string;
  }>;
  optimal_assignees: Array<{
    assignee: string;
    score: number;
    workload: {
      total_tasks: number;
      active_tasks: number;
      overdue_tasks: number;
      utilization_score: number;
    };
    historical_completion_rate: number;
    reason: string;
  }>;
  monte_carlo_summary: {
    p50_completion?: string;
    p95_completion?: string;
    critical_path_probability: number;
  } | null;
  markov_summary: {
    current_state?: string;
    expected_completion_days?: number;
    transition_probabilities: Record<string, number>;
  } | null;
}

export async function fetchTaskIntelligence(planId: string, taskId: string, includeSimulations: boolean = true) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/tasks/${planId}/${taskId}/intelligence?include_simulations=${includeSimulations}`);
  if (!r.ok) throw new Error(`Task intelligence: ${r.status}`);
  return r.json() as Promise<TaskIntelligence>;
}

export async function fetchAttentionDashboard(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/attention-dashboard/${planId}`);
  if (!r.ok) throw new Error(`Attention dashboard: ${r.status}`);
  return r.json() as Promise<AttentionDashboardResponse>;
}

export async function fetchExecutionTasks(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/execution-tasks/${planId}`);
  if (!r.ok) throw new Error(`Execution tasks: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; tasks: ExecutionTask[]; count: number }>;
}

export async function fetchTaskDependencies(planId: string, taskId: string) {
  const r = await fetch(
    `${CONGRESS_TWIN_API}/api/v1/planner/tasks/${planId}/dependencies/${taskId}`
  );
  if (!r.ok) throw new Error(`Dependencies: ${r.status}`);
  return r.json() as Promise<TaskDependenciesResponse>;
}

export async function fetchCriticalPath(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/critical-path/${planId}`);
  if (!r.ok) throw new Error(`Critical path: ${r.status}`);
  return r.json() as Promise<CriticalPathResponse>;
}

export async function fetchMilestoneAnalysis(
  planId: string = DEFAULT_PLAN_ID,
  eventDate?: string
) {
  const url = new URL(
    `${CONGRESS_TWIN_API}/api/v1/planner/milestone-analysis/${planId}`
  );
  if (eventDate) url.searchParams.set("event_date", eventDate);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`Milestone analysis: ${r.status}`);
  return r.json() as Promise<MilestoneAnalysisResponse>;
}

export async function fetchPlanLink(planId: string = DEFAULT_PLAN_ID) {
  const url = new URL(`${CONGRESS_TWIN_API}/api/v1/planner/plan-link`);
  url.searchParams.set("plan_id", planId);
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`Plan link: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; url: string }>;
}

// Advanced view (Commander)
export interface ProbabilityGanttBar {
  id: string;
  title: string;
  status?: string;
  start_date: string;
  end_date: string;
  confidence_percent?: number;
  variance_days?: number;
  on_critical_path?: boolean;
}

export async function fetchProbabilityGantt(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/probability-gantt/${planId}`);
  if (!r.ok) throw new Error(`Probability Gantt: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; bars: ProbabilityGanttBar[] }>;
}

export interface MitigationIntervention {
  id: string;
  task_id?: string;
  task_title?: string;
  action: string;
  reason?: string;
  at?: string;
}

export async function fetchMitigationFeed(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/mitigation-feed/${planId}`);
  if (!r.ok) throw new Error(`Mitigation feed: ${r.status}`);
  return r.json() as Promise<{ plan_id: string; interventions: MitigationIntervention[] }>;
}

export interface VeevaInsightsResponse {
  plan_id: string;
  kol_alignment_score?: number;
  kol_alignment_trend?: string;
  staff_fatigue_index?: number;
  staff_fatigue_trend?: string;
  summary?: string;
  insights?: string[];
}

export async function fetchVeevaInsights(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/veeva-insights/${planId}`);
  if (!r.ok) throw new Error(`Veeva insights: ${r.status}`);
  return r.json() as Promise<VeevaInsightsResponse>;
}

export interface SyncResponse {
  plan_id: string;
  status: "ok" | "error";
  source: "simulated" | "graph";
  tasks_synced: number;
  message: string;
}

export async function syncPlannerPlan(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/sync/${planId}`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(`Sync: ${r.status}`);
  return r.json() as Promise<SyncResponse>;
}

export interface ChangesSinceSyncResponse {
  plan_id: string;
  changes: { id: string; title: string; status?: string; dueDateTime?: string; assigneeNames?: string[]; lastModifiedAt?: string }[];
  count: number;
}

export async function fetchChangesSinceSync(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/changes-since-sync/${planId}`);
  if (!r.ok) throw new Error(`Changes since sync: ${r.status}`);
  return r.json() as Promise<ChangesSinceSyncResponse>;
}

// Alerts & external events (HITL)
export interface ExternalEvent {
  id: number;
  event_type: string;
  title?: string;
  description?: string;
  created_at: string;
}

export interface AgentProposedAction {
  id: number;
  title?: string;
  description?: string;
  created_at: string;
}

export interface AlertsResponse {
  plan_id: string;
  external_events: ExternalEvent[];
  pending_actions: AgentProposedAction[];
}

export async function fetchAlerts(planId: string = DEFAULT_PLAN_ID) {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/planner/alerts/${planId}`);
  if (!r.ok) throw new Error(`Alerts: ${r.status}`);
  return r.json() as Promise<AlertsResponse>;
}

export async function deleteExternalEvent(planId: string, eventId: number) {
  const r = await fetch(
    `${CONGRESS_TWIN_API}/api/v1/planner/external-events/${planId}/${eventId}`,
    { method: "DELETE" }
  );
  if (!r.ok) throw new Error(`Delete event: ${r.status}`);
}

export async function approveProposedAction(planId: string, actionId: number) {
  const r = await fetch(
    `${CONGRESS_TWIN_API}/api/v1/planner/proposed-actions/${planId}/${actionId}/approve`,
    { method: "POST" }
  );
  if (!r.ok) throw new Error(`Approve action: ${r.status}`);
}

export async function rejectProposedAction(planId: string, actionId: number) {
  const r = await fetch(
    `${CONGRESS_TWIN_API}/api/v1/planner/proposed-actions/${planId}/${actionId}/reject`,
    { method: "POST" }
  );
  if (!r.ok) throw new Error(`Reject action: ${r.status}`);
}

export async function deleteProposedAction(planId: string, actionId: number) {
  const r = await fetch(
    `${CONGRESS_TWIN_API}/api/v1/planner/proposed-actions/${planId}/${actionId}`,
    { method: "DELETE" }
  );
  if (!r.ok) throw new Error(`Delete action: ${r.status}`);
}

// Monte Carlo simulation
export interface MonteCarloSuggestion {
  id: string;
  type: "enhancement" | "modification";
  priority: "high" | "medium" | "low";
  title: string;
  detail: string;
  task_id?: string | null;
  action_hint?: string;
}

export interface MonteCarloResponse {
  plan_id: string;
  n_simulations: number;
  event_date: string;
  probability_on_time_percent: number;
  percentile_end_dates?: { p10?: string; p50?: string; p90?: string };
  risk_tasks: { task_id: string; title: string; variance_days?: number; p90_finish?: string; on_critical_path?: boolean }[];
  agent_suggestions: MonteCarloSuggestion[];
}

export async function fetchMonteCarlo(
  planId: string = DEFAULT_PLAN_ID,
  nSimulations = 500,
  eventDate?: string,
  seed?: number
) {
  const url = new URL(`${CONGRESS_TWIN_API}/api/v1/planner/monte-carlo/${planId}`);
  url.searchParams.set("n_simulations", String(nSimulations));
  if (eventDate) url.searchParams.set("event_date", eventDate);
  if (seed != null) url.searchParams.set("seed", String(seed));
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`Monte Carlo: ${r.status}`);
  return r.json() as Promise<MonteCarloResponse>;
}

// SSE stream URL for EventSource
export function getStreamUrl(planId: string = DEFAULT_PLAN_ID): string {
  const url = new URL(`${CONGRESS_TWIN_API}/api/v1/planner/stream`);
  url.searchParams.set("plan_id", planId);
  return url.toString();
}

// Enhanced Simulation APIs (per ACP PDFs)
export interface MonteCarloResult {
  plan_id: string;
  n_iterations: number;
  percentiles: {
    p50: string;
    p75: string;
    p95: string;
  };
  critical_path_probability: Record<string, number>;
  bottlenecks: Array<{
    task_id: string;
    title: string;
    bucket: string;
    variance_days: number;
    critical_path_probability: number;
  }>;
  risk_heatmap: Record<string, number>;
}

export interface MarkovAnalysis {
  plan_id?: string;
  task_id?: string;
  current_state?: string;
  transition_matrix?: Record<string, Record<string, number>>;
  expected_completion?: {
    expected_completion_days: number;
    current_state: string;
    variance: number;
  };
  task_analyses?: Array<{
    task_id: string;
    title: string;
    current_state: string;
    expected_completion_days: number;
  }>;
}

export interface CostBreakdown {
  schedule: number;
  resource: number;
  risk: number;
  quality: number;
  disruption: number;
}

export interface CostAnalysis {
  plan_id: string;
  total_cost: number;
  cost_breakdown: CostBreakdown;
  weights: Record<string, number>;
}

export interface HistoricalInsight {
  duration_bias: {
    bucket_stats: Record<string, {
      optimistic: number;
      most_likely: number;
      pessimistic: number;
      mean: number;
      bias_factor: number;
    }>;
    task_type_stats: Record<string, any>;
  };
  implicit_dependencies: Array<{
    from_pattern: string;
    to_pattern: string;
    confidence: number;
    occurrences: number;
  }>;
  bottlenecks: Array<{
    plan_id: string;
    task_id: string;
    title: string;
    bucket: string;
    downstream_count: number;
  }>;
  resource_throughput: Record<string, {
    tasks_completed: number;
    avg_duration_days: number;
    tasks_per_week: number;
  }>;
  response_latency: Record<string, {
    avg_latency_days: number;
    median_latency_days: number;
    samples: number;
  }>;
  block_frequency: {
    total_blocked: number;
    block_rate_by_bucket: Record<string, number>;
    blocked_tasks: Array<{
      task_id: string;
      title: string;
      bucket: string;
    }>;
  };
  phase_durations: Record<string, {
    avg_planned_days: number;
    avg_actual_days: number;
    bias_factor: number;
    sample_count: number;
  }>;
}

export async function runMonteCarlo(
  planId: string = DEFAULT_PLAN_ID,
  nIterations: number = 10000,
  historicalPlanIds?: string[]
): Promise<MonteCarloResult> {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/simulation/monte-carlo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_id: planId,
      n_iterations: nIterations,
      historical_plan_ids: historicalPlanIds,
    }),
  });
  if (!r.ok) throw new Error(`Monte Carlo simulation: ${r.status}`);
  return r.json();
}

export async function getMarkovAnalysis(
  planId: string = DEFAULT_PLAN_ID,
  taskId?: string
): Promise<MarkovAnalysis> {
  const url = new URL(`${CONGRESS_TWIN_API}/api/v1/simulation/markov-analysis`);
  url.searchParams.set("plan_id", planId);
  if (taskId) url.searchParams.set("task_id", taskId);
  const r = await fetch(url.toString(), { method: "GET" });
  if (!r.ok) throw new Error(`Markov analysis: ${r.status}`);
  return r.json();
}

export async function computeCost(
  planId: string = DEFAULT_PLAN_ID,
  weights?: Record<string, number>
): Promise<CostAnalysis> {
  const r = await fetch(`${CONGRESS_TWIN_API}/api/v1/simulation/cost-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_id: planId,
      weights,
    }),
  });
  if (!r.ok) throw new Error(`Cost analysis: ${r.status}`);
  return r.json();
}

export async function getHistoricalInsights(
  planId: string = DEFAULT_PLAN_ID,
  historicalPlanIds?: string[]
): Promise<HistoricalInsight> {
  const url = new URL(`${CONGRESS_TWIN_API}/api/v1/simulation/historical-insights`);
  url.searchParams.set("plan_id", planId);
  if (historicalPlanIds) {
    historicalPlanIds.forEach((id) => url.searchParams.append("historical_plan_ids", id));
  }
  const r = await fetch(url.toString());
  if (!r.ok) throw new Error(`Historical insights: ${r.status}`);
  return r.json();
}
