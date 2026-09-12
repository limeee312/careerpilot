import type { Metadata } from "next";

import { ManualJobForm } from "@/components/job-match/manual-job-form";

export const metadata: Metadata = {
  title: "新建职位匹配 | 职航 CareerPilot",
};

export default function NewJobMatchPage() {
  return <ManualJobForm />;
}
