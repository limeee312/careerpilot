import Link from "next/link";

import { AppNavigation } from "@/components/layout/app-navigation";
import { LogoutButton } from "@/components/layout/logout-button";
import { requireCurrentUser } from "@/lib/auth";

export default async function ProtectedLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const user = await requireCurrentUser();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4 lg:px-8">
          <div className="flex min-w-0 items-center gap-8">
            <Link
              className="shrink-0 font-semibold tracking-tight text-slate-950"
              href="/dashboard"
            >
              职航 CareerPilot
            </Link>
            <AppNavigation />
          </div>
          <div className="flex min-w-0 items-center gap-4">
            <div className="hidden min-w-0 text-right sm:block">
              <p className="truncate text-sm font-medium text-slate-800">
                {user.name ?? "CareerPilot 用户"}
              </p>
              <p className="truncate text-xs text-slate-500">{user.email}</p>
            </div>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-10 lg:px-8">{children}</main>
    </div>
  );
}
