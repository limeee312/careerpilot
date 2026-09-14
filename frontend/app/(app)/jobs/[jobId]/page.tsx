import type { Metadata } from "next";

import { JobDetailView } from "@/components/job-match/job-detail-view";

export const metadata: Metadata = {
  title: "职位匹配详情 | 职航 CareerPilot",
};

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;

  return <JobDetailView jobId={jobId} key={jobId} />;
}
