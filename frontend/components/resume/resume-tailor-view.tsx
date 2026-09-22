"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect, useMemo, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import type {
  JobMatchDetailData,
  JobMatchDetailEnvelope,
} from "@/lib/job-detail";
import {
  cloneTailorOutput,
  formatResumePeriod,
  getImprovementStatusLabel,
  getIncludedTailoredItems,
  getOrderedSkills,
  moveSkill,
  reorderIncludedItems,
  type ResumeTailorDraftData,
  type ResumeTailorDraftEnvelope,
  type ResumeTailorOutput,
  type TailoredSourceItem,
} from "@/lib/resume-tailor";
import {
  buildResumeVersionPayload,
  type ResumeVersionData,
  type ResumeVersionEnvelope,
  validateTailorDraftForSave,
} from "@/lib/resume-version";

type RequestIssue = {
  code: string;
  message: string;
  status: number;
};

type TailoredSection = "experiences" | "projects";

const editableTextClassName =
  "mt-3 min-h-24 w-full resize-y rounded-xl border border-blue-200 bg-white px-3.5 py-3 text-sm leading-6 text-slate-800 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

function toRequestIssue(error: unknown, fallback: string): RequestIssue {
  if (error instanceof ApiError) {
    return { code: error.code, message: error.message, status: error.status };
  }
  return { code: "UNKNOWN_ERROR", message: fallback, status: 0 };
}

function generationIssueTitle(issue: RequestIssue): string {
  if (issue.code === "MATCH_RESULT_NOT_FOUND") {
    return "该职位还没有可用的匹配结果";
  }
  if (issue.code === "AI_INVALID_INPUT") {
    return "当前匹配快照不完整";
  }
  if (issue.code === "AI_INVALID_OUTPUT") {
    return "AI 草稿未通过真实性校验";
  }
  if (issue.code === "AI_TIMEOUT") {
    return "AI 生成超时";
  }
  if (issue.code === "AI_PROVIDER_ERROR") {
    return "AI 服务暂时不可用";
  }
  return "针对性简历生成失败";
}

export function ResumeTailorView({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<JobMatchDetailData | null>(null);
  const [contextIssue, setContextIssue] = useState<RequestIssue | null>(null);
  const [isContextLoading, setIsContextLoading] = useState(true);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [tailorData, setTailorData] = useState<ResumeTailorDraftData | null>(
    null,
  );
  const [draft, setDraft] = useState<ResumeTailorOutput | null>(null);
  const [baseline, setBaseline] = useState<string | null>(null);
  const [generationIssue, setGenerationIssue] = useState<RequestIssue | null>(
    null,
  );
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveIssue, setSaveIssue] = useState<RequestIssue | null>(null);
  const [savedVersion, setSavedVersion] = useState<ResumeVersionData | null>(
    null,
  );
  const [savedBaseline, setSavedBaseline] = useState<string | null>(null);

  const isEdited = useMemo(
    () => draft !== null && baseline !== null && JSON.stringify(draft) !== baseline,
    [baseline, draft],
  );
  const hasUnsavedDraft = useMemo(
    () =>
      draft !== null &&
      (savedBaseline === null || JSON.stringify(draft) !== savedBaseline),
    [draft, savedBaseline],
  );

  useEffect(() => {
    let cancelled = false;

    void apiRequest<JobMatchDetailEnvelope>(`/jobs/${jobId}`)
      .then((response) => {
        if (!cancelled) {
          setJob(response.data);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        const issue = toRequestIssue(error, "职位信息加载失败，请稍后重试。");
        if (issue.status === 401) {
          router.replace("/login");
          router.refresh();
          return;
        }
        setContextIssue(issue);
      })
      .finally(() => {
        if (!cancelled) {
          setIsContextLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [jobId, loadAttempt, router]);

  useEffect(() => {
    function warnBeforeLeave(event: BeforeUnloadEvent) {
      if (!hasUnsavedDraft) {
        return;
      }
      event.preventDefault();
      event.returnValue = true;
    }

    window.addEventListener("beforeunload", warnBeforeLeave);
    return () => window.removeEventListener("beforeunload", warnBeforeLeave);
  }, [hasUnsavedDraft]);

  function retryContext() {
    setIsContextLoading(true);
    setContextIssue(null);
    setJob(null);
    setLoadAttempt((current) => current + 1);
  }

  async function generateDraft() {
    if (
      draft &&
      !window.confirm("重新生成会替换当前草稿和人工修改，确定继续吗？")
    ) {
      return;
    }

    setGenerationIssue(null);
    setIsGenerating(true);

    try {
      const response = await apiRequest<ResumeTailorDraftEnvelope>(
        `/jobs/${jobId}/resume-tailor`,
        { method: "POST" },
      );
      const nextDraft = cloneTailorOutput(response.data.draft);
      setTailorData(response.data);
      setDraft(nextDraft);
      setBaseline(JSON.stringify(nextDraft));
      setSavedBaseline(null);
      setSavedVersion(null);
      setSaveIssue(null);
    } catch (error: unknown) {
      const issue = toRequestIssue(
        error,
        "针对性简历生成失败，请稍后重试。",
      );
      if (issue.status === 401) {
        router.replace("/login");
        router.refresh();
        return;
      }
      setGenerationIssue(issue);
    } finally {
      setIsGenerating(false);
    }
  }

  function updateSummary(value: string) {
    setDraft((current) =>
      current ? { ...current, professional_summary: value } : current,
    );
  }

  function updateBullet(
    section: TailoredSection,
    sourceId: string,
    bulletIndex: number,
    value: string,
  ) {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        [section]: current[section].map((item) =>
          item.source_id === sourceId
            ? {
                ...item,
                bullets: item.bullets.map((bullet, index) =>
                  index === bulletIndex ? { ...bullet, text: value } : bullet,
                ),
              }
            : item,
        ),
      };
    });
  }

  function moveSectionItem(
    section: TailoredSection,
    sourceId: string,
    direction: -1 | 1,
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            [section]: reorderIncludedItems(
              current[section],
              sourceId,
              direction,
            ),
          }
        : current,
    );
  }

  function moveSkillItem(sourceId: string, direction: -1 | 1) {
    setDraft((current) =>
      current
        ? {
            ...current,
            skill_order: moveSkill(current.skill_order, sourceId, direction),
          }
        : current,
    );
  }

  async function saveDraft() {
    if (!draft || !tailorData) {
      return;
    }
    const localIssue = validateTailorDraftForSave(draft);
    if (localIssue) {
      setSaveIssue({ code: "INVALID_DRAFT", message: localIssue, status: 0 });
      return;
    }

    setSaveIssue(null);
    setIsSaving(true);
    const payload = buildResumeVersionPayload(tailorData, draft);
    try {
      const response = await apiRequest<ResumeVersionEnvelope>(
        "/resume/versions",
        { method: "POST", body: JSON.stringify(payload) },
      );
      setDraft(payload.draft);
      setSavedBaseline(JSON.stringify(payload.draft));
      setSavedVersion(response.data);
    } catch (error: unknown) {
      const issue = toRequestIssue(
        error,
        "岗位版简历保存失败，请稍后重试。",
      );
      if (issue.status === 401) {
        router.replace("/login");
        router.refresh();
        return;
      }
      setSaveIssue(issue);
    } finally {
      setIsSaving(false);
    }
  }

  if (isContextLoading) {
    return <TailorLoadingState message="正在加载目标职位与匹配结果…" />;
  }

  if (contextIssue || !job) {
    return <TailorContextError issue={contextIssue} onRetry={retryContext} />;
  }

  return (
    <div>
      <Link
        className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-800"
        href={`/jobs/${jobId}`}
      >
        ← 返回职位详情
      </Link>

      <header className="mt-5 border-b border-slate-200 pb-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold text-blue-600">Resume Tailor</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
              针对性简历
            </h1>
            <p className="mt-3 text-base text-slate-600">
              {job.company_name} · {job.title}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm shadow-sm">
            <span className="text-slate-500">当前匹配分</span>
            <strong className="ml-3 text-xl text-slate-950">
              {job.display_score}
            </strong>
            <span className="ml-1 text-slate-400">/ 100</span>
          </div>
        </div>
      </header>

      {!draft || !tailorData ? (
        <TailorStartState
          isGenerating={isGenerating}
          issue={generationIssue}
          onGenerate={generateDraft}
        />
      ) : (
        <>
          {generationIssue ? (
            <GenerationError issue={generationIssue} onRetry={generateDraft} />
          ) : null}
          {isGenerating ? (
            <div
              aria-live="polite"
              className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm font-medium text-blue-800"
            >
              正在重新生成，当前草稿会保留到新结果通过真实性校验。
            </div>
          ) : null}
          <TailorComparison
            data={tailorData}
            draft={draft}
            isEdited={isEdited}
            isGenerating={isGenerating}
            isSaved={!hasUnsavedDraft && savedVersion !== null}
            isSaving={isSaving}
            onMoveSectionItem={moveSectionItem}
            onMoveSkill={moveSkillItem}
            onRegenerate={generateDraft}
            onSave={saveDraft}
            onUpdateBullet={updateBullet}
            onUpdateSummary={updateSummary}
            saveIssue={saveIssue}
            savedVersion={savedVersion}
          />
        </>
      )}
    </div>
  );
}

function TailorLoadingState({ message }: { message: string }) {
  return (
    <div
      aria-live="polite"
      className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
    >
      <div className="mx-auto h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
      <h1 className="mt-5 text-xl font-semibold text-slate-950">
        正在准备简历优化
      </h1>
      <p className="mt-2 text-sm text-slate-500">{message}</p>
    </div>
  );
}

function TailorContextError({
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
            ? "该职位还不能生成针对性简历"
            : "简历优化页面暂时无法加载"}
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

function TailorStartState({
  isGenerating,
  issue,
  onGenerate,
}: {
  isGenerating: boolean;
  issue: RequestIssue | null;
  onGenerate: () => void;
}) {
  return (
    <section className="mt-8 overflow-hidden rounded-3xl bg-slate-950 text-white shadow-sm">
      <div className="grid gap-8 p-7 sm:p-10 lg:grid-cols-[minmax(0,1fr)_18rem] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-300">
            Review before save
          </p>
          <h2 className="mt-3 text-2xl font-semibold">
            从真实经历生成一份可审阅草稿
          </h2>
          <p className="mt-4 max-w-2xl leading-7 text-slate-300">
            系统只会选择、排序和改写现有简历材料。公司、职位、学校、时间、技能与数字不会由 AI 擅自新增或修改。
          </p>
          <ul className="mt-5 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
            <li>✓ 每条改写保留原文证据</li>
            <li>✓ 缺失能力只进入提升建议</li>
            <li>✓ 本步骤不会覆盖简历母版</li>
            <li>✓ 生成后可逐条人工修改</li>
          </ul>
        </div>
        <div>
          <button
            className="w-full rounded-xl bg-blue-500 px-5 py-3.5 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-400 disabled:cursor-wait disabled:bg-blue-800 disabled:text-blue-200"
            disabled={isGenerating}
            onClick={onGenerate}
            type="button"
          >
            {isGenerating ? "正在生成并校验…" : "生成针对性简历"}
          </button>
          <p className="mt-3 text-center text-xs leading-5 text-slate-400">
            生成可能需要几十秒；仅在你点击后调用 AI。
          </p>
        </div>
      </div>
      {issue ? (
        <div className="border-t border-red-400/20 bg-red-950/50 px-7 py-5 sm:px-10">
          <p className="font-semibold text-red-200">{generationIssueTitle(issue)}</p>
          <p className="mt-1 text-sm leading-6 text-red-100" role="alert">
            {issue.message}
          </p>
        </div>
      ) : null}
    </section>
  );
}

function GenerationError({
  issue,
  onRetry,
}: {
  issue: RequestIssue;
  onRetry: () => void;
}) {
  return (
    <div className="mt-6 flex flex-col gap-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-semibold text-red-800">{generationIssueTitle(issue)}</p>
        <p className="mt-1 text-sm text-red-700" role="alert">
          {issue.message} 当前草稿和人工修改仍保留。
        </p>
      </div>
      <button
        className="shrink-0 rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
        onClick={onRetry}
        type="button"
      >
        重新生成
      </button>
    </div>
  );
}

function TailorComparison({
  data,
  draft,
  isEdited,
  isGenerating,
  isSaved,
  isSaving,
  onMoveSectionItem,
  onMoveSkill,
  onRegenerate,
  onSave,
  onUpdateBullet,
  onUpdateSummary,
  saveIssue,
  savedVersion,
}: {
  data: ResumeTailorDraftData;
  draft: ResumeTailorOutput;
  isEdited: boolean;
  isGenerating: boolean;
  isSaved: boolean;
  isSaving: boolean;
  onMoveSectionItem: (
    section: TailoredSection,
    sourceId: string,
    direction: -1 | 1,
  ) => void;
  onMoveSkill: (sourceId: string, direction: -1 | 1) => void;
  onRegenerate: () => void;
  onSave: () => void;
  onUpdateBullet: (
    section: TailoredSection,
    sourceId: string,
    bulletIndex: number,
    value: string,
  ) => void;
  onUpdateSummary: (value: string) => void;
  saveIssue: RequestIssue | null;
  savedVersion: ResumeVersionData | null;
}) {
  const source = data.source_resume_snapshot;
  const includedExperiences = getIncludedTailoredItems(draft.experiences);
  const includedProjects = getIncludedTailoredItems(draft.projects);
  const experienceById = new Map(
    source.experiences.map((item) => [item.id, item]),
  );
  const projectById = new Map(source.projects.map((item) => [item.id, item]));
  const orderedSkills = getOrderedSkills(source, draft.skill_order);

  return (
    <>
      <div className="mt-8 flex flex-col gap-3 rounded-2xl border border-blue-100 bg-blue-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-900">
            已通过后端真实性校验
          </p>
          <p className="mt-1 text-xs leading-5 text-blue-700">
            {data.prompt_version} · {data.model} · 第 {data.attempts} 次尝试成功
          </p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-blue-700">
          {isSaved
            ? "已保存为岗位版"
            : isEdited
              ? "已人工修改 · 尚未保存"
              : "AI 草稿 · 尚未保存"}
        </span>
      </div>

      {savedVersion && isSaved ? (
        <div className="mt-5 flex flex-col gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800 sm:flex-row sm:items-center sm:justify-between">
          <p>
            已保存“{savedVersion.name}”，母版和匹配快照均未被修改。
          </p>
          <Link className="font-semibold hover:text-emerald-950" href="/resumes">
            前往简历库 →
          </Link>
          <Link
            className="font-semibold hover:text-emerald-950"
            href={`/applications/new?jobId=${savedVersion.job_id}&versionId=${savedVersion.id}`}
          >
            创建投递记录 →
          </Link>
        </div>
      ) : null}

      {saveIssue ? (
        <div
          className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700"
          role="alert"
        >
          {saveIssue.message}
        </div>
      ) : null}

      <div className="mt-6 grid gap-6 xl:grid-cols-2" aria-label="简历优化前后对照">
        <ResumePanel eyebrow="Source snapshot" title="原简历">
          <BasicIdentity resume={source} />
          <OriginalResumeSections resume={source} />
        </ResumePanel>

        <ResumePanel eyebrow="Editable draft" title="针对性简历" accent>
          <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
              不可变字段
            </p>
            <p className="mt-2 text-sm leading-6 text-blue-900">
              姓名、联系方式、教育、公司、职位、项目名称和日期沿用左侧快照；AI 只改写下方可编辑内容。
            </p>
          </div>

          <DraftSection title="职业概述">
            <textarea
              aria-label="针对性职业概述"
              className={editableTextClassName}
              onChange={(event) => onUpdateSummary(event.target.value)}
              placeholder="当前证据不足，未生成职业概述。"
              value={draft.professional_summary ?? ""}
            />
          </DraftSection>

          <DraftSection title={`工作与实习 · ${includedExperiences.length}`}>
            {includedExperiences.length > 0 ? (
              <div className="space-y-4">
                {includedExperiences.map((item, index) => {
                  const sourceItem = experienceById.get(item.source_id);
                  return sourceItem ? (
                    <EditableSourceCard
                      item={item}
                      key={item.source_id}
                      metadata={formatResumePeriod(
                        sourceItem.start_date,
                        sourceItem.end_date,
                        sourceItem.is_current,
                      )}
                      onMove={(direction) =>
                        onMoveSectionItem(
                          "experiences",
                          item.source_id,
                          direction,
                        )
                      }
                      onUpdateBullet={(bulletIndex, value) =>
                        onUpdateBullet(
                          "experiences",
                          item.source_id,
                          bulletIndex,
                          value,
                        )
                      }
                      position={{ index, total: includedExperiences.length }}
                      subtitle={sourceItem.position}
                      title={sourceItem.organization}
                    />
                  ) : null;
                })}
              </div>
            ) : (
              <DraftEmpty text="当前没有被选入岗位版的工作或实习经历。" />
            )}
          </DraftSection>

          <DraftSection title={`项目经历 · ${includedProjects.length}`}>
            {includedProjects.length > 0 ? (
              <div className="space-y-4">
                {includedProjects.map((item, index) => {
                  const sourceItem = projectById.get(item.source_id);
                  return sourceItem ? (
                    <EditableSourceCard
                      item={item}
                      key={item.source_id}
                      metadata={formatResumePeriod(
                        sourceItem.start_date,
                        sourceItem.end_date,
                      )}
                      onMove={(direction) =>
                        onMoveSectionItem(
                          "projects",
                          item.source_id,
                          direction,
                        )
                      }
                      onUpdateBullet={(bulletIndex, value) =>
                        onUpdateBullet(
                          "projects",
                          item.source_id,
                          bulletIndex,
                          value,
                        )
                      }
                      position={{ index, total: includedProjects.length }}
                      subtitle={sourceItem.role ?? "未填写角色"}
                      title={sourceItem.name}
                    />
                  ) : null;
                })}
              </div>
            ) : (
              <DraftEmpty text="当前没有被选入岗位版的项目经历。" />
            )}
          </DraftSection>

          <DraftSection title={`技能排序 · ${orderedSkills.length}`}>
            {orderedSkills.length > 0 ? (
              <ol className="space-y-2">
                {orderedSkills.map((skill, index) => (
                  <li
                    className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5"
                    key={skill.id}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-xs font-semibold text-blue-700">
                        {index + 1}
                      </span>
                      <span className="truncate text-sm font-medium text-slate-800">
                        {skill.skill_name}
                      </span>
                    </div>
                    <MoveButtons
                      canMoveDown={index < orderedSkills.length - 1}
                      canMoveUp={index > 0}
                      label={skill.skill_name}
                      onMove={(direction) => onMoveSkill(skill.id, direction)}
                    />
                  </li>
                ))}
              </ol>
            ) : (
              <DraftEmpty text="简历母版暂未提供可排序的技能。" />
            )}
          </DraftSection>
        </ResumePanel>
      </div>

      <ImprovementSection draft={draft} />

      <section className="sticky bottom-4 z-10 mt-8 rounded-2xl border border-slate-700 bg-slate-950/95 p-4 text-white shadow-xl backdrop-blur sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-semibold">确认后再保存岗位版</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              保存时后端会再次核对来源 ID、证据、技能和数字，并从原快照组装不可变字段。
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              className="rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-wait disabled:text-slate-500"
              disabled={isGenerating || isSaving}
              onClick={onRegenerate}
              type="button"
            >
              {isGenerating ? "重新生成中…" : "重新生成"}
            </button>
            <button
              className="rounded-xl bg-blue-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-400 disabled:cursor-wait disabled:bg-blue-800 disabled:text-blue-200"
              disabled={isGenerating || isSaving || isSaved}
              onClick={onSave}
              type="button"
            >
              {isSaving
                ? "正在保存并校验…"
                : isSaved
                  ? "已保存为岗位版简历"
                  : "保存为岗位版简历"}
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

function ResumePanel({
  accent = false,
  children,
  eyebrow,
  title,
}: {
  accent?: boolean;
  children: ReactNode;
  eyebrow: string;
  title: string;
}) {
  return (
    <section
      className={`rounded-3xl border bg-white p-5 shadow-sm sm:p-7 ${
        accent ? "border-blue-200" : "border-slate-200"
      }`}
    >
      <p
        className={`text-xs font-semibold uppercase tracking-wider ${
          accent ? "text-blue-600" : "text-slate-400"
        }`}
      >
        {eyebrow}
      </p>
      <h2 className="mt-1 text-2xl font-semibold text-slate-950">{title}</h2>
      <div className="mt-6 space-y-7">{children}</div>
    </section>
  );
}

function BasicIdentity({
  resume,
}: {
  resume: ResumeTailorDraftData["source_resume_snapshot"];
}) {
  const info = resume.basic_info;
  const contact = [info.phone, info.email, info.city].filter(Boolean).join(" · ");
  return (
    <div className="border-b border-slate-200 pb-5">
      <h3 className="text-xl font-semibold text-slate-950">
        {info.name ?? "未填写姓名"}
      </h3>
      <p className="mt-2 text-sm text-slate-500">
        {contact || "未填写联系方式与所在城市"}
      </p>
      {info.summary ? (
        <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-700">
          {info.summary}
        </p>
      ) : null}
    </div>
  );
}

function OriginalResumeSections({
  resume,
}: {
  resume: ResumeTailorDraftData["source_resume_snapshot"];
}) {
  return (
    <>
      <OriginalSection title={`教育经历 · ${resume.education.length}`}>
        {resume.education.length > 0 ? (
          resume.education.map((item) => (
            <OriginalCard
              key={item.id}
              metadata={formatResumePeriod(item.start_date, item.end_date)}
              subtitle={`${item.degree} · ${item.major}`}
              text={[item.courses, item.description].filter(Boolean).join("\n")}
              title={item.school}
            />
          ))
        ) : (
          <DraftEmpty text="没有教育经历。" />
        )}
      </OriginalSection>

      <OriginalSection title={`工作与实习 · ${resume.experiences.length}`}>
        {resume.experiences.length > 0 ? (
          resume.experiences.map((item) => (
            <OriginalCard
              key={item.id}
              metadata={formatResumePeriod(
                item.start_date,
                item.end_date,
                item.is_current,
              )}
              subtitle={item.position}
              text={[item.description, item.achievements].filter(Boolean).join("\n")}
              title={item.organization}
            />
          ))
        ) : (
          <DraftEmpty text="没有工作或实习经历。" />
        )}
      </OriginalSection>

      <OriginalSection title={`项目经历 · ${resume.projects.length}`}>
        {resume.projects.length > 0 ? (
          resume.projects.map((item) => (
            <OriginalCard
              key={item.id}
              metadata={formatResumePeriod(item.start_date, item.end_date)}
              subtitle={item.role ?? "未填写角色"}
              text={[item.background, item.description, item.achievements]
                .filter(Boolean)
                .join("\n")}
              title={item.name}
            />
          ))
        ) : (
          <DraftEmpty text="没有项目经历。" />
        )}
      </OriginalSection>

      <OriginalSection title={`技能 · ${resume.skills.length}`}>
        {resume.skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {resume.skills.map((skill) => (
              <span
                className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700"
                key={skill.id}
              >
                {skill.skill_name}
              </span>
            ))}
          </div>
        ) : (
          <DraftEmpty text="没有技能信息。" />
        )}
      </OriginalSection>
    </>
  );
}

function OriginalSection({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function DraftSection({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function OriginalCard({
  metadata,
  subtitle,
  text,
  title,
}: {
  metadata: string;
  subtitle: string;
  text: string;
  title: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="font-semibold text-slate-900">{title}</h4>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
        </div>
        <span className="shrink-0 text-xs text-slate-400">{metadata}</span>
      </div>
      {text ? (
        <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
          {text}
        </p>
      ) : null}
    </article>
  );
}

function EditableSourceCard({
  item,
  metadata,
  onMove,
  onUpdateBullet,
  position,
  subtitle,
  title,
}: {
  item: TailoredSourceItem;
  metadata: string;
  onMove: (direction: -1 | 1) => void;
  onUpdateBullet: (index: number, value: string) => void;
  position: { index: number; total: number };
  subtitle: string;
  title: string;
}) {
  return (
    <article className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="font-semibold text-slate-900">{title}</h4>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
          <p className="mt-1 text-xs text-slate-400">{metadata}</p>
        </div>
        <MoveButtons
          canMoveDown={position.index < position.total - 1}
          canMoveUp={position.index > 0}
          label={title}
          onMove={onMove}
        />
      </div>
      <div className="mt-4 space-y-4">
        {item.bullets.map((bullet, index) => (
          <div key={`${item.source_id}-${index}`}>
            <label
              className="text-xs font-semibold text-blue-800"
              htmlFor={`${item.source_id}-bullet-${index}`}
            >
              改写要点 {index + 1}
            </label>
            <textarea
              className={editableTextClassName}
              id={`${item.source_id}-bullet-${index}`}
              onChange={(event) => onUpdateBullet(index, event.target.value)}
              value={bullet.text}
            />
            <details className="mt-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
              <summary className="font-medium text-slate-600">
                查看原文证据 · {bullet.evidence_refs.length} 条
              </summary>
              <ul className="mt-2 space-y-2">
                {bullet.evidence_refs.map((reference, referenceIndex) => (
                  <li
                    className="border-l-2 border-blue-100 pl-3 leading-5"
                    key={`${reference.source_field}-${referenceIndex}`}
                  >
                    {reference.source_field === "description" ? "描述" : "成果"}
                    ：{reference.source_quote}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        ))}
      </div>
    </article>
  );
}

function MoveButtons({
  canMoveDown,
  canMoveUp,
  label,
  onMove,
}: {
  canMoveDown: boolean;
  canMoveUp: boolean;
  label: string;
  onMove: (direction: -1 | 1) => void;
}) {
  const className =
    "rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300";
  return (
    <div className="flex shrink-0 gap-2">
      <button
        aria-label={`上移${label}`}
        className={className}
        disabled={!canMoveUp}
        onClick={() => onMove(-1)}
        type="button"
      >
        ↑
      </button>
      <button
        aria-label={`下移${label}`}
        className={className}
        disabled={!canMoveDown}
        onClick={() => onMove(1)}
        type="button"
      >
        ↓
      </button>
    </div>
  );
}

function DraftEmpty({ text }: { text: string }) {
  return (
    <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-500">
      {text}
    </p>
  );
}

function ImprovementSection({ draft }: { draft: ResumeTailorOutput }) {
  return (
    <section className="mt-8 grid gap-6 lg:grid-cols-2" aria-label="岗位差距与生成提醒">
      <article className="rounded-3xl border border-amber-200 bg-white p-6 shadow-sm sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-700">
          Improvement suggestions
        </p>
        <h2 className="mt-1 text-xl font-semibold text-slate-950">
          岗位差距与提升建议
        </h2>
        {draft.improvement_suggestions.length > 0 ? (
          <div className="mt-5 space-y-4">
            {draft.improvement_suggestions.map((item, index) => (
              <div
                className="rounded-2xl bg-amber-50 p-4"
                key={`${item.job_requirement}-${index}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-amber-800">
                    {getImprovementStatusLabel(item.current_status)}
                  </span>
                  <span className="text-xs font-semibold text-red-700">
                    暂勿写入简历
                  </span>
                </div>
                <p className="mt-3 text-sm font-semibold leading-6 text-slate-800">
                  {item.job_requirement}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {item.suggestion}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-5 text-sm leading-6 text-slate-500">
            当前没有额外的补证或提升建议。
          </p>
        )}
      </article>

      <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Review warnings
        </p>
        <h2 className="mt-1 text-xl font-semibold text-slate-950">审阅提醒</h2>
        {draft.warnings.length > 0 ? (
          <ul className="mt-5 space-y-3">
            {draft.warnings.map((warning, index) => (
              <li
                className="flex gap-3 rounded-xl bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
                key={`${warning}-${index}`}
              >
                <span aria-hidden="true" className="text-amber-600">
                  !
                </span>
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-5 text-sm leading-6 text-slate-500">
            后端没有返回额外提醒。保存前仍应逐条确认人工修改符合真实经历。
          </p>
        )}
      </article>
    </section>
  );
}
