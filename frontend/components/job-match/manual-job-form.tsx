"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import {
  buildJobBatchPayload,
  createEmptyJobBatch,
  createEmptyManualJob,
  type JobBatchData,
  type JobBatchDraft,
  type JobBatchEnvelope,
  type JobBatchValidationError,
  type JobField,
  validateJobBatch,
} from "@/lib/job";

const inputClassName =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100";

export function ManualJobForm() {
  const router = useRouter();
  const [draft, setDraft] = useState<JobBatchDraft>(() => createEmptyJobBatch());
  const [validationError, setValidationError] =
    useState<JobBatchValidationError | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedBatch, setSavedBatch] = useState<JobBatchData | null>(null);

  function updateJob(clientKey: string, field: JobField, value: string) {
    setDraft((current) => ({
      ...current,
      jobs: current.jobs.map((job) =>
        job.clientKey === clientKey ? { ...job, [field]: value } : job,
      ),
    }));
    setValidationError(null);
    setRequestError(null);
  }

  function addJob() {
    setDraft((current) => {
      if (current.jobs.length >= 5) {
        return current;
      }
      return { ...current, jobs: [...current.jobs, createEmptyManualJob()] };
    });
    setValidationError(null);
  }

  function removeJob(clientKey: string) {
    setDraft((current) => {
      if (current.jobs.length <= 1) {
        return current;
      }
      return {
        ...current,
        jobs: current.jobs.filter((job) => job.clientKey !== clientKey),
      };
    });
    setValidationError(null);
    setRequestError(null);
  }

  async function submitBatch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const error = validateJobBatch(draft);
    if (error) {
      setValidationError(error);
      return;
    }

    setValidationError(null);
    setRequestError(null);
    setIsSaving(true);

    try {
      const response = await apiRequest<JobBatchEnvelope>(
        "/job-match/batches",
        {
          method: "POST",
          body: JSON.stringify(buildJobBatchPayload(draft)),
        },
      );
      setSavedBatch(response.data);
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 401) {
        router.replace("/login");
        router.refresh();
        return;
      }
      setRequestError(
        error instanceof ApiError
          ? error.message
          : "职位批次保存失败，请稍后重试。",
      );
    } finally {
      setIsSaving(false);
    }
  }

  function startAnotherBatch() {
    setDraft(createEmptyJobBatch());
    setSavedBatch(null);
    setValidationError(null);
    setRequestError(null);
  }

  if (savedBatch) {
    return (
      <section className="rounded-3xl border border-emerald-200 bg-white px-6 py-12 text-center shadow-sm sm:px-10">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-2xl text-emerald-700">
          ✓
        </div>
        <p className="mt-5 text-sm font-semibold text-emerald-700">批次已保存</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
          {savedBatch.name ?? "未命名职位批次"}
        </h1>
        <p className="mx-auto mt-3 max-w-xl leading-7 text-slate-600">
          已原样保存 {savedBatch.total_jobs} 个职位，当前状态为 DRAFT。AI
          解析与匹配会在后续开发步骤接入，不会在此阶段伪造分析结果。
        </p>
        <dl className="mx-auto mt-7 grid max-w-lg gap-3 text-left sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 px-4 py-3">
            <dt className="text-xs text-slate-500">批次 ID</dt>
            <dd className="mt-1 break-all text-sm font-medium text-slate-800">
              {savedBatch.id}
            </dd>
          </div>
          <div className="rounded-xl bg-slate-50 px-4 py-3">
            <dt className="text-xs text-slate-500">已保存职位</dt>
            <dd className="mt-1 text-sm font-medium text-slate-800">
              {savedBatch.total_jobs} 个
            </dd>
          </div>
        </dl>
        <button
          className="mt-8 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
          onClick={startAnotherBatch}
          type="button"
        >
          新建另一个批次
        </button>
      </section>
    );
  }

  return (
    <form className="space-y-8" noValidate onSubmit={submitBatch}>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold text-blue-600">Manual import</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            新建职位匹配
          </h1>
          <p className="mt-3 leading-7 text-slate-600">
            一次粘贴 1–5 个真实职位 JD。系统会先完整保存原始内容，后续再逐步接入结构化解析和证据匹配。
          </p>
        </div>

        <label className="mt-7 block max-w-xl text-sm font-semibold text-slate-800">
          批次名称
          <span className="ml-2 font-normal text-slate-400">选填</span>
          <input
            className={inputClassName}
            maxLength={200}
            onChange={(event) => {
              setDraft((current) => ({ ...current, name: event.target.value }));
              setValidationError(null);
              setRequestError(null);
            }}
            placeholder="例如：秋招产品运营岗位比较"
            value={draft.name}
          />
        </label>
        <p className="mt-3 text-sm text-slate-500">
          当前 {draft.jobs.length}/5 个职位 · 公司名称、职位名称和 JD 为必填项
        </p>
      </section>

      <div className="space-y-6">
        {draft.jobs.map((job, index) => {
          const errorForJob =
            validationError?.jobIndex === index ? validationError : null;
          return (
            <section
              className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
              key={job.clientKey}
            >
              <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
                    Job {String(index + 1).padStart(2, "0")}
                  </p>
                  <h2 className="mt-1 text-xl font-semibold text-slate-950">
                    职位 {index + 1}
                  </h2>
                </div>
                {draft.jobs.length > 1 ? (
                  <button
                    className="rounded-lg px-3 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50"
                    onClick={() => removeJob(job.clientKey)}
                    type="button"
                  >
                    移除此职位
                  </button>
                ) : null}
              </div>

              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <JobInput
                  error={errorForJob?.field === "company_name"}
                  label="公司名称"
                  onChange={(value) =>
                    updateJob(job.clientKey, "company_name", value)
                  }
                  placeholder="例如：腾讯"
                  required
                  value={job.company_name}
                />
                <JobInput
                  error={errorForJob?.field === "title"}
                  label="职位名称"
                  onChange={(value) => updateJob(job.clientKey, "title", value)}
                  placeholder="例如：产品运营"
                  required
                  value={job.title}
                />
                <JobInput
                  label="城市"
                  onChange={(value) =>
                    updateJob(job.clientKey, "location", value)
                  }
                  placeholder="例如：深圳"
                  value={job.location}
                />
                <JobInput
                  label="部门"
                  onChange={(value) =>
                    updateJob(job.clientKey, "department", value)
                  }
                  placeholder="例如：用户增长"
                  value={job.department}
                />
                <div className="sm:col-span-2">
                  <JobInput
                    error={errorForJob?.field === "source_url"}
                    label="职位链接"
                    onChange={(value) =>
                      updateJob(job.clientKey, "source_url", value)
                    }
                    placeholder="https://example.com/job/123"
                    type="url"
                    value={job.source_url}
                  />
                </div>
                <label className="block text-sm font-semibold text-slate-800 sm:col-span-2">
                  <span className="flex items-center justify-between gap-4">
                    <span>
                      完整 JD <span className="text-red-500">*</span>
                    </span>
                    <span
                      className={`text-xs font-normal ${
                        job.raw_jd.trim().length >= 50
                          ? "text-emerald-600"
                          : "text-slate-400"
                      }`}
                    >
                      {job.raw_jd.trim().length}/50 字符起
                    </span>
                  </span>
                  <textarea
                    aria-invalid={errorForJob?.field === "raw_jd" || undefined}
                    className={`${inputClassName} min-h-56 resize-y leading-7`}
                    onChange={(event) =>
                      updateJob(job.clientKey, "raw_jd", event.target.value)
                    }
                    placeholder="请粘贴完整职位描述，包括职责、任职要求及优先条件。"
                    value={job.raw_jd}
                  />
                </label>
              </div>

              {errorForJob ? (
                <p className="mt-4 text-sm font-medium text-red-600" role="alert">
                  {errorForJob.message}
                </p>
              ) : null}
            </section>
          );
        })}
      </div>

      <section className="flex flex-col gap-5 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div>
          <button
            className="rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-semibold text-blue-700 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400 disabled:hover:bg-white"
            disabled={draft.jobs.length >= 5 || isSaving}
            onClick={addJob}
            type="button"
          >
            + 添加另一个职位
          </button>
          <p className="mt-2 text-xs text-slate-500">每个批次最多 5 个职位</p>
        </div>
        <div className="sm:text-right">
          {validationError?.jobIndex === null ? (
            <p className="mb-2 text-sm font-medium text-red-600" role="alert">
              {validationError.message}
            </p>
          ) : null}
          {requestError ? (
            <p className="mb-2 text-sm font-medium text-red-600" role="alert">
              {requestError}
            </p>
          ) : null}
          <button
            className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            disabled={isSaving}
            type="submit"
          >
            {isSaving ? "正在保存…" : "保存并准备分析"}
          </button>
        </div>
      </section>
    </form>
  );
}

type JobInputProps = {
  error?: boolean;
  label: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  type?: "text" | "url";
  value: string;
};

function JobInput({
  error = false,
  label,
  onChange,
  placeholder,
  required = false,
  type = "text",
  value,
}: JobInputProps) {
  return (
    <label className="block text-sm font-semibold text-slate-800">
      {label} {required ? <span className="text-red-500">*</span> : null}
      <input
        aria-invalid={error || undefined}
        className={inputClassName}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
    </label>
  );
}
