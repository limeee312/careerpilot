import type {
  ResumeTailorDraftData,
  ResumeTailorOutput,
} from "./resume-tailor.ts";

export type ResumeVersionStatus = "DRAFT" | "SAVED";

export type ResumeVersionListItem = {
  id: string;
  resume_master_id: string;
  job_id: string;
  match_result_id: string | null;
  name: string;
  status: ResumeVersionStatus;
  company_name: string;
  job_title: string;
  prompt_version: string;
  model: string;
  created_at: string;
  updated_at: string;
};

export type ResumeVersionData = ResumeVersionListItem & {
  content: Record<string, unknown>;
  source_resume_snapshot: ResumeTailorDraftData["source_resume_snapshot"];
  source_job_snapshot: Record<string, unknown>;
};

export type ResumeVersionListEnvelope = {
  data: ResumeVersionListItem[];
};

export type ResumeVersionEnvelope = {
  data: ResumeVersionData;
};

export type ResumeVersionSavePayload = {
  match_result_id: string;
  draft: ResumeTailorOutput;
  prompt_version: string;
  model: string;
};

export function validateTailorDraftForSave(
  draft: ResumeTailorOutput,
): string | null {
  for (const item of [...draft.experiences, ...draft.projects]) {
    if (
      item.include &&
      item.bullets.some((bullet) => bullet.text.trim().length === 0)
    ) {
      return "已保留的经历和项目不能包含空白要点。";
    }
  }
  return null;
}

export function buildResumeVersionPayload(
  source: ResumeTailorDraftData,
  draft: ResumeTailorOutput,
): ResumeVersionSavePayload {
  return {
    match_result_id: source.match_result_id,
    draft: {
      ...draft,
      professional_summary: draft.professional_summary?.trim() || null,
      experiences: draft.experiences.map((item) => ({
        ...item,
        bullets: item.bullets.map((bullet) => ({
          ...bullet,
          text: bullet.text.trim(),
        })),
      })),
      projects: draft.projects.map((item) => ({
        ...item,
        bullets: item.bullets.map((bullet) => ({
          ...bullet,
          text: bullet.text.trim(),
        })),
      })),
    },
    prompt_version: source.prompt_version,
    model: source.model,
  };
}
