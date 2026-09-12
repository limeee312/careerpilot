export type ManualJobDraft = {
  clientKey: string;
  company_name: string;
  title: string;
  location: string;
  department: string;
  source_url: string;
  raw_jd: string;
};

export type JobBatchDraft = {
  name: string;
  jobs: ManualJobDraft[];
};

export type JobInputPayload = {
  company_name: string;
  title: string;
  location: string | null;
  department: string | null;
  source_url: string | null;
  raw_jd: string;
};

export type JobBatchPayload = {
  name: string | null;
  jobs: JobInputPayload[];
};

export type JobBatchData = {
  id: string;
  name: string | null;
  status: "DRAFT" | "PROCESSING" | "COMPLETED" | "PARTIAL_FAILED" | "FAILED";
  total_jobs: number;
  successful_jobs: number;
  failed_jobs: number;
  jobs: Array<JobInputPayload & { id: string; created_at: string; updated_at: string }>;
  created_at: string;
  updated_at: string;
};

export type JobBatchEnvelope = {
  data: JobBatchData;
};

export type JobField = Exclude<keyof ManualJobDraft, "clientKey">;

export type JobBatchValidationError = {
  jobIndex: number | null;
  field: JobField | "name" | "jobs";
  message: string;
};

function createClientKey(): string {
  return globalThis.crypto.randomUUID();
}

function nullable(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

export function createEmptyManualJob(): ManualJobDraft {
  return {
    clientKey: createClientKey(),
    company_name: "",
    title: "",
    location: "",
    department: "",
    source_url: "",
    raw_jd: "",
  };
}

export function createEmptyJobBatch(): JobBatchDraft {
  return {
    name: "",
    jobs: [createEmptyManualJob()],
  };
}

export function buildJobBatchPayload(draft: JobBatchDraft): JobBatchPayload {
  return {
    name: nullable(draft.name),
    jobs: draft.jobs.map((job) => ({
      company_name: job.company_name.trim(),
      title: job.title.trim(),
      location: nullable(job.location),
      department: nullable(job.department),
      source_url: nullable(job.source_url),
      raw_jd: job.raw_jd.trim(),
    })),
  };
}

function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

export function validateJobBatch(
  draft: JobBatchDraft,
): JobBatchValidationError | null {
  if (draft.name.trim().length > 200) {
    return {
      jobIndex: null,
      field: "name",
      message: "批次名称不能超过 200 个字符。",
    };
  }

  if (draft.jobs.length < 1 || draft.jobs.length > 5) {
    return {
      jobIndex: null,
      field: "jobs",
      message: "每个批次需要包含 1–5 个职位。",
    };
  }

  for (const [index, job] of draft.jobs.entries()) {
    if (!job.company_name.trim()) {
      return {
        jobIndex: index,
        field: "company_name",
        message: `职位 ${index + 1} 需要填写公司名称。`,
      };
    }
    if (!job.title.trim()) {
      return {
        jobIndex: index,
        field: "title",
        message: `职位 ${index + 1} 需要填写职位名称。`,
      };
    }
    if (job.source_url.trim() && !isHttpUrl(job.source_url.trim())) {
      return {
        jobIndex: index,
        field: "source_url",
        message: `职位 ${index + 1} 的职位链接需要以 http:// 或 https:// 开头。`,
      };
    }
    if (job.raw_jd.trim().length < 50) {
      return {
        jobIndex: index,
        field: "raw_jd",
        message: `职位 ${index + 1} 的 JD 至少需要 50 个字符。`,
      };
    }
  }

  return null;
}
