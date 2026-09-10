import Link from "next/link";

import { LogoutButton } from "@/components/layout/logout-button";
import { requireCurrentUser } from "@/lib/auth";

const upcomingNavigation = ["我的简历", "职位匹配", "投递管理"];

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
            <nav aria-label="主导航" className="hidden items-center gap-1 md:flex">
              <Link
                className="rounded-lg bg-blue-50 px-3 py-2 text-sm font-semibold text-blue-700"
                href="/dashboard"
              >
                首页
              </Link>
              {upcomingNavigation.map((item) => (
                <span
                  className="rounded-lg px-3 py-2 text-sm text-slate-400"
                  key={item}
                  title="将在后续开发步骤中开放"
                >
                  {item}
                </span>
              ))}
            </nav>
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
