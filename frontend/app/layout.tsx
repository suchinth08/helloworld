import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Novartis Planner",
  description: "Planner execution view — Dependency Lens, Attention Dashboard, Critical Path",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body className="min-h-screen text-[#111827] antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
