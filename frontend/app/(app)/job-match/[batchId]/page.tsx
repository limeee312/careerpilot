import type { Metadata } from "next";

import { MatchResultView } from "@/components/job-match/match-result-view";

export const metadata: Metadata = {
  title: "匹配结果 | 职航 CareerPilot",
};

export default async function MatchResultPage({
  params,
}: {
  params: Promise<{ batchId: string }>;
}) {
  const { batchId } = await params;

  return <MatchResultView batchId={batchId} key={batchId} />;
}
