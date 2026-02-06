import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-4xl">
      <div className="ct-card p-6 mb-6">
        <h2 className="text-xl font-bold text-[#111827] mb-1">Congress Twin</h2>
        <p className="text-sm text-[#6b7280] mb-4">
          Planner execution view — Dependency Lens, Attention Dashboard, Critical Path, Milestone lane.
        </p>
        <Link
          href="/planner"
          className="inline-flex items-center rounded-lg bg-[#16a34a] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#15803d]"
        >
          Open Planner
        </Link>
      </div>
    </div>
  );
}
