"use client";

import { useState, useEffect, createContext, useContext } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { LayoutDashboard, CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";

const SIDEBAR_COLLAPSED_KEY = "congress-twin-sidebar-collapsed";

const SidebarContext = createContext<{ collapsed: boolean }>({ collapsed: false });

export function useSidebarCollapsed() {
  return useContext(SidebarContext);
}

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isPlanner = pathname?.startsWith("/planner");
  const [collapsed, setCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    if (stored !== null) setCollapsed(JSON.parse(stored));
  }, [mounted]);

  const toggleSidebar = () => {
    const next = !collapsed;
    setCollapsed(next);
    try {
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, JSON.stringify(next));
    } catch {}
  };

  const navItems = [
    { href: "/", label: "Home", icon: LayoutDashboard, active: !isPlanner },
    { href: "/planner", label: "Planner", icon: CalendarDays, active: isPlanner },
  ];

  return (
    <SidebarContext.Provider value={{ collapsed }}>
    <div className="min-h-screen flex bg-[#f9fafb]">
      {/* Collapsible left sidebar - white background */}
      <aside
        style={{ width: collapsed ? 72 : 224, minWidth: collapsed ? 72 : 224 }}
        className="shrink-0 bg-white flex flex-col border-r border-[#e5e7eb] transition-[width] duration-200 ease-out overflow-hidden"
      >
        {/* Logo + Planner label (just beneath logo) + collapse toggle */}
        <div className={`p-3 border-b border-[#e5e7eb] flex flex-col gap-2 ${collapsed ? "items-center" : ""}`}>
          <div className={`flex items-center gap-2 w-full ${collapsed ? "flex-col" : "justify-between"}`}>
            <Link
              href="/"
              className={`flex items-center overflow-hidden min-w-0 ${collapsed ? "justify-center" : "flex-1"}`}
            >
              {collapsed ? (
                <div className="relative h-9 w-9 shrink-0 rounded-md overflow-hidden bg-[#f0fdf4] flex items-center justify-center">
                  <Image
                    src="/novartis-favicon.png"
                    alt="Novartis Planner"
                    width={36}
                    height={36}
                    className="object-contain"
                    unoptimized
                  />
                </div>
              ) : (
                <div className="relative h-12 w-full max-w-[180px] shrink-0 overflow-hidden">
                  <Image
                    src="/novartis-logo.png"
                    alt="Novartis"
                    width={180}
                    height={48}
                    className="object-contain object-left"
                    style={{ width: "auto", height: "auto" }}
                    unoptimized
                  />
                </div>
              )}
            </Link>
            <button
              type="button"
              onClick={toggleSidebar}
              className="shrink-0 rounded p-1.5 text-[#6b7280] hover:bg-[#f3f4f6] hover:text-[#111827] transition-colors"
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
            </button>
          </div>
          {!collapsed && (
            <p className="text-base font-semibold text-[#111827] pl-0.5">Planner</p>
          )}
        </div>

        <nav className="p-2 flex-1 flex flex-col gap-0.5">
          {navItems.map(({ href, label, icon: Icon, active }) => (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={`flex items-center rounded-lg text-sm font-medium transition-colors ${
                collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5"
              } ${
                active
                  ? "bg-[#dcfce7] text-[#166534]"
                  : "text-[#374151] hover:bg-[#f3f4f6] hover:text-[#111827]"
              }`}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{label}</span>}
            </Link>
          ))}
        </nav>

        {/* Bottom collapse hint when expanded */}
        {!collapsed && (
          <div className="p-2 border-t border-[#e5e7eb]">
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex items-center gap-3 w-full rounded-lg px-3 py-2.5 text-sm text-[#6b7280] hover:bg-[#f3f4f6] hover:text-[#111827] transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
              Collapse
            </button>
          </div>
        )}
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 shrink-0 border-b border-[#e5e7eb] bg-white flex items-center justify-end px-6">
          <div className="flex items-center gap-3">
            <span className="text-sm text-[#6b7280]">Plan view</span>
            <div className="flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-[#f9fafb] px-3 py-1.5 text-sm text-[#6b7280]">
              <CalendarDays className="h-4 w-4" />
              Last 30 days
            </div>
          </div>
        </header>
        <main className="flex-1 p-6 overflow-auto min-w-0">{children}</main>
      </div>
    </div>
    </SidebarContext.Provider>
  );
}
