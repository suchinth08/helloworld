"use client";

import { createContext, useContext, useState, useCallback } from "react";
import { DEFAULT_PLAN_ID } from "@/lib/congressTwinApi";

const PlanContext = createContext<{
  planId: string;
  setPlanId: (id: string) => void;
}>({ planId: DEFAULT_PLAN_ID, setPlanId: () => {} });

export function usePlanId() {
  const ctx = useContext(PlanContext);
  return ctx.planId;
}

export function useSetPlanId() {
  const ctx = useContext(PlanContext);
  return ctx.setPlanId;
}

export function usePlan() {
  return useContext(PlanContext);
}

export function PlanProvider({
  children,
  initialPlanId = DEFAULT_PLAN_ID,
}: {
  children: React.ReactNode;
  initialPlanId?: string;
}) {
  const [planId, setPlanIdState] = useState(initialPlanId);
  const setPlanId = useCallback((id: string) => setPlanIdState(id), []);
  return (
    <PlanContext.Provider value={{ planId, setPlanId }}>
      {children}
    </PlanContext.Provider>
  );
}
