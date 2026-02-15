"use client";

import { useEffect, useState } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { fetchPlans, type PlannerPlan } from "@/lib/congressTwinApi";
import { usePlan } from "./PlanContext";

export default function PlanSelector() {
  const { planId, setPlanId } = usePlan();
  const [plans, setPlans] = useState<PlannerPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetchPlans()
      .then((r) => setPlans(r.plans))
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  }, []);

  const current = plans.find((p) => p.plan_id === planId) || { plan_id: planId, name: planId };

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-[#f9fafb] px-3 py-1.5 text-sm text-[#6b7280]">
        <Loader2 className="h-4 w-4 animate-spin" />
        Plans…
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-white px-3 py-2 text-sm text-[#111827] hover:bg-[#f9fafb] min-w-[180px]"
      >
        <span className="truncate">{current.name}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-[#6b7280] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" aria-hidden onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 min-w-[220px] rounded-lg border border-[#e5e7eb] bg-white shadow-lg py-1 max-h-[280px] overflow-y-auto">
            {plans.map((p) => (
              <button
                key={p.plan_id}
                type="button"
                onClick={() => {
                  setPlanId(p.plan_id);
                  setOpen(false);
                }}
                className={`w-full text-left px-3 py-2 text-sm hover:bg-[#f3f4f6] ${
                  p.plan_id === planId ? "bg-[#dcfce7] text-[#166534] font-medium" : "text-[#374151]"
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
