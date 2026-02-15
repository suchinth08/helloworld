"use client";

import { usePlanId } from "./PlanContext";

export default function CongressTimeline() {
  const planId = usePlanId();
  // MVP: use fixed date or fetch from plan metadata
  const congressDate = new Date("2026-03-15");
  const now = new Date();
  const diff = Math.ceil((congressDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  return (
    <div className="ct-card p-4">
      <h3 className="text-sm font-semibold text-[#111827] mb-2">Congress countdown</h3>
      <div className="text-2xl font-bold text-[#16a34a]">
        {diff > 0 ? `${diff} days` : diff === 0 ? "Today" : "Past"}
      </div>
      <p className="text-xs text-[#6b7280] mt-1">
        Target: {congressDate.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
      </p>
    </div>
  );
}
