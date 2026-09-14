"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  clampPercent,
  formatDetailScore,
  getAssessmentStatusLabel,
  getDimensionCards,
  getDimensionLabel,
  getEvidenceSourceLabel,
  getMatchLevelLabel,
  getRequirementTypeLabel,
  type AssessmentStatus,
  type GapImportance,
  type HardGateDetail,
  type JobMatchDetailData,
  type JobMatchDetailEnvelope,
  type RequirementAssessmentDetail,
  type RequirementType,
  type ResumeEvidence,
} from "@/lib/job-detail";
import {
  getConfidenceLabel,
  getEligibilityLabel,
  type EligibilityStatus,
  type RecommendationLevel,
} from "@/lib/job-match";

type RequestIssue = {
  code: string;
  message: string;
  status: number;
};

function toRequestIssue(error: unknown): RequestIssue {
  if (error instanceof ApiError) {
    return {
      code: error.code,
      message: error.message,
      status: error.status,
    };
  }
  return {
    code: "UNKNOWN_ERROR",
    message: "职位详情加载失败，请稍后重试。",
    status: 0,
  };
}

function formatAnalyzedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "分析时间未知";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function eligibilityClassName(status: EligibilityStatus): string {
  const classes: Record<EligibilityStatus, string> = {
    PASS: "border-emerald-200 bg-emerald-50 text-emerald-800",
    WARN: "border-amber-200 bg-amber-50 text-amber-900",
    FAIL: "border-red-200 bg-red-50 text-red-800",
  };
  return classes[status];
}

function recommendationClassName(level: RecommendationLevel): string {
  const classes: Record<RecommendationLevel, string> = {
    PRIORITY: "bg-emerald-100 text-emerald-800",
    STRONG: "bg-blue-100 text-blue-800",
    SELECTIVE: "bg-amber-100 text-amber-800",
    LOW: "bg-slate-200 text-slate-700",
    BLOCKED: "bg-red-100 text-red-800",
  };
  return classes[level];
}

function assessmentClassName(status: AssessmentStatus): string {
  const classes: Record<AssessmentStatus, string> = {
    MATCHED: "bg-emerald-50 text-emerald-700",
    PARTIAL: "bg-blue-50 text-blue-700",
    CONFIRMED_GAP: "bg-red-50 text-red-700",
    UNKNOWN: "bg-amber-50 text-amber-800",
  };
  return classes[status];
}

function requirementClassName(type: RequirementType): string {
  const classes: Record<RequirementType, string> = {
    HARD: "bg-red-50 text-red-700",
    CORE: "bg-indigo-50 text-indigo-700",
    STANDARD: "bg-slate-100 text-slate-600",
    PREFERRED: "bg-violet-50 text-violet-700",
  };
  return classes[type];
}

function gapClassName(importance: GapImportance): string {
  const classes: Record<GapImportance, string> = {
    HIGH: "bg-red-50 text-red-700",
    MEDIUM: "bg-amber-50 text-amber-800",
    LOW: "bg-slate-100 text-slate-600",
  };
  return classes[importance];
}

export function JobDetailView({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [detail, setDetail] = useState<JobMatchDetailData | null>(null);
  const [issue, setIssue] = useState<RequestIssue | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    void apiRequest<JobMatchDetailEnvelope>(`/jobs/${jobId}`)
      .then((response) => {
        if (!cancelled) {
          setDetail(response.data);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const requestIssue = toRequestIssue(error);
        if (requestIssue.status === 401) {
          router.replace("/login");
          router.refresh();
          return;
        }
        setIssue(requestIssue);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId, loadAttempt, router]);

  function retryLoad() {
    setIsLoading(true);
    setIssue(null);
    setDetail(null);
    setLoadAttempt((current) => current + 1);
  }

  if (isLoading) {
    return <DetailLoadingState />;
  }

  if (issue || !detail) {
    return <DetailErrorState issue={issue} onRetry={retryLoad} />;
  }

  return <JobDetailContent detail={detail} />;
}

function DetailLoadingState() {
  return (
    <div
      aria-live="polite"
      className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
    >
      <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
      <h1 className="mt-5 text-xl font-semibold text-slate-950">
        正在整理匹配证据
      </h1>
      <p className="mt-2 text-sm text-slate-500">
        正在加载岗位要求、评分维度和简历证据。
      </p>
    </div>
  );
}

function DetailErrorState({
  issue,
  onRetry,
}: {
  issue: RequestIssue | null;
  onRetry: () => void;
}) {
  const notFound = issue?.code === "JOB_NOT_FOUND" || issue?.status === 404;
  const noResult = issue?.code === "MATCH_RESULT_NOT_FOUND";
  return (
    <div className="rounded-3xl border border-red-200 bg-white px-6 py-16 text-center shadow-sm">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-xl font-semibold text-red-700">
        !
      </div>
      <h1 className="mt-5 text-xl font-semibold text-slate-950">
        {notFound
          ? "找不到这个职位"
          : noResult
            ? "该职位还没有可用结果"
            : "职位详情暂时无法加载"}
      </h1>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-slate-600" role="alert">
        {notFound
          ? "该职位不存在，或你没有访问权限。"
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

function JobDetailContent({ detail }: { detail: JobMatchDetailData }) {
  const dimensions = getDimensionCards(detail.dimension_scores);
  const requirementByKey = new Map<string, string>([
    ...detail.hard_gates.map(
      (item): [string, string] => [
        item.requirement.requirement_key,
        item.requirement.requirement_text,
      ],
    ),
    ...detail.requirement_assessments.map(
      (item): [string, string] => [
        item.requirement.requirement_key,
        item.requirement.requirement_text,
      ],
    ),
  ]);
  const metadata = [detail.company_name, detail.location, detail.department].filter(
    Boolean,
  );

  return (
    <div>
      <Link
        className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-800"
        href={`/job-match/${detail.batch_id}`}
      >
        ← 返回匹配结果
      </Link>

      <header className="mt-5 border-b border-slate-200 pb-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-blue-600">Job match detail</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
              {detail.title}
            </h1>
            <p className="mt-3 text-base text-slate-600">{metadata.join(" · ")}</p>
            <p className="mt-2 text-xs text-slate-400">
              分析于 {formatAnalyzedAt(detail.analyzed_at)}
            </p>
          </div>
          {detail.source_url ? (
            <a
              className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              href={detail.source_url}
              rel="noreferrer"
              target="_blank"
            >
              查看原始职位 ↗
            </a>
          ) : null}
        </div>
      </header>

      <section className="mt-8 overflow-hidden rounded-3xl bg-slate-950 text-white shadow-sm">
        <div className="grid gap-8 p-7 sm:p-9 lg:grid-cols-[11rem_minmax(0,1fr)_16rem] lg:items-center">
          <div className="flex h-40 w-40 flex-col items-center justify-center rounded-full border border-white/15 bg-white/5">
            <span className="text-5xl font-semibold tracking-tight">
              {detail.display_score}
            </span>
            <span className="mt-1 text-sm text-slate-300">总匹配分 / 100</span>
          </div>
          <div>
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${recommendationClassName(detail.recommendation_level)}`}
            >
              {detail.recommendation_level}
            </span>
            <h2 className="mt-4 text-2xl font-semibold">{detail.recommendation}</h2>
            <p className="mt-3 max-w-2xl leading-7 text-slate-300">
              {detail.role_summary ?? "当前岗位已完成逐要求证据匹配。"}
            </p>
            {detail.eligibility_status === "FAIL" ? (
              <p className="mt-4 text-sm font-semibold text-red-300">
                能力分仍可查看，但明确硬性冲突使该岗位不进入正常可投排序。
              </p>
            ) : null}
            {detail.eligibility_status === "WARN" ? (
              <p className="mt-4 text-sm font-semibold text-amber-300">
                条件待核实：当前简历无法确认至少一项硬性条件。
              </p>
            ) : null}
          </div>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-2xl bg-white/10 px-5 py-4">
              <dt className="text-xs text-slate-300">Eligibility</dt>
              <dd className="mt-1 font-semibold">
                {detail.eligibility_status} · {getEligibilityLabel(detail.eligibility_status)}
              </dd>
            </div>
            <div className="rounded-2xl bg-white/10 px-5 py-4">
              <dt className="text-xs text-slate-300">证据置信度</dt>
              <dd className="mt-1 font-semibold">
                {formatDetailScore(detail.confidence_score)}% · {getConfidenceLabel(detail.confidence_level)}
              </dd>
            </div>
          </dl>
        </div>
        <p className="border-t border-white/10 px-7 py-4 text-xs leading-5 text-slate-400 sm:px-9">
          匹配分衡量当前简历证据与该 JD 要求的契合程度，不代表录用概率，也不评价其他候选人的竞争力。
        </p>
      </section>

      <section className="mt-10" aria-labelledby="dimension-heading">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              Backend-scored
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-slate-950" id="dimension-heading">
              六维评分
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-slate-500">
            JD 未出现的维度显示 N/A；适用维度由后端重新归一到 100 分，不用 0 分污染总分。
          </p>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {dimensions.map((card) => (
            <article
              className={`rounded-2xl border p-5 shadow-sm ${
                card.score
                  ? "border-slate-200 bg-white"
                  : "border-dashed border-slate-200 bg-slate-50"
              }`}
              key={card.dimension}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-semibold text-slate-900">{card.label}</h3>
                  <p className="mt-1 text-xs text-slate-400">{card.dimension}</p>
                </div>
                {card.score ? (
                  <p className="shrink-0 text-lg font-semibold text-slate-950">
                    {formatDetailScore(card.score.raw_score)}
                    <span className="text-sm font-normal text-slate-400">
                      /{formatDetailScore(card.score.max_score)}
                    </span>
                  </p>
                ) : (
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-400">
                    N/A
                  </span>
                )}
              </div>
              {card.score ? (
                <>
                  <div
                    aria-label={`${card.label}得分率 ${formatDetailScore(card.score.normalized_score)}%`}
                    aria-valuemax={100}
                    aria-valuemin={0}
                    aria-valuenow={clampPercent(card.score.normalized_score)}
                    className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100"
                    role="progressbar"
                  >
                    <div
                      className="h-full rounded-full bg-blue-600"
                      style={{
                        width: `${clampPercent(card.score.normalized_score)}%`,
                      }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-slate-500">
                    维度得分率 {formatDetailScore(card.score.normalized_score)}%
                  </p>
                </>
              ) : (
                <p className="mt-5 text-sm leading-6 text-slate-400">
                  该 JD 当前没有此维度的适用要求。
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="mt-10 grid gap-5 lg:grid-cols-2" aria-label="优势与差距">
        <article className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
            Strengths
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">优势</h2>
          {detail.strengths.length > 0 ? (
            <ul className="mt-5 space-y-3">
              {detail.strengths.map((strength) => (
                <li className="flex gap-3 text-sm leading-6 text-slate-700" key={strength}>
                  <span aria-hidden="true" className="mt-0.5 text-emerald-600">
                    ✓
                  </span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm leading-6 text-slate-500">
              当前没有达到 A/B 级证据标准的突出优势。
            </p>
          )}
        </article>

        <article className="rounded-3xl border border-amber-200 bg-white p-6 shadow-sm sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700">
            Gaps
          </p>
          <h2 className="mt-1 text-xl font-semibold text-slate-950">主要差距</h2>
          {detail.gaps.length > 0 ? (
            <div className="mt-5 space-y-5">
              {detail.gaps.map((gap, index) => (
                <div className="border-b border-slate-100 pb-5 last:border-0 last:pb-0" key={`${gap.requirement_key}-${index}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${gapClassName(gap.importance)}`}>
                      {gap.importance}
                    </span>
                    <span className="text-xs text-slate-400">{gap.requirement_key}</span>
                  </div>
                  <p className="mt-3 text-sm font-semibold leading-6 text-slate-800">
                    {gap.gap}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    对应要求：{requirementByKey.get(gap.requirement_key) ?? "未定位"}
                  </p>
                  <p className="mt-2 rounded-xl bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
                    提升方向：{gap.improvement_direction}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm leading-6 text-slate-500">
              当前未识别需要优先补证的主要差距。
            </p>
          )}
        </article>
      </section>

      <HardGateSection gates={detail.hard_gates} overall={detail.eligibility_status} />
      <RequirementSection assessments={detail.requirement_assessments} />

      <section className="mt-10 rounded-3xl border border-blue-100 bg-blue-50 p-6 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
          Overall recommendation
        </p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">总体建议</h2>
        <p className="mt-3 leading-7 text-slate-700">{detail.recommendation}</p>
        <p className="mt-3 text-sm leading-6 text-slate-500">
          建议结合上方 Hard Gate、核心要求及证据等级做最终投递决策，不要仅依据总分。
        </p>
      </section>

      <section className="mt-10 rounded-3xl bg-slate-950 p-6 text-white sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">下一步行动</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
              详情数据已经准备好。针对性简历和投递记录将在后续独立步骤接入，当前不会生成占位数据。
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              aria-disabled="true"
              className="cursor-not-allowed rounded-xl bg-slate-700 px-5 py-3 text-sm font-semibold text-slate-300"
              disabled
              title="将在 CP-023 开放"
              type="button"
            >
              针对该职位优化简历
            </button>
            <button
              aria-disabled="true"
              className="cursor-not-allowed rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-slate-400"
              disabled
              title="将在 CP-025 开放"
              type="button"
            >
              创建投递记录
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function HardGateSection({
  gates,
  overall,
}: {
  gates: HardGateDetail[];
  overall: EligibilityStatus;
}) {
  return (
    <section className="mt-10" aria-labelledby="hard-gate-heading">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Eligibility gate
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-950" id="hard-gate-heading">
            硬性条件
          </h2>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${eligibilityClassName(overall)}`}>
          {overall} · {getEligibilityLabel(overall)}
        </span>
      </div>
      {gates.length > 0 ? (
        <div className="mt-5 space-y-4">
          {gates.map((gate) => (
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm" key={gate.requirement.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-slate-400">
                    {gate.requirement.requirement_key} · HARD
                  </p>
                  <h3 className="mt-1 font-semibold text-slate-900">
                    {gate.requirement.requirement_text}
                  </h3>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${eligibilityClassName(gate.status)}`}>
                  {gate.status}
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-slate-700">{gate.reason}</p>
              <blockquote className="mt-3 border-l-2 border-slate-200 pl-4 text-sm italic leading-6 text-slate-500">
                JD 原文：{gate.requirement.source_quote}
              </blockquote>
              <EvidenceList evidence={gate.evidence} />
            </article>
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-6 text-sm leading-6 text-slate-600 shadow-sm">
          当前 JD 未解析出明确的硬性准入条件；Eligibility 因此没有发现硬性冲突。
        </div>
      )}
    </section>
  );
}

function RequirementSection({
  assessments,
}: {
  assessments: RequirementAssessmentDetail[];
}) {
  return (
    <section className="mt-10" aria-labelledby="requirements-heading">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
          Requirement evidence
        </p>
        <h2 className="mt-1 text-2xl font-semibold text-slate-950" id="requirements-heading">
          职位核心要求与简历证据
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
          AI 只负责逐项判断匹配等级和证据强度；最终分数由后端依据固定规则计算。
        </p>
      </div>
      <div className="mt-5 space-y-4">
        {assessments.map((assessment) => (
          <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7" key={assessment.requirement.id}>
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap gap-2">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${requirementClassName(assessment.requirement.requirement_type)}`}>
                    {assessment.requirement.requirement_key} · {getRequirementTypeLabel(assessment.requirement.requirement_type)}
                  </span>
                  {assessment.requirement.dimension ? (
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                      {getDimensionLabel(assessment.requirement.dimension)}
                    </span>
                  ) : null}
                  {assessment.requirement.importance === 2 ? (
                    <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
                      重点要求
                    </span>
                  ) : null}
                </div>
                <h3 className="mt-3 text-lg font-semibold leading-7 text-slate-950">
                  {assessment.requirement.requirement_text}
                </h3>
              </div>
              <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${assessmentClassName(assessment.status)}`}>
                {getAssessmentStatusLabel(assessment.status)}
              </span>
            </div>

            <dl className="mt-5 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-slate-50 px-4 py-3">
                <dt className="text-xs text-slate-500">匹配等级</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {assessment.match_level}/4 · {getMatchLevelLabel(assessment.match_level)}
                </dd>
              </div>
              <div className="rounded-xl bg-slate-50 px-4 py-3">
                <dt className="text-xs text-slate-500">证据等级</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {assessment.evidence_grade} · Cap {assessment.evidence_cap}
                </dd>
              </div>
              <div className="rounded-xl bg-slate-50 px-4 py-3">
                <dt className="text-xs text-slate-500">总分贡献</dt>
                <dd className="mt-1 text-sm font-semibold text-slate-900">
                  {formatDetailScore(assessment.weighted_score)} 分
                </dd>
              </div>
            </dl>

            <p className="mt-5 text-sm leading-7 text-slate-700">{assessment.reason}</p>
            <blockquote className="mt-3 border-l-2 border-blue-200 pl-4 text-sm italic leading-6 text-slate-500">
              JD 原文：{assessment.requirement.source_quote}
            </blockquote>
            <EvidenceList evidence={assessment.evidence} />
          </article>
        ))}
      </div>
    </section>
  );
}

function EvidenceList({ evidence }: { evidence: ResumeEvidence[] }) {
  const grounded = evidence.filter((item) => item.source_quote);
  return (
    <div className="mt-5 rounded-2xl bg-blue-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
        简历证据
      </p>
      {grounded.length > 0 ? (
        <ul className="mt-3 space-y-3">
          {grounded.map((item, index) => (
            <li className="text-sm leading-6 text-slate-700" key={`${item.source_id ?? "summary"}-${index}`}>
              <span className="mr-2 rounded bg-white px-2 py-1 text-xs font-semibold text-blue-700">
                {getEvidenceSourceLabel(item.source_type)}
              </span>
              “{item.source_quote}”
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-500">
          当前简历没有可定位的直接证据；这表示信息未知，不自动等于候选人不具备该能力。
        </p>
      )}
    </div>
  );
}
