export type ApplicationStage =
  | "APPLICATION"
  | "RESUME_SCREEN"
  | "ASSESSMENT"
  | "WRITTEN_TEST"
  | "AI_INTERVIEW"
  | "INTERVIEW"
  | "OFFER"
  | "OTHER";

export type ApplicationStatus =
  | "ACTIVE"
  | "REJECTED"
  | "OFFER"
  | "WITHDRAWN";

export type ApplicationEventOutcome =
  | "PENDING"
  | "PASSED"
  | "FAILED"
  | "COMPLETED"
  | "CANCELLED";

export type ApplicationListItem = {
  id: string;
  job_id: string | null;
  resume_version_id: string | null;
  company_name: string;
  job_title: string;
  job_url: string | null;
  applied_at: string;
  current_stage: ApplicationStage;
  current_round: number | null;
  process_status: ApplicationStatus;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationListEnvelope = {
  data: ApplicationListItem[];
};

export type ApplicationEvent = {
  id: string;
  application_id: string;
  event_type: ApplicationStage;
  custom_event_name: string | null;
  round_no: number | null;
  occurred_at: string;
  outcome: ApplicationEventOutcome | null;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type ApplicationData = ApplicationListItem & {
  events: ApplicationEvent[];
};

export type ApplicationEnvelope = {
  data: ApplicationData;
};

export type ApplicationEventEnvelope = {
  data: ApplicationEvent;
};

export type ApplicationEventDraft = {
  event_type: ApplicationStage;
  custom_event_name: string;
  round_no: string;
  occurred_at: string;
  outcome: "" | ApplicationEventOutcome;
  note: string;
};

export type ApplicationEventPayload = {
  event_type: ApplicationStage;
  custom_event_name: string | null;
  round_no: number | null;
  occurred_at: string;
  outcome: ApplicationEventOutcome | null;
  note: string | null;
};

export type ApplicationStatusPayload = {
  process_status: ApplicationStatus;
  current_stage?: ApplicationStage;
  current_round?: number;
};

type PayloadResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };

export type ApplicationFilter = "ALL" | ApplicationStatus;

export const APPLICATION_FILTERS: ReadonlyArray<{
  value: ApplicationFilter;
  label: string;
}> = [
  { value: "ALL", label: "全部" },
  { value: "ACTIVE", label: "进行中" },
  { value: "REJECTED", label: "已淘汰" },
  { value: "OFFER", label: "Offer" },
  { value: "WITHDRAWN", label: "主动放弃" },
];

export const APPLICATION_STAGE_OPTIONS: ReadonlyArray<{
  value: ApplicationStage;
  label: string;
}> = [
  { value: "APPLICATION", label: "已投递" },
  { value: "RESUME_SCREEN", label: "简历筛选" },
  { value: "ASSESSMENT", label: "在线测评" },
  { value: "WRITTEN_TEST", label: "笔试" },
  { value: "AI_INTERVIEW", label: "AI 面试" },
  { value: "INTERVIEW", label: "面试" },
  { value: "OFFER", label: "Offer" },
  { value: "OTHER", label: "自定义节点" },
];

export const APPLICATION_OUTCOME_OPTIONS: ReadonlyArray<{
  value: ApplicationEventOutcome;
  label: string;
}> = [
  { value: "PENDING", label: "待确认" },
  { value: "PASSED", label: "已通过" },
  { value: "FAILED", label: "未通过" },
  { value: "COMPLETED", label: "已完成" },
  { value: "CANCELLED", label: "已取消" },
];

const APPLICATION_STAGE_LABELS: Record<
  Exclude<ApplicationStage, "INTERVIEW">,
  string
> = {
  APPLICATION: "已投递",
  RESUME_SCREEN: "简历筛选",
  ASSESSMENT: "在线测评",
  WRITTEN_TEST: "笔试",
  AI_INTERVIEW: "AI 面试",
  OFFER: "Offer",
  OTHER: "其他环节",
};

const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  ACTIVE: "进行中",
  REJECTED: "已淘汰",
  OFFER: "Offer",
  WITHDRAWN: "主动放弃",
};

const APPLICATION_OUTCOME_LABELS: Record<ApplicationEventOutcome, string> = {
  PENDING: "待确认",
  PASSED: "已通过",
  FAILED: "未通过",
  COMPLETED: "已完成",
  CANCELLED: "已取消",
};

const INTERVIEW_ROUND_LABELS: Record<number, string> = {
  1: "一面",
  2: "二面",
  3: "三面",
  4: "四面",
  5: "五面",
};

export function getApplicationStageLabel(
  stage: ApplicationStage,
  currentRound: number | null,
): string {
  if (stage !== "INTERVIEW") {
    return APPLICATION_STAGE_LABELS[stage];
  }
  if (currentRound === null) {
    return "面试";
  }
  return INTERVIEW_ROUND_LABELS[currentRound] ?? `第 ${currentRound} 轮面试`;
}

export function getApplicationStatusLabel(status: ApplicationStatus): string {
  return APPLICATION_STATUS_LABELS[status];
}

export function getApplicationEventLabel(event: ApplicationEvent): string {
  if (event.event_type === "OTHER") {
    return event.custom_event_name ?? "自定义节点";
  }
  return getApplicationStageLabel(event.event_type, event.round_no);
}

export function getApplicationOutcomeLabel(
  outcome: ApplicationEventOutcome,
): string {
  return APPLICATION_OUTCOME_LABELS[outcome];
}

export function getApplicationProgressLabel(
  application: Pick<
    ApplicationListItem,
    "current_stage" | "current_round" | "process_status"
  >,
): string {
  const stage = getApplicationStageLabel(
    application.current_stage,
    application.current_round,
  );
  if (application.process_status === "REJECTED") {
    return `${stage}淘汰`;
  }
  if (application.process_status === "OFFER") {
    return "已获 Offer";
  }
  if (application.process_status === "WITHDRAWN") {
    return `${stage}主动放弃`;
  }
  return stage;
}

export function filterApplications(
  applications: ApplicationListItem[],
  filter: ApplicationFilter,
): ApplicationListItem[] {
  if (filter === "ALL") {
    return applications;
  }
  return applications.filter(
    (application) => application.process_status === filter,
  );
}

export function getApplicationFilterCounts(
  applications: ApplicationListItem[],
): Record<ApplicationFilter, number> {
  const counts: Record<ApplicationFilter, number> = {
    ALL: applications.length,
    ACTIVE: 0,
    REJECTED: 0,
    OFFER: 0,
    WITHDRAWN: 0,
  };

  for (const application of applications) {
    counts[application.process_status] += 1;
  }
  return counts;
}

function dateParts(value: string): Intl.DateTimeFormatPart[] | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
}

function partValue(parts: Intl.DateTimeFormatPart[], type: string): string {
  return parts.find((part) => part.type === type)?.value ?? "";
}

export function formatApplicationDate(value: string): string {
  const parts = dateParts(value);
  if (!parts) {
    return "日期未知";
  }
  return `${partValue(parts, "year")}-${partValue(parts, "month")}-${partValue(parts, "day")}`;
}

export function formatApplicationUpdatedAt(value: string): string {
  const parts = dateParts(value);
  if (!parts) {
    return "时间未知";
  }
  return `${partValue(parts, "month")}-${partValue(parts, "day")} ${partValue(parts, "hour")}:${partValue(parts, "minute")}`;
}

export function formatApplicationTime(value: string): string {
  const parts = dateParts(value);
  if (!parts) {
    return "时间未知";
  }
  return `${partValue(parts, "hour")}:${partValue(parts, "minute")}`;
}

export function toDateTimeLocalValue(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function positiveRound(value: string): number | null {
  const round = Number(value);
  if (!Number.isInteger(round) || round < 1 || round > 32767) {
    return null;
  }
  return round;
}

export function buildApplicationEventPayload(
  draft: ApplicationEventDraft,
): PayloadResult<ApplicationEventPayload> {
  const occurredAt = new Date(draft.occurred_at);
  if (!draft.occurred_at || Number.isNaN(occurredAt.getTime())) {
    return { data: null, error: "请选择有效的发生时间。" };
  }

  let roundNo: number | null = null;
  if (draft.event_type === "INTERVIEW") {
    roundNo = positiveRound(draft.round_no);
    if (roundNo === null) {
      return { data: null, error: "面试节点必须填写有效轮次。" };
    }
  }

  const customEventName = draft.custom_event_name.trim();
  if (draft.event_type === "OTHER" && !customEventName) {
    return { data: null, error: "自定义节点必须填写名称。" };
  }

  return {
    data: {
      event_type: draft.event_type,
      custom_event_name:
        draft.event_type === "OTHER" ? customEventName : null,
      round_no: roundNo,
      occurred_at: occurredAt.toISOString(),
      outcome: draft.outcome || null,
      note: draft.note.trim() || null,
    },
    error: null,
  };
}

export function buildApplicationStatusPayload(
  processStatus: ApplicationStatus,
  currentStage: ApplicationStage,
  currentRound: string,
): PayloadResult<ApplicationStatusPayload> {
  if (processStatus === "ACTIVE") {
    return { data: { process_status: "ACTIVE" }, error: null };
  }

  const payload: ApplicationStatusPayload = {
    process_status: processStatus,
    current_stage: currentStage,
  };
  if (currentStage === "INTERVIEW") {
    const round = positiveRound(currentRound);
    if (round === null) {
      return { data: null, error: "面试阶段必须填写有效轮次。" };
    }
    payload.current_round = round;
  }
  return { data: payload, error: null };
}
