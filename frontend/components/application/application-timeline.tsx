"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  APPLICATION_OUTCOME_OPTIONS,
  APPLICATION_STAGE_OPTIONS,
  buildApplicationEventPayload,
  buildApplicationStatusPayload,
  formatApplicationDate,
  formatApplicationTime,
  formatApplicationUpdatedAt,
  getApplicationEventLabel,
  getApplicationOutcomeLabel,
  getApplicationProgressLabel,
  getApplicationStageLabel,
  getApplicationStatusLabel,
  toDateTimeLocalValue,
  type ApplicationData,
  type ApplicationEnvelope,
  type ApplicationEvent,
  type ApplicationEventDraft,
  type ApplicationEventEnvelope,
  type ApplicationEventOutcome,
  type ApplicationEventPayload,
  type ApplicationStage,
  type ApplicationStatus,
  type ApplicationStatusPayload,
} from "@/lib/application";

const STATUS_CLASS_NAMES: Record<ApplicationStatus, string> = {
  ACTIVE: "bg-blue-50 text-blue-700 ring-blue-200",
  REJECTED: "bg-red-50 text-red-700 ring-red-200",
  OFFER: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  WITHDRAWN: "bg-slate-100 text-slate-600 ring-slate-200",
};

const OUTCOME_CLASS_NAMES: Record<ApplicationEventOutcome, string> = {
  PENDING: "bg-amber-50 text-amber-700",
  PASSED: "bg-emerald-50 text-emerald-700",
  FAILED: "bg-red-50 text-red-700",
  COMPLETED: "bg-blue-50 text-blue-700",
  CANCELLED: "bg-slate-100 text-slate-600",
};

type EventFormMode =
  | { kind: "create" }
  | { kind: "edit"; event: ApplicationEvent };

function requestMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

function eventToDraft(event?: ApplicationEvent): ApplicationEventDraft {
  return {
    event_type: event?.event_type ?? "ASSESSMENT",
    custom_event_name: event?.custom_event_name ?? "",
    round_no: event?.round_no ? String(event.round_no) : "",
    occurred_at: toDateTimeLocalValue(event?.occurred_at ?? new Date()),
    outcome: event?.outcome ?? "PENDING",
    note: event?.note ?? "",
  };
}

function FieldLabel({
  children,
  htmlFor,
}: {
  children: React.ReactNode;
  htmlFor: string;
}) {
  return (
    <label
      className="mb-2 block text-sm font-semibold text-slate-700"
      htmlFor={htmlFor}
    >
      {children}
    </label>
  );
}

function EventForm({
  event,
  onCancel,
  onSave,
}: {
  event?: ApplicationEvent;
  onCancel: () => void;
  onSave: (payload: ApplicationEventPayload) => Promise<string | null>;
}) {
  const [draft, setDraft] = useState<ApplicationEventDraft>(() =>
    eventToDraft(event),
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const idPrefix = event ? `edit-${event.id}` : "create-event";

  async function handleSubmit(eventObject: FormEvent<HTMLFormElement>) {
    eventObject.preventDefault();
    setFormError(null);
    const result = buildApplicationEventPayload(draft);
    if (result.data === null) {
      setFormError(result.error);
      return;
    }

    setIsSubmitting(true);
    const saveError = await onSave(result.data);
    if (saveError) {
      setFormError(saveError);
    }
    setIsSubmitting(false);
  }

  function updateStage(stage: ApplicationStage) {
    setDraft((current) => ({
      ...current,
      event_type: stage,
      custom_event_name: stage === "OTHER" ? current.custom_event_name : "",
      round_no:
        stage === "INTERVIEW" ? current.round_no || "1" : "",
    }));
  }

  return (
    <form
      className="rounded-3xl border border-blue-100 bg-blue-50/50 p-5 sm:p-6"
      onSubmit={handleSubmit}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
            {event ? "Edit milestone" : "New milestone"}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-slate-950">
            {event ? "修改时间线节点" : "添加时间线节点"}
          </h3>
        </div>
        <button
          className="text-sm font-semibold text-slate-500 hover:text-slate-800"
          disabled={isSubmitting}
          onClick={onCancel}
          type="button"
        >
          取消
        </button>
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <div>
          <FieldLabel htmlFor={`${idPrefix}-type`}>节点类型</FieldLabel>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            id={`${idPrefix}-type`}
            onChange={(input) =>
              updateStage(input.target.value as ApplicationStage)
            }
            value={draft.event_type}
          >
            {APPLICATION_STAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <FieldLabel htmlFor={`${idPrefix}-occurred-at`}>发生时间</FieldLabel>
          <input
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            id={`${idPrefix}-occurred-at`}
            onChange={(input) =>
              setDraft((current) => ({
                ...current,
                occurred_at: input.target.value,
              }))
            }
            required
            type="datetime-local"
            value={draft.occurred_at}
          />
        </div>

        {draft.event_type === "INTERVIEW" ? (
          <div>
            <FieldLabel htmlFor={`${idPrefix}-round`}>面试轮次</FieldLabel>
            <input
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              id={`${idPrefix}-round`}
              max={32767}
              min={1}
              onChange={(input) =>
                setDraft((current) => ({
                  ...current,
                  round_no: input.target.value,
                }))
              }
              required
              type="number"
              value={draft.round_no}
            />
          </div>
        ) : null}

        {draft.event_type === "OTHER" ? (
          <div>
            <FieldLabel htmlFor={`${idPrefix}-custom-name`}>
              自定义节点名称
            </FieldLabel>
            <input
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              id={`${idPrefix}-custom-name`}
              maxLength={200}
              onChange={(input) =>
                setDraft((current) => ({
                  ...current,
                  custom_event_name: input.target.value,
                }))
              }
              placeholder="例如：HR 沟通、案例分析"
              required
              type="text"
              value={draft.custom_event_name}
            />
          </div>
        ) : null}

        <div>
          <FieldLabel htmlFor={`${idPrefix}-outcome`}>节点结果</FieldLabel>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            id={`${idPrefix}-outcome`}
            onChange={(input) =>
              setDraft((current) => ({
                ...current,
                outcome: input.target.value as
                  | ""
                  | ApplicationEventOutcome,
              }))
            }
            value={draft.outcome}
          >
            <option value="">暂不记录</option>
            {APPLICATION_OUTCOME_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <FieldLabel htmlFor={`${idPrefix}-note`}>备注（可选）</FieldLabel>
          <textarea
            className="min-h-24 w-full resize-y rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            id={`${idPrefix}-note`}
            onChange={(input) =>
              setDraft((current) => ({
                ...current,
                note: input.target.value,
              }))
            }
            placeholder="记录时间、准备事项或结果说明"
            value={draft.note}
          />
        </div>
      </div>

      {formError ? (
        <p className="mt-4 text-sm text-red-700" role="alert">
          {formError}
        </p>
      ) : null}

      <div className="mt-5 flex justify-end">
        <button
          className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "正在保存…" : event ? "保存修改" : "添加节点"}
        </button>
      </div>
    </form>
  );
}

function StatusForm({
  application,
  onCancel,
  onSave,
}: {
  application: ApplicationData;
  onCancel: () => void;
  onSave: (payload: ApplicationStatusPayload) => Promise<string | null>;
}) {
  const [processStatus, setProcessStatus] = useState<ApplicationStatus>(
    application.process_status,
  );
  const [currentStage, setCurrentStage] = useState<ApplicationStage>(
    application.current_stage,
  );
  const [currentRound, setCurrentRound] = useState(
    application.current_round ? String(application.current_round) : "",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    const result = buildApplicationStatusPayload(
      processStatus,
      currentStage,
      currentRound,
    );
    if (result.data === null) {
      setFormError(result.error);
      return;
    }
    setIsSubmitting(true);
    const saveError = await onSave(result.data);
    if (saveError) {
      setFormError(saveError);
    }
    setIsSubmitting(false);
  }

  function updateProcessStatus(status: ApplicationStatus) {
    setProcessStatus(status);
    if (status === "OFFER") {
      setCurrentStage("OFFER");
      setCurrentRound("");
    }
  }

  return (
    <form
      className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4"
      onSubmit={handleSubmit}
    >
      <div>
        <FieldLabel htmlFor="process-status">流程状态</FieldLabel>
        <select
          className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          id="process-status"
          onChange={(input) =>
            updateProcessStatus(input.target.value as ApplicationStatus)
          }
          value={processStatus}
        >
          <option value="ACTIVE">进行中</option>
          <option value="REJECTED">已淘汰</option>
          <option value="OFFER">Offer</option>
          <option value="WITHDRAWN">主动放弃</option>
        </select>
      </div>

      {processStatus !== "ACTIVE" ? (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <div>
            <FieldLabel htmlFor="terminal-stage">结束时阶段</FieldLabel>
            <select
              className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              id="terminal-stage"
              onChange={(input) => {
                const stage = input.target.value as ApplicationStage;
                setCurrentStage(stage);
                if (stage !== "INTERVIEW") {
                  setCurrentRound("");
                }
              }}
              value={currentStage}
            >
              {APPLICATION_STAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {currentStage === "INTERVIEW" ? (
            <div>
              <FieldLabel htmlFor="terminal-round">面试轮次</FieldLabel>
              <input
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                id="terminal-round"
                max={32767}
                min={1}
                onChange={(input) => setCurrentRound(input.target.value)}
                required
                type="number"
                value={currentRound}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {formError ? (
        <p className="mt-4 text-sm text-red-700" role="alert">
          {formError}
        </p>
      ) : null}

      <div className="mt-5 flex justify-end gap-3">
        <button
          className="px-3 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
          disabled={isSubmitting}
          onClick={onCancel}
          type="button"
        >
          取消
        </button>
        <button
          className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "正在更新…" : "确认更新"}
        </button>
      </div>
    </form>
  );
}

function Timeline({
  application,
  deletingEventId,
  onDelete,
  onEdit,
}: {
  application: ApplicationData;
  deletingEventId: string | null;
  onDelete: (event: ApplicationEvent) => void;
  onEdit: (event: ApplicationEvent) => void;
}) {
  if (application.events.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center">
        <h3 className="font-semibold text-slate-950">时间线暂无节点</h3>
        <p className="mt-2 text-sm text-slate-500">
          添加一个节点，开始记录这次招聘流程。
        </p>
      </div>
    );
  }

  return (
    <ol className="space-y-0">
      {application.events.map((event, index) => {
        const isLast = index === application.events.length - 1;
        return (
          <li className="grid grid-cols-[4.75rem_1.25rem_minmax(0,1fr)] gap-3" key={event.id}>
            <div className="pt-1 text-right">
              <p className="text-xs font-semibold text-slate-700">
                {formatApplicationDate(event.occurred_at).slice(5)}
              </p>
              <p className="mt-1 text-xs text-slate-400">
                {formatApplicationTime(event.occurred_at)}
              </p>
            </div>
            <div className="flex flex-col items-center">
              <span className="mt-1.5 h-3 w-3 shrink-0 rounded-full border-2 border-white bg-blue-600 shadow-[0_0_0_3px_rgb(219_234_254)]" />
              {!isLast ? (
                <span className="mt-2 h-full min-h-20 w-px bg-slate-200" />
              ) : null}
            </div>
            <article className={`min-w-0 pb-7 ${isLast ? "pb-0" : ""}`}>
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-slate-950">
                        {getApplicationEventLabel(event)}
                      </h3>
                      {event.outcome ? (
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${OUTCOME_CLASS_NAMES[event.outcome]}`}
                        >
                          {getApplicationOutcomeLabel(event.outcome)}
                        </span>
                      ) : null}
                    </div>
                    {event.note ? (
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                        {event.note}
                      </p>
                    ) : (
                      <p className="mt-2 text-sm text-slate-400">暂无备注</p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-3 text-sm font-semibold">
                    <button
                      className="text-blue-700 hover:text-blue-800"
                      onClick={() => onEdit(event)}
                      type="button"
                    >
                      修改
                    </button>
                    <button
                      className="text-red-600 hover:text-red-700 disabled:opacity-50"
                      disabled={deletingEventId === event.id}
                      onClick={() => onDelete(event)}
                      type="button"
                    >
                      {deletingEventId === event.id ? "删除中…" : "删除"}
                    </button>
                  </div>
                </div>
              </div>
            </article>
          </li>
        );
      })}
    </ol>
  );
}

export function ApplicationTimeline({ applicationId }: { applicationId: string }) {
  const router = useRouter();
  const [application, setApplication] = useState<ApplicationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [eventFormMode, setEventFormMode] = useState<EventFormMode | null>(null);
  const [isEditingStatus, setIsEditingStatus] = useState(false);
  const [deletingEventId, setDeletingEventId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const handleUnauthorized = useCallback(() => {
    router.replace("/login");
    router.refresh();
  }, [router]);

  useEffect(() => {
    let cancelled = false;

    void apiRequest<ApplicationEnvelope>(`/applications/${applicationId}`)
      .then((response) => {
        if (!cancelled) {
          setApplication(response.data);
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiError && error.status === 401) {
          handleUnauthorized();
          return;
        }
        setLoadError(
          requestMessage(error, "投递详情加载失败，请稍后重试。"),
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
  }, [applicationId, handleUnauthorized, loadAttempt]);

  async function refreshApplication() {
    const response = await apiRequest<ApplicationEnvelope>(
      `/applications/${applicationId}`,
    );
    setApplication(response.data);
  }

  async function saveEvent(
    payload: ApplicationEventPayload,
  ): Promise<string | null> {
    setActionMessage(null);
    try {
      if (eventFormMode?.kind === "edit") {
        await apiRequest<ApplicationEventEnvelope>(
          `/application-events/${eventFormMode.event.id}`,
          { method: "PUT", body: JSON.stringify(payload) },
        );
      } else {
        await apiRequest<ApplicationEventEnvelope>(
          `/applications/${applicationId}/events`,
          { method: "POST", body: JSON.stringify(payload) },
        );
      }
      await refreshApplication();
      setEventFormMode(null);
      setActionMessage(
        eventFormMode?.kind === "edit" ? "节点已更新。" : "节点已添加。",
      );
      return null;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return "登录状态已失效，正在跳转。";
      }
      return requestMessage(error, "节点保存失败，请稍后重试。");
    }
  }

  async function deleteEvent(event: ApplicationEvent) {
    const eventLabel = getApplicationEventLabel(event);
    if (
      !window.confirm(
        `确定删除“${eventLabel}”节点吗？删除后会重新计算当前阶段。`,
      )
    ) {
      return;
    }

    setDeletingEventId(event.id);
    setActionMessage(null);
    try {
      await apiRequest<void>(`/application-events/${event.id}`, {
        method: "DELETE",
      });
      await refreshApplication();
      if (
        eventFormMode?.kind === "edit" &&
        eventFormMode.event.id === event.id
      ) {
        setEventFormMode(null);
      }
      setActionMessage("节点已删除，当前阶段已重新计算。");
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
      } else {
        setActionMessage(requestMessage(error, "节点删除失败，请稍后重试。"));
      }
    } finally {
      setDeletingEventId(null);
    }
  }

  async function saveStatus(
    payload: ApplicationStatusPayload,
  ): Promise<string | null> {
    setActionMessage(null);
    try {
      const response = await apiRequest<ApplicationEnvelope>(
        `/applications/${applicationId}/status`,
        { method: "PUT", body: JSON.stringify(payload) },
      );
      setApplication(response.data);
      setIsEditingStatus(false);
      setActionMessage("流程状态已更新。");
      return null;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized();
        return "登录状态已失效，正在跳转。";
      }
      return requestMessage(error, "流程状态更新失败，请稍后重试。");
    }
  }

  function retryLoad() {
    setIsLoading(true);
    setLoadError(null);
    setLoadAttempt((current) => current + 1);
  }

  if (isLoading) {
    return (
      <div
        aria-live="polite"
        className="rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center shadow-sm"
      >
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
        <p className="mt-4 text-sm text-slate-600">正在加载投递详情…</p>
      </div>
    );
  }

  if (loadError || !application) {
    return (
      <div className="rounded-3xl border border-red-200 bg-white px-6 py-14 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">
          投递详情暂时无法加载
        </h1>
        <p className="mt-3 text-sm text-red-700" role="alert">
          {loadError ?? "投递记录不存在或无法访问。"}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700"
            href="/applications"
          >
            返回投递列表
          </Link>
          <button
            className="rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white"
            onClick={retryLoad}
            type="button"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link
        className="text-sm font-semibold text-slate-500 transition hover:text-slate-900"
        href="/applications"
      >
        ← 返回投递管理
      </Link>

      <header className="mt-6 flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm font-semibold text-blue-600">
              Application timeline
            </p>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${STATUS_CLASS_NAMES[application.process_status]}`}
            >
              {getApplicationStatusLabel(application.process_status)}
            </span>
          </div>
          <h1 className="mt-2 truncate text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            {application.company_name}
          </h1>
          <p className="mt-2 text-lg text-slate-600">{application.job_title}</p>
          <p className="mt-4 text-sm text-slate-500">
            当前进度：
            <span className="font-semibold text-slate-800">
              {getApplicationProgressLabel(application)}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {application.job_id ? (
            <Link
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              href={`/jobs/${application.job_id}`}
            >
              查看职位
            </Link>
          ) : application.job_url ? (
            <a
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              href={application.job_url}
              rel="noreferrer"
              target="_blank"
            >
              查看职位 ↗
            </a>
          ) : null}
          <button
            className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
            onClick={() => {
              setIsEditingStatus(false);
              setEventFormMode({ kind: "create" });
            }}
            type="button"
          >
            + 添加节点
          </button>
        </div>
      </header>

      {actionMessage ? (
        <p
          className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-800"
          role="status"
        >
          {actionMessage}
        </p>
      ) : null}

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <main>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Hiring journey
              </p>
              <h2 className="mt-1 text-xl font-semibold text-slate-950">
                招聘流程时间线
              </h2>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
              {application.events.length} 个节点
            </span>
          </div>

          {eventFormMode ? (
            <div className="mt-5">
              <EventForm
                event={
                  eventFormMode.kind === "edit"
                    ? eventFormMode.event
                    : undefined
                }
                key={
                  eventFormMode.kind === "edit"
                    ? eventFormMode.event.id
                    : "create"
                }
                onCancel={() => setEventFormMode(null)}
                onSave={saveEvent}
              />
            </div>
          ) : null}

          <div className="mt-7">
            <Timeline
              application={application}
              deletingEventId={deletingEventId}
              onDelete={(event) => void deleteEvent(event)}
              onEdit={(event) => {
                setActionMessage(null);
                setEventFormMode({ kind: "edit", event });
              }}
            />
          </div>
        </main>

        <aside className="space-y-5">
          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold text-slate-950">流程概览</h2>
              <button
                className="text-sm font-semibold text-blue-700 hover:text-blue-800"
                onClick={() => {
                  setEventFormMode(null);
                  setIsEditingStatus((current) => !current);
                }}
                type="button"
              >
                {isEditingStatus ? "收起" : "更新状态"}
              </button>
            </div>
            <dl className="mt-5 space-y-4 text-sm">
              <div className="flex items-start justify-between gap-4">
                <dt className="text-slate-500">当前阶段</dt>
                <dd className="text-right font-semibold text-slate-900">
                  {getApplicationStageLabel(
                    application.current_stage,
                    application.current_round,
                  )}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt className="text-slate-500">流程状态</dt>
                <dd className="text-right font-semibold text-slate-900">
                  {getApplicationStatusLabel(application.process_status)}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt className="text-slate-500">投递日期</dt>
                <dd className="text-right font-semibold text-slate-900">
                  {formatApplicationDate(application.applied_at)}
                </dd>
              </div>
              <div className="flex items-start justify-between gap-4">
                <dt className="text-slate-500">最后更新</dt>
                <dd className="text-right font-semibold text-slate-900">
                  {formatApplicationUpdatedAt(application.updated_at)}
                </dd>
              </div>
            </dl>

            {isEditingStatus ? (
              <StatusForm
                application={application}
                key={`${application.id}-${application.updated_at}`}
                onCancel={() => setIsEditingStatus(false)}
                onSave={saveStatus}
              />
            ) : null}
          </section>

          {application.note ? (
            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold text-slate-950">投递备注</h2>
              <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                {application.note}
              </p>
            </section>
          ) : null}

          <section className="rounded-3xl bg-slate-950 p-5 text-white shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-300">
              Flexible timeline
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              招聘流程不固定。按实际顺序添加节点，系统会根据最新时间自动更新当前阶段。
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
