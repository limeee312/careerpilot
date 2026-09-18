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
