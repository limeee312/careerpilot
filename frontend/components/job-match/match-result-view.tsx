"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  getAnalysisStatusLabel,
  getAnalysisSteps,
  getBatchStatusLabel,
  getConfidenceLabel,
  getEligibilityLabel,
  getMatchProgress,
  getRankLabel,
  isTerminalBatchStatus,
  prepareBatchForAnalysis,
  type AnalysisStepState,
  type EligibilityStatus,
  type JobMatchBatchData,
  type JobMatchBatchEnvelope,
  type JobMatchResultItem,
  type RecommendationLevel,
} from "@/lib/job-match";

const POLL_INTERVAL_MS = 1_500;

type RequestIssue = {
  code: string;
  message: string;
  status: number;
};

function toRequestIssue(error: unknown, fallback: string): RequestIssue {
  if (error instanceof ApiError) {
    return {
      code: error.code,
      message: error.message,
      status: error.status,
    };
  }
  return { code: "UNKNOWN_ERROR", message: fallback, status: 0 };
}

function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "创建时间未知";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function batchStatusClassName(status: JobMatchBatchData["status"]): string {
  if (status === "COMPLETED") {
    return "bg-emerald-50 text-emerald-700";
  }
  if (status === "PARTIAL_FAILED") {
    return "bg-amber-50 text-amber-700";
  }
  if (status === "FAILED") {
    return "bg-red-50 text-red-700";
  }
  return "bg-blue-50 text-blue-700";
}

function recommendationClassName(level: RecommendationLevel): string {
  const classes: Record<RecommendationLevel, string> = {
    PRIORITY: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    STRONG: "bg-blue-50 text-blue-700 ring-blue-200",
    SELECTIVE: "bg-amber-50 text-amber-700 ring-amber-200",
    LOW: "bg-slate-100 text-slate-600 ring-slate-200",
    BLOCKED: "bg-red-50 text-red-700 ring-red-200",
  };
  return classes[level];
}

function eligibilityClassName(status: EligibilityStatus): string {
  const classes: Record<EligibilityStatus, string> = {
    PASS: "bg-emerald-50 text-emerald-700",
    WARN: "bg-amber-50 text-amber-800",
    FAIL: "bg-red-50 text-red-700",
  };
  return classes[status];
}

function applyBatchUpdate(
  current: JobMatchBatchData | null,
  incoming: JobMatchBatchData,
): JobMatchBatchData {
  if (
    current &&
    isTerminalBatchStatus(current.status) &&
    incoming.status === "PROCESSING"
  ) {
    return current;
  }
  return incoming;
}

export function MatchResultView({ batchId }: { batchId: string }) {
  const router = useRouter();
  const autoAnalysisStarted = useRef(false);
  const [batch, setBatch] = useState<JobMatchBatchData | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [loadIssue, setLoadIssue] = useState<RequestIssue | null>(null);
  const [analysisIssue, setAnalysisIssue] = useState<RequestIssue | null>(null);
  const [pollWarning, setPollWarning] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  const handleUnauthorized = useCallback(() => {
    router.replace("/login");
    router.refresh();
  }, [router]);

  const runAnalysis = useCallback(
    async (currentBatch: JobMatchBatchData) => {
      const priorBatch = currentBatch;
      setAnalysisIssue(null);
      setPollWarning(null);
      setIsAnalyzing(true);
      setBatch(prepareBatchForAnalysis(currentBatch));

      try {
        const response = await apiRequest<JobMatchBatchEnvelope>(
          `/job-match/batches/${batchId}/analyze`,
          { method: "POST" },
        );
        setBatch((current) => applyBatchUpdate(current, response.data));
      } catch (error: unknown) {
        const issue = toRequestIssue(
          error,
          "职位分析失败，请稍后重新分析。",
        );
        if (issue.status === 401) {
          handleUnauthorized();
          return;
        }
        if (issue.code === "BATCH_PROCESSING") {
          return;
        }
        setBatch(priorBatch);
        setAnalysisIssue(issue);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [batchId, handleUnauthorized],
  );

  useEffect(() => {
    let cancelled = false;

    void apiRequest<JobMatchBatchEnvelope>(`/job-match/${batchId}`)
      .then((response) => {
        if (!cancelled) {
          setBatch((current) => applyBatchUpdate(current, response.data));
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const issue = toRequestIssue(
          error,
          "匹配批次加载失败，请稍后重试。",
        );
        if (issue.status === 401) {
          handleUnauthorized();
          return;
        }
        setLoadIssue(issue);
      })
      .finally(() => {
        if (!cancelled) {
          setIsInitialLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [batchId, handleUnauthorized, loadAttempt]);

  useEffect(() => {
    if (
      batch?.status !== "DRAFT" ||
      autoAnalysisStarted.current ||
      analysisIssue
    ) {
      return;
    }
    autoAnalysisStarted.current = true;
    void runAnalysis(batch);
  }, [analysisIssue, batch, runAnalysis]);

  useEffect(() => {
    if (batch?.status !== "PROCESSING") {
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const response = await apiRequest<JobMatchBatchEnvelope>(
          `/job-match/${batchId}`,
        );
        if (cancelled) {
          return;
        }
        setPollWarning(null);
        setBatch((current) => applyBatchUpdate(current, response.data));
        if (response.data.status === "PROCESSING") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        const issue = toRequestIssue(
          error,
          "实时进度暂时无法刷新，系统会继续重试。",
        );
        if (issue.status === 401) {
          handleUnauthorized();
          return;
        }
        setPollWarning(issue.message);
        timer = setTimeout(poll, POLL_INTERVAL_MS);
      }
    }

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
      }
    };
  }, [batch?.status, batchId, handleUnauthorized]);

  function retryLoad() {
    setIsInitialLoading(true);
    setBatch(null);
    setLoadIssue(null);
    setLoadAttempt((current) => current + 1);
  }

  function retryAnalysis() {
    if (!batch) {
      return;
    }
    autoAnalysisStarted.current = true;
    void runAnalysis(batch);
  }

  if (isInitialLoading && !batch) {
    return <InitialLoadingState />;
  }

  if (loadIssue && !batch) {
    return <LoadErrorState issue={loadIssue} onRetry={retryLoad} />;
  }

  if (!batch) {
    return <LoadErrorState issue={loadIssue} onRetry={retryLoad} />;
  }

  const progress = getMatchProgress(batch);
  const isProcessing = batch.status === "PROCESSING";
  const results = batch.jobs.filter((job) => job.result !== null);
  const failedJobs = batch.jobs.filter(
    (job) => job.analysis_status === "FAILED",
  );

  return (
    <div>
      <header className="flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm font-semibold text-blue-600">Match results</p>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${batchStatusClassName(batch.status)}`}
            >
              {getBatchStatusLabel(batch.status)}
            </span>
          </div>
          <h1 className="mt-2 truncate text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            {batch.name ?? "匹配结果"}
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            {batch.total_jobs} 个职位 · 创建于 {formatCreatedAt(batch.created_at)}
          </p>
        </div>
        <Link
          className="inline-flex shrink-0 items-center justify-center rounded-xl border border-blue-200 bg-white px-5 py-3 text-sm font-semibold text-blue-700 transition hover:bg-blue-50"
          href="/job-match/new"
        >
          + 新建职位匹配
        </Link>
      </header>

      {analysisIssue ? (
        <AnalysisIssueBanner
          issue={analysisIssue}
          isAnalyzing={isAnalyzing}
          onRetry={retryAnalysis}
        />
      ) : null}

      {pollWarning ? (
        <p
          className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800"
          role="status"
        >
          {pollWarning}
        </p>
      ) : null}

      {isProcessing || batch.status === "DRAFT" ? (
        <AnalysisProgress batch={batch} progress={progress} />
      ) : (
        <>
          <BatchOutcome
            batch={batch}
            isAnalyzing={isAnalyzing}
            onRetry={retryAnalysis}
          />
          {results.length > 0 ? (
            <section className="mt-8" aria-labelledby="match-results-heading">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                    Deterministic ranking
                  </p>
                  <h2
                    className="mt-1 text-2xl font-semibold text-slate-950"
                    id="match-results-heading"
                  >
                    匹配结果
                  </h2>
                </div>
                <p className="max-w-xl text-sm leading-6 text-slate-500">
                  分数与排序由后端统一计算；硬性条件失败的岗位不参与正常可投排序。
                </p>
              </div>
              <div className="mt-5 space-y-4">
                {batch.jobs.map((job) =>
                  job.result ? (
                    <MatchResultCard job={job} key={job.job_id} />
                  ) : null,
                )}
              </div>
            </section>
          ) : null}
          {failedJobs.length > 0 ? (
            <FailedJobs jobs={failedJobs} />
          ) : null}
        </>
      )}
    </div>
  );
}

function InitialLoadingState() {
  return (
    <div
      aria-live="polite"
      className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
    >
      <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
      <h1 className="mt-5 text-xl font-semibold text-slate-950">
        正在加载匹配批次
      </h1>
      <p className="mt-2 text-sm text-slate-500">马上为你同步最新分析状态。</p>
    </div>
  );
}

function LoadErrorState({
  issue,
  onRetry,
}: {
  issue: RequestIssue | null;
  onRetry: () => void;
}) {
  const notFound = issue?.code === "BATCH_NOT_FOUND" || issue?.status === 404;
  return (
    <div className="rounded-3xl border border-red-200 bg-white px-6 py-16 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-xl text-red-700">
        !
      </div>
      <h1 className="mt-5 text-xl font-semibold text-slate-950">
        {notFound ? "找不到这个匹配批次" : "匹配结果暂时无法加载"}
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-600" role="alert">
        {notFound
          ? "该批次不存在，或你没有访问权限。"
          : (issue?.message ?? "请稍后重试。")}
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        {!notFound ? (
          <button
            className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
            onClick={onRetry}
            type="button"
          >
            重新加载
          </button>
        ) : null}
        <Link
          className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          href="/job-match/new"
        >
          返回职位匹配
        </Link>
      </div>
    </div>
  );
}

function AnalysisIssueBanner({
  issue,
  isAnalyzing,
  onRetry,
}: {
  issue: RequestIssue;
  isAnalyzing: boolean;
  onRetry: () => void;
}) {
  const needsResume = issue.code === "RESUME_REQUIRED";
  return (
    <section className="mt-7 rounded-2xl border border-red-200 bg-red-50 p-5 sm:flex sm:items-center sm:justify-between sm:gap-6">
      <div>
        <h2 className="font-semibold text-red-900">
          {needsResume ? "需要先创建简历母版" : "本次分析未能启动"}
        </h2>
        <p className="mt-1 text-sm leading-6 text-red-700" role="alert">
          {issue.message}
        </p>
      </div>
      {needsResume ? (
        <Link
          className="mt-4 inline-flex shrink-0 rounded-xl bg-red-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-800 sm:mt-0"
          href="/resumes/master/edit"
        >
          创建简历母版
        </Link>
      ) : (
        <button
          className="mt-4 shrink-0 rounded-xl bg-red-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-red-800 disabled:cursor-not-allowed disabled:bg-red-300 sm:mt-0"
          disabled={isAnalyzing}
          onClick={onRetry}
          type="button"
        >
          {isAnalyzing ? "正在重试…" : "重试分析"}
        </button>
      )}
    </section>
  );
}

function AnalysisProgress({
  batch,
  progress,
}: {
  batch: JobMatchBatchData;
  progress: ReturnType<typeof getMatchProgress>;
}) {
  return (
    <section className="mt-8" aria-labelledby="analysis-progress-heading">
      <div className="overflow-hidden rounded-3xl border border-blue-100 bg-white shadow-sm">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-7 text-white sm:px-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-blue-100">
                Parser → Matcher → Backend score
              </p>
              <h2
                className="mt-2 text-2xl font-semibold"
                id="analysis-progress-heading"
              >
                正在分析岗位…
              </h2>
              <p className="mt-2 text-sm leading-6 text-blue-100">
                页面会自动更新。每个岗位独立保存，单个失败不会影响其他结果。
              </p>
            </div>
            <p className="shrink-0 text-sm font-semibold">
              {progress.resolvedJobs}/{batch.total_jobs} 已完成
            </p>
          </div>
          <div
            aria-label={`分析进度 ${progress.percent}%`}
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={progress.percent}
            className="mt-6 h-2 overflow-hidden rounded-full bg-white/20"
            role="progressbar"
          >
            <div
              className="h-full rounded-full bg-white transition-[width] duration-500"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
        <div className="divide-y divide-slate-100">
          {batch.jobs.map((job, index) => (
            <JobProgressRow index={index} job={job} key={job.job_id} />
          ))}
        </div>
      </div>
    </section>
  );
}

function JobProgressRow({
  index,
  job,
}: {
  index: number;
  job: JobMatchResultItem;
}) {
  const steps = getAnalysisSteps(job.analysis_status);
  return (
    <article className="grid gap-4 px-6 py-5 sm:grid-cols-[minmax(0,1fr)_minmax(20rem,1fr)] sm:items-center sm:px-8">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Job {String(index + 1).padStart(2, "0")}
        </p>
        <h3 className="mt-1 truncate font-semibold text-slate-950">
          {job.title}
        </h3>
        <p className="mt-1 truncate text-sm text-slate-500">
          {job.company_name}
          {job.location ? ` · ${job.location}` : ""}
        </p>
      </div>
      {job.analysis_status === "FAILED" ? (
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          分析失败 · {job.error_code ?? "AI_PROCESSING_ERROR"}
        </div>
      ) : (
        <div>
          <p className="text-sm font-semibold text-slate-700">
            {getAnalysisStatusLabel(job.analysis_status)}
          </p>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm">
            <ProgressStep label="JD 解析" state={steps.parsing} />
            <ProgressStep label="证据匹配" state={steps.matching} />
          </div>
        </div>
      )}
    </article>
  );
}

function ProgressStep({
  label,
  state,
}: {
  label: string;
  state: AnalysisStepState;
}) {
  const marker = state === "complete" ? "✓" : state === "active" ? "●" : "○";
  const className =
    state === "complete"
      ? "text-emerald-700"
      : state === "active"
        ? "text-blue-700"
        : "text-slate-400";
  return (
    <span className={className}>
      <span aria-hidden="true" className="mr-1.5 font-semibold">
        {marker}
      </span>
      {label}
    </span>
  );
}

function BatchOutcome({
  batch,
  isAnalyzing,
  onRetry,
}: {
  batch: JobMatchBatchData;
  isAnalyzing: boolean;
  onRetry: () => void;
}) {
  if (batch.status === "COMPLETED") {
    return (
      <div className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800" role="status">
        <span className="font-semibold">全部分析完成。</span> 已生成 {batch.successful_jobs} 个岗位的匹配结果。
      </div>
    );
  }

  return (
    <section
      className={`mt-7 rounded-2xl border p-5 sm:flex sm:items-center sm:justify-between sm:gap-6 ${
        batch.status === "PARTIAL_FAILED"
          ? "border-amber-200 bg-amber-50"
          : "border-red-200 bg-red-50"
      }`}
    >
      <div>
        <h2
          className={`font-semibold ${
            batch.status === "PARTIAL_FAILED" ? "text-amber-900" : "text-red-900"
          }`}
        >
          {batch.status === "PARTIAL_FAILED"
            ? "部分岗位分析未完成"
            : "本批次分析失败"}
        </h2>
        <p
          className={`mt-1 text-sm leading-6 ${
            batch.status === "PARTIAL_FAILED" ? "text-amber-800" : "text-red-700"
          }`}
        >
          {batch.successful_jobs} 个岗位分析成功，{batch.failed_jobs} 个岗位分析失败。已成功的结果仍然保留。
        </p>
      </div>
      <button
        className={`mt-4 shrink-0 rounded-xl px-4 py-2.5 text-sm font-semibold text-white transition disabled:cursor-not-allowed sm:mt-0 ${
          batch.status === "PARTIAL_FAILED"
            ? "bg-amber-700 hover:bg-amber-800 disabled:bg-amber-300"
            : "bg-red-700 hover:bg-red-800 disabled:bg-red-300"
        }`}
        disabled={isAnalyzing}
        onClick={onRetry}
        type="button"
      >
        {isAnalyzing ? "正在重新分析…" : "重新分析本批次"}
      </button>
    </section>
  );
}

function MatchResultCard({ job }: { job: JobMatchResultItem }) {
  const result = job.result;
  if (!result) {
    return null;
  }
  const metadata = [job.company_name, job.location, job.department].filter(
    Boolean,
  );

  return (
    <article
      className={`overflow-hidden rounded-3xl border bg-white shadow-sm ${
        result.eligibility_status === "FAIL"
          ? "border-red-200"
          : result.eligibility_status === "WARN"
            ? "border-amber-200"
            : "border-slate-200"
      }`}
    >
      <div className="grid gap-6 p-6 sm:p-7 lg:grid-cols-[5.5rem_minmax(0,1fr)_auto] lg:items-center">
        <div className="flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-2xl bg-slate-950 text-white">
          <span className="text-xs text-slate-300">{getRankLabel(result)}</span>
          <span className="mt-0.5 text-2xl font-semibold">{result.display_score}</span>
          <span className="text-xs text-slate-300">分</span>
        </div>

        <div className="min-w-0">
          <h3 className="truncate text-xl font-semibold text-slate-950">
            {job.title}
          </h3>
          <p className="mt-1 truncate text-sm text-slate-500">
            {metadata.join(" · ")}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${recommendationClassName(result.recommendation_level)}`}
            >
              {result.recommendation_level} · {result.recommendation}
            </span>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${eligibilityClassName(result.eligibility_status)}`}
            >
              {getEligibilityLabel(result.eligibility_status)}
            </span>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
              {getConfidenceLabel(result.confidence_level)}
            </span>
          </div>
          {result.eligibility_status === "WARN" ? (
            <p className="mt-3 text-sm font-medium text-amber-800">
              条件待核实：当前简历无法确认至少一项硬性条件。
            </p>
          ) : null}
          {result.eligibility_status === "FAIL" ? (
            <p className="mt-3 text-sm font-medium text-red-700">
              能力匹配较高，但存在明确硬性条件冲突。
            </p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2 lg:flex-col lg:items-stretch">
          <Link
            className="rounded-xl bg-blue-600 px-4 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-blue-700"
            href={`/jobs/${job.job_id}`}
          >
            查看详情
          </Link>
          {job.source_url ? (
            <a
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-center text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
              href={job.source_url}
              rel="noreferrer"
              target="_blank"
            >
              原始职位 ↗
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function FailedJobs({ jobs }: { jobs: JobMatchResultItem[] }) {
  return (
    <section className="mt-8" aria-labelledby="failed-jobs-heading">
      <h2 className="text-lg font-semibold text-slate-950" id="failed-jobs-heading">
        未完成分析的岗位
      </h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {jobs.map((job) => (
          <article
            className="rounded-2xl border border-red-200 bg-white p-5"
            key={job.job_id}
          >
            <p className="font-semibold text-slate-900">{job.title}</p>
            <p className="mt-1 text-sm text-slate-500">{job.company_name}</p>
            <p className="mt-3 text-sm font-medium text-red-700">
              {job.error_code ?? "AI_PROCESSING_ERROR"}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
