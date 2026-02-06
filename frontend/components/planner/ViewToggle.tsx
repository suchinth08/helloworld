"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";

export type ViewMode = "base" | "advanced";

export default function ViewToggle() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const current = (searchParams.get("view") || "base") as ViewMode;
  const valid = current === "advanced" ? "advanced" : "base";

  const setView = (view: ViewMode) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", view);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="flex rounded-lg border border-[#e5e7eb] bg-[#f3f4f6] p-0.5" role="tablist" aria-label="View mode">
      <button
        type="button"
        role="tab"
        aria-selected={valid === "base"}
        onClick={() => setView("base")}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          valid === "base"
            ? "bg-[#16a34a] text-white shadow-sm"
            : "text-[#6b7280] hover:text-[#111827]"
        }`}
      >
        Base view
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={valid === "advanced"}
        onClick={() => setView("advanced")}
        className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          valid === "advanced"
            ? "bg-[#16a34a] text-white shadow-sm"
            : "text-[#6b7280] hover:text-[#111827]"
        }`}
      >
        Advanced view
      </button>
    </div>
  );
}
