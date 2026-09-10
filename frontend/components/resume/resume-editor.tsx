"use client";

import { useRouter } from "next/navigation";
import {
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  buildResumePayload,
  calculateResumeCompleteness,
  createEmptyEducation,
  createEmptyExperience,
  createEmptyProject,
  createEmptyResume,
  createEmptySkill,
  type EducationDraft,
  type ExperienceDraft,
  type ProjectDraft,
  type ResumeBasicInfo,
  type ResumeDraft,
  type ResumeMasterEnvelope,
  resumeDataToDraft,
  type SkillDraft,
  validateResume,
} from "@/lib/resume";

type SectionKey =
  | "basic"
  | "education"
  | "experiences"
  | "projects"
  | "skills";

type SaveState = "idle" | "saving" | "saved" | "error";

const sectionDefinitions: Array<{
  key: SectionKey;
  label: string;
  description: string;
}> = [
  { key: "basic", label: "基本信息", description: "联系方式与职业概述" },
  { key: "education", label: "教育经历", description: "学校、专业与课程" },
  { key: "experiences", label: "工作与实习", description: "职责、行动与成果" },
  { key: "projects", label: "项目经历", description: "项目背景与个人贡献" },
  { key: "skills", label: "技能", description: "工具、语言与专业能力" },
];

const inputClassName =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 disabled:bg-slate-100 disabled:text-slate-500";

function replaceAt<T>(items: T[], index: number, item: T): T[] {
  return items.map((current, currentIndex) =>
    currentIndex === index ? item : current,
  );
}

function moveAt<T>(items: T[], index: number, direction: -1 | 1): T[] {
  const target = index + direction;
  if (target < 0 || target >= items.length) {
    return items;
  }

  const next = [...items];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function sectionCount(draft: ResumeDraft, section: SectionKey): number | null {
  if (section === "basic") {
    return null;
  }
  return draft[section].length;
}

function Field({
  children,
  htmlFor,
  label,
  required = false,
}: {
  children: ReactNode;
  htmlFor: string;
  label: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-slate-800" htmlFor={htmlFor}>
        {label}
        {required ? <span className="ml-1 text-red-500">*</span> : null}
      </label>
      {children}
    </div>
  );
}

function CardActions({
  canMoveDown,
  canMoveUp,
  itemLabel,
  onDelete,
  onMoveDown,
  onMoveUp,
}: {
  canMoveDown: boolean;
  canMoveUp: boolean;
  itemLabel: string;
  onDelete: () => void;
  onMoveDown: () => void;
  onMoveUp: () => void;
}) {
  const buttonClass =
    "rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-300";

  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <button
        aria-label={`上移${itemLabel}`}
        className={buttonClass}
        disabled={!canMoveUp}
        onClick={onMoveUp}
        type="button"
      >
        ↑ 上移
      </button>
      <button
        aria-label={`下移${itemLabel}`}
        className={buttonClass}
        disabled={!canMoveDown}
        onClick={onMoveDown}
        type="button"
      >
        ↓ 下移
      </button>
      <button
        aria-label={`删除${itemLabel}`}
        className="rounded-lg border border-red-200 bg-white px-2.5 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50"
        onClick={onDelete}
        type="button"
      >
        删除
      </button>
    </div>
  );
}

function EmptySection({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
      <p className="font-medium text-slate-700">暂时没有{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">
        添加真实信息后，它会成为岗位匹配与针对性简历的事实来源。
      </p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function AddButton({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return (
    <button
      className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:border-blue-300 hover:bg-blue-100"
      onClick={onClick}
      type="button"
    >
      + {children}
    </button>
  );
}

export function ResumeEditor() {
  const router = useRouter();
  const [draft, setDraft] = useState<ResumeDraft>(() => createEmptyResume());
  const [activeSection, setActiveSection] = useState<SectionKey>("basic");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [savedPayload, setSavedPayload] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);

  const payload = useMemo(() => buildResumePayload(draft), [draft]);
  const serializedPayload = useMemo(() => JSON.stringify(payload), [payload]);
  const isDirty = !isLoading && serializedPayload !== savedPayload;
  const completeness = useMemo(
    () => calculateResumeCompleteness(draft),
    [draft],
  );

  useEffect(() => {
    let cancelled = false;

    void apiRequest<ResumeMasterEnvelope>("/resume/master")
      .then((response) => {
        if (cancelled) {
          return;
        }
        const nextDraft = response.data
          ? resumeDataToDraft(response.data)
          : createEmptyResume();
        setDraft(nextDraft);
        setSavedPayload(JSON.stringify(buildResumePayload(nextDraft)));
        setSaveState("idle");
      })
      .catch((requestError: unknown) => {
        if (cancelled) {
          return;
        }
        if (requestError instanceof ApiError && requestError.status === 401) {
          router.replace("/login");
          router.refresh();
          return;
        }
        setLoadError(
          requestError instanceof ApiError
            ? requestError.message
            : "简历加载失败，请稍后重试。",
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
  }, [loadAttempt, router]);

  function retryLoad() {
    setIsLoading(true);
    setLoadError(null);
    setLoadAttempt((current) => current + 1);
  }

  useEffect(() => {
    function warnBeforeLeave(event: BeforeUnloadEvent) {
      if (!isDirty) {
        return;
      }
      event.preventDefault();
      event.returnValue = true;
    }

    window.addEventListener("beforeunload", warnBeforeLeave);
    return () => window.removeEventListener("beforeunload", warnBeforeLeave);
  }, [isDirty]);

  function markChanged() {
    setActionError(null);
    setSaveState("idle");
  }

  function updateBasicInfo(patch: Partial<ResumeBasicInfo>) {
    markChanged();
    setDraft((current) => ({
      ...current,
      basic_info: { ...current.basic_info, ...patch },
    }));
  }

  function updateEducation(index: number, patch: Partial<EducationDraft>) {
    markChanged();
    setDraft((current) => ({
      ...current,
      education: replaceAt(current.education, index, {
        ...current.education[index],
        ...patch,
      }),
    }));
  }

  function updateExperience(index: number, patch: Partial<ExperienceDraft>) {
    markChanged();
    setDraft((current) => ({
      ...current,
      experiences: replaceAt(current.experiences, index, {
        ...current.experiences[index],
        ...patch,
      }),
    }));
  }

  function updateProject(index: number, patch: Partial<ProjectDraft>) {
    markChanged();
    setDraft((current) => ({
      ...current,
      projects: replaceAt(current.projects, index, {
        ...current.projects[index],
        ...patch,
      }),
    }));
  }

  function updateSkill(index: number, patch: Partial<SkillDraft>) {
    markChanged();
    setDraft((current) => ({
      ...current,
      skills: replaceAt(current.skills, index, {
        ...current.skills[index],
        ...patch,
      }),
    }));
  }

  function addEducation() {
    markChanged();
    setDraft((current) => ({
      ...current,
      education: [...current.education, createEmptyEducation()],
    }));
  }

  function addExperience() {
    markChanged();
    setDraft((current) => ({
      ...current,
      experiences: [...current.experiences, createEmptyExperience()],
    }));
  }

  function addProject() {
    markChanged();
    setDraft((current) => ({
      ...current,
      projects: [...current.projects, createEmptyProject()],
    }));
  }

  function addSkill() {
    markChanged();
    setDraft((current) => ({
      ...current,
      skills: [...current.skills, createEmptySkill()],
    }));
  }

  function confirmDelete(label: string, remove: () => void) {
    if (!window.confirm(`确定删除${label}吗？保存后将无法恢复这条内容。`)) {
      return;
    }
    markChanged();
    remove();
  }

  function moveSection(
    section: "education" | "experiences" | "projects" | "skills",
    index: number,
    direction: -1 | 1,
  ) {
    markChanged();
    if (section === "education") {
      setDraft((current) => ({
        ...current,
        education: moveAt(current.education, index, direction),
      }));
    } else if (section === "experiences") {
      setDraft((current) => ({
        ...current,
        experiences: moveAt(current.experiences, index, direction),
      }));
    } else if (section === "projects") {
      setDraft((current) => ({
        ...current,
        projects: moveAt(current.projects, index, direction),
      }));
    } else {
      setDraft((current) => ({
        ...current,
        skills: moveAt(current.skills, index, direction),
      }));
    }
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActionError(null);

    const validationError = validateResume(draft);
    if (validationError) {
      setSaveState("error");
      setActiveSection(validationError.section);
      setActionError(validationError.message);
      return;
    }

    setSaveState("saving");

    try {
      const response = await apiRequest<ResumeMasterEnvelope>("/resume/master", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      if (!response.data) {
        throw new Error("保存响应缺少简历数据");
      }

      const savedDraft = resumeDataToDraft(response.data);
      setDraft(savedDraft);
      setSavedPayload(JSON.stringify(buildResumePayload(savedDraft)));
      setSaveState("saved");
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        router.replace("/login");
        router.refresh();
        return;
      }
      setSaveState("error");
      setActionError(
        requestError instanceof ApiError
          ? requestError.message
          : "保存失败，当前填写内容已保留，请重试。",
      );
    }
  }

  if (isLoading) {
    return (
      <div
        aria-live="polite"
        className="rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center shadow-sm"
      >
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
        <p className="mt-4 text-sm text-slate-600">正在加载简历母版…</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-white px-6 py-12 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-slate-950">简历暂时无法加载</h1>
        <p className="mt-3 text-sm text-red-700" role="alert">
          {loadError}
        </p>
        <button
          className="mt-6 rounded-xl bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          onClick={retryLoad}
          type="button"
        >
          重新加载
        </button>
      </div>
    );
  }

  const activeDefinition = sectionDefinitions.find(
    (item) => item.key === activeSection,
  )!;

  return (
    <form onSubmit={handleSave}>
      <div className="flex flex-col gap-5 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-blue-600">Resume Master</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
            编辑简历母版
          </h1>
          <p className="mt-3 max-w-2xl leading-7 text-slate-600">
            这里保存的是你的真实经历原始档案。之后的岗位匹配和简历优化都会以它为事实来源。
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-stretch gap-2 sm:items-end">
          <button
            className="min-w-32 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:bg-blue-300"
            disabled={saveState === "saving" || !isDirty}
            type="submit"
          >
            {saveState === "saving"
              ? "保存中…"
              : saveState === "saved" && !isDirty
                ? "保存成功 ✓"
                : isDirty
                  ? "保存"
                  : "已保存"}
          </button>
          <span
            aria-live="polite"
            className={`text-xs ${isDirty ? "text-amber-700" : "text-slate-500"}`}
          >
            {isDirty ? "有尚未保存的修改" : "所有修改均已保存"}
          </span>
        </div>
      </div>

      <fieldset
        className="m-0 min-w-0 border-0 p-0"
        disabled={saveState === "saving"}
      >
      {actionError ? (
        <div
          className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
        >
          {actionError} 当前填写内容仍保留在页面中。
        </div>
      ) : null}

      <div className="mt-7 grid gap-6 lg:grid-cols-[13.5rem_minmax(0,1fr)] xl:grid-cols-[13.5rem_minmax(0,1fr)_17rem]">
        <nav
          aria-label="简历分区"
          className="flex gap-2 overflow-x-auto pb-1 lg:block lg:space-y-2 lg:overflow-visible lg:pb-0"
        >
          {sectionDefinitions.map((section) => {
            const count = sectionCount(draft, section.key);
            const isActive = section.key === activeSection;
            return (
              <button
                aria-current={isActive ? "step" : undefined}
                className={`min-w-fit rounded-xl border px-4 py-3 text-left transition lg:w-full ${
                  isActive
                    ? "border-blue-200 bg-blue-50 text-blue-800 shadow-sm"
                    : "border-transparent text-slate-600 hover:border-slate-200 hover:bg-white"
                }`}
                key={section.key}
                onClick={() => setActiveSection(section.key)}
                type="button"
              >
                <span className="flex items-center justify-between gap-3 text-sm font-semibold">
                  {section.label}
                  {count !== null ? (
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        isActive
                          ? "bg-blue-100 text-blue-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {count}
                    </span>
                  ) : null}
                </span>
                <span className="mt-1 hidden text-xs leading-5 opacity-75 lg:block">
                  {section.description}
                </span>
              </button>
            );
          })}
        </nav>

        <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-950">
              {activeDefinition.label}
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              {activeDefinition.description}
            </p>
          </div>

          {activeSection === "basic" ? (
            <BasicInfoSection value={draft.basic_info} onChange={updateBasicInfo} />
          ) : null}
          {activeSection === "education" ? (
            <EducationSection
              items={draft.education}
              onAdd={addEducation}
              onChange={updateEducation}
              onDelete={(index) =>
                confirmDelete(`第 ${index + 1} 段教育经历`, () =>
                  setDraft((current) => ({
                    ...current,
                    education: current.education.filter((_, itemIndex) => itemIndex !== index),
                  })),
                )
              }
              onMove={(index, direction) =>
                moveSection("education", index, direction)
              }
            />
          ) : null}
          {activeSection === "experiences" ? (
            <ExperienceSection
              items={draft.experiences}
              onAdd={addExperience}
              onChange={updateExperience}
              onDelete={(index) =>
                confirmDelete(`第 ${index + 1} 段工作或实习经历`, () =>
                  setDraft((current) => ({
                    ...current,
                    experiences: current.experiences.filter(
                      (_, itemIndex) => itemIndex !== index,
                    ),
                  })),
                )
              }
              onMove={(index, direction) =>
                moveSection("experiences", index, direction)
              }
            />
          ) : null}
          {activeSection === "projects" ? (
            <ProjectSection
              items={draft.projects}
              onAdd={addProject}
              onChange={updateProject}
              onDelete={(index) =>
                confirmDelete(`第 ${index + 1} 个项目`, () =>
                  setDraft((current) => ({
                    ...current,
                    projects: current.projects.filter((_, itemIndex) => itemIndex !== index),
                  })),
                )
              }
              onMove={(index, direction) =>
                moveSection("projects", index, direction)
              }
            />
          ) : null}
          {activeSection === "skills" ? (
            <SkillSection
              items={draft.skills}
              onAdd={addSkill}
              onChange={updateSkill}
              onDelete={(index) =>
                confirmDelete(`技能“${draft.skills[index].skill_name || index + 1}”`, () =>
                  setDraft((current) => ({
                    ...current,
                    skills: current.skills.filter((_, itemIndex) => itemIndex !== index),
                  })),
                )
              }
              onMove={(index, direction) =>
                moveSection("skills", index, direction)
              }
            />
          ) : null}
        </section>

        <CompletenessPanel
          activeSection={activeSection}
          completeness={completeness}
          onSelectSection={setActiveSection}
        />
      </div>
      </fieldset>
    </form>
  );
}

function BasicInfoSection({
  onChange,
  value,
}: {
  onChange: (patch: Partial<ResumeBasicInfo>) => void;
  value: ResumeBasicInfo;
}) {
  return (
    <div className="grid gap-5 sm:grid-cols-2">
      <Field htmlFor="resume-name" label="姓名">
        <input
          autoComplete="name"
          className={inputClassName}
          id="resume-name"
          maxLength={100}
          onChange={(event) => onChange({ name: event.target.value })}
          placeholder="用于简历展示的姓名"
          value={value.name}
        />
      </Field>
      <Field htmlFor="resume-city" label="所在城市">
        <input
          autoComplete="address-level2"
          className={inputClassName}
          id="resume-city"
          maxLength={100}
          onChange={(event) => onChange({ city: event.target.value })}
          placeholder="例如：上海"
          value={value.city}
        />
      </Field>
      <Field htmlFor="resume-email" label="简历联系邮箱">
        <input
          autoComplete="email"
          className={inputClassName}
          id="resume-email"
          maxLength={320}
          onChange={(event) => onChange({ email: event.target.value })}
          placeholder="用于投递，可与账号邮箱不同"
          type="email"
          value={value.email}
        />
      </Field>
      <Field htmlFor="resume-phone" label="联系电话">
        <input
          autoComplete="tel"
          className={inputClassName}
          id="resume-phone"
          maxLength={50}
          onChange={(event) => onChange({ phone: event.target.value })}
          placeholder="手机号或其他联系电话"
          type="tel"
          value={value.phone}
        />
      </Field>
      <Field htmlFor="resume-status" label="当前求职状态">
        <input
          className={inputClassName}
          id="resume-status"
          maxLength={100}
          onChange={(event) => onChange({ job_status: event.target.value })}
          placeholder="例如：在职，考虑机会"
          value={value.job_status}
        />
      </Field>
      <div className="sm:col-span-2">
        <Field htmlFor="resume-summary" label="职业概述">
          <textarea
            className={`${inputClassName} min-h-32 resize-y leading-6`}
            id="resume-summary"
            onChange={(event) => onChange({ summary: event.target.value })}
            placeholder="概括你的经验方向、擅长领域与有证据支持的优势。"
            value={value.summary}
          />
        </Field>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          只写已经具备的真实能力；后续 AI 不会替你创造经历。
        </p>
      </div>
    </div>
  );
}

function EducationSection({
  items,
  onAdd,
  onChange,
  onDelete,
  onMove,
}: {
  items: EducationDraft[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<EducationDraft>) => void;
  onDelete: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  if (items.length === 0) {
    return (
      <EmptySection title="教育经历">
        <AddButton onClick={onAdd}>添加教育经历</AddButton>
      </EmptySection>
    );
  }

  return (
    <div className="space-y-5">
      {items.map((item, index) => (
        <article
          className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5"
          key={item.clientKey}
        >
          <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                Education {String(index + 1).padStart(2, "0")}
              </p>
              <h3 className="mt-1 font-semibold text-slate-900">
                {item.school || `教育经历 ${index + 1}`}
              </h3>
            </div>
            <CardActions
              canMoveDown={index < items.length - 1}
              canMoveUp={index > 0}
              itemLabel={`第 ${index + 1} 段教育经历`}
              onDelete={() => onDelete(index)}
              onMoveDown={() => onMove(index, 1)}
              onMoveUp={() => onMove(index, -1)}
            />
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <Field htmlFor={`${item.clientKey}-school`} label="学校" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-school`}
                maxLength={200}
                onChange={(event) => onChange(index, { school: event.target.value })}
                placeholder="学校名称"
                required
                value={item.school}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-major`} label="专业" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-major`}
                maxLength={200}
                onChange={(event) => onChange(index, { major: event.target.value })}
                placeholder="专业名称"
                required
                value={item.major}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-degree`} label="学历" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-degree`}
                maxLength={100}
                onChange={(event) => onChange(index, { degree: event.target.value })}
                placeholder="例如：本科"
                required
                value={item.degree}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-gpa`} label="GPA / 成绩">
              <input
                className={inputClassName}
                id={`${item.clientKey}-gpa`}
                maxLength={50}
                onChange={(event) => onChange(index, { gpa: event.target.value })}
                placeholder="例如：3.7 / 4.0"
                value={item.gpa}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-education-start`} label="开始年月" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-education-start`}
                onChange={(event) => onChange(index, { start_date: event.target.value })}
                required
                type="month"
                value={item.start_date}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-education-end`} label="结束年月" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-education-end`}
                min={item.start_date || undefined}
                onChange={(event) => onChange(index, { end_date: event.target.value })}
                required
                type="month"
                value={item.end_date}
              />
            </Field>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-courses`} label="相关课程">
                <textarea
                  className={`${inputClassName} min-h-24 resize-y leading-6`}
                  id={`${item.clientKey}-courses`}
                  onChange={(event) => onChange(index, { courses: event.target.value })}
                  placeholder="填写与目标方向相关的课程，可用换行分隔。"
                  value={item.courses}
                />
              </Field>
            </div>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-education-description`} label="补充说明">
                <textarea
                  className={`${inputClassName} min-h-24 resize-y leading-6`}
                  id={`${item.clientKey}-education-description`}
                  onChange={(event) =>
                    onChange(index, { description: event.target.value })
                  }
                  placeholder="奖项、研究方向或其他与求职相关的信息。"
                  value={item.description}
                />
              </Field>
            </div>
          </div>
        </article>
      ))}
      <AddButton onClick={onAdd}>添加教育经历</AddButton>
    </div>
  );
}

function ExperienceSection({
  items,
  onAdd,
  onChange,
  onDelete,
  onMove,
}: {
  items: ExperienceDraft[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<ExperienceDraft>) => void;
  onDelete: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  if (items.length === 0) {
    return (
      <EmptySection title="工作或实习经历">
        <AddButton onClick={onAdd}>添加工作或实习经历</AddButton>
      </EmptySection>
    );
  }

  return (
    <div className="space-y-5">
      {items.map((item, index) => (
        <article
          className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5"
          key={item.clientKey}
        >
          <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                Experience {String(index + 1).padStart(2, "0")}
              </p>
              <h3 className="mt-1 font-semibold text-slate-900">
                {item.organization || `工作或实习经历 ${index + 1}`}
              </h3>
            </div>
            <CardActions
              canMoveDown={index < items.length - 1}
              canMoveUp={index > 0}
              itemLabel={`第 ${index + 1} 段工作或实习经历`}
              onDelete={() => onDelete(index)}
              onMoveDown={() => onMove(index, 1)}
              onMoveUp={() => onMove(index, -1)}
            />
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <Field htmlFor={`${item.clientKey}-experience-type`} label="经历类型" required>
              <select
                className={inputClassName}
                id={`${item.clientKey}-experience-type`}
                onChange={(event) =>
                  onChange(index, {
                    experience_type: event.target.value as ExperienceDraft["experience_type"],
                  })
                }
                value={item.experience_type}
              >
                <option value="WORK">工作经历</option>
                <option value="INTERNSHIP">实习经历</option>
                <option value="CAMPUS">校园经历</option>
                <option value="OTHER">其他经历</option>
              </select>
            </Field>
            <Field htmlFor={`${item.clientKey}-organization`} label="组织 / 公司" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-organization`}
                maxLength={200}
                onChange={(event) =>
                  onChange(index, { organization: event.target.value })
                }
                placeholder="公司或组织名称"
                required
                value={item.organization}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-position`} label="职位 / 角色" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-position`}
                maxLength={200}
                onChange={(event) => onChange(index, { position: event.target.value })}
                placeholder="你的真实职位或角色"
                required
                value={item.position}
              />
            </Field>
            <div className="hidden sm:block" />
            <Field htmlFor={`${item.clientKey}-experience-start`} label="开始年月" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-experience-start`}
                onChange={(event) => onChange(index, { start_date: event.target.value })}
                required
                type="month"
                value={item.start_date}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-experience-end`} label="结束年月" required={!item.is_current}>
              <input
                className={inputClassName}
                disabled={item.is_current}
                id={`${item.clientKey}-experience-end`}
                min={item.start_date || undefined}
                onChange={(event) => onChange(index, { end_date: event.target.value })}
                required={!item.is_current}
                type="month"
                value={item.end_date}
              />
              <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
                <input
                  checked={item.is_current}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600"
                  onChange={(event) =>
                    onChange(index, {
                      is_current: event.target.checked,
                      end_date: event.target.checked ? "" : item.end_date,
                    })
                  }
                  type="checkbox"
                />
                至今
              </label>
            </Field>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-experience-description`} label="职责与行动" required>
                <textarea
                  className={`${inputClassName} min-h-32 resize-y leading-6`}
                  id={`${item.clientKey}-experience-description`}
                  onChange={(event) =>
                    onChange(index, { description: event.target.value })
                  }
                  placeholder="写清你负责什么、采用了什么方法；不要把团队成果写成个人成果。"
                  required
                  value={item.description}
                />
              </Field>
            </div>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-experience-achievements`} label="成果与交付">
                <textarea
                  className={`${inputClassName} min-h-28 resize-y leading-6`}
                  id={`${item.clientKey}-experience-achievements`}
                  onChange={(event) =>
                    onChange(index, { achievements: event.target.value })
                  }
                  placeholder="填写真实发生且可解释的结果；没有数据时不必创造数字。"
                  value={item.achievements}
                />
              </Field>
            </div>
          </div>
        </article>
      ))}
      <AddButton onClick={onAdd}>添加工作或实习经历</AddButton>
    </div>
  );
}

function ProjectSection({
  items,
  onAdd,
  onChange,
  onDelete,
  onMove,
}: {
  items: ProjectDraft[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<ProjectDraft>) => void;
  onDelete: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  if (items.length === 0) {
    return (
      <EmptySection title="项目经历">
        <AddButton onClick={onAdd}>添加项目经历</AddButton>
      </EmptySection>
    );
  }

  return (
    <div className="space-y-5">
      {items.map((item, index) => (
        <article
          className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5"
          key={item.clientKey}
        >
          <div className="flex flex-col gap-3 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                Project {String(index + 1).padStart(2, "0")}
              </p>
              <h3 className="mt-1 font-semibold text-slate-900">
                {item.name || `项目经历 ${index + 1}`}
              </h3>
            </div>
            <CardActions
              canMoveDown={index < items.length - 1}
              canMoveUp={index > 0}
              itemLabel={`第 ${index + 1} 个项目`}
              onDelete={() => onDelete(index)}
              onMoveDown={() => onMove(index, 1)}
              onMoveUp={() => onMove(index, -1)}
            />
          </div>
          <div className="mt-5 grid gap-5 sm:grid-cols-2">
            <Field htmlFor={`${item.clientKey}-project-name`} label="项目名称" required>
              <input
                className={inputClassName}
                id={`${item.clientKey}-project-name`}
                maxLength={200}
                onChange={(event) => onChange(index, { name: event.target.value })}
                placeholder="项目名称"
                required
                value={item.name}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-project-role`} label="项目角色">
              <input
                className={inputClassName}
                id={`${item.clientKey}-project-role`}
                maxLength={200}
                onChange={(event) => onChange(index, { role: event.target.value })}
                placeholder="例如：产品负责人"
                value={item.role}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-project-start`} label="开始年月">
              <input
                className={inputClassName}
                id={`${item.clientKey}-project-start`}
                onChange={(event) => onChange(index, { start_date: event.target.value })}
                type="month"
                value={item.start_date}
              />
            </Field>
            <Field htmlFor={`${item.clientKey}-project-end`} label="结束年月">
              <input
                className={inputClassName}
                id={`${item.clientKey}-project-end`}
                min={item.start_date || undefined}
                onChange={(event) => onChange(index, { end_date: event.target.value })}
                type="month"
                value={item.end_date}
              />
            </Field>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-project-background`} label="项目背景">
                <textarea
                  className={`${inputClassName} min-h-24 resize-y leading-6`}
                  id={`${item.clientKey}-project-background`}
                  onChange={(event) =>
                    onChange(index, { background: event.target.value })
                  }
                  placeholder="说明问题、目标或业务背景。"
                  value={item.background}
                />
              </Field>
            </div>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-project-description`} label="个人行动与贡献" required>
                <textarea
                  className={`${inputClassName} min-h-32 resize-y leading-6`}
                  id={`${item.clientKey}-project-description`}
                  onChange={(event) =>
                    onChange(index, { description: event.target.value })
                  }
                  placeholder="写清你的实际参与范围、采用的方法和交付内容。"
                  required
                  value={item.description}
                />
              </Field>
            </div>
            <div className="sm:col-span-2">
              <Field htmlFor={`${item.clientKey}-project-achievements`} label="成果">
                <textarea
                  className={`${inputClassName} min-h-28 resize-y leading-6`}
                  id={`${item.clientKey}-project-achievements`}
                  onChange={(event) =>
                    onChange(index, { achievements: event.target.value })
                  }
                  placeholder="记录真实结果、交付或当前项目状态。"
                  value={item.achievements}
                />
              </Field>
            </div>
          </div>
        </article>
      ))}
      <AddButton onClick={onAdd}>添加项目经历</AddButton>
    </div>
  );
}

function SkillSection({
  items,
  onAdd,
  onChange,
  onDelete,
  onMove,
}: {
  items: SkillDraft[];
  onAdd: () => void;
  onChange: (index: number, patch: Partial<SkillDraft>) => void;
  onDelete: (index: number) => void;
  onMove: (index: number, direction: -1 | 1) => void;
}) {
  if (items.length === 0) {
    return (
      <EmptySection title="技能">
        <AddButton onClick={onAdd}>添加技能</AddButton>
      </EmptySection>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <article
          className="rounded-2xl border border-slate-200 bg-slate-50/70 p-5"
          key={item.clientKey}
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="grid min-w-0 flex-1 gap-4 sm:grid-cols-3">
              <Field htmlFor={`${item.clientKey}-skill-name`} label="技能名称" required>
                <input
                  className={inputClassName}
                  id={`${item.clientKey}-skill-name`}
                  maxLength={150}
                  onChange={(event) =>
                    onChange(index, { skill_name: event.target.value })
                  }
                  placeholder="例如：SQL"
                  required
                  value={item.skill_name}
                />
              </Field>
              <Field htmlFor={`${item.clientKey}-skill-category`} label="分类">
                <input
                  className={inputClassName}
                  id={`${item.clientKey}-skill-category`}
                  maxLength={100}
                  onChange={(event) =>
                    onChange(index, { skill_category: event.target.value })
                  }
                  placeholder="例如：数据工具"
                  value={item.skill_category}
                />
              </Field>
              <Field htmlFor={`${item.clientKey}-skill-proficiency`} label="熟练程度">
                <input
                  className={inputClassName}
                  id={`${item.clientKey}-skill-proficiency`}
                  maxLength={50}
                  onChange={(event) =>
                    onChange(index, { proficiency: event.target.value })
                  }
                  placeholder="按真实水平填写"
                  value={item.proficiency}
                />
              </Field>
            </div>
            <CardActions
              canMoveDown={index < items.length - 1}
              canMoveUp={index > 0}
              itemLabel={`第 ${index + 1} 项技能`}
              onDelete={() => onDelete(index)}
              onMoveDown={() => onMove(index, 1)}
              onMoveUp={() => onMove(index, -1)}
            />
          </div>
        </article>
      ))}
      <AddButton onClick={onAdd}>添加技能</AddButton>
    </div>
  );
}

function CompletenessPanel({
  activeSection,
  completeness,
  onSelectSection,
}: {
  activeSection: SectionKey;
  completeness: ReturnType<typeof calculateResumeCompleteness>;
  onSelectSection: (section: SectionKey) => void;
}) {
  const itemSections: Record<string, SectionKey> = {
    basic: "basic",
    education: "education",
    experience: "experiences",
    project: "projects",
    skills: "skills",
    achievement: "experiences",
  };

  return (
    <aside className="lg:col-start-2 xl:col-start-auto">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-500">简历完整度</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950">
              {completeness.score}%
            </p>
          </div>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            实时计算
          </span>
        </div>
        <div
          aria-label={`简历完整度 ${completeness.score}%`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={completeness.score}
          className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"
          role="progressbar"
        >
          <div
            className="h-full rounded-full bg-blue-600 transition-all"
            style={{ width: `${completeness.score}%` }}
          />
        </div>

        {completeness.isSparse ? (
          <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-800">
            简历信息较少，可能影响匹配结果准确性，但不会阻止后续操作。
          </p>
        ) : null}

        <ul className="mt-5 space-y-2">
          {completeness.items.map((item) => {
            const section = itemSections[item.key];
            return (
              <li key={item.key}>
                <button
                  className={`flex w-full items-start gap-3 rounded-xl px-2.5 py-2 text-left transition hover:bg-slate-50 ${
                    activeSection === section ? "bg-slate-50" : ""
                  }`}
                  onClick={() => onSelectSection(section)}
                  type="button"
                >
                  <span
                    aria-hidden="true"
                    className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      item.complete
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {item.complete ? "✓" : "·"}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex justify-between gap-2 text-xs font-medium text-slate-700">
                      <span>{item.label}</span>
                      <span>+{item.weight}%</span>
                    </span>
                    <span className="mt-0.5 block text-xs leading-5 text-slate-500">
                      {item.detail}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}
