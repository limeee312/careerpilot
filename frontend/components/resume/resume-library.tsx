"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  calculateResumeCompleteness,
  formatResumeUpdatedAt,
  type ResumeMasterData,
  type ResumeMasterEnvelope,
  resumeDataToDraft,
} from "@/lib/resume";
import type {
  ResumeVersionListEnvelope,
  ResumeVersionListItem,
} from "@/lib/resume-version";

export function ResumeLibrary() {
  const router = useRouter();
  const [resume, setResume] = useState<ResumeMasterData | null>(null);
  const [versions, setVersions] = useState<ResumeVersionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    void Promise.all([
      apiRequest<ResumeMasterEnvelope>("/resume/master"),
      apiRequest<ResumeVersionListEnvelope>("/resume/versions"),
    ])
      .then(([masterResponse, versionResponse]) => {
        if (!cancelled) {
          setResume(masterResponse.data);
          setVersions(versionResponse.data);
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
            : "简历库加载失败，请稍后重试。",
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

  const completeness = useMemo(
    () =>
      resume
        ? calculateResumeCompleteness(resumeDataToDraft(resume))
        : null,
    [resume],
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
        className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm"
      >
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
        <p className="mt-4 text-sm text-slate-600">正在加载简历库…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-white px-6 py-12 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">简历库暂时无法加载</h1>
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
      <div className="flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">Resume Library</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            我的简历
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">
            母版记录你的完整真实经历；针对性简历会在不覆盖母版的前提下，为不同岗位生成独立版本。
          </p>
        </div>
        <Link
          className="inline-flex shrink-0 items-center justify-center rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          href="/resumes/master/edit"
        >
          {resume ? "编辑简历母版" : "创建简历母版"}
        </Link>
      </div>

      <section className="mt-8" aria-labelledby="master-resume-heading">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              Source of truth
            </p>
            <h2
              className="mt-1 text-xl font-semibold text-slate-950"
              id="master-resume-heading"
            >
              简历母版
            </h2>
          </div>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
            始终保留 1 份
          </span>
        </div>

        {resume && completeness ? (
          <article className="overflow-hidden rounded-3xl border border-blue-100 bg-white shadow-sm">
            <div className="border-b border-blue-100 bg-gradient-to-r from-blue-50 to-white px-6 py-5 sm:px-7">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-blue-700">
                    ⭐ 简历母版
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                    {resume.basic_info.name
                      ? `${resume.basic_info.name}的简历母版`
                      : "我的简历母版"}
                  </h3>
                  <p className="mt-2 text-sm text-slate-500">
                    最后修改：{formatResumeUpdatedAt(resume.updated_at)}
                  </p>
                </div>
                <Link
                  className="inline-flex items-center justify-center rounded-xl border border-blue-200 bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
                  href="/resumes/master/edit"
                >
                  查看并编辑 →
                </Link>
              </div>
            </div>

            <div className="grid gap-7 px-6 py-6 sm:px-7 lg:grid-cols-[minmax(0,1fr)_15rem]">
              <div className="min-w-0">
                <p className="line-clamp-3 leading-7 text-slate-600">
                  {resume.basic_info.summary ||
                    "尚未填写职业概述。继续补充经历和技能，可以提高后续岗位匹配的证据质量。"}
                </p>
                <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ["教育经历", resume.education.length],
                    ["工作与实习", resume.experiences.length],
                    ["项目经历", resume.projects.length],
                    ["技能", resume.skills.length],
                  ].map(([label, count]) => (
                    <div
                      className="rounded-xl bg-slate-50 px-4 py-3"
                      key={label}
                    >
                      <dt className="text-xs text-slate-500">{label}</dt>
                      <dd className="mt-1 text-lg font-semibold text-slate-900">
                        {count}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="rounded-2xl bg-slate-950 p-5 text-white">
                <p className="text-sm text-slate-300">当前完整度</p>
                <p className="mt-1 text-3xl font-semibold">
                  {completeness.score}%
                </p>
                <div
                  aria-label={`简历完整度 ${completeness.score}%`}
                  aria-valuemax={100}
                  aria-valuemin={0}
                  aria-valuenow={completeness.score}
                  className="mt-4 h-2 overflow-hidden rounded-full bg-slate-700"
                  role="progressbar"
                >
                  <div
                    className="h-full rounded-full bg-blue-400"
                    style={{ width: `${completeness.score}%` }}
                  />
                </div>
                <p className="mt-4 text-xs leading-5 text-slate-300">
                  完整度只用于提示，不限制后续岗位匹配。
                </p>
              </div>
            </div>
          </article>
        ) : (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center shadow-sm">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-xl">
              ⭐
            </div>
            <h3 className="mt-5 text-lg font-semibold text-slate-950">
              还没有简历母版
            </h3>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500">
              从基本信息开始，逐步整理教育、经历、项目和技能，建立后续分析所需的真实事实库。
            </p>
            <Link
              className="mt-6 inline-flex rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
              href="/resumes/master/edit"
            >
              创建简历母版
            </Link>
          </div>
        )}
      </section>

      <section className="mt-10" aria-labelledby="tailored-resumes-heading">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Job-specific versions
            </p>
            <h2
              className="mt-1 text-xl font-semibold text-slate-950"
              id="tailored-resumes-heading"
            >
              针对性简历
            </h2>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">
            {versions.length} 份
          </span>
        </div>
        {versions.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {versions.map((version) => (
              <article
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
                key={version.id}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                      Saved version
                    </p>
                    <h3 className="mt-2 truncate text-xl font-semibold text-slate-950">
                      {version.name}
                    </h3>
                    <p className="mt-2 text-sm text-slate-500">
                      {version.company_name} · {version.job_title}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                    已保存
                  </span>
                </div>
                <div className="mt-5 flex items-center justify-between gap-4 border-t border-slate-100 pt-4">
                  <p className="text-xs text-slate-500">
                    创建：{formatResumeUpdatedAt(version.created_at)}
                  </p>
                  <Link
                    className="text-sm font-semibold text-blue-700 hover:text-blue-800"
                    href={`/jobs/${version.job_id}/resume-tailor`}
                  >
                    查看来源职位 →
                  </Link>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
            <h3 className="font-semibold text-slate-900">还没有针对性简历</h3>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
              完成职位匹配并主动保存岗位版简历后，它会出现在这里。每个版本独立保存，不会覆盖简历母版。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
