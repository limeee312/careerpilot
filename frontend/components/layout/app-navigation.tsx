"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/dashboard", label: "首页" },
  { href: "/resumes", label: "我的简历" },
  { href: "/job-match/new", label: "职位匹配" },
] as const;

const upcomingNavigation = ["投递管理"];

export function AppNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="主导航" className="hidden items-center gap-1 md:flex">
      {navigation.map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/dashboard" && pathname.startsWith(item.href));
        return (
          <Link
            aria-current={isActive ? "page" : undefined}
            className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
              isActive
                ? "bg-blue-50 text-blue-700"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
            href={item.href}
            key={item.href}
          >
            {item.label}
          </Link>
        );
      })}
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
  );
}
