export type ExperienceType = "WORK" | "INTERNSHIP" | "CAMPUS" | "OTHER";

export type ResumeBasicInfo = {
  name: string;
  phone: string;
  email: string;
  city: string;
  job_status: string;
  summary: string;
};

type DraftSection = {
  id?: string;
  clientKey: string;
};

export type EducationDraft = DraftSection & {
  school: string;
  degree: string;
  major: string;
  start_date: string;
  end_date: string;
  gpa: string;
  courses: string;
  description: string;
};

export type ExperienceDraft = DraftSection & {
  experience_type: ExperienceType;
  organization: string;
  position: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  description: string;
  achievements: string;
};

export type ProjectDraft = DraftSection & {
  name: string;
  role: string;
  start_date: string;
  end_date: string;
  background: string;
  description: string;
  achievements: string;
};

export type SkillDraft = DraftSection & {
  skill_name: string;
  skill_category: string;
  proficiency: string;
};

export type ResumeDraft = {
  basic_info: ResumeBasicInfo;
  education: EducationDraft[];
  experiences: ExperienceDraft[];
  projects: ProjectDraft[];
  skills: SkillDraft[];
};

type EducationPayload = {
  id?: string;
  school: string;
  degree: string;
  major: string;
  start_date: string;
  end_date: string;
  gpa: string | null;
  courses: string | null;
  description: string | null;
};

type ExperiencePayload = {
  id?: string;
  experience_type: ExperienceType;
  organization: string;
  position: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  description: string;
  achievements: string | null;
};

type ProjectPayload = {
  id?: string;
  name: string;
  role: string | null;
  start_date: string | null;
  end_date: string | null;
  background: string | null;
  description: string;
  achievements: string | null;
};

type SkillPayload = {
  id?: string;
  skill_name: string;
  skill_category: string | null;
  proficiency: string | null;
};

export type ResumeMasterData = {
  id: string;
  basic_info: {
    name: string | null;
    phone: string | null;
    email: string | null;
    city: string | null;
    job_status: string | null;
    summary: string | null;
  };
  education: Array<EducationPayload & { id: string }>;
  experiences: Array<ExperiencePayload & { id: string }>;
  projects: Array<ProjectPayload & { id: string }>;
  skills: Array<SkillPayload & { id: string }>;
  created_at: string;
  updated_at: string;
};

export type ResumeMasterEnvelope = {
  data: ResumeMasterData | null;
};

export type ResumePayload = {
  basic_info: {
    name: string | null;
    phone: string | null;
    email: string | null;
    city: string | null;
    job_status: string | null;
    summary: string | null;
  };
  education: EducationPayload[];
  experiences: ExperiencePayload[];
  projects: ProjectPayload[];
  skills: SkillPayload[];
};

export type CompletenessItem = {
  key: string;
  label: string;
  detail: string;
  weight: number;
  complete: boolean;
};

export type ResumeCompleteness = {
  score: number;
  items: CompletenessItem[];
  isSparse: boolean;
};

export type ResumeValidationError = {
  section: "education" | "experiences" | "projects" | "skills";
  message: string;
};

function createClientKey(): string {
  return globalThis.crypto.randomUUID();
}

function nullable(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

function required(value: string): string {
  return value.trim();
}

export function createEmptyResume(): ResumeDraft {
  return {
    basic_info: {
      name: "",
      phone: "",
      email: "",
      city: "",
      job_status: "",
      summary: "",
    },
    education: [],
    experiences: [],
    projects: [],
    skills: [],
  };
}

export function createEmptyEducation(): EducationDraft {
  return {
    clientKey: createClientKey(),
    school: "",
    degree: "",
    major: "",
    start_date: "",
    end_date: "",
    gpa: "",
    courses: "",
    description: "",
  };
}

export function createEmptyExperience(): ExperienceDraft {
  return {
    clientKey: createClientKey(),
    experience_type: "INTERNSHIP",
    organization: "",
    position: "",
    start_date: "",
    end_date: "",
    is_current: false,
    description: "",
    achievements: "",
  };
}

export function createEmptyProject(): ProjectDraft {
  return {
    clientKey: createClientKey(),
    name: "",
    role: "",
    start_date: "",
    end_date: "",
    background: "",
    description: "",
    achievements: "",
  };
}

export function createEmptySkill(): SkillDraft {
  return {
    clientKey: createClientKey(),
    skill_name: "",
    skill_category: "",
    proficiency: "",
  };
}

export function resumeDataToDraft(data: ResumeMasterData): ResumeDraft {
  return {
    basic_info: {
      name: data.basic_info.name ?? "",
      phone: data.basic_info.phone ?? "",
      email: data.basic_info.email ?? "",
      city: data.basic_info.city ?? "",
      job_status: data.basic_info.job_status ?? "",
      summary: data.basic_info.summary ?? "",
    },
    education: data.education.map((item) => ({
      ...item,
      clientKey: item.id,
      gpa: item.gpa ?? "",
      courses: item.courses ?? "",
      description: item.description ?? "",
    })),
    experiences: data.experiences.map((item) => ({
      ...item,
      clientKey: item.id,
      end_date: item.end_date ?? "",
      achievements: item.achievements ?? "",
    })),
    projects: data.projects.map((item) => ({
      ...item,
      clientKey: item.id,
      role: item.role ?? "",
      start_date: item.start_date ?? "",
      end_date: item.end_date ?? "",
      background: item.background ?? "",
      achievements: item.achievements ?? "",
    })),
    skills: data.skills.map((item) => ({
      ...item,
      clientKey: item.id,
      skill_category: item.skill_category ?? "",
      proficiency: item.proficiency ?? "",
    })),
  };
}

export function buildResumePayload(draft: ResumeDraft): ResumePayload {
  return {
    basic_info: {
      name: nullable(draft.basic_info.name),
      phone: nullable(draft.basic_info.phone),
      email: nullable(draft.basic_info.email),
      city: nullable(draft.basic_info.city),
      job_status: nullable(draft.basic_info.job_status),
      summary: nullable(draft.basic_info.summary),
    },
    education: draft.education.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      school: required(item.school),
      degree: required(item.degree),
      major: required(item.major),
      start_date: required(item.start_date),
      end_date: required(item.end_date),
      gpa: nullable(item.gpa),
      courses: nullable(item.courses),
      description: nullable(item.description),
    })),
    experiences: draft.experiences.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      experience_type: item.experience_type,
      organization: required(item.organization),
      position: required(item.position),
      start_date: required(item.start_date),
      end_date: item.is_current ? null : nullable(item.end_date),
      is_current: item.is_current,
      description: required(item.description),
      achievements: nullable(item.achievements),
    })),
    projects: draft.projects.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      name: required(item.name),
      role: nullable(item.role),
      start_date: nullable(item.start_date),
      end_date: nullable(item.end_date),
      background: nullable(item.background),
      description: required(item.description),
      achievements: nullable(item.achievements),
    })),
    skills: draft.skills.map((item) => ({
      ...(item.id ? { id: item.id } : {}),
      skill_name: required(item.skill_name),
      skill_category: nullable(item.skill_category),
      proficiency: nullable(item.proficiency),
    })),
  };
}

export function validateResume(draft: ResumeDraft): ResumeValidationError | null {
  for (const [index, item] of draft.education.entries()) {
    if (
      !item.school.trim() ||
      !item.degree.trim() ||
      !item.major.trim() ||
      !item.start_date ||
      !item.end_date
    ) {
      return {
        section: "education",
        message: `请补全第 ${index + 1} 段教育经历的必填项。`,
      };
    }
    if (item.end_date < item.start_date) {
      return {
        section: "education",
        message: `第 ${index + 1} 段教育经历的结束年月不能早于开始年月。`,
      };
    }
  }

  for (const [index, item] of draft.experiences.entries()) {
    if (
      !item.organization.trim() ||
      !item.position.trim() ||
      !item.start_date ||
      !item.description.trim()
    ) {
      return {
        section: "experiences",
        message: `请补全第 ${index + 1} 段工作或实习经历的必填项。`,
      };
    }
    if (!item.is_current && !item.end_date) {
      return {
        section: "experiences",
        message: `请填写第 ${index + 1} 段经历的结束年月，或标记为“至今”。`,
      };
    }
    if (
      !item.is_current &&
      item.end_date &&
      item.end_date < item.start_date
    ) {
      return {
        section: "experiences",
        message: `第 ${index + 1} 段经历的结束年月不能早于开始年月。`,
      };
    }
  }

  for (const [index, item] of draft.projects.entries()) {
    if (!item.name.trim() || !item.description.trim()) {
      return {
        section: "projects",
        message: `请补全第 ${index + 1} 个项目的名称和项目描述。`,
      };
    }
    if (
      item.start_date &&
      item.end_date &&
      item.end_date < item.start_date
    ) {
      return {
        section: "projects",
        message: `第 ${index + 1} 个项目的结束年月不能早于开始年月。`,
      };
    }
  }

  const skillNames = draft.skills.map((item) => item.skill_name.trim());
  if (skillNames.some((name) => !name)) {
    return { section: "skills", message: "请填写每一项技能的名称。" };
  }
  if (new Set(skillNames).size !== skillNames.length) {
    return { section: "skills", message: "同一份简历不能包含重名技能。" };
  }

  return null;
}

export function calculateResumeCompleteness(
  draft: ResumeDraft,
): ResumeCompleteness {
  const hasBasicInfo = Boolean(
    draft.basic_info.name.trim() &&
      (draft.basic_info.email.trim() || draft.basic_info.phone.trim()),
  );
  const hasWorkOrInternship = draft.experiences.some((item) =>
    ["WORK", "INTERNSHIP"].includes(item.experience_type) &&
    Boolean(
      item.organization.trim() &&
        item.position.trim() &&
        item.start_date &&
        item.description.trim(),
    ),
  );
  const hasAchievement = draft.experiences.some((item) =>
    Boolean(item.description.trim() && item.achievements.trim()),
  );

  const items: CompletenessItem[] = [
    {
      key: "basic",
      label: "基本信息",
      detail: "姓名及至少一种联系方式",
      weight: 10,
      complete: hasBasicInfo,
    },
    {
      key: "education",
      label: "教育经历",
      detail: "至少 1 段",
      weight: 20,
      complete: draft.education.some((item) =>
        Boolean(
          item.school.trim() &&
            item.degree.trim() &&
            item.major.trim() &&
            item.start_date &&
            item.end_date,
        ),
      ),
    },
    {
      key: "experience",
      label: "工作或实习",
      detail: "至少 1 段",
      weight: 25,
      complete: hasWorkOrInternship,
    },
    {
      key: "project",
      label: "项目经历",
      detail: "至少 1 段",
      weight: 20,
      complete: draft.projects.some((item) =>
        Boolean(item.name.trim() && item.description.trim()),
      ),
    },
    {
      key: "skills",
      label: "技能",
      detail: "至少 3 项",
      weight: 10,
      complete:
        draft.skills.filter((item) => Boolean(item.skill_name.trim())).length >=
        3,
    },
    {
      key: "achievement",
      label: "成果描述",
      detail: "至少 1 段经历包含成果",
      weight: 15,
      complete: hasAchievement,
    },
  ];
  const score = items.reduce(
    (total, item) => total + (item.complete ? item.weight : 0),
    0,
  );

  return { score, items, isSparse: score < 50 };
}

export function formatResumeUpdatedAt(
  value: string,
  timeZone?: string,
): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "未知日期";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "long",
    day: "numeric",
    ...(timeZone ? { timeZone } : {}),
  }).format(date);
}
