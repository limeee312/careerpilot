import type {
  ConfidenceLevel,
  EligibilityStatus,
  RecommendationLevel,
} from "./job-match.ts";

export type MatchDimension =
  | "RESPONSIBILITY"
  | "TOOLS_METHODS"
  | "BUSINESS_DOMAIN"
  | "OWNERSHIP"
  | "OUTCOME"
  | "COMMUNICATION";

export type RequirementType = "HARD" | "CORE" | "STANDARD" | "PREFERRED";
export type AssessmentStatus =
  | "MATCHED"
  | "PARTIAL"
  | "CONFIRMED_GAP"
  | "UNKNOWN";
export type EvidenceGrade = "A" | "B" | "C" | "X";
export type EvidenceSourceType =
  | "education"
  | "experience"
  | "project"
  | "skill"
  | "summary";
export type GapImportance = "HIGH" | "MEDIUM" | "LOW";

export type ResumeEvidence = {
  source_type: EvidenceSourceType | null;
  source_id: string | null;
  source_quote: string | null;
};

export type JobRequirement = {
  id: string;
  requirement_key: string;
  requirement_type: RequirementType;
  dimension: MatchDimension | null;
  requirement_text: string;
  source_quote: string;
  importance: 1 | 2;
};

export type HardGateDetail = {
  requirement: JobRequirement;
  status: EligibilityStatus;
  reason: string;
  evidence: ResumeEvidence[];
};

export type RequirementAssessmentDetail = {
  requirement: JobRequirement;
  match_level: number;
  evidence_grade: EvidenceGrade;
  evidence_cap: number;
  weighted_score: string;
  status: AssessmentStatus;
  reason: string;
  evidence: ResumeEvidence[];
};

export type DimensionScoreDetail = {
  dimension: MatchDimension;
  raw_score: string;
  max_score: string;
  normalized_score: string;
};

export type MatchGapDetail = {
  requirement_key: string;
  importance: GapImportance;
  gap: string;
  improvement_direction: string;
};

export type JobMatchDetailData = {
  job_id: string;
  batch_id: string;
  result_id: string;
  company_name: string;
  title: string;
  location: string | null;
  department: string | null;
  source_url: string | null;
  role_summary: string | null;
  eligibility_status: EligibilityStatus;
  total_score: string;
  display_score: number;
  confidence_score: string;
  confidence_level: ConfidenceLevel;
  recommendation_level: RecommendationLevel;
  recommendation: string;
  strengths: string[];
  gaps: MatchGapDetail[];
  dimension_scores: DimensionScoreDetail[];
  hard_gates: HardGateDetail[];
  requirement_assessments: RequirementAssessmentDetail[];
  analyzed_at: string;
};

export type JobMatchDetailEnvelope = {
  data: JobMatchDetailData;
};

export const MATCH_DIMENSIONS: MatchDimension[] = [
  "RESPONSIBILITY",
  "TOOLS_METHODS",
  "BUSINESS_DOMAIN",
  "OWNERSHIP",
  "OUTCOME",
  "COMMUNICATION",
];

export function getDimensionLabel(dimension: MatchDimension): string {
  const labels: Record<MatchDimension, string> = {
    RESPONSIBILITY: "工作职责",
    TOOLS_METHODS: "工具与方法",
    BUSINESS_DOMAIN: "业务领域",
    OWNERSHIP: "负责程度",
    OUTCOME: "结果与闭环",
    COMMUNICATION: "沟通协作",
  };
  return labels[dimension];
}

export function getDimensionCards(scores: DimensionScoreDetail[]): Array<{
  dimension: MatchDimension;
  label: string;
  score: DimensionScoreDetail | null;
}> {
  const byDimension = new Map(scores.map((score) => [score.dimension, score]));
  return MATCH_DIMENSIONS.map((dimension) => ({
    dimension,
    label: getDimensionLabel(dimension),
    score: byDimension.get(dimension) ?? null,
  }));
}

export function getAssessmentStatusLabel(status: AssessmentStatus): string {
  const labels: Record<AssessmentStatus, string> = {
    MATCHED: "已匹配",
    PARTIAL: "部分匹配",
    CONFIRMED_GAP: "明确差距",
    UNKNOWN: "证据未知",
  };
  return labels[status];
}

export function getMatchLevelLabel(level: number): string {
  const labels = ["暂无证据", "弱证据", "可迁移", "直接部分匹配", "直接强匹配"];
  return labels[level] ?? "未知等级";
}

export function getRequirementTypeLabel(type: RequirementType): string {
  const labels: Record<RequirementType, string> = {
    HARD: "硬性条件",
    CORE: "核心要求",
    STANDARD: "一般要求",
    PREFERRED: "优先条件",
  };
  return labels[type];
}

export function getEvidenceSourceLabel(
  sourceType: EvidenceSourceType | null,
): string {
  if (sourceType === null) {
    return "无直接来源";
  }
  const labels: Record<EvidenceSourceType, string> = {
    education: "教育经历",
    experience: "工作与实习",
    project: "项目经历",
    skill: "技能",
    summary: "职业概述",
  };
  return labels[sourceType];
}

export function formatDetailScore(value: string): string {
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return "N/A";
  }
  return Number.isInteger(score) ? String(score) : score.toFixed(1);
}

export function clampPercent(value: string): number {
  const score = Number(value);
  if (!Number.isFinite(score)) {
    return 0;
  }
  return Math.min(100, Math.max(0, score));
}
