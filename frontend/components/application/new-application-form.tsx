"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import type { ApplicationEnvelope } from "@/lib/application";
import type { JobMatchDetailData, JobMatchDetailEnvelope } from "@/lib/job-detail";
import type { ResumeVersionListEnvelope, ResumeVersionListItem } from "@/lib/resume-version";

function localDate() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function NewApplicationForm({
  jobId,
  preferredVersionId,
}: {
  jobId: string;
  preferredVersionId: string;
}) {
  const router = useRouter();
  const [job, setJob] = useState<JobMatchDetailData | null>(null);
  const [versions, setVersions] = useState<ResumeVersionListItem[]>([]);
  const [versionId, setVersionId] = useState(preferredVersionId);
  const [appliedAt, setAppliedAt] = useState(localDate);
  const [note, setNote] = useState("");
  const [isLoading, setIsLoading] = useState(Boolean(jobId));
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    void Promise.all([
      apiRequest<JobMatchDetailEnvelope>(`/jobs/${jobId}`),
      apiRequest<ResumeVersionListEnvelope>("/resume/versions"),
    ])
      .then(([jobResponse, versionResponse]) => {
        if (cancelled) return;
        setJob(jobResponse.data);
        const available = versionResponse.data.filter((item) => item.job_id === jobId);
        setVersions(available);
        if (!available.some((item) => item.id === preferredVersionId)) setVersionId("");
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        if (reason instanceof ApiError && reason.status === 401) {
          router.replace("/login");
          return;
        }
        setError(reason instanceof ApiError ? reason.message : "职位信息加载失败，请稍后重试。");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => { cancelled = true; };
  }, [jobId, preferredVersionId, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!job || !appliedAt) return;
    setError(null);
    setIsSaving(true);
    try {
      const response = await apiRequest<ApplicationEnvelope>("/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: job.job_id,
          resume_version_id: versionId || null,
          applied_at: appliedAt,
          note: note.trim() || null,
        }),
      });
      router.push(`/applications/${response.data.id}`);
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.status === 401) {
        router.replace("/login");
        return;
      }
      setError(reason instanceof ApiError ? reason.message : "创建投递记录失败，请稍后重试。");
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link className="text-sm font-semibold text-blue-700" href={jobId ? `/jobs/${jobId}` : "/applications"}>
        ← 返回职位
      </Link>
      <h1 className="mt-5 text-3xl font-semibold text-slate-950">创建投递记录</h1>
      {isLoading ? <p className="mt-6 text-slate-600">正在加载职位…</p> : null}
      {!jobId ? <p className="mt-6 text-slate-600">请从职位详情选择要记录的岗位。</p> : null}
      {job ? (
        <form className="mt-7 space-y-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8" onSubmit={submit}>
          <div>
            <p className="text-sm text-slate-500">投递职位</p>
            <p className="mt-1 text-xl font-semibold text-slate-950">{job.company_name} · {job.title}</p>
          </div>
          <div>
            <label className="text-sm font-semibold text-slate-800" htmlFor="resume-version">岗位版简历</label>
            <select
              className="mt-2 block w-full rounded-xl border border-slate-300 bg-white px-4 py-3"
              id="resume-version"
              onChange={(event) => setVersionId(event.target.value)}
              value={versionId}
            >
              <option value="">不关联简历版本</option>
              {versions.map((version) => <option key={version.id} value={version.id}>{version.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-semibold text-slate-800" htmlFor="applied-at">投递日期</label>
            <input className="mt-2 block w-full rounded-xl border border-slate-300 px-4 py-3" id="applied-at" onChange={(event) => setAppliedAt(event.target.value)} required type="date" value={appliedAt} />
          </div>
          <div>
            <label className="text-sm font-semibold text-slate-800" htmlFor="application-note">备注</label>
            <textarea className="mt-2 block min-h-24 w-full rounded-xl border border-slate-300 px-4 py-3" id="application-note" onChange={(event) => setNote(event.target.value)} value={note} />
          </div>
          {error ? <p className="text-sm text-red-700" role="alert">{error}</p> : null}
          <button className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white disabled:bg-blue-300" disabled={isSaving} type="submit">
            {isSaving ? "正在创建…" : "确认创建投递"}
          </button>
        </form>
      ) : error ? <p className="mt-6 text-red-700" role="alert">{error}</p> : null}
    </div>
  );
}
