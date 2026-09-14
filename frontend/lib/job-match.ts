export type JobMatchBatchStatus =
  | "DRAFT"
  | "PROCESSING"
  | "COMPLETED"
  | "PARTIAL_FAILED"
  | "FAILED";

export type JobAnalysisStatus =
  | "PENDING"
  | "PARSING"
  | "MATCHING"
  | "COMPLETED"
  | "FAILED";

export type EligibilityStatus = "PASS" | "WARN" | "FAIL";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export type RecommendationLevel =
  | "BLOCKED"
  | "PRIORITY"
  | "STRONG"
  | "SELECTIVE"
  | "LOW";

export type MatchResultSummary = {
  id: string;
  rank: number | null;
  near_tie_group: number | null;
  is_tied: boolean;
  eligibility_status: EligibilityStatus;
  total_score: string;
  display_score: number;
  confidence_score: string;
  confidence_level: ConfidenceLevel;
  recommendation_level: RecommendationLevel;
  recommendation: string;
  created_at: string;
};

export type JobMatchResultItem = {
  job_id: string;
  company_name: string;
  title: string;
  location: string | null;
  department: string | null;
  source_url: string | null;
  analysis_status: JobAnalysisStatus;
  error_code: string | null;
  result: MatchResultSummary | null;
};

export type JobMatchBatchData = {
  id: string;
  name: string | null;
  status: JobMatchBatchStatus;
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  jobs: JobMatchResultItem[];
  created_at: string;
  updated_at: string;
};

export type JobMatchBatchEnvelope = {
  data: JobMatchBatchData;
};

export type MatchProgress = {
  resolvedJobs: number;
  percent: number;
};

export type AnalysisStepState = "waiting" | "active" | "complete";

export function isTerminalBatchStatus(status: JobMatchBatchStatus): boolean {
  return (
    status === "COMPLETED" ||
    status === "PARTIAL_FAILED" ||
    status === "FAILED"
  );
}

export function getMatchProgress(batch: JobMatchBatchData): MatchProgress {
  const resolvedJobs = Math.min(
    batch.total_jobs,
    batch.successful_jobs + batch.failed_jobs,
  );
  return {
    resolvedJobs,
    percent:
      batch.total_jobs > 0
        ? Math.round((resolvedJobs / batch.total_jobs) * 100)
        : 0,
  };
}

export function getAnalysisSteps(status: JobAnalysisStatus): {
  parsing: AnalysisStepState;
  matching: AnalysisStepState;
} {
  if (status === "COMPLETED") {
    return { parsing: "complete", matching: "complete" };
  }
  if (status === "MATCHING") {
    return { parsing: "complete", matching: "active" };
  }
  if (status === "PARSING") {
    return { parsing: "active", matching: "waiting" };
  }
  return { parsing: "waiting", matching: "waiting" };
}

export function getAnalysisStatusLabel(status: JobAnalysisStatus): string {
  const labels: Record<JobAnalysisStatus, string> = {
    PENDING: "等待分析",
    PARSING: "正在解析 JD",
    MATCHING: "正在匹配简历证据",
    COMPLETED: "分析完成",
    FAILED: "分析失败",
  };
  return labels[status];
}

export function getBatchStatusLabel(status: JobMatchBatchStatus): string {
  const labels: Record<JobMatchBatchStatus, string> = {
    DRAFT: "准备分析",
    PROCESSING: "分析进行中",
    COMPLETED: "分析完成",
    PARTIAL_FAILED: "部分完成",
    FAILED: "分析失败",
  };
  return labels[status];
}

export function getEligibilityLabel(status: EligibilityStatus): string {
  const labels: Record<EligibilityStatus, string> = {
    PASS: "硬性条件通过",
    WARN: "条件待核实",
    FAIL: "存在硬性条件冲突",
  };
  return labels[status];
}

export function getConfidenceLabel(level: ConfidenceLevel): string {
  const labels: Record<ConfidenceLevel, string> = {
    HIGH: "证据充分",
    MEDIUM: "证据中等",
    LOW: "证据有限",
  };
  return labels[level];
}

export function getRankLabel(result: MatchResultSummary): string {
  if (result.rank === null) {
    return "不参与排序";
  }
  return result.is_tied ? `并列第 ${result.rank}` : `第 ${result.rank}`;
}

export function prepareBatchForAnalysis(
  batch: JobMatchBatchData,
): JobMatchBatchData {
  return {
    ...batch,
    status: "PROCESSING",
    successful_jobs: 0,
    failed_jobs: 0,
    jobs: batch.jobs.map((job) => ({
      ...job,
      analysis_status: "PENDING",
      error_code: null,
      result: null,
    })),
  };
}
