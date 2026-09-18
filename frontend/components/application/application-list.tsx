"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  APPLICATION_FILTERS,
  filterApplications,
  formatApplicationDate,
  formatApplicationUpdatedAt,
  getApplicationFilterCounts,
  getApplicationStageLabel,
  getApplicationStatusLabel,
  type ApplicationFilter,
  type ApplicationListEnvelope,
  type ApplicationListItem,
  type ApplicationStatus,
} from "@/lib/application";

const STATUS_CLASS_NAMES: Record<ApplicationStatus, string> = {
  ACTIVE: "bg-blue-50 text-blue-700 ring-blue-200",
  REJECTED: "bg-red-50 text-red-700 ring-red-200",
  OFFER: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  WITHDRAWN: "bg-slate-100 text-slate-600 ring-slate-200",
};

function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_CLASS_NAMES[status]}`}
    >
      {getApplicationStatusLabel(status)}
    </span>
  );
}

function StageLabel({ application }: { application: ApplicationListItem }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-700">
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${
          application.process_status === "ACTIVE"
            ? "bg-blue-500"
            : "bg-slate-300"
        }`}
      />
      {getApplicationStageLabel(
        application.current_stage,
        application.current_round,
      )}
    </span>
  );
}

function ApplicationTable({
  applications,
}: {
  applications: ApplicationListItem[];
}) {
  return (
    <div className="hidden overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm md:block">
      <table className="w-full border-collapse text-left">
        <thead className="border-b border-slate-200 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-500">
          <tr>
            <th className="px-6 py-4" scope="col">
              公司 / 职位
            </th>
            <th className="px-4 py-4" scope="col">
              当前阶段
            </th>
            <th className="px-4 py-4" scope="col">
              状态
            </th>
            <th className="px-4 py-4" scope="col">
              投递日期
            </th>
            <th className="px-6 py-4 text-right" scope="col">
              最后更新
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {applications.map((application) => (
            <tr className="transition hover:bg-slate-50/70" key={application.id}>
              <td className="px-6 py-5">
                <div className="flex min-w-0 items-center gap-3">
                  <span
                    aria-hidden="true"
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-sm font-semibold text-white"
                  >
                    {application.company_name.trim().slice(0, 1) || "职"}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-950">
                      {application.company_name}
                    </p>
                    <p className="mt-1 truncate text-sm text-slate-500">
                      {application.job_title}
                    </p>
                  </div>
                </div>
              </td>
              <td className="px-4 py-5">
                <StageLabel application={application} />
              </td>
              <td className="px-4 py-5">
                <StatusBadge status={application.process_status} />
              </td>
              <td className="px-4 py-5 text-sm text-slate-600">
                {formatApplicationDate(application.applied_at)}
              </td>
              <td className="px-6 py-5 text-right text-sm text-slate-500">
                {formatApplicationUpdatedAt(application.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ApplicationCards({
  applications,
}: {
  applications: ApplicationListItem[];
}) {
  return (
    <div className="grid gap-4 md:hidden">
      {applications.map((application) => (
        <article
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          key={application.id}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="truncate text-lg font-semibold text-slate-950">
                {application.company_name}
              </p>
              <p className="mt-1 truncate text-sm text-slate-500">
                {application.job_title}
              </p>
            </div>
            <StatusBadge status={application.process_status} />
          </div>
          <div className="mt-5 flex items-center justify-between gap-4 border-t border-slate-100 pt-4">
            <StageLabel application={application} />
            <p className="text-xs text-slate-500">
              投递 {formatApplicationDate(application.applied_at)}
            </p>
          </div>
          <p className="mt-3 text-right text-xs text-slate-400">
            最后更新 {formatApplicationUpdatedAt(application.updated_at)}
          </p>
        </article>
      ))}
    </div>
  );
}

export function ApplicationList() {
  const router = useRouter();
  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [activeFilter, setActiveFilter] = useState<ApplicationFilter>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    void apiRequest<ApplicationListEnvelope>("/applications")
      .then((response) => {
        if (!cancelled) {
          setApplications(response.data);
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
            : "投递记录加载失败，请稍后重试。",
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

  const counts = useMemo(
    () => getApplicationFilterCounts(applications),
    [applications],
  );
  const visibleApplications = useMemo(
    () => filterApplications(applications, activeFilter),
    [activeFilter, applications],
  );

  function retryLoad() {
    setIsLoading(true);
    setError(null);
    setLoadAttempt((current) => current + 1);
  }

  if (isLoading) {
    return (
      <div
        aria-live="polite"
        className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
      >
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
        <p className="mt-4 text-sm text-slate-600">正在加载投递记录…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-red-200 bg-white px-6 py-14 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">
          投递记录暂时无法加载
        </h1>
        <p className="mt-3 text-sm text-red-700" role="alert">
          {error}
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
          <p className="text-sm font-semibold text-blue-600">
            Application tracker
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            投递管理
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">
            汇总每个岗位的投递阶段与流程状态，让下一步跟进一目了然。
          </p>
        </div>
        <div className="grid w-full grid-cols-3 gap-2 sm:w-auto sm:min-w-[22rem]">
          {[
            ["全部投递", counts.ALL],
            ["进行中", counts.ACTIVE],
            ["Offer", counts.OFFER],
          ].map(([label, count]) => (
            <div
              className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center shadow-sm"
              key={label}
            >
              <p className="text-2xl font-semibold text-slate-950">{count}</p>
              <p className="mt-1 text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      </header>

      {applications.length === 0 ? (
        <section className="mt-8 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-xl">
            ↗
          </div>
          <h2 className="mt-5 text-lg font-semibold text-slate-950">
            还没有投递记录
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
            从职位匹配开始筛选适合的机会；确认投递后，这里会持续记录流程进展。
          </p>
          <Link
            className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
            href="/job-match/new"
          >
            开始职位匹配
          </Link>
        </section>
      ) : (
        <section className="mt-8" aria-labelledby="application-list-heading">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Pipeline
              </p>
              <h2
                className="mt-1 text-xl font-semibold text-slate-950"
                id="application-list-heading"
              >
                投递记录
              </h2>
            </div>
            <div
              aria-label="按投递状态筛选"
              className="flex gap-2 overflow-x-auto pb-1"
              role="group"
            >
              {APPLICATION_FILTERS.map((filter) => {
                const isActive = activeFilter === filter.value;
                return (
                  <button
                    aria-pressed={isActive}
                    className={`shrink-0 rounded-full px-3.5 py-2 text-sm font-semibold transition ${
                      isActive
                        ? "bg-slate-950 text-white"
                        : "border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950"
                    }`}
                    key={filter.value}
                    onClick={() => setActiveFilter(filter.value)}
                    type="button"
                  >
                    {filter.label}
                    <span
                      className={`ml-1.5 ${isActive ? "text-slate-300" : "text-slate-400"}`}
                    >
                      {counts[filter.value]}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-5">
            {visibleApplications.length > 0 ? (
              <>
                <ApplicationTable applications={visibleApplications} />
                <ApplicationCards applications={visibleApplications} />
              </>
            ) : (
              <div className="rounded-3xl border border-slate-200 bg-white px-6 py-12 text-center shadow-sm">
                <h3 className="font-semibold text-slate-950">
                  该状态暂无投递记录
                </h3>
                <p className="mt-2 text-sm text-slate-500">
                  切换到其他状态，或查看全部投递。
                </p>
                <button
                  className="mt-5 text-sm font-semibold text-blue-700 hover:text-blue-800"
                  onClick={() => setActiveFilter("ALL")}
                  type="button"
                >
                  查看全部
                </button>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
