import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <h2 className="text-xl font-semibold text-[#111827] mb-2">Page not found</h2>
      <p className="text-[#6b7280] mb-4">The requested resource could not be found.</p>
      <Link
        href="/"
        className="rounded-lg bg-[#16a34a] px-4 py-2 text-sm font-medium text-white hover:bg-[#15803d]"
      >
        Return home
      </Link>
    </div>
  );
}
