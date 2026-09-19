"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  formatApplicationDate,
  getApplicationProgressLabel,
  getApplicationStatusLabel,
  type ApplicationListItem,
  type ApplicationStatus,
} from "@/lib/application";
import { ApiError, apiRequest } from "@/lib/api";
import {
  getDashboardMetrics,
  isDashboardEmpty,
  type DashboardData,
  type DashboardEnvelope,
  type DashboardMetric,
} from "@/lib/dashboard";

const METRIC_STYLES: Record<
  DashboardMetric["tone"],
  { accent: string; icon: string; value: string }
> = {
  slate: {
    accent: "bg-slate-100 text-slate-700",
    icon: "∑",
    value: "text-slate-950",
  },
  blue: {
    accent: "bg-blue-50 text-blue-700",
    icon: "→",
    value: "text-blue-700",
  },
  amber: {
    accent: "bg-amber-50 text-amber-700",
    icon: "—",
    value: "text-amber-700",
  },
  emerald: {
    accent: "bg-emerald-50 text-emerald-700",
    icon: "✓",
    value: "text-emerald-700",
  },
};

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  ACTIVE: "bg-blue-50 text-blue-700",
  REJECTED: "bg-red-50 text-red-700",
  OFFER: "bg-emerald-50 text-emerald-700",
  WITHDRAWN: "bg-slate-100 text-slate-600",
};

function DashboardLoading() {
  return (
    <div aria-live="polite" aria-label="正在加载求职进度">
      <div className="animate-pulse">
        <div className="h-4 w-24 rounded bg-slate-200" />
        <div className="mt-4 h-10 w-64 max-w-full rounded bg-slate-200" />
        <div className="mt-4 h-5 w-full max-w-xl rounded bg-slate-100" />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <div
              className="h-40 rounded-3xl border border-slate-200 bg-white"
              key={item}
            />
          ))}
        </div>
        <div className="mt-8 h-72 rounded-3xl border border-slate-200 bg-white" />
      </div>
    </div>
  );
}

function MetricCard({ metric }: { metric: DashboardMetric }) {
  const styles = METRIC_STYLES[metric.tone];

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-600">{metric.label}</p>
          <p className={`mt-3 text-4xl font-semibold tracking-tight ${styles.value}`}>
            {metric.value}
          </p>
        </div>
        <span
          aria-hidden="true"
          className={`flex h-10 w-10 items-center justify-center rounded-2xl text-lg font-semibold ${styles.accent}`}
        >
          {styles.icon}
        </span>
      </div>
      <p className="mt-5 text-xs leading-5 text-slate-500">
        {metric.description}
      </p>
    </article>
  );
}

function RecentApplication({
  application,
}: {
  application: ApplicationListItem;
}) {
  return (
    <li className="group border-b border-slate-100 last:border-b-0">
      <Link
        className="grid gap-4 px-5 py-5 transition hover:bg-slate-50 sm:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_auto] sm:items-center sm:px-6"
        href={`/applications/${application.id}`}
      >
        <div className="min-w-0">
          <p className="truncate font-semibold text-slate-950 group-hover:text-blue-700">
            {application.job_title}
          </p>
          <p className="mt-1 truncate text-sm text-slate-500">
            {application.company_name}
          </p>
        </div>
        <div>
          <p className="text-sm font-medium text-slate-700">
            {getApplicationProgressLabel(application)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {formatApplicationDate(application.applied_at)} 投递
          </p>
        </div>
        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[application.process_status]}`}
          >
            {getApplicationStatusLabel(application.process_status)}
          </span>
          <span aria-hidden="true" className="text-slate-300 group-hover:text-blue-600">
            →
          </span>
        </div>
      </Link>
    </li>
  );
}

function EmptyDashboard() {
  return (
    <section className="mt-8 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center shadow-sm">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-2xl text-blue-700">
        ↗
      </div>
      <h2 className="mt-5 text-xl font-semibold text-slate-950">
        开始记录第一份投递
      </h2>
      <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-slate-500">
        完成职位匹配并确认投递后，首页会自动汇总流程状态和最近进展。
      </p>
      <Link
        className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
        href="/job-match/new"
      >
        开始职位匹配
      </Link>
    </section>
  );
}

function DashboardContent({ dashboard }: { dashboard: DashboardData }) {
  const metrics = getDashboardMetrics(dashboard.overview);

  return (
    <>
      <section
        aria-label="投递状态总览"
        className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        {metrics.map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </section>

      <section
        aria-labelledby="recent-applications-heading"
        className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"
      >
        <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-5 sm:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recent activity
            </p>
            <h2
              className="mt-1 text-xl font-semibold text-slate-950"
              id="recent-applications-heading"
            >
              最近投递
            </h2>
          </div>
          <Link
            className="text-sm font-semibold text-blue-700 hover:text-blue-800"
            href="/applications"
          >
            查看全部 →
          </Link>
        </div>
        <ul>
          {dashboard.recent_applications.map((application) => (
            <RecentApplication application={application} key={application.id} />
          ))}
        </ul>
      </section>
    </>
  );
}

export function DashboardOverview() {
  const router = useRouter();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    void apiRequest<DashboardEnvelope>("/dashboard")
      .then((response) => {
        if (!cancelled) {
          setDashboard(response.data);
        }
      })
      .catch((requestError: unknown) => {
        if (cancelled) {
          return;
        }
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace("/login");
          router.refresh();
          return;
        }
        setError(
          requestError instanceof ApiError
            ? requestError.message
            : "求职进度加载失败，请稍后重试。",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [loadAttempt, router]);

  function retryLoad() {
    setDashboard(null);
    setError(null);
    setIsLoading(true);
    setLoadAttempt((current) => current + 1);
  }

  if (isLoading) {
    return <DashboardLoading />;
  }

  if (error || dashboard === null) {
    return (
      <div className="rounded-3xl border border-red-200 bg-white px-6 py-14 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">
          求职进度暂时无法加载
        </h1>
        <p className="mt-3 text-sm text-red-700" role="alert">
          {error ?? "请稍后重试。"}
        </p>
        <button
          className="mt-6 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          onClick={retryLoad}
          type="button"
        >
          重新加载
        </button>
      </div>
    );
  }

  return (
    <div>
      <header className="flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">Dashboard</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            求职进度总览
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">
            汇总所有投递的当前状态，并快速回到最近更新的招聘流程。
          </p>
        </div>
        <Link
          className="inline-flex w-fit rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          href="/applications"
        >
          管理投递
        </Link>
      </header>

      {isDashboardEmpty(dashboard) ? (
        <EmptyDashboard />
      ) : (
        <DashboardContent dashboard={dashboard} />
      )}
    </div>
  );
}
