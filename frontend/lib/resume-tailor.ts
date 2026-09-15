import type { ResumeMasterData } from "./resume.ts";

export type TailorEvidenceReference = {
  source_field: "description" | "achievements";
  source_quote: string;
};

export type TailoredBullet = {
  text: string;
  evidence_refs: TailorEvidenceReference[];
};

export type TailoredSourceItem = {
  source_id: string;
  include: boolean;
  order: number | null;
  bullets: TailoredBullet[];
};

export type ImprovementStatus =
  | "NO_EVIDENCE"
  | "WEAK_EVIDENCE"
  | "PARTIAL_MATCH";

export type ImprovementSuggestion = {
  job_requirement: string;
  current_status: ImprovementStatus;
  suggestion: string;
  do_not_claim_yet: true;
};

export type ResumeTailorOutput = {
  professional_summary: string | null;
  experiences: TailoredSourceItem[];
  projects: TailoredSourceItem[];
  skill_order: string[];
  improvement_suggestions: ImprovementSuggestion[];
  warnings: string[];
};

export type ResumeTailorDraftData = {
  job_id: string;
  match_result_id: string;
  resume_master_id: string;
  company_name: string;
  job_title: string;
  source_resume_snapshot: ResumeMasterData;
  draft: ResumeTailorOutput;
  skill_name: string;
  prompt_version: string;
  model: string;
  attempts: number;
};

export type ResumeTailorDraftEnvelope = {
  data: ResumeTailorDraftData;
};

export function cloneTailorOutput(
  output: ResumeTailorOutput,
): ResumeTailorOutput {
  return {
    ...output,
    experiences: output.experiences.map((item) => ({
      ...item,
      bullets: item.bullets.map((bullet) => ({
        ...bullet,
        evidence_refs: bullet.evidence_refs.map((reference) => ({
          ...reference,
        })),
      })),
    })),
    projects: output.projects.map((item) => ({
      ...item,
      bullets: item.bullets.map((bullet) => ({
        ...bullet,
        evidence_refs: bullet.evidence_refs.map((reference) => ({
          ...reference,
        })),
      })),
    })),
    skill_order: [...output.skill_order],
    improvement_suggestions: output.improvement_suggestions.map((item) => ({
      ...item,
    })),
    warnings: [...output.warnings],
  };
}

export function getIncludedTailoredItems(
  items: TailoredSourceItem[],
): TailoredSourceItem[] {
  return items
    .filter((item) => item.include)
    .toSorted((left, right) => (left.order ?? 0) - (right.order ?? 0));
}

export function reorderIncludedItems(
  items: TailoredSourceItem[],
  sourceId: string,
  direction: -1 | 1,
): TailoredSourceItem[] {
  const included = getIncludedTailoredItems(items);
  const index = included.findIndex((item) => item.source_id === sourceId);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= included.length) {
    return items;
  }

  const reordered = [...included];
  [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
  const orderById = new Map(
    reordered.map((item, itemIndex) => [item.source_id, itemIndex + 1]),
  );

  return items.map((item) =>
    item.include ? { ...item, order: orderById.get(item.source_id)! } : item,
  );
}

export function moveSkill(
  skillOrder: string[],
  sourceId: string,
  direction: -1 | 1,
): string[] {
  const index = skillOrder.indexOf(sourceId);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= skillOrder.length) {
    return skillOrder;
  }
  const next = [...skillOrder];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

export function getOrderedSkills(
  resume: ResumeMasterData,
  skillOrder: string[],
): ResumeMasterData["skills"] {
  const skillById = new Map(resume.skills.map((skill) => [skill.id, skill]));
  return skillOrder.flatMap((sourceId) => {
    const skill = skillById.get(sourceId);
    return skill ? [skill] : [];
  });
}

export function formatResumeMonth(value: string | null): string {
  if (!value) {
    return "未填写";
  }
  const [year, month] = value.split("-");
  if (!/^\d{4}$/.test(year) || !/^(0[1-9]|1[0-2])$/.test(month)) {
    return value;
  }
  return `${year}.${month}`;
}

export function formatResumePeriod(
  startDate: string | null,
  endDate: string | null,
  isCurrent = false,
): string {
  return `${formatResumeMonth(startDate)} – ${isCurrent ? "至今" : formatResumeMonth(endDate)}`;
}

export function getImprovementStatusLabel(
  status: ImprovementStatus,
): string {
  const labels: Record<ImprovementStatus, string> = {
    NO_EVIDENCE: "暂无证据",
    WEAK_EVIDENCE: "证据较弱",
    PARTIAL_MATCH: "部分匹配",
  };
  return labels[status];
}
