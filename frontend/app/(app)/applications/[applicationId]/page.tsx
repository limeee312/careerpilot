import type { Metadata } from "next";

import { ApplicationTimeline } from "@/components/application/application-timeline";

export const metadata: Metadata = {
  title: "投递详情 | 职航 CareerPilot",
};

export default async function ApplicationTimelinePage({
  params,
}: {
  params: Promise<{ applicationId: string }>;
}) {
  const { applicationId } = await params;

  return <ApplicationTimeline applicationId={applicationId} key={applicationId} />;
}
