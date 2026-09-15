import type { Metadata } from "next";

import { ResumeTailorView } from "@/components/resume/resume-tailor-view";

export const metadata: Metadata = {
  title: "针对性简历 | 职航 CareerPilot",
};

export default async function ResumeTailorPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;

  return <ResumeTailorView jobId={jobId} key={jobId} />;
}
